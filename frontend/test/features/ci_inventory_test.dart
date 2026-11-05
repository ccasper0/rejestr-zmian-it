import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/features/ci/data/ci_filters.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);

Map<String, Object?> _ci(
  String id,
  String identifier,
  String name, {
  bool active = true,
  String? owner,
}) => {
  'id': id,
  'company_id': companyAlfa,
  'ci_type_id': 't-fw',
  'ci_type_code': 'firewall',
  'ci_type_name': 'Firewall',
  'identifier': identifier,
  'name': name,
  'description': null,
  'owner_user_id': owner,
  'is_active': active,
  'created_at': '2026-10-28T08:00:00Z',
  'updated_at': '2026-10-28T08:00:00Z',
};

FakeApi _api({Map<String, Object?>? me}) => FakeApi()
  ..installDefaults(me: me)
  ..reply(
    'GET',
    '/ci-types',
    page([
      {'id': 't-fw', 'code': 'firewall', 'name': 'Firewall', 'is_active': true},
      {'id': 't-srv', 'code': 'server', 'name': 'Serwer', 'is_active': true},
    ]),
  )
  ..reply(
    'GET',
    '/companies/c-alfa/ci',
    page([
      _ci('ci-1', 'FW-01', 'Zapora brzegowa', owner: userApprover),
      _ci('ci-2', 'FW-OLD', 'Stara zapora', active: false),
    ], total: 2),
  );

void main() {
  test('filters: URL <-> API', () {
    final filters = CiFilters.fromQuery({
      'q': ['fw'],
      'type': ['firewall', 'BAD TYPE', 'server'],
      'status': ['inactive'],
      'page': ['3'],
    });
    expect(filters.types, ['firewall', 'server']);
    expect(filters.active, isFalse);
    expect(
      filters.location('ALFA'),
      '/c/ALFA/ci?q=fw&type=firewall&type=server&status=inactive&page=3',
    );
    expect(filters.toApiQuery(), {
      'q': 'fw',
      'type': ['firewall', 'server'],
      'active': false,
      'limit': 50,
      'offset': 100,
    });
    expect(const CiFilters().location('ALFA'), '/c/ALFA/ci');
  });

  testWidgets('URL filters reach the API; the table shows the inventory', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(
      tester,
      api: api,
      location: '/c/ALFA/ci?q=fw&type=firewall&status=active',
    );
    final query = api.calls('GET', '/companies/c-alfa/ci').last.query;
    expect(query['q'], ['fw']);
    expect(query['type'], ['firewall']);
    expect(query['active'], ['true']);
    expect(find.text('FW-01'), findsOneWidget);
    expect(find.text('Jan Zatwierdzający'), findsOneWidget); // owner
    expect(find.text('Nieaktywny'), findsOneWidget);
    expect(find.text('Obiektów: 2'), findsOneWidget);
  });

  testWidgets('UI filters write the URL', (tester) async {
    setSurfaceSize(tester, _wide);
    final router = await pumpApp(tester, api: _api(), location: '/c/ALFA/ci');

    await tester.tap(find.text('Nieaktywne'));
    await tester.pumpAndSettle();
    expect(currentUri(router).toString(), '/c/ALFA/ci?status=inactive');

    await tester.enterText(find.byKey(const ValueKey('ci-search')), 'zapora');
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(
      currentUri(router).toString(),
      '/c/ALFA/ci?q=zapora&status=inactive',
    );

    await tester.tap(find.byKey(const ValueKey('ci-filters-clear')));
    await tester.pumpAndSettle();
    expect(currentUri(router).toString(), '/c/ALFA/ci');
  });

  testWidgets('viewer: read-only inventory', (tester) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(me: meJson(alfaRoles: const ['viewer'])),
      location: '/c/ALFA/ci',
    );
    expect(find.text('FW-01'), findsOneWidget);
    expect(find.byKey(const ValueKey('new-ci')), findsNothing);
  });

  testWidgets('editor adds a CI with an owner; identifier taken → inline', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    var attempts = 0;
    api.on('POST', '/companies/c-alfa/ci', (r) {
      attempts++;
      if (attempts == 1) {
        return FakeResponse.problem(
          409,
          'ci.identifier_taken',
          'Obiekt o identyfikatorze FW-01 już istnieje w tej spółce.',
        );
      }
      return FakeResponse(201, _ci('ci-3', 'FW-02', 'Zapora DMZ'));
    });
    await pumpApp(tester, api: api, location: '/c/ALFA/ci');

    await tester.tap(find.byKey(const ValueKey('new-ci')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ci-type')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Firewall').last);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('ci-identifier')),
      'FW-01',
    );
    await tester.enterText(find.byKey(const ValueKey('ci-name')), 'Zapora DMZ');
    await tester.tap(find.byKey(const ValueKey('ci-owner')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jan Zatwierdzający').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ci-save')));
    await tester.pumpAndSettle();

    expect(
      find.text('Obiekt o identyfikatorze FW-01 już istnieje w tej spółce.'),
      findsOneWidget,
    );
    await tester.enterText(
      find.byKey(const ValueKey('ci-identifier')),
      'FW-02',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('ci-save')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/companies/c-alfa/ci').last.json, {
      'ci_type_id': 't-fw',
      'identifier': 'FW-02',
      'name': 'Zapora DMZ',
      'description': null,
      'owner_user_id': userApprover,
    });
    expect(find.byKey(const ValueKey('ci-save')), findsNothing);
  });

  testWidgets('deactivation is a PATCH of is_active (no delete)', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    api.on(
      'PATCH',
      '/companies/c-alfa/ci/ci-1',
      (_) => FakeResponse(
        200,
        _ci('ci-1', 'FW-01', 'Zapora brzegowa', active: false),
      ),
    );
    await pumpApp(tester, api: api, location: '/c/ALFA/ci');
    await tester.tap(find.text('FW-01'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ci-active')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('ci-save')));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', '/companies/c-alfa/ci/ci-1').single.json, {
      'is_active': false,
    });
  });

  testWidgets('owner locked by a change: Polish message at the owner field', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    api.on(
      'PATCH',
      '/companies/c-alfa/ci/ci-1',
      (_) => FakeResponse.problem(
        409,
        'ci.owner_locked_by_change',
        'Nie można zmienić właściciela: CHG-ALFA-2026-0040 czeka na zgodę.',
      ),
    );
    await pumpApp(tester, api: api, location: '/c/ALFA/ci');
    await tester.tap(find.text('FW-01'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ci-owner')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('brak').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ci-save')));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('CHG-ALFA-2026-0040 czeka na zgodę'),
      findsOneWidget,
    );
  });

  testWidgets('admin without a role manages the CI on the admin path', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(me: adminMe())
      ..reply('GET', '/companies', page([companyJson()]));
    await pumpApp(tester, api: api, location: '/c/ALFA/ci');
    expect(find.text('FW-01'), findsOneWidget);
    expect(find.byKey(const ValueKey('new-ci')), findsOneWidget);
    expect(find.textContaining('jako administrator aplikacji'), findsOneWidget);
  });
}
