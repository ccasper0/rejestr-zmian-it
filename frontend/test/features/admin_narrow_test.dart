// Narrow screens (< 900 px: drawer): the new screens lay out without
// overflow errors (a RenderFlex overflow fails a widget test).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _phone = Size(400, 900);

void main() {
  for (final location in [
    '/admin/companies',
    '/admin/categories',
    '/admin/ci-types',
    '/admin/permissions',
    '/admin/users',
    '/admin/audit',
  ]) {
    testWidgets('admin $location', (tester) async {
      setSurfaceSize(tester, _phone);
      final api = FakeApi()..installAdmin();
      api.reply('GET', '/permissions/matrix', {
        'roles': ['app_admin', 'approver', 'editor', 'auditor', 'viewer'],
        'actions': [
          {
            'action': 'company.manage',
            'label': 'Zarządzanie spółkami (dodaj, edytuj, archiwizuj)',
            'note': 'Także kategorie dostępne w spółce.',
            'roles': ['app_admin'],
          },
        ],
        'change_actions': <Object?>[],
      });
      api.reply('GET', '/audit', page([]));
      await pumpApp(tester, api: api, location: location);
      expect(find.byType(AppBar), findsOneWidget);
      expect(find.byKey(const ValueKey('no-access')), findsNothing);
    });
  }

  testWidgets('new company panel on a phone', (tester) async {
    setSurfaceSize(tester, _phone);
    final api = FakeApi()..installAdmin();
    await pumpApp(tester, api: api, location: '/admin/companies');
    await tester.tap(find.byKey(const ValueKey('new-company')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('company-prefix')), findsOneWidget);
  });

  for (final width in [1000.0, 1400.0]) {
    testWidgets('company edit panel at $width px', (tester) async {
      setSurfaceSize(tester, Size(width, 1000));
      final api = FakeApi()..installAdmin();
      await pumpApp(tester, api: api, location: '/admin/companies');
      await tester.tap(find.text('Alfa S.A.'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('company-categories-save')),
        findsOneWidget,
      );
    });
  }

  for (final location in ['/c/ALFA/ci', '/c/ALFA/audit']) {
    testWidgets('member $location', (tester) async {
      setSurfaceSize(tester, _phone);
      final api = FakeApi()
        ..installDefaults(me: meJson(alfaRoles: const ['editor', 'auditor']))
        ..reply('GET', '/audit', page([]));
      await pumpApp(tester, api: api, location: location);
      expect(find.byType(AppBar), findsOneWidget);
      expect(find.byKey(const ValueKey('no-access')), findsNothing);
    });
  }
}
