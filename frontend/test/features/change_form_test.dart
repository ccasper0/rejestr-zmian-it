import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/widgets/audit_timeline.dart' show DiffLine;

import '../helpers.dart';

const _wide = Size(1400, 2600);
const _number = 'CHG-ALFA-2026-0001';
const _editPath = '/c/ALFA/changes/$_number/edit';
const _byNumber = '/companies/c-alfa/changes/by-number/$_number';
const _patch = '/companies/c-alfa/changes/ch-1';
const _readiness = '/companies/c-alfa/changes/ch-1/readiness';

const _rollbackError = 'Plan wycofania jest wymagany przy wysokim ryzyku.';

FakeApi _api({Map<String, Object?>? change, bool readyOk = true}) {
  final initial = change ?? changeJson();
  var version = initial['version']! as int;
  return FakeApi()
    ..installDefaults()
    ..reply('GET', _byNumber, initial)
    ..reply('GET', _patch, initial)
    ..reply('GET', _readiness, readinessJson(ok: readyOk))
    ..on('PATCH', _patch, (request) {
      version++;
      final body = request.json;
      return FakeResponse(200, {
        ...initial,
        if (body.containsKey('risk')) 'risk': body['risk'],
        if (body.containsKey('rollback_plan'))
          'rollback_plan': body['rollback_plan'],
        if (body.containsKey('change_type')) 'change_type': body['change_type'],
        if (body.containsKey('title')) 'title': body['title'],
        if (body.containsKey('impact')) 'impact': body['impact'],
        if (body.containsKey('window_start'))
          'window_start': body['window_start'],
        if (body.containsKey('window_end')) 'window_end': body['window_end'],
        'version': version,
      });
    });
}

/// Form test: unmounts at the end (background save of unsaved edits).
void formTest(String description, Future<void> Function(WidgetTester) body) {
  testWidgets(description, (tester) async {
    await body(tester);
    await unmountApp(tester);
  });
}

Finder _field(String name) => find.byKey(ValueKey('field-$name'));

FilledButton _submit(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byKey(const ValueKey('form-submit')));

Future<void> _tapRisk(WidgetTester tester, String label) async {
  await tester.tap(
    find.descendant(of: _field('risk'), matching: find.text(label)),
  );
  await tester.pump();
}

void main() {
  group('high risk requires a rollback plan (inline validation)', () {
    formTest('error shown and submit disabled while the plan is empty', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _api(change: changeJson(risk: 'high', rollbackPlan: null)),
        location: _editPath,
      );

      expect(find.text(_rollbackError), findsOneWidget);
      expect(
        find.text('Plan wycofania (wymagany przy wysokim ryzyku)'),
        findsOneWidget,
      );
      expect(_submit(tester).onPressed, isNull);

      await tester.enterText(
        _field('rollback_plan'),
        'Przywrócenie konfiguracji z kopii.',
      );
      await tester.pump();
      expect(find.text(_rollbackError), findsNothing);
      expect(_submit(tester).onPressed, isNotNull);
    });

    formTest('raising the risk to high makes the plan required at once', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _api(change: changeJson(risk: 'low', rollbackPlan: null)),
        location: _editPath,
      );

      expect(find.text(_rollbackError), findsNothing);
      await _tapRisk(tester, 'Wysokie');
      expect(find.text(_rollbackError), findsOneWidget);
      expect(_submit(tester).onPressed, isNull);

      await _tapRisk(tester, 'Średnie');
      expect(find.text(_rollbackError), findsNothing);
    });

    formTest('high risk also needs the service window', (tester) async {
      setSurfaceSize(tester, _wide);
      final change = changeJson(risk: 'high')
        ..['window_start'] = null
        ..['window_end'] = null;
      await pumpApp(
        tester,
        api: _api(change: change),
        location: _editPath,
      );

      expect(
        find.text(
          'Okno serwisowe (od i do) jest wymagane przy wysokim ryzyku.',
        ),
        findsOneWidget,
      );
      expect(_submit(tester).onPressed, isNull);
    });
  });

  formTest('submit is disabled while /readiness reports errors', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(tester, api: _api(readyOk: false), location: _editPath);

    expect(find.text('Kontrola przed wysłaniem'), findsOneWidget);
    expect(find.text('1 pozycja do poprawy'), findsOneWidget);
    expect(
      find.text('Przy wysokim ryzyku podano plan wycofania.'),
      findsOneWidget,
    );
    expect(_submit(tester).onPressed, isNull);
  });

  formTest('submit enabled when ready; saves first, then POST submit', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply('POST', '/companies/c-alfa/changes/ch-1/actions/submit', {
        'action': 'submit',
        'from_status': 'draft',
        'to_status': 'pending_approval',
        'performed_by_system': false,
        'warnings': <Object?>[],
        'change': changeJson(status: 'pending_approval', version: 3),
      });
    final router = await pumpApp(tester, api: api, location: _editPath);
    expect(find.text('Gotowa do wysłania'), findsOneWidget);

    await tester.enterText(_field('title'), 'Nowy tytuł');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-submit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('action-confirm')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', _patch).single.json, {
      'title': 'Nowy tytuł',
      'version': 1,
    });
    // the action uses the version returned by the save
    expect(api.calls('POST', '.*/actions/submit').single.json, {'version': 2});
    expect(currentPath(router), '/c/ALFA/changes/$_number');
  });

  formTest('three type cards with descriptions; selection is saved', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(tester, api: api, location: _editPath);

    for (final type in ['standard', 'normal', 'emergency']) {
      expect(find.byKey(ValueKey('type-card-$type')), findsOneWidget);
    }
    expect(find.textContaining('zatwierdzenie po fakcie'), findsOneWidget);
    expect(
      tester
          .getSemantics(find.byKey(const ValueKey('type-card-normal')))
          .flagsCollection
          .isChecked,
      isNotNull,
    );

    await tester.tap(find.byKey(const ValueKey('type-card-emergency')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-save')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', _patch).single.json, {
      'change_type': 'emergency',
      'version': 1,
    });
    expect(find.text('Zapisano szkic.'), findsOneWidget);
  });

  formTest('autosave every 30 s sends only edits with the version', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(tester, api: api, location: _editPath);

    await tester.pump(const Duration(seconds: 31));
    expect(api.calls('PATCH', _patch), isEmpty, reason: 'nothing to save');

    await tester.enterText(_field('impact'), 'Krótka przerwa VPN.');
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', _patch).single.json, {
      'impact': 'Krótka przerwa VPN.',
      'version': 1,
    });

    await tester.enterText(_field('impact'), 'Przerwa VPN do 5 min.');
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', _patch).last.json['version'], 2);
  });

  FakeApi conflictApi() => _api()
    ..on(
      'PATCH',
      _patch,
      (_) => FakeResponse.problem(
        409,
        'change.version_conflict',
        'Nieaktualna wersja.',
        {'current_version': 5},
      ),
    )
    ..reply('GET', _patch, changeJson(title: 'Tytuł kolegi', version: 5));

  formTest('409 conflict: autosave stops, own values kept, diffs shown', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = conflictApi();
    await pumpApp(tester, api: api, location: _editPath);

    await tester.enterText(_field('title'), 'Mój tytuł');
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('conflict-banner')), findsOneWidget);
    expect(find.textContaining('(5)'), findsOneWidget);
    expect(_submit(tester).onPressed, isNull);
    // local value is NOT replaced by the server's
    expect(
      tester.widget<TextField>(_field('title')).controller!.text,
      'Mój tytuł',
    );
    // field-by-field comparison: server → mine
    expect(find.byKey(const ValueKey('conflict-diffs')), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (w) =>
            w is DiffLine &&
            w.field == 'title' &&
            w.before == 'Tytuł kolegi' &&
            w.after == 'Mój tytuł',
      ),
      findsOneWidget,
    );

    await tester.pump(const Duration(seconds: 31));
    expect(api.calls('PATCH', _patch), hasLength(1), reason: 'paused');
  });

  formTest('conflict: "Zapisz moje na nowej wersji" saves on version 5', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = conflictApi();
    await pumpApp(tester, api: api, location: _editPath);
    await tester.enterText(_field('title'), 'Mój tytuł');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-save')));
    await tester.pumpAndSettle();

    api.on(
      'PATCH',
      _patch,
      (r) => FakeResponse(
        200,
        changeJson(title: r.json['title'] as String, version: 6),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('conflict-overwrite')));
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', _patch).last.json, {
      'title': 'Mój tytuł',
      'version': 5,
    });
    expect(find.byKey(const ValueKey('conflict-banner')), findsNothing);
    expect(find.text('Zapisano Twoje zmiany na nowej wersji.'), findsOneWidget);
  });

  formTest('conflict: "Odrzuć moje zmiany" needs consent, then loads server', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(tester, api: conflictApi(), location: _editPath);
    await tester.enterText(_field('title'), 'Mój tytuł');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-save')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('conflict-discard')));
    await tester.pumpAndSettle();
    expect(find.text('Odrzucić Twoje zmiany?'), findsOneWidget);
    await tester.tap(find.text('Wróć do edycji'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(_field('title')).controller!.text,
      'Mój tytuł',
    );

    await tester.tap(find.byKey(const ValueKey('conflict-discard')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-discard')));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(_field('title')).controller!.text,
      'Tytuł kolegi',
    );
    expect(find.byKey(const ValueKey('conflict-banner')), findsNothing);
  });

  formTest('window chosen in the picker is saved once and stays clean', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    await pumpApp(tester, api: api, location: _editPath);

    // real date + time picker for "Okno serwisowe od"
    await tester.tap(find.byTooltip('Wybierz datę i godzinę').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('15'));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OK')); // time picker: keep 19:00
    await tester.pumpAndSettle();
    expect(find.text('15.11.2026 19:00'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('form-save')));
    await tester.pumpAndSettle();
    // 19:00 in Warsaw (CET) = 18:00 UTC
    expect(api.calls('PATCH', _patch).single.json, {
      'window_start': '2026-11-15T18:00:00.000Z',
      'version': 1,
    });
    expect(
      find.textContaining('Niezapisane zmiany'),
      findsNothing,
      reason: 'the saved window equals the server value',
    );

    await tester.pump(const Duration(seconds: 31));
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', _patch), hasLength(1), reason: 'no re-save');
  });

  formTest('leaving with unsaved edits saves first, then navigates', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    final router = await pumpApp(tester, api: api, location: _editPath);

    await tester.enterText(_field('impact'), 'Przerwa 5 min.');
    await tester.tap(find.text('Rejestr zmian').first);
    await tester.pumpAndSettle();

    expect(api.calls('PATCH', _patch).single.json, {
      'impact': 'Przerwa 5 min.',
      'version': 1,
    });
    expect(currentPath(router), '/c/ALFA/changes');
  });

  formTest('failed save on leave keeps the user on the form', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..on(
        'PATCH',
        _patch,
        (_) => FakeResponse.problem(500, 'server.internal_error', 'Błąd.'),
      );
    final router = await pumpApp(tester, api: api, location: _editPath);

    await tester.enterText(_field('impact'), 'Przerwa 5 min.');
    await tester.tap(find.text('Rejestr zmian').first);
    await tester.pumpAndSettle();

    expect(currentPath(router), _editPath);
    expect(find.byKey(const ValueKey('save-error-banner')), findsOneWidget);
    expect(
      tester.widget<TextField>(_field('impact')).controller!.text,
      'Przerwa 5 min.',
    );

    await tester.tap(find.byKey(const ValueKey('discard-and-leave')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-discard')));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/changes/$_number');
  });

  formTest('leaving during a conflict is blocked (nothing lost silently)', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final router = await pumpApp(
      tester,
      api: conflictApi(),
      location: _editPath,
    );
    await tester.enterText(_field('title'), 'Mój tytuł');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-save')));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Dziennik audytu'));
    await tester.pumpAndSettle();
    expect(currentPath(router), _editPath);
    expect(find.byKey(const ValueKey('conflict-banner')), findsOneWidget);
  });

  formTest('409 frozen stops autosave and refreshes editable fields', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..on(
        'PATCH',
        _patch,
        (_) => FakeResponse.problem(409, 'change.frozen', 'Zamrożona.'),
      )
      ..reply(
        'GET',
        _patch,
        changeJson(status: 'implemented', allowedActions: const []),
      );
    await pumpApp(tester, api: api, location: _editPath);

    await tester.enterText(_field('impact'), 'Nowy wpływ');
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('blocked-banner')), findsOneWidget);
    expect(api.calls('GET', _patch), isNotEmpty, reason: 'state refreshed');
    expect(tester.widget<TextField>(_field('impact')).enabled, isFalse);
    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();
    expect(api.calls('PATCH', _patch), hasLength(1), reason: 'stopped');
  });

  formTest('fields outside editable_fields are read-only', (tester) async {
    setSurfaceSize(tester, _wide);
    await pumpApp(
      tester,
      api: _api(
        change: changeJson(
          status: 'pending_approval',
          allowedActions: ['approve'],
          editableFields: ['approver_id', 'window_end', 'window_start'],
        ),
      ),
      location: _editPath,
    );

    expect(tester.widget<TextField>(_field('title')).enabled, isFalse);
    expect(tester.widget<TextField>(_field('rollback_plan')).enabled, isFalse);
    expect(
      tester.widget<DropdownButton<String?>>(_field('approver_id')).onChanged,
      isNotNull,
    );
    // submit is not an allowed action → no button at all
    expect(find.byKey(const ValueKey('form-submit')), findsNothing);
  });

  formTest('four-eyes hint when the approver is the requester', (tester) async {
    setSurfaceSize(tester, _wide);
    final change = changeJson()
      ..['approver'] = userRef(userEditor, 'Ewa Edytorska');
    await pumpApp(
      tester,
      api: _api(change: change),
      location: _editPath,
    );

    expect(find.textContaining('Zasada czterech oczu'), findsOneWidget);
    expect(find.text('Ustaw domyślnego'), findsOneWidget);
  });

  formTest('"Nowa zmiana" creates a numbered draft and opens its form', (
    tester,
  ) async {
    setSurfaceSize(tester, _wide);
    final api = _api()
      ..reply('POST', '/companies/c-alfa/changes', changeJson(), 201);
    final router = await pumpApp(tester, api: api);

    await tester.tap(find.byKey(const ValueKey('new-change')));
    await tester.pumpAndSettle();

    expect(api.calls('POST', '/companies/c-alfa/changes'), hasLength(1));
    expect(currentPath(router), _editPath);
    expect(find.byKey(const ValueKey('form-number')), findsOneWidget);
    expect(find.text(_number), findsWidgets);
  });

  formTest('cancel with unsaved edits asks before discarding', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = _api();
    final router = await pumpApp(tester, api: api, location: _editPath);

    await tester.enterText(_field('title'), 'Szkic roboczy');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('form-cancel')));
    await tester.pumpAndSettle();
    expect(find.text('Odrzucić niezapisane zmiany?'), findsOneWidget);

    await tester.tap(find.text('Odrzuć zmiany'));
    await tester.pumpAndSettle();
    expect(currentPath(router), '/c/ALFA/changes/$_number');
    expect(api.calls('PATCH', _patch), isEmpty);
  });
}
