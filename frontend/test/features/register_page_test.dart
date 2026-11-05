import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/widgets/status_pill.dart';

import '../helpers.dart';

const _wide = Size(1400, 1000);

FakeApi _api() => FakeApi()
  ..installDefaults()
  ..reply(
    'GET',
    '/companies/c-alfa/changes',
    page([
      changeJson(
        number: 'CHG-ALFA-2026-0003',
        status: 'verified',
        type: 'standard',
        autoApproved: true,
        approvedAt: '2026-10-05T06:55:58Z',
        implementedAt: '2026-10-06T06:25:58Z',
      ),
      changeJson(
        id: 'ch-2',
        number: 'CHG-ALFA-2026-0004',
        status: 'implemented',
        type: 'emergency',
        approvedBy: userRef(userApprover, 'Jan Zatwierdzający'),
        approvedAt: '2026-10-07T10:00:00Z',
        implementedAt: '2026-10-07T09:00:00Z',
      ),
    ], total: 120),
  );

void main() {
  testWidgets(
    'table rows: mono ID, status pill, actual approver, Warsaw time',
    (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api());

      expect(find.text('Alfa S.A.'), findsWidgets);
      expect(find.text('CHG-ALFA-2026-0003'), findsOneWidget);
      expect(find.byType(StatusPill), findsNWidgets(2));
      // auto-approved standard change: "system", not the designated approver
      expect(find.text('system'), findsOneWidget);
      expect(find.text('(automatycznie)'), findsOneWidget);
      expect(find.text('Jan Zatwierdzający'), findsOneWidget);
      // 06:25 UTC on 6 Oct = 08:25 CEST
      expect(find.text('06.10.2026 08:25'), findsOneWidget);
      expect(find.text('Awaryjna'), findsOneWidget);
      // tiles from /stats
      expect(find.text('Wdrożone bez weryfikacji'), findsOneWidget);
      expect(find.text('w tym bez zatwierdzenia w 24 h: 1'), findsOneWidget);
      // footer
      expect(
        find.text('Wyświetlono 1–2 z 120', findRichText: true),
        findsOneWidget,
      );
      expect(find.text('Strona 1 z 3'), findsOneWidget);
      // editor may create changes; register export is not his (§5)
      expect(find.byKey(const ValueKey('new-change')), findsOneWidget);
      expect(find.byKey(const ValueKey('register-export-csv')), findsNothing);
    },
  );

  testWidgets('filters from the URL are sent to the API', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(
      tester,
      api: api,
      location:
          '/c/ALFA/changes?status=pending_approval&type=emergency'
          '&approved_by=system&q=zapora&sort=number&page=2',
    );

    final query = api.calls('GET', '/companies/c-alfa/changes').last.query;
    expect(query['status'], ['pending_approval']);
    expect(query['type'], ['emergency']);
    expect(query['approved_by'], ['system']);
    expect(query['q'], ['zapora']);
    expect(query['sort'], ['number']);
    expect(query['offset'], ['50']);
    // UI reflects the URL
    expect(find.text('Status: Do zatwierdzenia'), findsOneWidget);
    expect(find.text('Typ: Awaryjna'), findsOneWidget);
    expect(find.text('Zatwierdził: system'), findsOneWidget);
    final search = tester.widget<TextField>(
      find.byKey(const ValueKey('register-search')),
    );
    expect(search.controller!.text, 'zapora');
  });

  testWidgets('tile and filter changes are written to the URL', (tester) async {
    setSurfaceSize(tester, _wide);
    final router = await pumpApp(tester, api: _api());

    await tester.tap(find.byKey(const ValueKey('tile-pending')));
    await tester.pumpAndSettle();
    expect(
      currentUri(router).toString(),
      '/c/ALFA/changes?status=pending_approval',
    );

    await tester.tap(find.byKey(const ValueKey('filter-type')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Awaryjna').last);
    await tester.tap(find.text('Zastosuj'));
    await tester.pumpAndSettle();
    expect(currentUri(router).queryParametersAll, {
      'status': ['pending_approval'],
      'type': ['emergency'],
    });

    await tester.enterText(
      find.byKey(const ValueKey('register-search')),
      'SD-1234',
    );
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(currentUri(router).queryParameters['q'], 'SD-1234');

    await tester.tap(find.byKey(const ValueKey('filters-clear')));
    await tester.pumpAndSettle();
    expect(currentUri(router).toString(), '/c/ALFA/changes');
  });

  testWidgets('sorting by a column and paging update the URL', (tester) async {
    setSurfaceSize(tester, _wide);
    final router = await pumpApp(tester, api: _api());

    await tester.tap(find.text('ID'));
    await tester.pumpAndSettle();
    expect(currentUri(router).queryParameters['sort'], 'number');

    await tester.tap(find.byTooltip('Następna strona'));
    await tester.pumpAndSettle();
    expect(currentUri(router).queryParameters['page'], '2');
  });

  testWidgets('row opens the change card by number', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply(
        'GET',
        '/companies/c-alfa/changes/by-number/CHG-ALFA-2026-0003',
        changeJson(number: 'CHG-ALFA-2026-0003', status: 'verified'),
      );
    final router = await pumpApp(tester, api: api);

    await tester.tap(find.text('CHG-ALFA-2026-0003'));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/changes/CHG-ALFA-2026-0003');
  });

  testWidgets('viewer has no "Nowa zmiana" button', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply('GET', '/me', meJson(alfaRoles: ['viewer'], betaRoles: []));
    await pumpApp(tester, api: api);

    expect(find.byKey(const ValueKey('new-change')), findsNothing);
  });
}
