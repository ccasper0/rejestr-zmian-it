import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/widgets/app_shell.dart';

import '../helpers.dart';

const _companyLabels = [
  'Rejestr zmian IT',
  'Rejestr zmian',
  'Do zatwierdzenia',
  'Obiekty (CI)',
  'Raporty i eksport',
  'Dziennik audytu',
];
const _adminLabels = ['Spółki i słowniki', 'Użytkownicy i role'];

const _wide = Size(1280, 900);

FakeApi _api({bool admin = false, bool auditor = false}) =>
    FakeApi()..installDefaults(
      me: meJson(
        admin: admin,
        alfaRoles: ['editor', if (auditor) 'auditor'],
        betaRoles: [if (auditor) 'auditor' else 'editor'],
      ),
    );

void main() {
  group('wide layout', () {
    testWidgets(
      'side panel with navigation from /me; admin section for admins',
      (tester) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(tester, api: _api(admin: true));

        final panel = find.byType(NavigationPanel);
        expect(panel, findsOneWidget);
        for (final label in [..._companyLabels, ..._adminLabels]) {
          expect(
            find.descendant(of: panel, matching: find.text(label)),
            findsOneWidget,
            reason: label,
          );
        }
        expect(
          find.descendant(of: panel, matching: find.text('ADMINISTRACJA')),
          findsOneWidget,
        );
        // Status and version on separate lines: nothing truncated.
        expect(find.text('API: połączono'), findsOneWidget);
        expect(find.text('v0.1.0'), findsOneWidget);
        expect(find.text('Ewa Edytorska'), findsWidgets);
        expect(find.text('Administrator · Edytor'), findsOneWidget);
        expect(tester.getSize(panel).width, 232);
        expect(find.byType(AppBar), findsNothing);
      },
    );

    testWidgets('no admin section without app admin role', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api());

      for (final label in _adminLabels) {
        expect(find.text(label), findsNothing);
      }
    });

    testWidgets('pending approvals badge comes from /stats', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api());

      final link = tester.widget<NavLink>(
        find.ancestor(
          of: find.text('Do zatwierdzenia').first,
          matching: find.byType(NavLink),
        ),
      );
      expect(link.badge, 2);
    });

    testWidgets('active link is highlighted and navigation updates URL', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final router = await pumpApp(tester, api: _api());

      NavLink link(String label) => tester.widget<NavLink>(
        find.ancestor(of: find.text(label), matching: find.byType(NavLink)),
      );

      expect(link('Rejestr zmian').selected, isTrue);
      expect(link('Obiekty (CI)').selected, isFalse);

      await tester.tap(find.text('Obiekty (CI)'));
      await tester.pumpAndSettle();

      expect(currentPath(router), '/c/ALFA/ci');
      expect(link('Obiekty (CI)').selected, isTrue);
      expect(link('Rejestr zmian').selected, isFalse);
    });

    testWidgets('global audit chain highlights "Dziennik audytu"', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api(admin: true), location: '/admin/audit');

      NavLink link(String label) => tester.widget<NavLink>(
        find.ancestor(of: find.text(label), matching: find.byType(NavLink)),
      );

      expect(link('Dziennik audytu').selected, isTrue);
      expect(link('Spółki i słowniki').selected, isFalse);
    });

    testWidgets('nav links have touch targets of at least 44 px', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api(admin: true));

      final links = find.byType(NavLink).evaluate().toList();
      expect(links, hasLength(7));
      for (final element in links) {
        expect(element.size!.height, greaterThanOrEqualTo(44));
      }
    });

    testWidgets('company switcher lists memberships and changes the URL', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final router = await pumpApp(
        tester,
        api: _api(auditor: true),
        location: '/c/ALFA/audit',
      );

      await tester.tap(find.byKey(const ValueKey('company-switcher')));
      await tester.pumpAndSettle();
      expect(find.text('Wszystkie spółki (audytor)'), findsWidgets);

      await tester.tap(find.text('Beta sp. z o.o.').last);
      await tester.pumpAndSettle();

      expect(currentPath(router), '/c/BETA/audit');
    });

    testWidgets('no cross-company option without the auditor role', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api());

      await tester.tap(find.byKey(const ValueKey('company-switcher')));
      await tester.pumpAndSettle();
      expect(find.text('Wszystkie spółki (audytor)'), findsNothing);
    });

    testWidgets('auditor "all companies" view lists the auditor companies', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final router = await pumpApp(
        tester,
        api: _api(auditor: true),
        location: '/c/all/changes',
      );

      expect(find.textContaining('Zbiorczego rejestru'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('all-companies-reports')),
        findsOneWidget,
      );
      await tester.tap(find.text('Beta sp. z o.o.').last);
      await tester.pumpAndSettle();
      expect(currentPath(router), '/c/BETA/changes');
    });

    testWidgets('root redirects to the first company from /me', (tester) async {
      setSurfaceSize(tester, _wide);
      final router = await pumpApp(tester, api: _api(), location: '/');

      expect(currentPath(router), '/c/ALFA/changes');
    });

    testWidgets('unknown company prefix shows no-access (like API 404)', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api(), location: '/c/ZETA/changes');

      expect(find.text('Brak dostępu'), findsOneWidget);
    });

    testWidgets('health indicator shows failure', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api(), health: healthFailing());

      expect(find.text('API: brak połączenia'), findsOneWidget);
    });
  });

  group('narrow layout', () {
    testWidgets('collapses navigation into a drawer', (tester) async {
      setSurfaceSize(tester, const Size(600, 900));
      final router = await pumpApp(tester, api: _api());

      expect(find.byType(NavigationPanel), findsNothing);
      expect(find.byType(AppBar), findsOneWidget);

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      final panel = find.byType(NavigationPanel);
      expect(panel, findsOneWidget);
      for (final label in _companyLabels) {
        expect(
          find.descendant(of: panel, matching: find.text(label)),
          findsOneWidget,
          reason: label,
        );
      }

      await tester.tap(
        find.descendant(of: panel, matching: find.text('Dziennik audytu')),
      );
      await tester.pumpAndSettle();

      expect(currentPath(router), '/c/ALFA/audit');
      expect(find.byType(NavigationPanel), findsNothing);
    });
  });
}
