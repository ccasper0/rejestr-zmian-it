// Export buttons of the register ("Eksport PDF", "CSV") and of the change
// card ("Karta PDF") by role (§5: admin ✓ — also without a role, approver ✓,
// auditor ✓, editor only the card, viewer —; ADR 0017 §4, §12).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/files/file_service.dart';

import '../admin_helpers.dart';
import '../helpers.dart';
import '../report_helpers.dart';

const _wide = Size(1500, 1400);
const _number = 'CHG-ALFA-2026-0001';
const _cardPath = '/c/ALFA/changes/$_number';
const _byNumber = '/companies/c-alfa/changes/by-number/$_number';
const _csv = '/companies/c-alfa/changes/export.csv';

const _pdf = ValueKey('register-export-pdf');
const _csvButton = ValueKey('register-export-csv');
const _cardPdf = ValueKey('card-pdf');

Map<String, Object?> _me(List<String> roles) =>
    meJson(alfaRoles: roles, betaRoles: const []);

FakeResponse _csvFile() => FakeResponse.file(
  [0xEF, 0xBB, 0xBF, ...utf8.encode('Spółka;Numer\r\n')],
  headers: {
    'content-type': 'text/csv; charset=utf-8',
    'content-disposition': 'attachment; filename="RAP-ALFA-2026-0007.csv"',
    'x-report-id': 'r-csv',
    'x-report-number': 'RAP-ALFA-2026-0007',
    'x-data-sha256': '9f2c${'1a' * 30}',
  },
);

void main() {
  group('register', () {
    for (final (label, roles, visible) in [
      ('viewer', ['viewer'], false),
      ('editor', ['editor'], false),
      ('approver', ['approver'], true),
      ('auditor', ['auditor'], true),
    ]) {
      testWidgets('$label: export buttons ${visible ? 'shown' : 'hidden'}', (
        tester,
      ) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(tester, api: FakeApi()..installDefaults(me: _me(roles)));
        expect(find.byKey(_pdf), visible ? findsOneWidget : findsNothing);
        expect(find.byKey(_csvButton), visible ? findsOneWidget : findsNothing);
      });
    }

    testWidgets('app admin without a role: export buttons shown', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()..installAdmin();
      await pumpApp(tester, api: api);
      expect(find.byKey(_pdf), findsOneWidget);
      expect(find.byKey(_csvButton), findsOneWidget);
    });

    testWidgets('CSV: the register filters in the query, file from '
        'Content-Disposition', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults(me: _me(['approver']))
        ..on('GET', _csv, (_) => _csvFile());
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location:
            '/c/ALFA/changes?status=implemented&status=verified'
            '&type=emergency&category=cat-fw&ci=ci-1&approved_by=system'
            '&q=zapora&from=2026-10-01&to=2026-10-31&period_by=implemented'
            '&sort=number&page=2',
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      await tester.tap(find.byKey(_csvButton));
      await tester.pumpAndSettle();

      final query = api.calls('GET', _csv).single.query;
      expect(query['status'], ['implemented', 'verified']);
      expect(query['type'], ['emergency']);
      expect(query['category'], ['cat-fw']);
      expect(query['ci'], ['ci-1']);
      expect(query['approved_by'], ['system']);
      expect(query['q'], ['zapora']);
      expect(query['period_from'], ['2026-09-30T22:00:00.000Z']);
      expect(query['period_to'], ['2026-10-31T23:00:00.000Z']);
      expect(query['period_by'], ['implemented']);
      // the CSV has no sort or paging
      expect(query.keys, isNot(contains('sort')));
      expect(query.keys, isNot(contains('limit')));
      expect(query.keys, isNot(contains('offset')));

      final saved = files.saved.single;
      expect(saved.filename, 'RAP-ALFA-2026-0007.csv');
      expect(saved.contentType, startsWith('text/csv'));
      expect(saved.bytes.take(3), [0xEF, 0xBB, 0xBF]);
      expect(find.textContaining('RAP-ALFA-2026-0007'), findsOneWidget);
    });

    testWidgets('CSV error: Polish message', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults(me: _me(['auditor']))
        ..on(
          'GET',
          _csv,
          (_) => FakeResponse.problem(
            422,
            'change.invalid_filter',
            'Filtr approved_by przyjmuje identyfikator użytkownika albo '
                "'system'.",
          ),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );
      await tester.tap(find.byKey(_csvButton));
      await tester.pumpAndSettle();
      expect(find.textContaining('Nieprawidłowy filtr rejestru.'), findsOne);
      expect(files.saved, isEmpty);
    });

    testWidgets('"Eksport PDF" opens the report screen with the filters', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults(me: _me(['auditor']))
        ..reply('GET', '/reports', page([]));
      final router = await pumpApp(
        tester,
        api: api,
        location:
            '/c/ALFA/changes?status=verified&from=2026-10-01&to=2026-10-31'
            '&sort=number&page=3',
      );

      await tester.tap(find.byKey(_pdf));
      await tester.pumpAndSettle();

      final uri = currentUri(router);
      expect(uri.path, '/c/ALFA/reports');
      expect(uri.queryParametersAll, {
        'status': ['verified'],
        'from': ['2026-10-01'],
        'to': ['2026-10-31'],
      });
      expect(find.text('Status: Zweryfikowana'), findsOneWidget);
      expect(find.text('Od: 01.10.2026'), findsOneWidget);
    });
  });

  group('change card', () {
    FakeApi cardApi(List<String> roles) => FakeApi()
      ..installDefaults(me: _me(roles))
      ..reply(
        'GET',
        _byNumber,
        changeJson(status: 'approved', allowedActions: const []),
      );

    for (final (label, roles, visible) in [
      ('viewer', ['viewer'], false),
      ('editor', ['editor'], true),
      ('approver', ['approver'], true),
      ('auditor', ['auditor'], true),
    ]) {
      testWidgets('$label: "Karta PDF" ${visible ? 'shown' : 'hidden'}', (
        tester,
      ) async {
        setSurfaceSize(tester, _wide);
        await pumpApp(tester, api: cardApi(roles), location: _cardPath);
        expect(find.byKey(_cardPdf), visible ? findsOneWidget : findsNothing);
      });
    }

    testWidgets('editor: POST change_card → 201 → file saved', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = cardApi(['editor'])
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse(
            201,
            reportJson(
              id: 'r-card',
              number: 'RAP-ALFA-2026-0008',
              kind: 'change_card',
              changeId: 'ch-1',
              changeNumber: _number,
              periodFrom: null,
              periodTo: null,
            ),
          ),
        )
        ..on(
          'GET',
          '/reports/r-card/download',
          (_) => pdfFile('RAP-ALFA-2026-0008'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _cardPath,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      await tester.tap(find.byKey(_cardPdf));
      await tester.pumpAndSettle();

      final body = api.calls('POST', '/reports').single.json;
      expect(body['kind'], 'change_card');
      expect(body['company_id'], companyAlfa);
      expect(body['change_id'], 'ch-1');
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0008.pdf');
      expect(find.textContaining('RAP-ALFA-2026-0008'), findsOneWidget);
    });

    testWidgets('pending card is polled until done, then saved', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      var polls = 0;
      Map<String, Object?> card(String status) => reportJson(
        id: 'r-card',
        number: 'RAP-ALFA-2026-0008',
        kind: 'change_card',
        status: status,
        changeId: 'ch-1',
        changeNumber: _number,
      );
      final api = cardApi(['auditor'])
        ..on('POST', '/reports', (_) => FakeResponse(202, card('pending')))
        ..on('GET', '/reports/r-card', (_) {
          polls++;
          return FakeResponse(200, card('done'));
        })
        ..on(
          'GET',
          '/reports/r-card/download',
          (_) => pdfFile('RAP-ALFA-2026-0008'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _cardPath,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      await tester.tap(find.byKey(_cardPdf));
      await tester.pump(const Duration(milliseconds: 100));
      expect(files.saved, isEmpty);
      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();
      expect(polls, 1);
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0008.pdf');
    });

    testWidgets('failed card: Polish error, nothing saved', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = cardApi(['approver'])
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse.problem(
            404,
            'change.not_found',
            'Nie znaleziono zmiany.',
          ),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _cardPath,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );
      await tester.tap(find.byKey(_cardPdf));
      await tester.pumpAndSettle();
      expect(find.text('Nie znaleziono zmiany.'), findsOneWidget);
      expect(files.saved, isEmpty);
    });

    testWidgets('app admin without a role: "Karta PDF" on the read-only card', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installAdmin()
        ..reply(
          'GET',
          _byNumber,
          changeJson(
            status: 'implemented',
            access: 'admin_read_only',
            allowedActions: const [],
            editableFields: const [],
          ),
        )
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse(
            201,
            reportJson(id: 'r-adm', number: 'RAP-ALFA-2026-0010'),
          ),
        )
        ..on(
          'GET',
          '/reports/r-adm/download',
          (_) => pdfFile('RAP-ALFA-2026-0010'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _cardPath,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      expect(find.byKey(const ValueKey('admin-read-only')), findsOneWidget);
      await tester.tap(find.byKey(_cardPdf));
      await tester.pumpAndSettle();
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0010.pdf');
    });
  });
}
