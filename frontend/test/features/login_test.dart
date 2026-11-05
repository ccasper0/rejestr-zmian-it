import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';
import 'package:rejestr_zmian/core/auth/token_storage.dart';

import '../helpers.dart';

const _wide = Size(1280, 900);

/// Backend with `AUTH_MODE=local`: no dev login (404).
FakeApi _localApi() => FakeApi()
  ..installDefaults()
  ..on(
    'GET',
    '/auth/dev/users',
    (_) => FakeResponse.problem(404, 'http.not_found', 'Nie znaleziono.'),
  );

Future<void> _fillLogin(
  WidgetTester tester, {
  String email = 'ewa@example.com',
  String password = 'mocne-haslo-do-testu',
}) async {
  await tester.enterText(find.byKey(const ValueKey('login-email')), email);
  await tester.enterText(
    find.byKey(const ValueKey('login-password')),
    password,
  );
}

FilledButton _submit(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byKey(const ValueKey('login-submit')));

void main() {
  testWidgets('signed out: any page redirects to dev login, then back', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installDefaults();
    final router = await pumpApp(
      tester,
      api: api,
      signedIn: false,
      location: '/c/BETA/changes?status=draft',
    );

    expect(currentPath(router), '/login');
    expect(find.text('Tryb deweloperski'), findsOneWidget);
    expect(find.text('Ewa Edytorska'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('dev-user-dev-editor')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/auth/dev/token').single.json, {
      'external_id': 'dev-editor',
    });
    expect(currentUri(router).toString(), '/c/BETA/changes?status=draft');
    // Requests after login carry the new bearer token.
    expect(
      api.calls('GET', '/me').last.headers['Authorization'],
      'Bearer new-token',
    );
  });

  group('local accounts (AUTH_MODE=local)', () {
    testWidgets('404 of the dev login → e-mail + password; Enter submits; '
        'tokens stored; back to the page', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi()
        ..reply('POST', '/auth/login', sessionTokensJson());
      final storage = MemoryTokenStorage();
      final router = await pumpApp(
        tester,
        api: api,
        signedIn: false,
        storage: storage,
        location: '/c/BETA/changes?status=draft',
      );

      expect(currentPath(router), '/login');
      expect(find.text('Tryb deweloperski'), findsNothing);
      expect(find.byKey(const ValueKey('login-email')), findsOneWidget);

      await _fillLogin(tester, email: '  ewa@example.com ');
      // Enter in the password field sends the form.
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      final login = api.calls('POST', '/auth/login').single;
      expect(login.json, {
        'email': 'ewa@example.com',
        'password': 'mocne-haslo-do-testu',
      });
      expect(login.headers.containsKey('Authorization'), isFalse);
      expect(currentUri(router).toString(), '/c/BETA/changes?status=draft');
      expect(
        api.calls('GET', '/me').last.headers['Authorization'],
        'Bearer access-2',
      );
      final stored = AuthToken.decode(storage.read());
      expect(stored?.refreshToken, 'refresh-2');
      expect(stored?.sessionExpiresAt, DateTime.utc(2026, 11, 3, 20));
    });

    testWidgets('password can be shown and hidden', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _localApi(), signedIn: false);

      TextField field() => tester.widget<TextField>(
        find.byKey(const ValueKey('login-password')),
      );
      expect(field().obscureText, isTrue);
      await tester.tap(find.byKey(const ValueKey('login-password-toggle')));
      await tester.pump();
      expect(field().obscureText, isFalse);
      expect(find.byTooltip('Ukryj hasło'), findsOneWidget);
    });

    testWidgets('empty fields: inline errors, nothing sent', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi();
      await pumpApp(tester, api: api, signedIn: false);

      await tester.tap(find.byKey(const ValueKey('login-submit')));
      await tester.pump();

      expect(find.text('Podaj adres e-mail.'), findsOneWidget);
      expect(find.text('Podaj hasło.'), findsOneWidget);
      expect(api.calls('POST', '/auth/login'), isEmpty);
    });

    testWidgets('401 auth.invalid_credentials: one Polish message, password '
        'cleared, still on the login page', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi()
        ..on(
          'POST',
          '/auth/login',
          (_) => FakeResponse.fixture(401, 'problem_invalid_credentials'),
        );
      final router = await pumpApp(tester, api: api, signedIn: false);

      await _fillLogin(tester);
      await tester.tap(find.byKey(const ValueKey('login-submit')));
      await tester.pumpAndSettle();

      expect(currentPath(router), '/login');
      expect(
        find.text(
          'Nieprawidłowy e-mail lub hasło albo konto jest '
          'zablokowane/nieaktywne.',
        ),
        findsOneWidget,
      );
      expect(
        tester
            .widget<TextField>(find.byKey(const ValueKey('login-password')))
            .controller
            ?.text,
        isEmpty,
      );
      expect(_submit(tester).onPressed, isNotNull);
    });

    testWidgets('401 auth.temporary_password_expired: Polish message about '
        'the expired temporary password', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi()
        ..on(
          'POST',
          '/auth/login',
          (_) =>
              FakeResponse.fixture(401, 'problem_temporary_password_expired'),
        );
      final router = await pumpApp(tester, api: api, signedIn: false);

      await _fillLogin(tester);
      await tester.tap(find.byKey(const ValueKey('login-submit')));
      await tester.pumpAndSettle();

      expect(currentPath(router), '/login');
      expect(
        find.descendant(
          of: find.byKey(const ValueKey('login-error')),
          matching: find.text(
            'Hasło tymczasowe wygasło. Poproś administratora o ponowne '
            'ustawienie hasła.',
          ),
        ),
        findsOneWidget,
      );
    });

    testWidgets('429 auth.too_many_attempts: wait from Retry-After, button '
        'blocked until it passes', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi()
        ..on(
          'POST',
          '/auth/login',
          (_) => FakeResponse.fixture(429, 'problem_too_many_attempts', {
            'Retry-After': '30',
          }),
        );
      await pumpApp(tester, api: api, signedIn: false);

      await _fillLogin(tester);
      await tester.tap(find.byKey(const ValueKey('login-submit')));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Zbyt wiele nieudanych prób logowania z tej sieci. Spróbuj ponownie '
          'za 30 s.',
        ),
        findsOneWidget,
      );
      expect(_submit(tester).onPressed, isNull);
      expect(find.text('Spróbuj ponownie za 30 s'), findsOneWidget);
      // Enter does not bypass the wait either.
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pump();
      expect(api.calls('POST', '/auth/login'), hasLength(1));

      await tester.pump(const Duration(seconds: 10));
      expect(find.text('Spróbuj ponownie za 20 s'), findsOneWidget);
      await tester.pump(const Duration(seconds: 20));
      expect(find.text('Zaloguj się'), findsOneWidget);
      expect(_submit(tester).onPressed, isNotNull);
    });

    testWidgets('429 request.rate_limited from nginx without a readable '
        'Retry-After: generic hint, default wait', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi()
        ..on(
          'POST',
          '/auth/login',
          (_) => FakeResponse.fixture(429, 'problem_rate_limited'),
        );
      await pumpApp(tester, api: api, signedIn: false);

      await _fillLogin(tester);
      await tester.tap(find.byKey(const ValueKey('login-submit')));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Przekroczono limit żądań. Odczekaj chwilę i spróbuj ponownie.',
        ),
        findsOneWidget,
      );
      expect(_submit(tester).onPressed, isNull);
      await tester.pump(const Duration(seconds: 30));
      expect(_submit(tester).onPressed, isNotNull);
    });

    testWidgets('sign out from the user menu ends the session on the server', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _localApi();
      final storage = localSessionStorage();
      final router = await pumpApp(tester, api: api, storage: storage);

      await tester.tap(find.byKey(const ValueKey('user-menu')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('sign-out')));
      await tester.pumpAndSettle();

      expect(
        api.calls('POST', '/auth/logout').single.headers['Authorization'],
        'Bearer access-1',
      );
      expect(storage.read(), isNull);
      expect(currentPath(router), '/login');
      // A deliberate sign-out keeps no return path for the next person.
      expect(currentUri(router).queryParameters, isNot(contains('from')));
    });
  });

  testWidgets('401 from the API ends the session and returns to login', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()
      ..installDefaults()
      ..on(
        'GET',
        '/companies/[^/]+/changes',
        (_) => FakeResponse.problem(401, 'auth.invalid_token', 'Token wygasł.'),
      );
    final router = await pumpApp(tester, api: api);

    expect(currentPath(router), '/login');
    expect(find.text('Sesja wygasła. Zaloguj się ponownie.'), findsOneWidget);
  });

  testWidgets('sign out clears the session (dev: no logout call)', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installDefaults();
    final router = await pumpApp(tester, api: api);

    await tester.tap(find.byKey(const ValueKey('user-menu')));
    await tester.pumpAndSettle();
    // Dev users have no password: no "Zmień hasło".
    expect(find.byKey(const ValueKey('change-password')), findsNothing);
    await tester.tap(find.byKey(const ValueKey('sign-out')));
    await tester.pumpAndSettle();

    expect(currentPath(router), '/login');
    expect(api.calls('POST', '/auth/logout'), isEmpty);
  });

  testWidgets('403 auth.user_inactive → login with a notice', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()
      ..installDefaults()
      ..on(
        'GET',
        '/me',
        (_) => FakeResponse.problem(403, 'auth.user_inactive', 'Nieaktywne.'),
      );
    final router = await pumpApp(
      tester,
      api: api,
      storage: localSessionStorage(),
    );

    expect(currentPath(router), '/login');
    expect(find.text(SessionNotices.inactive), findsWidgets);
  });
}
