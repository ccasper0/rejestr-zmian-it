import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../api_client.dart';
import '../config.dart';
import 'token_storage.dart';

part 'auth.freezed.dart';
part 'auth.g.dart';

/// Tokens of the current session.
///
/// Dev login (`POST /auth/dev/token`, `TokenOut`): an access token only.
/// Local accounts (`POST /auth/login`, `/auth/refresh`, `/auth/password`,
/// `SessionTokensOut`, ADR 0018 §4): also a one-time refresh token, its idle
/// expiry, the absolute end of the session and `must_change_password`.
@immutable
class AuthToken {
  const AuthToken({
    required this.accessToken,
    required this.expiresAt,
    this.refreshToken,
    this.refreshExpiresAt,
    this.sessionExpiresAt,
    this.mustChangePassword = false,
  });

  /// Token from `TokenOut` / `SessionTokensOut` (`expires_in` and
  /// `refresh_expires_in` in seconds), relative to [now].
  factory AuthToken.fromResponse(Map<String, dynamic> json, DateTime now) {
    final utc = now.toUtc();
    final refresh = json['refresh_token'];
    final refreshIn = (json['refresh_expires_in'] as num?)?.toInt();
    return AuthToken(
      accessToken: json['access_token'] as String,
      expiresAt: utc.add(
        Duration(seconds: (json['expires_in'] as num?)?.toInt() ?? 0),
      ),
      refreshToken: refresh is String && refresh.isNotEmpty ? refresh : null,
      refreshExpiresAt: refreshIn == null
          ? null
          : utc.add(Duration(seconds: refreshIn)),
      sessionExpiresAt: DateTime.tryParse('${json['session_expires_at']}')
          ?.toUtc(),
      mustChangePassword: json['must_change_password'] == true,
    );
  }

  final String accessToken;
  final DateTime expiresAt;

  /// One-time refresh token (local accounts only; rotated on every refresh).
  final String? refreshToken;
  final DateTime? refreshExpiresAt;
  final DateTime? sessionExpiresAt;

  /// A temporary password must be changed before anything else.
  final bool mustChangePassword;

  /// Local account session (refreshable, password can be changed).
  bool get isLocalAccount => refreshToken != null;

  /// Treated as expired a minute early (clock skew, in-flight requests).
  bool isExpiredAt(DateTime now) =>
      !now.toUtc().isBefore(expiresAt.subtract(const Duration(minutes: 1)));

  /// Whether a refresh can still succeed (token present, not idle-expired,
  /// the session's absolute limit not reached).
  bool canRefreshAt(DateTime now) {
    if (refreshToken == null) return false;
    final utc = now.toUtc();
    if (refreshExpiresAt case final at? when !utc.isBefore(at)) return false;
    if (sessionExpiresAt case final at? when !utc.isBefore(at)) return false;
    return true;
  }

  AuthToken copyWith({bool? mustChangePassword}) => AuthToken(
    accessToken: accessToken,
    expiresAt: expiresAt,
    refreshToken: refreshToken,
    refreshExpiresAt: refreshExpiresAt,
    sessionExpiresAt: sessionExpiresAt,
    mustChangePassword: mustChangePassword ?? this.mustChangePassword,
  );

  String encode() => jsonEncode({
    'access_token': accessToken,
    'expires_at': expiresAt.toUtc().toIso8601String(),
    if (refreshToken != null) 'refresh_token': refreshToken,
    if (refreshExpiresAt != null)
      'refresh_expires_at': refreshExpiresAt!.toUtc().toIso8601String(),
    if (sessionExpiresAt != null)
      'session_expires_at': sessionExpiresAt!.toUtc().toIso8601String(),
    'must_change_password': mustChangePassword,
  });

  static AuthToken? decode(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    try {
      final json = jsonDecode(raw);
      if (json is! Map) return null;
      final token = json['access_token'];
      final expires = DateTime.tryParse('${json['expires_at']}');
      if (token is! String || token.isEmpty || expires == null) return null;
      final refresh = json['refresh_token'];
      return AuthToken(
        accessToken: token,
        expiresAt: expires.toUtc(),
        refreshToken: refresh is String && refresh.isNotEmpty ? refresh : null,
        refreshExpiresAt: DateTime.tryParse('${json['refresh_expires_at']}')
            ?.toUtc(),
        sessionExpiresAt: DateTime.tryParse('${json['session_expires_at']}')
            ?.toUtc(),
        mustChangePassword: json['must_change_password'] == true,
      );
    } on FormatException {
      return null;
    }
  }
}

/// Signed in ([token] set) or signed out (optionally with a [notice] for the
/// login screen, e.g. "session expired").
///
/// [epoch] changes with every new session (login, password change) but not
/// when the tokens of the same session are refreshed — data that depends on
/// who is signed in (`GET /me`) is keyed by it, not by the access token.
@immutable
class AuthState {
  const AuthState.signedIn(AuthToken this.token, {this.epoch = 0})
    : notice = null;
  const AuthState.signedOut({this.notice, this.epoch = 0}) : token = null;

  final AuthToken? token;
  final String? notice;
  final int epoch;

  bool get isSignedIn => token != null;

  bool get mustChangePassword => token?.mustChangePassword ?? false;
}

/// Messages of the login screen after the session ended.
abstract final class SessionNotices {
  static const String expired = 'Sesja wygasła. Zaloguj się ponownie.';
  static const String ended =
      'Sesja wygasła lub została zakończona. Zaloguj się ponownie.';
  static const String inactive =
      'Twoje konto jest nieaktywne. Skontaktuj się z administratorem.';

  /// Refresh of a session opened with a temporary password after its
  /// deadline (401 `auth.temporary_password_expired`, ADR 0020 §9).
  static const String temporaryPasswordExpired =
      'Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie '
      'hasła.';
}

/// Clock used for token expiry (overridable in tests).
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => createTokenStorage(),
);

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() {
    final storage = ref.watch(tokenStorageProvider);
    final token = AuthToken.decode(storage.read());
    final now = ref.read(clockProvider)();
    // An expired access token of a local account is fine while the session
    // can still be refreshed (the first request refreshes it).
    if (token == null || (token.isExpiredAt(now) && !token.canRefreshAt(now))) {
      storage.clear();
      return const AuthState.signedOut();
    }
    return AuthState.signedIn(token);
  }

  /// A new session (login, or the new pair after a password change).
  void signIn(AuthToken token) {
    ref.read(tokenStorageProvider).write(token.encode());
    state = AuthState.signedIn(token, epoch: state.epoch + 1);
  }

  /// New tokens of the SAME session (refresh rotation).
  void updateTokens(AuthToken token) {
    if (!state.isSignedIn) return;
    ref.read(tokenStorageProvider).write(token.encode());
    state = AuthState.signedIn(token, epoch: state.epoch);
  }

  /// Clears the session locally (no API call).
  void signOut({String? notice}) {
    ref.read(tokenStorageProvider).clear();
    state = AuthState.signedOut(notice: notice, epoch: state.epoch + 1);
  }

  /// "Wyloguj": ends the session on the server too (local accounts,
  /// `POST /auth/logout`), then clears it here — also when the API call
  /// fails (the tokens are forgotten either way).
  Future<void> logout() async {
    final token = state.token;
    if (token != null && token.isLocalAccount) {
      try {
        await ref
            .read(apiClientProvider)
            .post<void>('/auth/logout')
            .timeout(const Duration(seconds: 5));
      } on Object {
        // Best effort: the session expires on the server anyway.
      }
    }
    signOut();
  }

  /// The API answered 401: the token expired or was revoked.
  void sessionExpired({String notice = SessionNotices.expired}) {
    if (!state.isSignedIn) return;
    signOut(notice: notice);
  }

  /// `must_change_password` from `GET /me` or 403
  /// `auth.password_change_required` (ADR 0018 §5).
  void setMustChangePassword(bool value) {
    final token = state.token;
    if (token == null || token.mustChangePassword == value) return;
    updateTokens(token.copyWith(mustChangePassword: value));
  }
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);

// --------------------------------------------------------------------------
// Login methods (ADR 0014 §1, ADR 0018 §1)

enum AuthMethod { dev, local }

/// A way of obtaining an [AuthToken]: dev login (test users without a
/// password) or a local account (e-mail + password).
sealed class AuthProvider {
  const AuthProvider();

  AuthMethod get method;
}

/// User offered by the dev login (`GET /auth/dev/users`).
@freezed
abstract class DevUser with _$DevUser {
  const factory DevUser({
    required String externalId,
    required String displayName,
    @Default('') String email,
    @Default(false) bool isAppAdmin,
    @Default(true) bool isActive,
  }) = _DevUser;

  factory DevUser.fromJson(Map<String, dynamic> json) =>
      _$DevUserFromJson(json);
}

/// Dev login (`AUTH_MODE=dev` on the backend only; ADR 0007).
class DevAuthProvider extends AuthProvider {
  const DevAuthProvider(this._dio, this._now, {this.prefetchedUsers});

  final Dio _dio;
  final DateTime Function() _now;

  /// Users already fetched while detecting the mode.
  final List<DevUser>? prefetchedUsers;

  @override
  AuthMethod get method => AuthMethod.dev;

  Future<List<DevUser>> users() async {
    if (prefetchedUsers != null) return prefetchedUsers!;
    final response = await _dio.get<List<Object?>>('/auth/dev/users');
    return parseDevUsers(response.data);
  }

  Future<AuthToken> signIn(String externalId) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/dev/token',
      data: {'external_id': externalId},
    );
    return AuthToken.fromResponse(response.data ?? const {}, _now());
  }
}

/// Local accounts (`AUTH_MODE=local`, ADR 0018): e-mail + password.
class LocalAuthProvider extends AuthProvider {
  const LocalAuthProvider(this._dio, this._now);

  final Dio _dio;
  final DateTime Function() _now;

  @override
  AuthMethod get method => AuthMethod.local;

  Future<AuthToken> signIn({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    return AuthToken.fromResponse(response.data ?? const {}, _now());
  }
}

/// `POST /auth/password` (current + new password). Every session of the
/// user ends; the answer is a new pair for this tab (ADR 0018 §5).
Future<AuthToken> changePassword(
  Dio dio,
  DateTime now, {
  required String currentPassword,
  required String newPassword,
}) async {
  final response = await dio.post<Map<String, dynamic>>(
    '/auth/password',
    data: {'current_password': currentPassword, 'new_password': newPassword},
  );
  return AuthToken.fromResponse(response.data ?? const {}, now);
}

List<DevUser> parseDevUsers(List<Object?>? data) => [
  for (final item in data ?? const <Object?>[])
    if (item is Map) DevUser.fromJson(Map<String, dynamic>.from(item)),
];

/// Resolves the login method: from `AUTH_MODE` or by asking the API.
final authProviderProvider = FutureProvider<AuthProvider>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final now = ref.watch(clockProvider);
  final setting = ref.watch(authModeSettingProvider);
  switch (setting) {
    case AuthModeSetting.dev:
      return DevAuthProvider(dio, now);
    case AuthModeSetting.local:
      return LocalAuthProvider(dio, now);
    case AuthModeSetting.auto:
      try {
        final response = await dio.get<List<Object?>>('/auth/dev/users');
        return DevAuthProvider(
          dio,
          now,
          prefetchedUsers: parseDevUsers(response.data),
        );
      } on DioException catch (error) {
        // Not mounted outside AUTH_MODE=dev (ADR 0018 §1).
        if (error.response?.statusCode == 404) {
          return LocalAuthProvider(dio, now);
        }
        rethrow;
      }
  }
});

final authModeSettingProvider = Provider<AuthModeSetting>(
  (ref) => AppConfig.authMode,
);
