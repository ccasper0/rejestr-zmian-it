// AuthInterceptor (ADR 0018 §10): Bearer, single-flight refresh, session
// answers of the API. Runs on the real provider wiring (AuthController,
// token storage) with the fake dio adapter.
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/api_client.dart';
import 'package:rejestr_zmian/core/api_error.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';
import 'package:rejestr_zmian/core/auth/token_storage.dart';
import 'package:rejestr_zmian/core/service_notice.dart';

import '../helpers.dart';

/// 401 `auth.invalid_token` unless the request carries [valid].
FakeHandler protectedBy(String valid, Object? body) =>
    (r) => r.headers['Authorization'] == 'Bearer $valid'
    ? FakeResponse(200, body)
    : FakeResponse.problem(401, 'auth.invalid_token', 'Token wygasł.');

void main() {
  late FakeApi api;
  late TokenStorage storage;
  late ProviderContainer container;

  ProviderContainer start(TokenStorage tokens) {
    storage = tokens;
    final c = ProviderContainer(
      overrides: [
        httpClientAdapterProvider.overrideWithValue(api),
        apiBaseUrlProvider.overrideWithValue('http://api.test/api/v1'),
        tokenStorageProvider.overrideWithValue(tokens),
      ],
    );
    addTearDown(c.dispose);
    return c;
  }

  Dio dio() => container.read(apiClientProvider);
  AuthState auth() => container.read(authControllerProvider);

  setUp(() {
    api = FakeApi()
      ..on(
        'POST',
        '/auth/refresh',
        (r) => r.json['refresh_token'] == 'refresh-1'
            ? FakeResponse(200, sessionTokensJson())
            : FakeResponse.problem(
                401,
                'auth.invalid_refresh_token',
                'Sesja wygasła lub została zakończona.',
              ),
      );
  });

  test('parallel 401 → exactly one refresh, every request repeated with the '
      'new token', () async {
    api
      ..latency['POST /auth/refresh'] = const Duration(milliseconds: 50)
      ..on('GET', '/a', protectedBy('access-2', {'a': 1}))
      ..on('GET', '/b', protectedBy('access-2', {'b': 2}))
      ..on('GET', '/c', protectedBy('access-2', {'c': 3}));
    container = start(localSessionStorage());

    final results = await Future.wait([
      dio().get<Map<String, dynamic>>('/a'),
      dio().get<Map<String, dynamic>>('/b'),
      dio().get<Map<String, dynamic>>('/c'),
    ]);

    expect(results.map((r) => r.data), [
      {'a': 1},
      {'b': 2},
      {'c': 3},
    ]);
    final refreshes = api.calls('POST', '/auth/refresh');
    expect(refreshes, hasLength(1));
    expect(refreshes.single.json, {'refresh_token': 'refresh-1'});
    // The public endpoint never carries the access token.
    expect(refreshes.single.headers.containsKey('Authorization'), isFalse);
    expect(api.calls('GET', '/[abc]'), hasLength(6));
    // The rotated pair is kept in memory and in sessionStorage.
    expect(auth().token?.accessToken, 'access-2');
    expect(auth().token?.refreshToken, 'refresh-2');
    expect(AuthToken.decode(storage.read())?.refreshToken, 'refresh-2');
  });

  test('a 401 that arrives after the refresh reuses the new token (no '
      'second refresh with the rotated one)', () async {
    api
      ..on('GET', '/fast', protectedBy('access-2', {'r': 'fast'}))
      ..on('GET', '/slow', protectedBy('access-2', {'r': 'slow'}))
      ..latency['GET /slow'] = const Duration(milliseconds: 80);
    container = start(localSessionStorage());

    final slow = dio().get<Map<String, dynamic>>('/slow');
    final fast = await dio().get<Map<String, dynamic>>('/fast');
    expect(fast.data, {'r': 'fast'});
    expect((await slow).data, {'r': 'slow'});
    expect(api.calls('POST', '/auth/refresh'), hasLength(1));
  });

  test('expired access token: refreshed BEFORE the request', () async {
    api.on('GET', '/me', protectedBy('access-2', {'ok': true}));
    container = start(localSessionStorage(accessValidFor: Duration.zero));

    final response = await dio().get<Map<String, dynamic>>('/me');

    expect(response.data, {'ok': true});
    expect(api.calls('POST', '/auth/refresh'), hasLength(1));
    // No request was sent with the expired token.
    expect(
      api.calls('GET', '/me').single.headers['Authorization'],
      'Bearer access-2',
    );
  });

  test('refresh refused (401 auth.invalid_refresh_token) → signed out with '
      'a notice', () async {
    api.on('GET', '/me', protectedBy('access-2', {}));
    container = start(localSessionStorage(refreshToken: 'stolen'));

    await expectLater(dio().get<Object?>('/me'), throwsA(isA<DioException>()));

    expect(auth().isSignedIn, isFalse);
    expect(auth().notice, SessionNotices.ended);
    expect(storage.read(), isNull);
    expect(api.calls('POST', '/auth/refresh'), hasLength(1));
  });

  test('refresh refused with 401 auth.temporary_password_expired → signed '
      'out with the temporary password notice', () async {
    api
      ..on('GET', '/me', protectedBy('access-2', {}))
      ..on(
        'POST',
        '/auth/refresh',
        (_) => FakeResponse.fixture(401, 'problem_temporary_password_expired'),
      );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(isA<DioException>()));

    expect(auth().isSignedIn, isFalse);
    expect(auth().notice, SessionNotices.temporaryPasswordExpired);
    expect(storage.read(), isNull);
  });

  test('refresh failing on the network keeps the session', () async {
    api
      ..on('GET', '/me', protectedBy('access-2', {}))
      ..on(
        'POST',
        '/auth/refresh',
        (_) => FakeResponse.problem(503, 'api.unavailable', 'Niedostępny.'),
      );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(isA<DioException>()));
    expect(auth().isSignedIn, isTrue);
    expect(auth().token?.refreshToken, 'refresh-1');
  });

  test('the repeated request failing with 401 again → no second refresh, '
      'signed out', () async {
    api.on(
      'GET',
      '/me',
      (_) => FakeResponse.problem(401, 'auth.invalid_token', 'Nie.'),
    );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(isA<DioException>()));
    expect(api.calls('POST', '/auth/refresh'), hasLength(1));
    expect(api.calls('GET', '/me'), hasLength(2));
    expect(auth().isSignedIn, isFalse);
  });

  test(
    '401 auth.session_expired → login with "ended" notice, no refresh',
    () async {
      api.on(
        'GET',
        '/me',
        (_) => FakeResponse.problem(401, 'auth.session_expired', 'Koniec.'),
      );
      container = start(localSessionStorage());

      await expectLater(dio().get<Object?>('/me'), throwsA(anything));
      expect(api.calls('POST', '/auth/refresh'), isEmpty);
      expect(auth().isSignedIn, isFalse);
      expect(auth().notice, SessionNotices.ended);
    },
  );

  test('403 auth.user_inactive → signed out with a notice', () async {
    api.on(
      'GET',
      '/me',
      (_) => FakeResponse.problem(403, 'auth.user_inactive', 'Nieaktywne.'),
    );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(anything));
    expect(auth().isSignedIn, isFalse);
    expect(auth().notice, SessionNotices.inactive);
  });

  test('403 auth.password_change_required → forced password change', () async {
    api.on(
      'GET',
      '/companies',
      (_) => FakeResponse.problem(
        403,
        'auth.password_change_required',
        'Zmień hasło.',
      ),
    );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/companies'), throwsA(anything));
    expect(auth().isSignedIn, isTrue);
    expect(auth().mustChangePassword, isTrue);
    expect(AuthToken.decode(storage.read())?.mustChangePassword, isTrue);
  });

  test('dev token (no refresh token): 401 ends the session', () async {
    api.on(
      'GET',
      '/me',
      (_) => FakeResponse.problem(401, 'auth.invalid_token', 'Wygasł.'),
    );
    container = start(signedInStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(anything));
    expect(api.calls('POST', '/auth/refresh'), isEmpty);
    expect(auth().notice, SessionNotices.expired);
  });

  test(
    'public endpoints carry no bearer and their 401 keeps the session',
    () async {
      api.on(
        'POST',
        '/auth/login',
        (_) => FakeResponse.problem(401, 'auth.invalid_credentials', 'Nie.'),
      );
      container = start(localSessionStorage());

      await expectLater(
        dio().post<Object?>(
          '/auth/login',
          data: {'email': 'a', 'password': 'b'},
        ),
        throwsA(anything),
      );
      final login = api.calls('POST', '/auth/login').single;
      expect(login.headers.containsKey('Authorization'), isFalse);
      expect(auth().isSignedIn, isTrue);
    },
  );

  test(
    'a multipart upload is repeated with a fresh body after refresh',
    () async {
      api.on('POST', '/upload', protectedBy('access-2', {'id': 'att-1'}));
      container = start(localSessionStorage());

      final response = await dio().post<Map<String, dynamic>>(
        '/upload',
        data: FormData.fromMap({
          'file': MultipartFile.fromBytes(
            Uint8List.fromList([1, 2, 3]),
            filename: 'a.pdf',
          ),
        }),
      );
      expect(response.data, {'id': 'att-1'});
      expect(api.calls('POST', '/upload'), hasLength(2));
    },
  );

  test('429 request.rate_limited → app-wide notice with the Retry-After '
      'time (one per burst)', () async {
    api.on(
      'GET',
      '/me',
      (_) => FakeResponse.fixture(429, 'problem_rate_limited', {
        'Retry-After': '30',
      }),
    );
    container = start(localSessionStorage());

    Object? caught;
    try {
      await dio().get<Object?>('/me');
    } on DioException catch (error) {
      caught = error;
    }
    expect(ApiProblem.from(caught!).retryAfter, const Duration(seconds: 30));
    final notice = container.read(serviceNoticeProvider);
    expect(notice?.code, 'request.rate_limited');
    expect(
      notice?.message,
      'Przekroczono limit żądań. Spróbuj ponownie za 30 s.',
    );
    await expectLater(dio().get<Object?>('/me'), throwsA(anything));
    expect(container.read(serviceNoticeProvider)?.sequence, notice?.sequence);
    expect(auth().isSignedIn, isTrue);
  });

  test('503 api.unavailable → app-wide notice', () async {
    api.on(
      'GET',
      '/me',
      (_) => FakeResponse.fixture(503, 'problem_api_unavailable'),
    );
    container = start(localSessionStorage());

    await expectLater(dio().get<Object?>('/me'), throwsA(anything));
    expect(
      container.read(serviceNoticeProvider)?.message,
      'Serwer aplikacji jest chwilowo niedostępny. Spróbuj ponownie za '
      'chwilę.',
    );
  });

  test(
    'logout: POST /auth/logout with the bearer, then storage cleared',
    () async {
      api.reply('POST', '/auth/logout', null, 204);
      container = start(localSessionStorage());

      await container.read(authControllerProvider.notifier).logout();

      final logout = api.calls('POST', '/auth/logout').single;
      expect(logout.headers['Authorization'], 'Bearer access-1');
      expect(auth().isSignedIn, isFalse);
      expect(storage.read(), isNull);
    },
  );

  test('restored session with an expired access token stays signed in while '
      'it can be refreshed', () {
    api = FakeApi();
    container = start(localSessionStorage(accessValidFor: Duration.zero));
    expect(auth().isSignedIn, isTrue);
    container = start(
      MemoryTokenStorage(
        AuthToken(
          accessToken: 'a',
          expiresAt: DateTime.now().toUtc(),
          refreshToken: 'r',
          refreshExpiresAt: DateTime.now().toUtc().subtract(
            const Duration(minutes: 1),
          ),
        ).encode(),
      ),
    );
    expect(auth().isSignedIn, isFalse);
  });
}
