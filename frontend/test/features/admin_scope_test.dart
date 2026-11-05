// Owner decision 2026-11-02 (ADR 0015 §1): the admin's company switcher
// lists ALL companies; without a role the CI inventory and the audit log
// open on the admin path, the change register read-only (ADR 0016, see
// admin_read_only_register_test.dart).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);

void main() {
  testWidgets('switcher lists every company for the admin', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin(me: adminMe(alfaRoles: ['viewer']));
    final router = await pumpApp(
      tester,
      api: api,
      location: '/admin/companies',
    );
    await tester.tap(find.byKey(const ValueKey('company-switcher')));
    await tester.pumpAndSettle();
    // ALFA through the membership, BETA through the admin path
    expect(find.text('Alfa S.A.').last, findsOneWidget);
    expect(
      find.text('Beta sp. z o.o. (administrator, archiwum)').last,
      findsOneWidget,
    );
    await tester.tap(
      find.text('Beta sp. z o.o. (administrator, archiwum)').last,
    );
    await tester.pumpAndSettle();
    expect(currentPath(router), startsWith('/c/BETA/'));
  });

  testWidgets('nav links of an admin without roles point to a company', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply('GET', '/audit', page([]));
    final router = await pumpApp(
      tester,
      api: api,
      location: '/admin/companies',
    );
    await tester.tap(find.text('Dziennik audytu').first);
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/audit');
    expect(api.calls('GET', '/audit'), isNotEmpty);
  });
}
