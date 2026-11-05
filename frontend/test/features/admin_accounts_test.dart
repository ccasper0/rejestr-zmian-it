// Local accounts in "Użytkownicy i role" (ADR 0018 §5): create with a
// one-time temporary password, reset, (de)activation and the admin flag
// with confirmations, state labels.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);
const _temporary = 'k7Pq2-Xm9Rt-Ab3Hz-Wn6Ef';

/// 12:00 UTC = 13:00 in Warsaw (CET, November).
final _now = DateTime.utc(2026, 11, 3, 12);

Map<String, Object?> _account(
  String id,
  String name, {
  bool admin = false,
  bool active = true,
  bool hasPassword = true,
  bool mustChange = false,
  String? lockedUntil,
  String? tempExpiresAt,
  String? changedAt = '2026-10-30T09:30:00Z',
}) => {
  ...userJson(id, name, admin: admin, active: active),
  'has_password': hasPassword,
  'must_change_password': mustChange,
  'password_changed_at': hasPassword ? changedAt : null,
  'locked_until': lockedUntil,
  'temp_password_expires_at': tempExpiresAt,
};

Map<String, Object?> _detail(Map<String, Object?> account) => {
  ...account,
  'memberships': <Object?>[],
};

Future<void> _open(WidgetTester tester, FakeApi api, String location) =>
    pumpApp(
      tester,
      api: api,
      location: location,
      overrides: [clockProvider.overrideWithValue(() => _now)],
    );

/// Captures `Clipboard.setData`.
List<String> _captureClipboard(WidgetTester tester) {
  final copied = <String>[];
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
    SystemChannels.platform,
    (call) async {
      if (call.method == 'Clipboard.setData') {
        copied.add((call.arguments as Map)['text'] as String);
      }
      return null;
    },
  );
  addTearDown(
    () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      null,
    ),
  );
  return copied;
}

void main() {
  testWidgets('directory: account state labels (password, temporary, '
      'locked until — Warsaw time, inactive)', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users',
      page([
        _account(adminId, 'Adam Administrator', admin: true),
        _account(editorUuid, 'Ewa Edytorska', mustChange: true),
        _account(
          approverUuid,
          'Jan Zatwierdzający',
          lockedUntil: '2026-11-03T14:15:00Z',
          active: false,
        ),
        _account(
          '00000000-0000-4000-8000-000000000009',
          'Dawny Użytkownik',
          hasPassword: false,
          lockedUntil: '2026-11-03T11:00:00Z',
        ),
      ]),
    );
    await _open(tester, api, '/admin/users');

    Finder stateOf(String id, String label) => find.descendant(
      of: find.byKey(ValueKey('user-state-$id')),
      matching: find.text(label),
    );
    expect(stateOf(adminId, 'Hasło ustawione'), findsOneWidget);
    expect(stateOf(adminId, 'Administrator'), findsOneWidget);
    expect(stateOf(editorUuid, 'Wymaga zmiany hasła'), findsOneWidget);
    expect(
      stateOf(approverUuid, 'Zablokowane do 03.11.2026 15:15'),
      findsOneWidget,
    );
    expect(stateOf(approverUuid, 'Nieaktywne'), findsOneWidget);
    const old = '00000000-0000-4000-8000-000000000009';
    expect(stateOf(old, 'Brak hasła'), findsOneWidget);
    // A lockout in the past is not shown.
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('user-state-$old')),
        matching: find.textContaining('Zablokowane'),
      ),
      findsNothing,
    );
  });

  testWidgets('temporary password: "ważne do" while valid, "wygasło" '
      'after the deadline', (tester) async {
    setSurfaceSize(tester, _wide);
    const expiredId = '00000000-0000-4000-8000-000000000011';
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users',
      page([
        // 14:30Z = 15:30 in Warsaw, after _now (12:00Z).
        _account(
          editorUuid,
          'Ewa Edytorska',
          mustChange: true,
          tempExpiresAt: '2026-11-03T14:30:00Z',
        ),
        // The deadline itself counts as expired (the backend refuses).
        _account(
          expiredId,
          'Piotr Przeterminowany',
          mustChange: true,
          tempExpiresAt: '2026-11-03T12:00:00Z',
        ),
      ]),
    );
    await _open(tester, api, '/admin/users');

    Finder stateOf(String id, Finder matching) => find.descendant(
      of: find.byKey(ValueKey('user-state-$id')),
      matching: matching,
    );
    expect(
      stateOf(editorUuid, find.text('Wymaga zmiany hasła')),
      findsOneWidget,
    );
    expect(
      stateOf(editorUuid, find.text('ważne do 03.11.2026 15:30')),
      findsOneWidget,
    );
    expect(
      stateOf(editorUuid, find.text('Hasło tymczasowe wygasło')),
      findsNothing,
    );
    expect(
      stateOf(expiredId, find.text('Hasło tymczasowe wygasło')),
      findsOneWidget,
    );
    expect(stateOf(expiredId, find.textContaining('ważne do')), findsNothing);
    expect(stateOf(expiredId, find.text('Wymaga zmiany hasła')), findsNothing);
  });

  testWidgets('user detail: expired temporary password label', (tester) async {
    setSurfaceSize(tester, _wide);
    const expiredId = '00000000-0000-4000-8000-000000000011';
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users/$expiredId',
      _detail(
        _account(
          expiredId,
          'Piotr Przeterminowany',
          mustChange: true,
          tempExpiresAt: '2026-11-02T08:00:00Z',
        ),
      ),
    );
    await _open(tester, api, '/admin/users/$expiredId');

    expect(
      find.descendant(
        of: find.byKey(const ValueKey('account-state')),
        matching: find.text('Hasło tymczasowe wygasło'),
      ),
      findsOneWidget,
    );
  });

  testWidgets('"Nowy użytkownik": POST /users, temporary password shown '
      'once with a warning and copy button', (tester) async {
    setSurfaceSize(tester, _wide);
    final copied = _captureClipboard(tester);
    final api = FakeApi()..installAdmin();
    api.on('POST', '/users', (_) => FakeResponse.fixture(201, 'user_created'));
    await _open(tester, api, '/admin/users');
    final listLoads = api.calls('GET', '/users').length;

    await tester.tap(find.byKey(const ValueKey('user-create')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('user-create-submit')));
    await tester.pump();
    expect(
      find.text('Podaj adres e-mail (login użytkownika).'),
      findsOneWidget,
    );
    expect(find.text('Podaj imię i nazwisko.'), findsOneWidget);
    expect(api.calls('POST', '/users'), isEmpty);

    await tester.enterText(
      find.byKey(const ValueKey('user-email')),
      ' nowak@example.com ',
    );
    await tester.enterText(
      find.byKey(const ValueKey('user-name')),
      'Anna Nowak',
    );
    await tester.tap(find.byKey(const ValueKey('user-admin')));
    await tester.tap(find.byKey(const ValueKey('user-create-submit')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/users').single.json, {
      'email': 'nowak@example.com',
      'display_name': 'Anna Nowak',
      'is_app_admin': true,
    });
    expect(find.text('Konto zostało utworzone'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('temporary-password-warning')),
      findsOneWidget,
    );
    expect(find.text('Hasło jest wyświetlane tylko raz'), findsOneWidget);
    expect(find.text(_temporary), findsOneWidget);
    // Deadline from `user.temp_password_expires_at` (08:00Z = 09:00 CET).
    expect(
      find.text(
        'Hasło tymczasowe jest ważne do 10.11.2026 09:00 (Europe/Warsaw) — '
        'po tym terminie konieczny będzie ponowny reset hasła.',
      ),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('temporary-password-copy')));
    await tester.pumpAndSettle();
    expect(copied, [_temporary]);
    expect(find.text('Skopiowano'), findsOneWidget);

    // The barrier does not close it; only "Zamknij".
    await tester.tapAt(const Offset(5, 5));
    await tester.pumpAndSettle();
    expect(find.text(_temporary), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('temporary-password-close')));
    await tester.pumpAndSettle();

    expect(find.text(_temporary), findsNothing);
    expect(api.calls('GET', '/users').length, greaterThan(listLoads));
  });

  testWidgets('409 user.email_taken is shown at the e-mail field', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.on(
      'POST',
      '/users',
      (_) => FakeResponse.problem(
        409,
        'user.email_taken',
        'Użytkownik o tym adresie e-mail już istnieje.',
      ),
    );
    await _open(tester, api, '/admin/users');

    await tester.tap(find.byKey(const ValueKey('user-create')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('user-email')),
      'ewa@example.com',
    );
    await tester.enterText(find.byKey(const ValueKey('user-name')), 'Ewa');
    await tester.tap(find.byKey(const ValueKey('user-create-submit')));
    await tester.pumpAndSettle();

    expect(
      find.text('Użytkownik o tym adresie e-mail już istnieje.'),
      findsOneWidget,
    );
    expect(find.text('Nowy użytkownik'), findsWidgets);
    expect(find.byKey(const ValueKey('temporary-password')), findsNothing);
  });

  testWidgets('"Resetuj hasło": confirmation, then the new temporary '
      'password once', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api
      ..reply(
        'GET',
        '/users/$editorUuid',
        _detail(
          _account(
            editorUuid,
            'Ewa Edytorska',
            lockedUntil: '2026-11-03T14:15:00Z',
          ),
        ),
      )
      ..on(
        'POST',
        '/users/$editorUuid/reset-password',
        (_) => FakeResponse(200, {
          'user': _account(editorUuid, 'Ewa Edytorska', mustChange: true),
          'temporary_password': _temporary,
        }),
      );
    await _open(tester, api, '/admin/users/$editorUuid');

    expect(
      find.descendant(
        of: find.byKey(const ValueKey('account-state')),
        matching: find.text('Zablokowane do 03.11.2026 15:15'),
      ),
      findsOneWidget,
    );
    expect(
      find.textContaining('30.10.2026 10:30', findRichText: true),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('user-reset-password')));
    await tester.pumpAndSettle();
    expect(find.text('Zresetować hasło?'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('confirm-cancel')));
    await tester.pumpAndSettle();
    expect(api.calls('POST', '/users/.*/reset-password'), isEmpty);

    await tester.tap(find.byKey(const ValueKey('user-reset-password')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-action')));
    await tester.pumpAndSettle();

    expect(
      api.calls('POST', '/users/$editorUuid/reset-password'),
      hasLength(1),
    );
    expect(find.text('Nowe hasło tymczasowe'), findsOneWidget);
    expect(find.text(_temporary), findsOneWidget);
    // An answer without the deadline: the default 7 days.
    expect(
      find.byKey(const ValueKey('temporary-password-validity')),
      findsOneWidget,
    );
    expect(find.textContaining('ważne 7 dni'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('temporary-password-close')));
    await tester.pumpAndSettle();
    expect(find.text(_temporary), findsNothing);
  });

  testWidgets('own account: no reset, no deactivation, no removal of the '
      'admin role', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users/$adminId',
      _detail(_account(adminId, 'Adam Administrator', admin: true)),
    );
    await _open(tester, api, '/admin/users/$adminId');

    ButtonStyleButton button(String key) =>
        tester.widget<ButtonStyleButton>(find.byKey(ValueKey(key)));
    expect(button('user-reset-password').onPressed, isNull);
    expect(button('user-deactivate').onPressed, isNull);
    expect(button('user-revoke-admin').onPressed, isNull);
    expect(button('user-rename').onPressed, isNotNull);
  });

  testWidgets('"Dezaktywuj" asks first (Flutter dialog); "Anuluj" sends '
      'nothing, confirmation sends PATCH is_active=false', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    var active = true;
    api
      ..on(
        'GET',
        '/users/$editorUuid',
        (_) => FakeResponse(
          200,
          _detail(_account(editorUuid, 'Ewa Edytorska', active: active)),
        ),
      )
      ..on('PATCH', '/users/$editorUuid', (r) {
        active = r.json['is_active'] as bool? ?? active;
        return FakeResponse(
          200,
          _account(editorUuid, 'Ewa Edytorska', active: active),
        );
      });
    await _open(tester, api, '/admin/users/$editorUuid');

    await tester.tap(find.byKey(const ValueKey('user-deactivate')));
    await tester.pumpAndSettle();
    expect(find.text('Dezaktywować konto?'), findsOneWidget);
    expect(
      find.textContaining('zostanie natychmiast wylogowany'),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('confirm-cancel')));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', '/users/.*'), isEmpty);

    await tester.tap(find.byKey(const ValueKey('user-deactivate')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-action')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', '/users/$editorUuid').single.json, {
      'is_active': false,
    });
    expect(find.text('Konto dezaktywowano.'), findsOneWidget);
    // Reloaded: "Aktywuj" (no confirmation needed) instead.
    await tester.tap(find.byKey(const ValueKey('user-activate')));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', '/users/$editorUuid').last.json, {
      'is_active': true,
    });
  });

  testWidgets('removing the admin role: confirmation; 409 user.last_admin '
      'in Polish', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api
      ..reply(
        'GET',
        '/users/$approverUuid',
        _detail(_account(approverUuid, 'Jan Zatwierdzający', admin: true)),
      )
      ..on(
        'PATCH',
        '/users/$approverUuid',
        (_) => FakeResponse.fixture(409, 'problem_last_admin'),
      );
    await _open(tester, api, '/admin/users/$approverUuid');

    await tester.tap(find.byKey(const ValueKey('user-revoke-admin')));
    await tester.pumpAndSettle();
    expect(find.text('Odebrać uprawnienia administratora?'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('confirm-action')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', '/users/$approverUuid').single.json, {
      'is_app_admin': false,
    });
    expect(
      find.textContaining('To ostatni aktywny administrator aplikacji'),
      findsOneWidget,
    );
  });

  testWidgets('rename: PATCH display_name only', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api
      ..reply(
        'GET',
        '/users/$editorUuid',
        _detail(_account(editorUuid, 'Ewa Edytorska')),
      )
      ..on(
        'PATCH',
        '/users/$editorUuid',
        (_) => FakeResponse(200, _account(editorUuid, 'Ewa Nowak')),
      );
    await _open(tester, api, '/admin/users/$editorUuid');

    await tester.tap(find.byKey(const ValueKey('user-rename')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('user-name-edit')),
      ' Ewa Nowak ',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('user-name-save')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', '/users/$editorUuid').single.json, {
      'display_name': 'Ewa Nowak',
    });
  });
}
