import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);

Map<String, Object?> _detail(
  String id,
  String name, {
  bool active = true,
  List<Map<String, Object?>> memberships = const [],
}) => {...userJson(id, name, active: active), 'memberships': memberships};

Map<String, Object?> _membership(String roles0, [List<String>? roles]) => {
  'company_id': companyAlfa,
  'company_name': 'Alfa S.A.',
  'company_prefix': 'ALFA',
  'company_status': 'active',
  'roles': roles ?? [roles0],
};

void main() {
  testWidgets('directory: search and page in the URL and in the API query', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    final router = await pumpApp(
      tester,
      api: api,
      location: '/admin/users?q=ewa&page=2',
    );
    final query = api.calls('GET', '/users').last.query;
    expect(query['q'], ['ewa']);
    expect(query['offset'], ['50']);

    await tester.enterText(find.byKey(const ValueKey('users-search')), 'jan');
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(currentUri(router).toString(), '/admin/users?q=jan');

    await tester.tap(find.text('Jan Zatwierdzający'));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/admin/users/$approverUuid');
  });

  testWidgets('roles of a user: PUT with the FULL set of roles', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users/$editorUuid',
      _detail(
        editorUuid,
        'Ewa Edytorska',
        memberships: [
          _membership('editor', ['editor', 'viewer']),
        ],
      ),
    );
    api.on(
      'PUT',
      '/companies/c-alfa/members/$editorUuid',
      (r) => FakeResponse(200, {
        'user_id': editorUuid,
        'display_name': 'Ewa Edytorska',
        'email': 'ewa@example.com',
        'is_active': true,
        'roles': r.json['roles'],
      }),
    );
    await pumpApp(tester, api: api, location: '/admin/users/$editorUuid');

    expect(find.textContaining('Alfa S.A.', findRichText: true), findsWidgets);
    expect(find.text('Edytor'), findsOneWidget);
    expect(find.text('Obserwator'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('edit-roles-ALFA')));
    await tester.pumpAndSettle();
    final save = find.byKey(const ValueKey('roles-save'));
    // nothing changed yet
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    await tester.tap(find.byKey(const ValueKey('role-approver')));
    await tester.tap(find.byKey(const ValueKey('role-editor')));
    await tester.pump();
    // not the admin's own account: no self-grant warning
    expect(find.byKey(const ValueKey('self-grant-warning')), findsNothing);
    await tester.tap(save);
    await tester.pumpAndSettle();

    final put = api.calls('PUT', '/companies/c-alfa/members/$editorUuid');
    expect(put.single.json, {
      'roles': ['approver', 'viewer'],
    });
  });

  testWidgets('admin granting a role to self is warned (segregation)', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply('GET', '/users/$adminId', _detail(adminId, 'Adam Administrator'));
    await pumpApp(tester, api: api, location: '/admin/users/$adminId');

    expect(find.textContaining('To Twoje konto'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('user-add-company')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('pick-company-ALFA')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('role-approver')));
    await tester.pump();
    expect(find.byKey(const ValueKey('self-grant-warning')), findsOneWidget);
  });

  testWidgets('inactive user: a new role cannot be granted', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users/$editorUuid',
      _detail(
        editorUuid,
        'Ewa Edytorska',
        active: false,
        memberships: [_membership('editor')],
      ),
    );
    await pumpApp(tester, api: api, location: '/admin/users/$editorUuid');
    await tester.tap(find.byKey(const ValueKey('edit-roles-ALFA')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('role-auditor')));
    await tester.pump();
    final save = find.byKey(const ValueKey('roles-save'));
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    // revoking stays possible
    await tester.tap(find.byKey(const ValueKey('role-auditor')));
    await tester.tap(find.byKey(const ValueKey('role-editor')));
    await tester.pump();
    expect(tester.widget<FilledButton>(save).onPressed, isNotNull);
  });

  testWidgets('API error of the role change is shown in Polish', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/users/$editorUuid',
      _detail(
        editorUuid,
        'Ewa Edytorska',
        memberships: [_membership('viewer')],
      ),
    );
    api.on(
      'PUT',
      '/companies/c-alfa/members/$editorUuid',
      (_) => FakeResponse.problem(
        422,
        'membership.user_inactive',
        'Nie można nadać roli nieaktywnemu użytkownikowi.',
      ),
    );
    await pumpApp(tester, api: api, location: '/admin/users/$editorUuid');
    await tester.tap(find.byKey(const ValueKey('edit-roles-ALFA')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('role-editor')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('roles-save')));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Nie można nadać roli nieaktywnemu użytkownikowi'),
      findsOneWidget,
    );
  });

  testWidgets('invalid user id in the URL: not found, no API call', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    await pumpApp(tester, api: api, location: '/admin/users/..%2F..%2Fme');
    expect(find.text('Nie znaleziono strony'), findsOneWidget);
    expect(api.calls('GET', '/users/.*'), isEmpty);
    await unmountApp(tester);
  });

  testWidgets('company panel lists members and adds a person', (tester) async {
    setSurfaceSize(tester, const Size(1600, 1400));
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/companies/c-alfa/members',
      page([
        {
          'user_id': approverUuid,
          'display_name': 'Jan Zatwierdzający',
          'email': 'jan@example.com',
          'is_active': true,
          'roles': ['approver'],
        },
      ]),
    );
    api.on(
      'PUT',
      '/companies/c-alfa/members/$editorUuid',
      (r) => FakeResponse(200, {
        'user_id': editorUuid,
        'display_name': 'Ewa Edytorska',
        'email': 'ewa@example.com',
        'is_active': true,
        'roles': r.json['roles'],
      }),
    );
    await pumpApp(tester, api: api, location: '/admin/companies');
    await tester.tap(find.text('Alfa S.A.'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('member-$approverUuid')), findsOneWidget);

    await tester.ensureVisible(find.byKey(const ValueKey('member-add')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('member-add')));
    await tester.pumpAndSettle();
    // existing members are not offered
    expect(
      find.byKey(const ValueKey('user-option-$approverUuid')),
      findsNothing,
    );
    await tester.tap(find.byKey(const ValueKey('user-option-$editorUuid')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('role-editor')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('roles-save')));
    await tester.pumpAndSettle();
    expect(
      api.calls('PUT', '/companies/c-alfa/members/$editorUuid').single.json,
      {
        'roles': ['editor'],
      },
    );
  });
}
