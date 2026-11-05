import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/time.dart';
import 'package:rejestr_zmian/features/admin/data/validation.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1600, 1200);

Future<void> _enter(WidgetTester tester, String key, String text) async {
  await tester.enterText(find.byKey(ValueKey(key)), text);
  await tester.pump();
}

void main() {
  group('validation (UX copy of the backend rules)', () {
    test('prefix, example number', () {
      expect(validatePrefix('DELTA'), isNull);
      expect(validatePrefix('D'), isNotNull);
      expect(validatePrefix('DELTA1'), isNotNull);
      expect(validatePrefix('ŻETA'), isNotNull);
      expect(validatePrefix('ABCDEFGHI'), isNotNull);
      expect(exampleChangeNumber('DELTA', 2026), 'CHG-DELTA-2026-0001');
    });

    test('NIP: separators and PL prefix, checksum', () {
      expect(validateNip(''), isNull);
      expect(validateNip('526-025-09-95'), isNull);
      expect(validateNip('PL 5260250995'), isNull);
      expect(normalizeNip('PL 526-025-09-95'), '5260250995');
      expect(validateNip('5260250994'), 'NIP ma nieprawidłową sumę kontrolną.');
      expect(validateNip('12345'), 'NIP musi składać się z 10 cyfr.');
    });

    test('dictionary codes', () {
      expect(validateCategoryCode('NET-VLAN'), isNull);
      expect(validateCategoryCode('net'), isNotNull);
      expect(validateCategoryCode('N'), isNotNull);
      expect(validateCiTypeCode('network_device'), isNull);
      expect(validateCiTypeCode('Server'), isNotNull);
    });
  });

  testWidgets('non-admin: "Brak dostępu", no admin API call, no admin nav', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installDefaults();
    await pumpApp(tester, api: api, location: '/admin/companies');

    expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
    expect(find.text('Spółki i słowniki'), findsNothing);
    expect(api.calls('GET', '/companies'), isEmpty);
    expect(api.calls('GET', '/users'), isEmpty);
  });

  testWidgets('table: prefix, counters, status', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    await pumpApp(tester, api: api, location: '/admin/companies');

    expect(find.byKey(const ValueKey('companies-table')), findsOneWidget);
    expect(find.text('ALFA'), findsOneWidget);
    expect(find.text('12'), findsOneWidget); // active CI
    expect(find.text('Zarchiwizowana'), findsOneWidget);
    expect(find.text('NIP 5260250995 · uoKSC'), findsOneWidget);
    for (final tab in [
      'Spółki',
      'Kategorie zmian',
      'Typy obiektów (CI)',
      'Role i uprawnienia',
    ]) {
      expect(find.text(tab), findsOneWidget);
    }
  });

  testWidgets(
    'new company: prefix validated inline, example ID, then POST + PUT',
    (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      api.on(
        'POST',
        '/companies',
        (r) => FakeResponse(
          201,
          companyJson(
              id: companyDelta,
              name: r.json['name']! as String,
              prefix: r.json['prefix']! as String,
              taxId: r.json['tax_id'] as String?,
              ksc: r.json['is_ksc_entity']! as bool,
              counts: const {},
            )
            ..remove('counts')
            ..remove('my_roles'),
        ),
      );
      api.reply('PUT', '/companies/c-delta/categories', {'items': <Object?>[]});
      await pumpApp(tester, api: api, location: '/admin/companies');

      await tester.tap(find.byKey(const ValueKey('new-company')));
      await tester.pumpAndSettle();
      expect(find.text('Nowa spółka'), findsWidgets);

      final year = WarsawTime.toWarsaw(DateTime.now()).year;
      // lower case is upper-cased; digits are not allowed
      await _enter(tester, 'company-prefix', 'de1');
      expect(find.text('DE1'), findsOneWidget);
      expect(
        find.text('Od 2 do 8 wielkich liter A–Z (bez polskich znaków i cyfr).'),
        findsOneWidget,
      );
      expect(
        find.textContaining('CHG-…-$year-0001', findRichText: true),
        findsOneWidget,
      );
      await _enter(tester, 'company-prefix', 'delta');
      expect(
        find.textContaining('CHG-DELTA-$year-0001', findRichText: true),
        findsOneWidget,
      );
      expect(
        find.text('Od 2 do 8 wielkich liter A–Z (bez polskich znaków i cyfr).'),
        findsNothing,
      );

      await _enter(tester, 'company-nip', '5260250994');
      expect(find.text('NIP ma nieprawidłową sumę kontrolną.'), findsOneWidget);
      await _enter(tester, 'company-nip', '526-025-09-95');
      await _enter(tester, 'company-name', 'Delta sp. z o.o.');
      await tester.tap(find.byKey(const ValueKey('company-ksc')));
      await tester.pump();
      // all active top-level categories are ticked; untick OT
      await tester.ensureVisible(find.byKey(const ValueKey('new-category-OT')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('new-category-OT')));
      await tester.pump();
      expect(find.byKey(const ValueKey('new-category-OLD')), findsNothing);

      await tester.ensureVisible(find.byKey(const ValueKey('company-save')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('company-save')));
      await tester.pumpAndSettle();

      final post = api.calls('POST', '/companies').single.json;
      expect(post, {
        'name': 'Delta sp. z o.o.',
        'prefix': 'DELTA',
        'tax_id': '5260250995',
        'is_ksc_entity': true,
        'default_approver_id': null,
      });
      final put = api.calls('PUT', '/companies/c-delta/categories').single;
      expect(put.json['categories'], [
        {'category_id': 'cat-acc', 'approver_override_id': null},
        {'category_id': 'cat-fw', 'approver_override_id': null},
      ]);
      // the panel switches to the new company with the next step
      expect(find.byKey(const ValueKey('company-notice')), findsOneWidget);
    },
  );

  testWidgets('409 name_taken is shown under the name field', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.on(
      'POST',
      '/companies',
      (_) => FakeResponse.problem(
        409,
        'company.name_taken',
        'Spółka o tej nazwie już istnieje.',
      ),
    );
    await pumpApp(tester, api: api, location: '/admin/companies');
    await tester.tap(find.byKey(const ValueKey('new-company')));
    await tester.pumpAndSettle();
    await _enter(tester, 'company-name', 'Alfa S.A.');
    await _enter(tester, 'company-prefix', 'ALFB');
    await tester.ensureVisible(find.byKey(const ValueKey('company-save')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('company-save')));
    await tester.pumpAndSettle();

    expect(find.text('Spółka o tej nazwie już istnieje.'), findsOneWidget);
    expect(api.calls('PUT', '/companies/.*/categories'), isEmpty);
  });

  testWidgets('edit: prefix read-only, PATCH sends only changed fields', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply('PATCH', '/companies/c-alfa', companyJson(ksc: false));
    await pumpApp(tester, api: api, location: '/admin/companies');

    await tester.tap(find.text('Alfa S.A.'));
    await tester.pumpAndSettle();
    final prefix = tester.widget<TextField>(
      find.descendant(
        of: find.byKey(const ValueKey('company-prefix')),
        matching: find.byType(TextField),
      ),
    );
    expect(prefix.readOnly, isTrue);
    expect(
      find.text('Prefiks jest niezmienny po utworzeniu spółki.'),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('company-ksc')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('company-save')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', '/companies/c-alfa').single.json, {
      'is_ksc_entity': false,
    });
  });

  testWidgets('archive asks with consequences and the typed prefix', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'POST',
      '/companies/c-alfa/archive',
      companyJson(status: 'archived'),
    );
    await pumpApp(tester, api: api, location: '/admin/companies');
    await tester.tap(find.text('Alfa S.A.'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.byKey(const ValueKey('company-archive')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('company-archive')));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('inwentarz obiektów (CI) zostaje zamrożony'),
      findsOneWidget,
    );
    final confirm = find.byKey(const ValueKey('archive-confirm'));
    expect(tester.widget<FilledButton>(confirm).onPressed, isNull);
    await tester.enterText(
      find.byKey(const ValueKey('archive-confirm-prefix')),
      'ALFA',
    );
    await tester.pump();
    await tester.tap(confirm);
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/companies/c-alfa/archive'), hasLength(1));
  });

  testWidgets('leaving with unsaved panel edits asks first', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    final router = await pumpApp(
      tester,
      api: api,
      location: '/admin/companies',
    );
    await tester.tap(find.byKey(const ValueKey('new-company')));
    await tester.pumpAndSettle();
    await _enter(tester, 'company-name', 'Niedokończona');

    await tester.tap(find.byKey(const ValueKey('admin-tab-categories')));
    await tester.pumpAndSettle();
    expect(find.text('Odrzucić niezapisane zmiany?'), findsOneWidget);
    await tester.tap(find.text('Wróć do edycji'));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/admin/companies');

    await tester.tap(find.byKey(const ValueKey('admin-tab-categories')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('discard-confirm')));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/admin/categories');
  });
}
