import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_error.dart';
import 'auth/auth.dart';
import 'config.dart';
import 'service_notice.dart';

/// Creates the HTTP client used for all API calls.
///
/// `baseUrl` already ends with `/api/v1`, so request paths are e.g. `/health`.
Dio createApiClient({String? baseUrl}) {
  return Dio(
    BaseOptions(
      baseUrl: baseUrl ?? AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      responseType: ResponseType.json,
      // FastAPI list parameters: `status=a&status=b`.
      listFormat: ListFormat.multi,
      headers: const {'Accept': 'application/json, application/problem+json'},
    ),
  );
}

/// What [AuthInterceptor] needs from the session (implemented over
/// [AuthController]; an interface so the interceptor is unit-testable).
abstract interface class SessionHooks {
  AuthToken? get token;
  DateTime now();

  /// New tokens of the same session (`POST /auth/refresh`).
  void tokensRefreshed(AuthToken token);

  /// The session cannot continue: back to the login screen with [notice].
  void sessionEnded(String notice);

  /// 403 `auth.password_change_required` (ADR 0018 §5).
  void passwordChangeRequired();

  /// 429 `request.rate_limited` / 503 `api.unavailable` (ADR 0019 §8).
  void serviceProblem(ApiProblem problem);
}

/// Bearer token, token refresh and the session-level answers of the API
/// (ADR 0018 §10):
///
/// * every request except the public `/auth/login`, `/auth/refresh` and
///   `/auth/dev/*` carries `Authorization: Bearer …`;
/// * local accounts: an access token about to expire is refreshed BEFORE the
///   request; a 401 `auth.invalid_token` triggers one refresh and one repeat
///   of the request;
/// * refresh is single-flight per tab: concurrent requests wait for the one
///   `POST /auth/refresh` in progress — two refreshes with the same one-time
///   token would look like token theft and end the session on the server;
/// * 401 `auth.session_expired`, a failed refresh or any other 401 → login;
///   403 `auth.user_inactive` → login with a notice; 403
///   `auth.password_change_required` → forced password change.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.dio, required this.hooks});

  /// The client this interceptor is installed in (refresh and repeat).
  final Dio dio;
  final SessionHooks hooks;

  Future<AuthToken>? _refreshing;

  static const String _tokenKey = 'auth.access_token';
  static const String _retriedKey = 'auth.retried';

  /// Public endpoints: no bearer, no session handling of their answers.
  static bool isPublic(RequestOptions options) {
    final path = options.path;
    return path == '/auth/login' ||
        path == '/auth/refresh' ||
        path.startsWith('/auth/dev/');
  }

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (isPublic(options)) return handler.next(options);
    var token = hooks.token;
    if (token != null &&
        token.isLocalAccount &&
        token.isExpiredAt(hooks.now())) {
      try {
        token = await refresh(usedAccessToken: token.accessToken);
      } on DioException catch (error) {
        return handler.reject(_asErrorOf(options, error));
      }
    }
    if (token != null) {
      options.headers['Authorization'] = 'Bearer ${token.accessToken}';
      options.extra[_tokenKey] = token.accessToken;
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final status = err.response?.statusCode;
    if (status == null) return handler.next(err);
    final problem = ApiProblem.from(err);
    if (isPublic(options)) return handler.next(err);

    if (status == 429 && problem.code == 'request.rate_limited' ||
        status == 503 && problem.code == 'api.unavailable') {
      hooks.serviceProblem(problem);
      return handler.next(err);
    }

    if (status == 401) {
      final token = hooks.token;
      final used = options.extra[_tokenKey];
      if (problem.code == 'auth.invalid_token' &&
          token != null &&
          token.isLocalAccount &&
          used is String &&
          options.extra[_retriedKey] != true) {
        try {
          await refresh(usedAccessToken: used);
          final response = await dio.fetch<dynamic>(_retryOf(options));
          return handler.resolve(response);
        } on DioException catch (error) {
          return handler.next(error);
        }
      }
      hooks.sessionEnded(
        problem.code == 'auth.session_expired' ||
                problem.code == 'auth.invalid_refresh_token'
            ? SessionNotices.ended
            : SessionNotices.expired,
      );
      return handler.next(err);
    }

    if (status == 403 && problem.code == 'auth.user_inactive') {
      hooks.sessionEnded(SessionNotices.inactive);
    } else if (status == 403 &&
        problem.code == 'auth.password_change_required') {
      hooks.passwordChangeRequired();
    }
    handler.next(err);
  }

  /// Fresh tokens for a request that used [usedAccessToken].
  ///
  /// When another request already refreshed the session, its (still valid)
  /// token is returned without a new refresh; otherwise every caller shares
  /// the single `POST /auth/refresh` in progress. Throws [DioException] when
  /// the refresh fails; a refusal (4xx other than 429) ends the session.
  Future<AuthToken> refresh({required String usedAccessToken}) {
    final current = hooks.token;
    if (current != null &&
        current.accessToken != usedAccessToken &&
        !current.isExpiredAt(hooks.now())) {
      return Future.value(current);
    }
    final inFlight = _refreshing;
    if (inFlight != null) return inFlight;
    final started = _refresh(current);
    _refreshing = started;
    // Cleared after every waiter got the result (they attached already).
    started.then<void>((_) {}, onError: (Object _) {}).whenComplete(() {
      if (identical(_refreshing, started)) _refreshing = null;
    });
    return started;
  }

  Future<AuthToken> _refresh(AuthToken? current) async {
    final options = RequestOptions(path: '/auth/refresh', method: 'POST');
    final refreshToken = current?.refreshToken;
    if (current == null ||
        refreshToken == null ||
        !current.canRefreshAt(hooks.now())) {
      hooks.sessionEnded(SessionNotices.ended);
      throw _sessionEndedError(options);
    }
    try {
      final response = await dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final token = AuthToken.fromResponse(
        response.data ?? const {},
        hooks.now(),
      );
      hooks.tokensRefreshed(token);
      return token;
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      // 401 auth.invalid_refresh_token (or any refusal): log in again.
      // Network errors, 429 and 5xx keep the session (try again later).
      if (status != null && status >= 400 && status < 500 && status != 429) {
        hooks.sessionEnded(
          ApiProblem.from(error).code == 'auth.temporary_password_expired'
              ? SessionNotices.temporaryPasswordExpired
              : SessionNotices.ended,
        );
      }
      rethrow;
    }
  }

  static RequestOptions _retryOf(RequestOptions options) {
    final data = options.data;
    return options.copyWith(
      // A multipart body is consumed by the first attempt.
      data: data is FormData ? data.clone() : data,
      extra: {...options.extra, _retriedKey: true},
    );
  }

  static DioException _sessionEndedError(RequestOptions options) =>
      DioException(
        requestOptions: options,
        type: DioExceptionType.badResponse,
        response: Response<Map<String, dynamic>>(
          requestOptions: options,
          statusCode: 401,
          data: const {
            'status': 401,
            'code': 'auth.session_expired',
            'detail': SessionNotices.ended,
          },
        ),
      );

  /// The refresh failure reported as the error of the original request.
  static DioException _asErrorOf(RequestOptions options, DioException error) =>
      DioException(
        requestOptions: options,
        type: error.type,
        response: error.response,
        error: error.error,
        message: error.message,
      );
}

class _ControllerHooks implements SessionHooks {
  _ControllerHooks(this._ref);

  final Ref _ref;

  AuthController get _controller => _ref.read(authControllerProvider.notifier);

  @override
  AuthToken? get token => _ref.read(authControllerProvider).token;

  @override
  DateTime now() => _ref.read(clockProvider)();

  @override
  void tokensRefreshed(AuthToken token) => _controller.updateTokens(token);

  @override
  void sessionEnded(String notice) =>
      _controller.sessionExpired(notice: notice);

  @override
  void passwordChangeRequired() => _controller.setMustChangePassword(true);

  @override
  void serviceProblem(ApiProblem problem) =>
      _ref.read(serviceNoticeProvider.notifier).report(problem);
}

/// Transport override for tests (fake adapter); null = the platform default.
final httpClientAdapterProvider = Provider<HttpClientAdapter?>((ref) => null);

final apiBaseUrlProvider = Provider<String>((ref) => AppConfig.apiBaseUrl);

final apiClientProvider = Provider<Dio>((ref) {
  final dio = createApiClient(baseUrl: ref.watch(apiBaseUrlProvider));
  final adapter = ref.watch(httpClientAdapterProvider);
  if (adapter != null) dio.httpClientAdapter = adapter;
  dio.interceptors.add(AuthInterceptor(dio: dio, hooks: _ControllerHooks(ref)));
  ref.onDispose(dio.close);
  return dio;
});
