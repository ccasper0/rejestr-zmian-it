import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/features/admin/presentation/categories_tab.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);

void main() {
  group('category tree', () {
    testWidgets('two levels: subcategory under its parent, rules shown', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      await pumpApp(tester, api: api, location: '/admin/categories');

      Offset label(String code) => tester.getTopLeft(
        find.textContaining('$code  ', findRichText: true).first,
      );
      final acc = label('ACC');
      final priv = label('ACC-PRIV');
      final fw = label('FW');
      final nat = label('FW-NAT');
      // order: ACC, ACC-PRIV, FW, FW-NAT
      expect(priv.dy, greaterThan(acc.dy));
      expect(fw.dy, greaterThan(priv.dy));
      expect(nat.dy, greaterThan(fw.dy));
      // left-aligned: every category at the same x, every subcategory at the
      // same fixed indent (review of stage 6: rows were centred)
      expect(fw.dx, acc.dx);
      expect(priv.dx, greaterThan(acc.dx));
      expect(nat.dx, priv.dx);
      final card = tester.getTopLeft(find.byType(CategoryTree));
      expect(acc.dx - card.dx, lessThan(40));
      expect(find.text('standard — bez zatwierdzenia'), findsOneWidget);
      expect(find.text('zgoda właściciela CI'), findsOneWidget);
      expect(
        find.textContaining('Podkategoria może tylko zaostrzyć'),
        findsOneWidget,
      );
      // a subcategory of a category requiring approval shows the inherited rule
      expect(find.text('wymaga zatwierdzenia (z kategorii)'), findsOneWidget);
    });

    testWidgets('activity filter lives in the URL', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      final router = await pumpApp(
        tester,
        api: api,
        location: '/admin/categories?status=inactive',
      );
      // inactive: OLD and FW-NAT (with its active parent dimmed for context)
      expect(find.byKey(const ValueKey('category-OLD')), findsOneWidget);
      expect(find.byKey(const ValueKey('category-FW-NAT')), findsOneWidget);
      expect(find.byKey(const ValueKey('category-FW')), findsOneWidget);
      expect(find.byKey(const ValueKey('category-ACC')), findsNothing);

      await tester.tap(find.text('Aktywne'));
      await tester.pumpAndSettle();
      expect(currentUri(router).toString(), '/admin/categories?status=active');
      expect(find.byKey(const ValueKey('category-OLD')), findsNothing);
      expect(find.byKey(const ValueKey('category-ACC')), findsOneWidget);
    });

    testWidgets(
      'subcategory of an approval category cannot lift the requirement',
      (tester) async {
        setSurfaceSize(tester, _wide);
        final api = FakeApi()..installAdmin();
        api.on(
          'POST',
          '/categories',
          (r) => FakeResponse(
            201,
            categoryJson(
              id: 'cat-fw-vpn',
              code: r.json['code']! as String,
              name: r.json['name']! as String,
              parentId: 'cat-fw',
            ),
          ),
        );
        await pumpApp(tester, api: api, location: '/admin/categories');

        await tester.tap(find.byKey(const ValueKey('add-sub-FW')));
        await tester.pumpAndSettle();
        final checkbox = tester.widget<CheckboxListTile>(
          find.byKey(const ValueKey('category-requires-approval')),
        );
        expect(checkbox.value, isTrue);
        expect(checkbox.onChanged, isNull);
        expect(
          find.textContaining('podkategoria nie może znieść tego wymogu'),
          findsOneWidget,
        );

        await tester.enterText(
          find.byKey(const ValueKey('category-code')),
          'fw-vpn',
        );
        await tester.pump();
        expect(find.textContaining('Od 2 do 32 znaków'), findsOneWidget);
        await tester.enterText(
          find.byKey(const ValueKey('category-code')),
          'FW-VPN',
        );
        await tester.enterText(
          find.byKey(const ValueKey('category-name')),
          'VPN',
        );
        await tester.pump();
        await tester.tap(find.byKey(const ValueKey('category-save')));
        await tester.pumpAndSettle();

        expect(api.calls('POST', '/categories').single.json, {
          'code': 'FW-VPN',
          'name': 'VPN',
          'parent_id': 'cat-fw',
          'requires_approval': true,
          'default_risk': 'medium',
          'requires_ci_owner_consent': false,
        });
      },
    );

    testWidgets('edit: code read-only, deactivation instead of delete', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      api.reply(
        'PATCH',
        '/categories/cat-ot',
        categoryJson(
          id: 'cat-ot',
          code: 'OT',
          name: 'Systemy OT',
          active: false,
        ),
      );
      await pumpApp(tester, api: api, location: '/admin/categories');

      await tester.tap(find.byKey(const ValueKey('edit-OT')));
      await tester.pumpAndSettle();
      final code = tester.widget<TextField>(
        find.descendant(
          of: find.byKey(const ValueKey('category-code')),
          matching: find.byType(TextField),
        ),
      );
      expect(code.readOnly, isTrue);
      await tester.tap(find.text('Anuluj'));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const ValueKey('toggle-OT')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('toggle-confirm')));
      await tester.pumpAndSettle();
      expect(api.calls('PATCH', '/categories/cat-ot').single.json, {
        'is_active': false,
      });
    });

    testWidgets('closing a dirty editor asks before discarding', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      await pumpApp(tester, api: api, location: '/admin/categories');
      await tester.tap(find.byKey(const ValueKey('new-category')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const ValueKey('category-name')), 'X');
      await tester.pump();
      await tester.tap(find.text('Anuluj'));
      await tester.pumpAndSettle();
      expect(find.text('Odrzucić niezapisane zmiany?'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('discard-confirm')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('category-name')), findsNothing);
    });
  });

  testWidgets('CI types: list, new type with code validation', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/ci-types',
      page([
        {'id': 't-1', 'code': 'server', 'name': 'Serwer', 'is_active': true},
        {'id': 't-2', 'code': 'other', 'name': 'Inne', 'is_active': false},
      ]),
    );
    api.on(
      'POST',
      '/ci-types',
      (r) => FakeResponse(201, {
        'id': 't-3',
        'code': r.json['code'],
        'name': r.json['name'],
        'is_active': true,
      }),
    );
    await pumpApp(tester, api: api, location: '/admin/ci-types');
    expect(find.text('Serwer'), findsOneWidget);
    expect(find.text('Nieaktywny'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('new-ci-type')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('ci-type-code')), 'Lb');
    await tester.pump();
    expect(find.textContaining('małe litery a–z'), findsOneWidget);
    await tester.enterText(
      find.byKey(const ValueKey('ci-type-code')),
      'load_balancer',
    );
    await tester.enterText(
      find.byKey(const ValueKey('ci-type-name')),
      'Load balancer',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('ci-type-save')));
    await tester.pumpAndSettle();
    expect(api.calls('POST', '/ci-types').single.json, {
      'code': 'load_balancer',
      'name': 'Load balancer',
    });
  });

  testWidgets('permission matrix is rendered from the API, read-only', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply('GET', '/permissions/matrix', {
      'roles': ['app_admin', 'approver', 'editor', 'auditor', 'viewer'],
      'actions': [
        {
          'action': 'change.approve',
          'label': 'Zatwierdzanie, odrzucanie, zwrot do poprawy',
          'note': 'Nie własnych zmian (zasada czterech oczu).',
          'roles': ['approver'],
        },
        {
          'action': 'register.view',
          'label': 'Podgląd rejestru',
          'note':
              'Administrator bez roli w spółce — tylko odczyt: bez akcji, '
              'edycji, komentarzy i pobierania plików załączników (widzi ich '
              'listę z sha256).',
          'roles': ['app_admin', 'approver', 'editor', 'auditor', 'viewer'],
        },
      ],
      'change_actions': [
        {'action': 'approve', 'requires': 'change.approve'},
      ],
    });
    await pumpApp(tester, api: api, location: '/admin/permissions');

    expect(find.byKey(const ValueKey('permission-matrix')), findsOneWidget);
    expect(
      find.text('Zatwierdzanie, odrzucanie, zwrot do poprawy'),
      findsOneWidget,
    );
    expect(
      find.text('Nie własnych zmian (zasada czterech oczu).'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Administrator bez roli w spółce — tylko odczyt'),
      findsOneWidget,
    );
    // 1 + 5 checks
    expect(find.byIcon(Icons.check), findsNWidgets(6));
    // nothing editable on the screen
    expect(find.byType(Checkbox), findsNothing);
    expect(find.byType(TextField), findsNothing);
  });
}
