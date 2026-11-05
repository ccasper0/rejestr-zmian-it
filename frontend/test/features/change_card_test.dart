import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/theme.dart';
import 'package:rejestr_zmian/widgets/audit_timeline.dart';

import '../helpers.dart';

const _wide = Size(1400, 1400);
const _number = 'CHG-ALFA-2026-0001';
const _cardPath = '/c/ALFA/changes/$_number';
const _byNumber = '/companies/c-alfa/changes/by-number/$_number';

Map<String, Object?> _auditEntry({
  required int seq,
  required String action,
  Map<String, Object?> diff = const {},
  Map<String, Object?> context = const {},
  String? actorId = userEditor,
  bool hashValid = true,
}) => {
  'seq': seq,
  'occurred_at': '2026-10-29T08:0$seq:00Z',
  'actor_id': actorId,
  'actor_display': actorId == null ? 'system' : 'Ewa Edytorska',
  'actor_roles': actorId == null ? <String>[] : ['editor'],
  'ip_address': '10.0.0.$seq',
  'request_id': 'req-$seq',
  'entity_type': 'change',
  'entity_id': 'ch-1',
  'action': action,
  'diff': diff,
  'context': context,
  'prev_hash': '0' * 64,
  'hash': 'ab' * 32,
  'hash_valid': hashValid,
};

FakeApi _api(Map<String, Object?> change, {Map<String, Object?>? me}) =>
    FakeApi()
      ..installDefaults(me: me)
      ..reply('GET', _byNumber, change);

void main() {
  testWidgets('approver sees exactly the actions from allowed_actions', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(
        changeJson(
          status: 'pending_approval',
          allowedActions: ['approve', 'reject', 'return'],
        ),
      ),
      location: _cardPath,
    );

    for (final action in ['approve', 'reject', 'return']) {
      expect(find.byKey(ValueKey('action-$action')), findsOneWidget);
    }
    for (final action in [
      'submit',
      'implement',
      'verify',
      'rollback',
      'cancel',
    ]) {
      expect(find.byKey(ValueKey('action-$action')), findsNothing);
    }
    // no editable fields → no "Edytuj"; the card PDF is an export (§5),
    // not an action — offered independently of allowed_actions
    expect(find.byKey(const ValueKey('card-edit')), findsNothing);
    final pdf = tester.widget<ButtonStyleButton>(
      find.byKey(const ValueKey('card-pdf')),
    );
    expect(pdf.onPressed, isNotNull);
  });

  testWidgets('viewer: no action buttons when allowed_actions is empty', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(
        changeJson(status: 'approved', allowedActions: const []),
        me: meJson(alfaRoles: ['viewer'], betaRoles: []),
      ),
      location: _cardPath,
    );

    expect(
      find.byWidgetPredicate((w) {
        final key = w.key;
        return key is ValueKey<String> && key.value.startsWith('action-');
      }),
      findsNothing,
    );
    expect(find.byKey(const ValueKey('comment-field')), findsNothing);
  });

  testWidgets('draft: edit + submit; actions send the card version', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(changeJson(version: 4))
      ..reply('POST', '/companies/c-alfa/changes/ch-1/actions/submit', {
        'action': 'submit',
        'from_status': 'draft',
        'to_status': 'pending_approval',
        'performed_by_system': false,
        'warnings': <Object?>[],
        'change': changeJson(status: 'pending_approval', version: 5),
      });
    await pumpApp(tester, api: api, location: _cardPath);

    expect(find.byKey(const ValueKey('card-edit')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('action-submit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();

    final call = api.calls(
      'POST',
      '/companies/c-alfa/changes/ch-1/actions/submit',
    );
    expect(call.single.json, {'version': 4});
    expect(find.text('Status zmiany: Do zatwierdzenia.'), findsOneWidget);
  });

  testWidgets('reject requires a comment (dialog validation)', (tester) async {
    setSurfaceSize(tester, _wide);
    final api =
        _api(changeJson(status: 'pending_approval', allowedActions: ['reject']))
          ..reply('POST', '/companies/c-alfa/changes/ch-1/actions/reject', {
            'action': 'reject',
            'from_status': 'pending_approval',
            'to_status': 'rejected',
            'performed_by_system': false,
            'warnings': <Object?>[],
            'change': changeJson(status: 'rejected'),
          });
    await pumpApp(tester, api: api, location: _cardPath);

    await tester.tap(find.byKey(const ValueKey('action-reject')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();
    expect(
      find.text('Komentarz jest wymagany dla tej operacji.'),
      findsOneWidget,
    );
    expect(api.calls('POST', '.*/actions/reject'), isEmpty);

    await tester.enterText(
      find.byKey(const ValueKey('action-comment')),
      'Brak testu w środowisku testowym.',
    );
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();
    expect(api.calls('POST', '.*/actions/reject').single.json, {
      'version': 1,
      'comment': 'Brak testu w środowisku testowym.',
    });
  });

  testWidgets('409 version conflict is explained and the card reloaded', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api =
        _api(
          changeJson(status: 'pending_approval', allowedActions: ['approve']),
        )..on(
          'POST',
          '.*/actions/approve',
          (_) => FakeResponse.problem(
            409,
            'change.version_conflict',
            'Zmiana ma nowszą wersję.',
            {'current_version': 2},
          ),
        );
    await pumpApp(tester, api: api, location: _cardPath);
    final loads = api.calls('GET', _byNumber).length;

    await tester.tap(find.byKey(const ValueKey('action-approve')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();

    expect(
      find.text('Zmiana została zmieniona przez kogoś innego'),
      findsOneWidget,
    );
    expect(api.calls('GET', _byNumber).length, greaterThan(loads));
  });

  testWidgets('422 not_ready lists the failing checks', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api(changeJson())
      ..on(
        'POST',
        '.*/actions/submit',
        (_) => FakeResponse.problem(422, 'change.not_ready', 'Niegotowa.', {
          'checks': [
            {
              'code': 'ci.required',
              'ok': false,
              'level': 'error',
              'message_pl': 'Wskazano co najmniej jeden obiekt (CI).',
              'field': 'ci_ids',
            },
          ],
        }),
      );
    await pumpApp(tester, api: api, location: _cardPath);

    await tester.tap(find.byKey(const ValueKey('action-submit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();

    expect(find.text('Zmiana nie spełnia warunków'), findsOneWidget);
    expect(
      find.text('Wskazano co najmniej jeden obiekt (CI).'),
      findsOneWidget,
    );
  });

  testWidgets('audit trail: diff before → after, actor, chain badge, hash', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api(changeJson())
      ..reply(
        'GET',
        '/companies/c-alfa/changes/ch-1/audit',
        page([
          _auditEntry(
            seq: 1,
            action: 'update',
            diff: {
              'risk': {'before': 'medium', 'after': 'high'},
              'approver_id': {'before': null, 'after': userApprover},
            },
          ),
          _auditEntry(
            seq: 2,
            action: 'transition',
            actorId: null,
            diff: {
              'status': {'before': 'draft', 'after': 'approved'},
            },
            context: {
              'action': 'submit',
              'auto_approved': true,
              'from_status': 'draft',
              'to_status': 'approved',
            },
            hashValid: false,
          ),
        ]),
      );
    await pumpApp(tester, api: api, location: _cardPath);

    expect(find.text('Łańcuch spójny'), findsOneWidget);
    expect(
      find.text(
        'Ewa Edytorska (Edytor) — zmienił(a) dane zmiany',
        findRichText: true,
      ),
      findsOneWidget,
    );
    expect(
      find.text(
        'system — zatwierdził automatycznie (zmiana standardowa)',
        findRichText: true,
      ),
      findsOneWidget,
    );
    expect(find.text('29.10.2026 09:01 · IP 10.0.0.1'), findsOneWidget);

    final riskLine = tester.widget<DiffLine>(
      find.byWidgetPredicate((w) => w is DiffLine && w.field == 'risk'),
    );
    expect(riskLine.before, 'Średnie');
    expect(riskLine.after, 'Wysokie');
    final rich = tester.widget<RichText>(
      find.descendant(
        of: find.byWidget(riskLine),
        matching: find.byType(RichText),
      ),
    );
    final spans = <TextSpan>[];
    rich.text.visitChildren((span) {
      if (span is TextSpan && span.text != null) spans.add(span);
      return true;
    });
    final old = spans.firstWhere((s) => s.text == 'Średnie');
    final fresh = spans.firstWhere((s) => s.text == 'Wysokie');
    expect(old.style!.decoration, TextDecoration.lineThrough);
    expect(old.style!.color, AppColors.diffRemoved);
    expect(fresh.style!.color, AppColors.diffAdded);
    // user id resolved to a name
    expect(
      find.byWidgetPredicate(
        (w) => w is DiffLine && w.after == 'Jan Zatwierdzający',
      ),
      findsOneWidget,
    );
    expect(find.text('Skrót niezgodny z treścią wpisu'), findsOneWidget);
    expect(find.textContaining('sha256 abababababab'), findsNWidgets(2));
  });

  testWidgets('stale chain status is shown as such', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api(changeJson())
      ..reply('GET', '/companies/c-alfa/audit/status', {
        'status': 'stale',
        'ok': null,
        'checked_at': '2026-10-20T02:30:00Z',
        'verified_head_seq': 10,
        'head_seq': 99,
      });
    await pumpApp(tester, api: api, location: _cardPath);

    expect(find.text('Weryfikacja nieaktualna'), findsOneWidget);
    expect(find.text('sprawdzono 20.10.2026 04:30'), findsOneWidget);
  });

  testWidgets('CI owner consent by requester/assignee is flagged', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(
        changeJson(
          status: 'pending_approval',
          allowedActions: ['approve'],
          consents: [
            {
              'ci_id': 'ci-1',
              'owner': userRef(userEditor, 'Ewa Edytorska'),
              'consented_at': '2026-10-29T09:00:00Z',
              'valid': true,
              'by_requester_or_assignee': true,
            },
          ],
        ),
      ),
      location: _cardPath,
    );

    expect(find.text('Zgody właścicieli obiektów (CI)'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('consent-not-independent')),
      findsOneWidget,
    );
  });

  testWidgets('classification shows designated and actual approver', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(
        changeJson(
          status: 'approved',
          type: 'standard',
          allowedActions: const [],
          autoApproved: true,
          approvedAt: '2026-10-29T10:00:00Z',
        ),
      ),
      location: _cardPath,
    );

    expect(find.text('Jan Zatwierdzający'), findsWidgets);
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('classification-approved-by')),
        matching: find.text('system (automatycznie), 29.10.2026 11:00'),
      ),
      findsOneWidget,
    );
  });

  testWidgets('narrow screen: single column, still all sections', (
    tester,
  ) async {
    setSurfaceSize(tester, const Size(420, 2400));
    await pumpApp(tester, api: _api(changeJson()), location: _cardPath);

    expect(find.text('Klasyfikacja'), findsOneWidget);
    expect(find.text('Ścieżka audytu'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
