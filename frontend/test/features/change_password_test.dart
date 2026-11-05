import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';
import 'package:rejestr_zmian/core/auth/token_storage.dart';

import '../helpers.dart';

const _wide = Size(1280, 1000);

Map<String, Object?> _me({bool mustChange = false}) => {
  ...meJson(),
  'must_change_password': mustChange,
};

/// Local backend; `/me` reports a pending temporary password until the
/// request carries the token issued by the password change (`access-3`).
FakeApi _api() => FakeApi()
  ..installDefaults()
  ..on(
    'GET',
    '/auth/dev/users',
    (_) => FakeResponse.problem(404, 'http.not_found', 'Nie znaleziono.'),
  )
  ..on(
    'GET',
    '/me',
    (r) => FakeResponse(
      200,
      _me(mustChange: r.headers['Authorization'] != 'Bearer access-3'),
    ),
  );

Future<void> _fill(
  WidgetTester tester, {
  String current = 'k7Pq2-Xm9Rt-Ab3Hz-Wn6Ef',
  String password = 'trzy zielone latarnie nad wisłą',
  String? confirm,
}) async {
  await tester.enterText(
    find.byKey(const ValueKey('password-current')),
    current,
  );
  await tester.enterText(find.byKey(const ValueKey('password-new')), password);
  await tester.enterText(
    find.byKey(const ValueKey('password-confirm')),
    confirm ?? password,
  );
}

Future<void> _submit(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('password-submit')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('login with a temporary password → forced change page; other '
      'pages redirect back to it', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply(
        'POST',
        '/auth/login',
        sessionTokensJson(mustChangePassword: true),
      );
    final router = await pumpApp(
      tester,
      api: api,
      signedIn: false,
      location: '/c/BETA/changes',
    );

    await tester.enterText(
      find.byKey(const ValueKey('login-email')),
      'ewa@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('login-password')),
      'k7Pq2-Xm9Rt-Ab3Hz-Wn6Ef',
    );
    await tester.tap(find.byKey(const ValueKey('login-submit')));
    await tester.pumpAndSettle();

    expect(currentPath(router), '/account/password');
    expect(currentUri(router).queryParameters['from'], '/c/BETA/changes');
    expect(find.byKey(const ValueKey('password-forced')), findsOneWidget);
    // Forced: no "Anuluj", only "Wyloguj".
    expect(find.byKey(const ValueKey('password-cancel')), findsNothing);
    expect(find.byKey(const ValueKey('password-logout')), findsOneWidget);

    router.go('/c/ALFA/changes');
    await tester.pumpAndSettle();
    expect(currentPath(router), '/account/password');
    // Nothing but /me was requested with the temporary session.
    expect(api.calls('GET', '/companies/.*'), isEmpty);
  });

  testWidgets('403 auth.password_change_required from any endpoint → '
      'forced change page', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()
      ..installDefaults()
      ..on(
        'GET',
        '/companies/[^/]+/changes',
        (_) => FakeResponse.problem(
          403,
          'auth.password_change_required',
          'Przed dalszą pracą musisz zmienić hasło tymczasowe.',
        ),
      );
    final router = await pumpApp(
      tester,
      api: api,
      storage: localSessionStorage(),
      location: '/c/ALFA/changes?status=draft',
    );

    expect(currentPath(router), '/account/password');
    expect(
      currentUri(router).queryParameters['from'],
      '/c/ALFA/changes?status=draft',
    );
  });

  testWidgets('inline validation (UX only): length and confirmation; '
      'nothing sent', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(
      tester,
      api: api,
      storage: localSessionStorage(mustChangePassword: true),
    );

    await _fill(tester, password: 'krotkie', confirm: 'inne');
    await _submit(tester);

    expect(
      find.text('Hasło musi mieć co najmniej 12 znaków (wpisano 7).'),
      findsOneWidget,
    );
    expect(find.text('Hasła nie są takie same.'), findsOneWidget);

    await _fill(tester, password: 'a' * 129);
    await _submit(tester);
    expect(find.text('Hasło może mieć najwyżej 128 znaków.'), findsOneWidget);

    await _fill(
      tester,
      current: 'to samo haslo 1',
      password: 'to samo haslo 1',
    );
    await _submit(tester);
    expect(
      find.text('Nowe hasło musi się różnić od obecnego.'),
      findsOneWidget,
    );
    expect(api.calls('POST', '/auth/password'), isEmpty);
    // The policy is explained up front.
    expect(find.text('Wymagania dla hasła'), findsOneWidget);
  });

  testWidgets('policy errors of the API at the fields (422, 400), 423 as '
      'a banner', (tester) async {
    setSurfaceSize(tester, _wide);
    var answer = FakeResponse.fixture(422, 'problem_password_too_common');
    final api = _api()..on('POST', '/auth/password', (_) => answer);
    final router = await pumpApp(
      tester,
      api: api,
      storage: localSessionStorage(mustChangePassword: true),
    );

    await _fill(tester, password: 'zaq1@WSXcde3');
    await _submit(tester);
    expect(
      find.text(
        'To hasło jest zbyt popularne (znajduje się na liście często '
        'używanych haseł).',
      ),
      findsOneWidget,
    );

    answer = FakeResponse.problem(
      400,
      'auth.invalid_current_password',
      'Obecne hasło jest nieprawidłowe.',
    );
    await _fill(tester);
    await _submit(tester);
    expect(find.text('Obecne hasło jest nieprawidłowe.'), findsOneWidget);

    answer = FakeResponse.problem(423, 'auth.account_locked', 'Zablokowane.');
    await _fill(tester);
    await _submit(tester);
    expect(
      find.textContaining('Konto jest czasowo zablokowane'),
      findsOneWidget,
    );
    expect(currentPath(router), '/account/password');
  });

  testWidgets('success: new tokens replace the session, back to the page', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply(
        'POST',
        '/auth/password',
        sessionTokensJson(accessToken: 'access-3', refreshToken: 'refresh-3'),
      );
    final storage = localSessionStorage(mustChangePassword: true);
    final router = await pumpApp(
      tester,
      api: api,
      storage: storage,
      location: '/c/BETA/changes',
    );
    expect(currentPath(router), '/account/password');

    await _fill(tester);
    await _submit(tester);

    final change = api.calls('POST', '/auth/password').single;
    expect(change.json, {
      'current_password': 'k7Pq2-Xm9Rt-Ab3Hz-Wn6Ef',
      'new_password': 'trzy zielone latarnie nad wisłą',
    });
    expect(change.headers['Authorization'], 'Bearer access-1');
    expect(currentPath(router), '/c/BETA/changes');
    expect(find.text('Hasło zostało zmienione.'), findsOneWidget);
    final stored = AuthToken.decode(storage.read());
    expect(stored?.accessToken, 'access-3');
    expect(stored?.refreshToken, 'refresh-3');
    expect(stored?.mustChangePassword, isFalse);
    expect(
      api.calls('GET', '/me').last.headers['Authorization'],
      'Bearer access-3',
    );
  });

  testWidgets('voluntary change from the user menu; "Anuluj" goes back', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()..on('GET', '/me', (_) => FakeResponse(200, _me()));
    final router = await pumpApp(
      tester,
      api: api,
      storage: localSessionStorage(),
      location: '/c/ALFA/changes',
    );

    await tester.tap(find.byKey(const ValueKey('user-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('change-password')));
    await tester.pumpAndSettle();

    expect(currentPath(router), '/account/password');
    expect(find.byKey(const ValueKey('password-forced')), findsNothing);
    await tester.tap(find.byKey(const ValueKey('password-cancel')));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/changes');
  });

  testWidgets('forced page: "Wyloguj" ends the session', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    final TokenStorage storage = localSessionStorage(mustChangePassword: true);
    final router = await pumpApp(tester, api: api, storage: storage);

    await tester.tap(find.byKey(const ValueKey('password-logout')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/auth/logout'), hasLength(1));
    expect(storage.read(), isNull);
    expect(currentPath(router), '/login');
  });
}
