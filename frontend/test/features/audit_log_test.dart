import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/time.dart';
import 'package:rejestr_zmian/features/audit/data/audit_filters.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1100);
const _actor = '00000000-0000-4000-8000-0000000000aa';

Map<String, Object?> _entry(
  int seq, {
  String entity = 'ci',
  String action = 'update',
  Map<String, Object?> diff = const {},
  Map<String, Object?> context = const {},
}) => {
  'id': 1000 + seq,
  'company_id': companyAlfa,
  'seq': seq,
  'occurred_at': '2026-10-29T10:15:00Z',
  'actor_id': userEditor,
  'actor_display': 'Ewa Edytorska',
  'actor_roles': ['editor'],
  'ip_address': '10.0.0.5',
  'user_agent': 'Mozilla/5.0',
  'request_id': '7d3c1a52-6c44-4a9e-9f6e-2b3b9a1f0c11',
  'entity_type': entity,
  'entity_id': 'ci-1',
  'action': action,
  'diff': diff,
  'context': context,
  'prev_hash': 'a' * 64,
  'hash': 'b' * 64,
};

FakeApi _api({Map<String, Object?>? me}) => FakeApi()
  ..installDefaults(me: me ?? meJson(alfaRoles: const ['auditor']))
  ..reply(
    'GET',
    '/audit',
    page([
      _entry(
        42,
        diff: {
          'name': {'before': 'Zapora', 'after': 'Zapora brzegowa'},
        },
        context: {'identifier': 'FW-01'},
      ),
      _entry(
        41,
        entity: 'membership',
        action: 'role_grant',
        diff: {
          'roles': {
            'before': <String>[],
            'after': ['auditor'],
          },
        },
      ),
    ], total: 120),
  );

void main() {
  test('every backend audit action has a Polish label', () {
    // Mirror of app.domain.audit.AuditAction (backend/app/domain/audit.py).
    const backendActions = {
      'create',
      'update',
      'transition',
      'archive',
      'deactivate',
      'attach',
      'download',
      'comment',
      'export',
      'login',
      'login_failed',
      'logout',
      'token_refresh',
      'session_revoke',
      'lockout',
      'password_change',
      'password_reset',
      'role_grant',
      'role_revoke',
      'access_denied',
      'verify',
    };
    expect(AuditFilters.actions.keys.toSet(), backendActions);
  });

  test('filters: URL <-> API (Warsaw days, exclusive end)', () {
    WarsawTime.ensureInitialized();
    final filters = AuditFilters.fromQuery({
      'entity': 'change',
      'action': 'transition',
      'actor': _actor,
      'from': '2026-10-01',
      'to': '2026-10-31',
      'page': '2',
    });
    expect(
      filters.location('/c/ALFA/audit'),
      '/c/ALFA/audit?entity=change&action=transition&actor=$_actor'
      '&from=2026-10-01&to=2026-10-31&page=2',
    );
    expect(filters.toApiQuery(), {
      'entity_type': 'change',
      'action': 'transition',
      'actor_id': _actor,
      // 1 Oct 00:00 CEST; 1 Nov 00:00 CET (DST ended on 25 Oct)
      'occurred_from': '2026-09-30T22:00:00.000Z',
      'occurred_to': '2026-10-31T23:00:00.000Z',
      'limit': 50,
      'offset': 50,
    });
    // unknown values are dropped instead of a 422 from the API
    final bad = AuditFilters.fromQuery({
      'entity': 'nope',
      'action': 'drop_table',
      'actor': '../me',
      'from': '2026-02-31',
    });
    expect(bad.hasFilters, isFalse);
  });

  testWidgets('auditor: entries with diff, URL filters reach the API', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(
      tester,
      api: api,
      location: '/c/ALFA/audit?entity=ci&action=update',
    );
    final query = api.calls('GET', '/audit').last.query;
    expect(query['company_id'], [companyAlfa]);
    expect(query['entity_type'], ['ci']);
    expect(query['action'], ['update']);

    expect(find.text('Łańcuch spójny'), findsOneWidget);
    expect(find.text('29.10.2026 11:15 · IP 10.0.0.5'), findsNWidgets(2));
    expect(
      find.textContaining('Obiekt (CI): Edycja', findRichText: true),
      findsOneWidget,
    );
    // DiffLine: old value struck through, new value (semantic labels)
    expect(
      find.text(
        'Nazwa: przed: Zapora → po: Zapora brzegowa',
        findRichText: true,
      ),
      findsOneWidget,
    );
    expect(find.text('Role: po: Audytor', findRichText: true), findsOneWidget);
    expect(find.text('Wpisów: 120'), findsOneWidget);
    expect(find.byKey(const ValueKey('verify-chain')), findsOneWidget);
  });

  testWidgets('UI filters write the URL', (tester) async {
    setSurfaceSize(tester, _wide);
    final router = await pumpApp(
      tester,
      api: _api(),
      location: '/c/ALFA/audit',
    );

    await tester.tap(find.byKey(const ValueKey('audit-filter-action')));
    await tester.pumpAndSettle();
    // The action list is longer than the menu: scroll the item into view.
    await tester.ensureVisible(find.text('Nadanie roli'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Nadanie roli'));
    await tester.pumpAndSettle();
    expect(currentUri(router).toString(), '/c/ALFA/audit?action=role_grant');

    await tester.tap(find.byKey(const ValueKey('audit-filter-actor')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jan Zatwierdzający'));
    await tester.pumpAndSettle();
    expect(
      currentUri(router).toString(),
      '/c/ALFA/audit?action=role_grant&actor=$userApprover',
    );

    await tester.tap(find.byTooltip('Starsze wpisy'));
    await tester.pumpAndSettle();
    expect(currentUri(router).queryParameters['page'], '2');
  });

  testWidgets('verify: POST for the company chain, result shown', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply('POST', '/audit/verify', {
        'company_id': companyAlfa,
        'chain': 'company',
        'ok': false,
        'checked': 120,
        'first_broken_seq': 42,
        'head_seq': 120,
        'head_hash': 'c' * 64,
        'verified_at': '2026-10-30T09:00:00Z',
        'recorded_in': 'global',
        'audit_entry': {'company_id': null, 'seq': 900, 'hash': 'd' * 64},
      });
    await pumpApp(tester, api: api, location: '/c/ALFA/audit');

    await tester.tap(find.byKey(const ValueKey('verify-chain')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/audit/verify').single.query['company_id'], [
      companyAlfa,
    ]);
    expect(
      find.text('Łańcuch spółki naruszony — pierwszy niezgodny wpis #42'),
      findsOneWidget,
    );
    expect(find.text('Pierwszy niezgodny wpis'), findsOneWidget);
  });

  testWidgets('editor: no access to the whole log, no API call', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(me: meJson());
    await pumpApp(tester, api: api, location: '/c/ALFA/audit');
    expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
    expect(find.byKey(const ValueKey('verify-chain')), findsNothing);
    expect(api.calls('GET', '/audit'), isEmpty);
  });

  testWidgets('admin: global chain without company_id', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply(
      'GET',
      '/audit',
      page([
        {
          ..._entry(7, entity: 'company', action: 'create'),
          'company_id': null,
          'actor_id': null,
          'actor_display': 'system',
          'actor_roles': <String>[],
          'context': {'prefix': 'DELTA'},
        },
      ]),
    );
    await pumpApp(tester, api: api, location: '/admin/audit');
    final query = api.calls('GET', '/audit').last.query;
    expect(query.containsKey('company_id'), isFalse);
    expect(find.text('Łańcuch globalny'), findsWidgets);
    expect(
      find.textContaining('system — Spółka: Utworzenie', findRichText: true),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('verify-chain')), findsOneWidget);
  });

  testWidgets('non-admin cannot open the global chain', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(tester, api: api, location: '/admin/audit');
    expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
    expect(api.calls('GET', '/audit'), isEmpty);
  });
  testWidgets('diffs show names and Polish labels, never raw ids or keys', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    const typeA = '11111111-0000-4000-8000-000000000001';
    const typeB = '11111111-0000-4000-8000-000000000002';
    final api = _api()
      ..reply(
        'GET',
        '/ci-types',
        page([
          {'id': typeA, 'code': 'server', 'name': 'Serwer', 'is_active': true},
          {
            'id': typeB,
            'code': 'firewall',
            'name': 'Firewall',
            'is_active': true,
          },
        ]),
      )
      ..reply(
        'GET',
        '/categories',
        page([
          {
            'id': 'cat-fw',
            'code': 'FW',
            'name': 'Firewall / sieć',
            'parent_id': null,
            'requires_approval': true,
            'requires_ci_owner_consent': false,
            'default_risk': 'medium',
            'is_active': true,
          },
        ]),
      )
      ..reply(
        'GET',
        '/audit',
        page([
          _entry(
            5,
            diff: {
              'ci_type_id': {'before': typeA, 'after': typeB},
              'description': {'before': null, 'after': 'Brzeg sieci'},
              'owner_user_id': {'before': null, 'after': userApprover},
            },
          ),
          _entry(
            4,
            entity: 'company_category',
            diff: {
              'FW': {
                'before': null,
                'after': {'approver_override_id': userApprover},
              },
              'ACC': {
                'before': {'approver_override_id': null},
                'after': null,
              },
            },
          ),
          _entry(
            3,
            entity: 'category',
            action: 'create',
            diff: {
              'parent_id': {'before': null, 'after': 'cat-fw'},
              'requires_approval': {'before': null, 'after': true},
            },
          ),
          _entry(
            2,
            entity: 'company',
            diff: {
              'status': {'before': 'active', 'after': 'archived'},
            },
          ),
        ]),
      );
    await pumpApp(tester, api: api, location: '/c/ALFA/audit');

    Finder line(String text) => find.text(text, findRichText: true);
    expect(line('Typ obiektu: przed: Serwer → po: Firewall'), findsOneWidget);
    expect(line('Opis: po: Brzeg sieci'), findsOneWidget);
    expect(line('Właściciel: po: Jan Zatwierdzający'), findsOneWidget);
    expect(
      line(
        'Kategoria FW: przed: niedostępna → po: dostępna (zatwierdzający: '
        'Jan Zatwierdzający)',
      ),
      findsOneWidget,
    );
    expect(
      line(
        'Kategoria ACC: przed: dostępna (zatwierdzający: domyślny spółki) → '
        'po: niedostępna',
      ),
      findsOneWidget,
    );
    expect(
      line('Kategoria nadrzędna: po: FW — Firewall / sieć'),
      findsOneWidget,
    );
    expect(line('Wymaga zatwierdzenia: po: tak'), findsOneWidget);
    expect(
      line('Status spółki: przed: aktywna → po: zarchiwizowana'),
      findsOneWidget,
    );
    expect(
      find.textContaining('approver_override_id', findRichText: true),
      findsNothing,
    );
    expect(find.textContaining(typeA, findRichText: true), findsNothing);
  });

  testWidgets('admin without a role reads the company log (admin path)', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()..installAdmin();
    api.reply('GET', '/audit', page([_entry(9)]));
    await pumpApp(tester, api: api, location: '/c/ALFA/audit');
    expect(api.calls('GET', '/audit').last.query['company_id'], [companyAlfa]);
    expect(find.byKey(const ValueKey('verify-chain')), findsOneWidget);
    expect(find.byKey(const ValueKey('no-access')), findsNothing);
  });
}
