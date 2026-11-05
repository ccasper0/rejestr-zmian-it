// Correction of a frozen change from the UI (CLAUDE.md §4.2, ADR 0021).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/features/changes/data/models.dart';
import 'package:rejestr_zmian/features/changes/presentation/correction.dart';

import '../helpers.dart';

const _wide = Size(1400, 2600);
const _original = 'CHG-ALFA-2026-0001';
const _correction = 'CHG-ALFA-2026-0002';
const _cardPath = '/c/ALFA/changes/$_original';
const _changes = '/companies/c-alfa/changes';

Map<String, Object?> _verified({String status = 'verified'}) => {
  ...changeJson(
    status: status,
    risk: 'high',
    allowedActions: const [],
    implementedAt: '2026-11-02T19:00:00Z',
  ),
  'subcategory': {'id': 'sub-rules', 'code': 'FW-RULES', 'name': 'Reguły'},
  'verifier': userRef(userApprover, 'Jan Zatwierdzający'),
  'verified_at': '2026-11-03T08:00:00Z',
};

Map<String, Object?> _correctedOriginal() => {
  ..._verified(),
  'superseded_by': [
    {'id': 'ch-2', 'number': _correction, 'status': 'draft'},
    {'id': 'ch-3', 'number': 'CHG-ALFA-2026-0003', 'status': 'cancelled'},
  ],
};

Map<String, Object?> _correctionDraft() => {
  ...changeJson(
    id: 'ch-2',
    number: _correction,
    title: 'Korekta: Aktualizacja reguł zapory',
    risk: 'high',
  ),
  'window_start': null,
  'window_end': null,
  'supersedes_change_id': 'ch-1',
  'supersedes_number': _original,
};

FakeApi _api(Map<String, Object?> original, {Map<String, Object?>? me}) {
  final draft = _correctionDraft();
  return FakeApi()
    ..installDefaults(me: me)
    ..reply('GET', '$_changes/by-number/$_original', original)
    ..reply('POST', _changes, draft, 201)
    ..reply('GET', '$_changes/by-number/$_correction', draft)
    ..reply('GET', '$_changes/ch-2/readiness', readinessJson(ok: false));
}

Finder get _button => find.byKey(const ValueKey('card-correction'));

void main() {
  group('"Utwórz korektę" visibility', () {
    for (final status in [
      'implemented',
      'verified',
      'rolled_back',
      'rejected',
      'cancelled',
    ]) {
      testWidgets('frozen status $status: shown to the editor', (tester) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(
          tester,
          api: _api(_verified(status: status)),
          location: _cardPath,
        );
        expect(_button, findsOneWidget);
      });
    }

    for (final status in ['draft', 'pending_approval', 'approved']) {
      testWidgets('status $status (not frozen): hidden', (tester) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(
          tester,
          api: _api(_verified(status: status)),
          location: _cardPath,
        );
        expect(_button, findsNothing);
      });
    }

    testWidgets('approver of the company: shown', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _api(
          _verified(),
          me: meJson(id: userApprover, alfaRoles: ['approver']),
        ),
        location: _cardPath,
      );
      expect(_button, findsOneWidget);
    });

    for (final role in ['viewer', 'auditor']) {
      testWidgets('$role: hidden', (tester) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(
          tester,
          api: _api(_verified(), me: meJson(alfaRoles: [role])),
          location: _cardPath,
        );
        expect(_button, findsNothing);
        // the card itself is shown
        expect(find.text('Aktualizacja reguł zapory'), findsWidgets);
      });
    }

    testWidgets('card not read as a member (admin_read_only): hidden', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _api({..._verified(), 'access': 'admin_read_only'}),
        location: _cardPath,
      );
      expect(_button, findsNothing);
    });
  });

  testWidgets('confirm → POST with supersedes_change_id and copied fields → '
      'edit form of the correction', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_verified());
    final router = await pumpApp(tester, api: api, location: _cardPath);

    await tester.tap(_button);
    await tester.pumpAndSettle();
    expect(find.text('Utworzyć korektę zmiany?'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('correction-confirm')));
    await tester.pumpAndSettle();

    final body = api.calls('POST', _changes).single.json;
    expect(body, {
      'supersedes_change_id': 'ch-1',
      'title': 'Korekta: Aktualizacja reguł zapory',
      'category_id': 'cat-fw',
      'subcategory_id': 'sub-rules',
      'change_type': 'normal',
      'risk': 'high',
      'description': 'Otwarcie portu 443 dla nowego serwera.',
      'implementation_plan': '1. Kopia konfiguracji. 2. Reguła. 3. Test.',
      'rollback_plan': 'Przywrócenie kopii konfiguracji.',
      'impact': 'Brak przerwy.',
      'requirement_ref': 'ISO/IEC 27001:2022 A.8.32',
      'ticket_ref': 'SD-1234',
      'assignee_id': userEditor,
      'approver_id': userApprover,
      'verifier_id': userApprover,
      'ci_ids': ['ci-1'],
    });
    // never the window, lifecycle dates or status
    for (final key in [
      'window_start',
      'window_end',
      'status',
      'implemented_at',
      'verified_at',
    ]) {
      expect(body.containsKey(key), isFalse, reason: key);
    }

    expect(currentPath(router), '/c/ALFA/changes/$_correction/edit');
    final banner = find.byKey(const ValueKey('correction-banner'));
    expect(banner, findsOneWidget);
    expect(
      find.descendant(
        of: banner,
        matching: find.text('Korekta zmiany $_original'),
      ),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('correction-original')));
    await tester.pumpAndSettle();
    expect(currentPath(router), _cardPath);
    await unmountApp(tester);
  });

  testWidgets('cancelled dialog: no draft is created', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_verified());
    final router = await pumpApp(tester, api: api, location: _cardPath);

    await tester.tap(_button);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('correction-cancel')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', _changes), isEmpty);
    expect(currentPath(router), _cardPath);
  });

  testWidgets('API error: Polish message, the card stays', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_verified())
      ..on(
        'POST',
        _changes,
        (_) => FakeResponse.problem(
          422,
          'change.ci_not_found',
          'Nie znaleziono obiektu (CI) w tej spółce.',
        ),
      );
    final router = await pumpApp(tester, api: api, location: _cardPath);

    await tester.tap(_button);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('correction-confirm')));
    await tester.pumpAndSettle();

    expect(currentPath(router), _cardPath);
    expect(find.textContaining('Nie znaleziono obiektu (CI)'), findsWidgets);
    final button = tester.widget<ButtonStyleButton>(_button);
    expect(button.onPressed, isNotNull);
  });

  testWidgets('card of a correction links to the original by number', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_verified());
    final router = await pumpApp(
      tester,
      api: api,
      location: '/c/ALFA/changes/$_correction',
    );

    final link = find.byKey(const ValueKey('supersedes-link'));
    expect(link, findsOneWidget);
    expect(
      find.descendant(of: link, matching: find.textContaining(_original)),
      findsOneWidget,
    );
    // a draft is not frozen: no correction of the correction yet
    expect(_button, findsNothing);

    await tester.tap(link);
    await tester.pumpAndSettle();
    expect(currentPath(router), _cardPath);
  });

  testWidgets('without supersedes_number: plain label, no extra request', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_verified())
      ..reply('GET', '$_changes/by-number/$_correction', {
        ..._correctionDraft(),
        'supersedes_number': null,
      });
    await pumpApp(tester, api: api, location: '/c/ALFA/changes/$_correction');

    expect(find.byKey(const ValueKey('supersedes-link')), findsNothing);
    expect(find.text('Korekta wcześniejszej zmiany'), findsOneWidget);
    // the number comes from the card itself, never from a GET of the original
    expect(api.calls('GET', '$_changes/ch-1'), isEmpty);
  });

  testWidgets('original lists its corrections with status pills and links', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(_correctedOriginal());
    final router = await pumpApp(tester, api: api, location: _cardPath);

    final links = find.byKey(const ValueKey('superseded-by'));
    expect(links, findsOneWidget);
    expect(
      find.descendant(of: links, matching: find.text('Skorygowana przez:')),
      findsOneWidget,
    );
    for (final label in ['Szkic', 'Anulowana']) {
      expect(
        find.descendant(of: links, matching: find.text(label)),
        findsOneWidget,
      );
    }
    // a correction exists already, a further one is still possible
    expect(_button, findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('superseded-by-$_correction')));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/changes/$_correction');
    await unmountApp(tester);
  });

  testWidgets('change without corrections: no "Skorygowana przez"', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(tester, api: _api(_verified()), location: _cardPath);
    expect(find.byKey(const ValueKey('superseded-by')), findsNothing);
  });

  group('ChangeCorrection', () {
    Change original({String? title = 'Reguły', String? verifier}) =>
        Change.fromJson({
          ..._verified(),
          'title': title,
          if (verifier != null) 'verifier': userRef(verifier, 'Ktoś'),
        });

    test('title prefix is not doubled and respects the API limit', () {
      expect(ChangeCorrection.title(original()), 'Korekta: Reguły');
      expect(
        ChangeCorrection.title(original(title: 'Korekta: Reguły')),
        'Korekta: Reguły',
      );
      expect(
        ChangeCorrection.title(original(title: null)),
        'Korekta: $_original',
      );
      expect(
        ChangeCorrection.title(original(title: 'x' * 600)).length,
        ChangeCorrection.titleMax,
      );
    });

    test('people who are no longer members are left out', () {
      final fields = ChangeCorrection.draftFields(
        original(verifier: 'u-gone'),
        memberIds: {userEditor, userApprover},
      );
      expect(fields['assignee_id'], userEditor);
      expect(fields['approver_id'], userApprover);
      expect(fields.containsKey('verifier_id'), isFalse);
    });
  });
}
