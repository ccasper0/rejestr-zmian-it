// Screen 5 "Raporty i eksport" (§10, ADR 0017 §10): visibility by role, the
// register report form (period validation, request body), the report list
// (statuses, Warsaw time, sha256), polling of pending reports and errors.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/files/file_service.dart';
import 'package:rejestr_zmian/features/reports/data/reports_api.dart';

import '../admin_helpers.dart';
import '../helpers.dart';
import '../report_helpers.dart';

const _wide = Size(1800, 1600);
const _reports = '/c/ALFA/reports';

Map<String, Object?> _auditorMe() => meJson(
  id: userAuditor,
  name: 'Alicja Audytorka',
  alfaRoles: ['auditor'],
  betaRoles: ['auditor'],
);

FakeApi _api({Map<String, Object?>? me, List<Map<String, Object?>>? list}) =>
    FakeApi()
      ..installDefaults(me: me ?? _auditorMe())
      ..reply('GET', '/reports', page(list ?? const []));

Finder _generate() => find.byKey(const ValueKey('report-generate'));

bool _enabled(WidgetTester tester, Finder finder) =>
    tester.widget<ButtonStyleButton>(finder).onPressed != null;

/// Leaves the app and lets a pending poll delay run out (it then stops).
Future<void> _leave(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pump(const Duration(seconds: 3));
}

void main() {
  group('visibility', () {
    testWidgets('viewer: "Brak dostępu", the list is not requested', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api(
        me: meJson(alfaRoles: ['viewer'], betaRoles: []),
      );
      await pumpApp(tester, api: api, location: _reports);

      expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
      expect(find.text('Brak dostępu'), findsOneWidget);
      expect(_generate(), findsNothing);
      expect(api.calls('GET', '/reports'), isEmpty);
    });

    testWidgets('editor: only change cards, no register report form', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api(
        me: meJson(),
        list: [
          reportJson(
            kind: 'change_card',
            changeId: 'ch-1',
            changeNumber: 'CHG-ALFA-2026-0001',
            periodFrom: null,
            periodTo: null,
            author: 'Ewa Edytorska',
            changeCount: 1,
          ),
        ],
      );
      await pumpApp(tester, api: api, location: _reports);

      expect(find.byKey(const ValueKey('reports-cards-only')), findsOneWidget);
      expect(_generate(), findsNothing);
      expect(find.text('Wygenerowane karty zmian'), findsOneWidget);
      expect(find.text('Karta zmiany (PDF)'), findsOneWidget);
      expect(find.text('CHG-ALFA-2026-0001'), findsOneWidget);
      final query = api.calls('GET', '/reports').last.query;
      expect(query['company_id'], [companyAlfa]);
      expect(query['kind'], ['change_card']);
    });

    testWidgets('app admin without a role: form on the admin export path', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installAdmin()
        ..reply('GET', '/reports', page([]))
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse(
            201,
            reportJson(id: 'r-adm', number: 'RAP-ALFA-2026-0009'),
          ),
        )
        ..on(
          'GET',
          '/reports/r-adm/download',
          (_) => pdfFile('RAP-ALFA-2026-0009'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _reports,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      expect(find.byKey(const ValueKey('reports-admin-path')), findsOneWidget);
      expect(api.calls('GET', '/reports').last.query['company_id'], [
        companyAlfa,
      ]);
      await tester.tap(_generate());
      await tester.pumpAndSettle();

      expect(
        api.calls('POST', '/reports').single.json['company_id'],
        companyAlfa,
      );
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0009.pdf');
    });

    testWidgets('"Wszystkie spółki (audytor)": multi-company report', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api()
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse(
            201,
            reportJson(
              id: 'r-all',
              number: 'RAP-2026-0001',
              companyId: null,
              companies: [
                {'id': companyAlfa, 'name': 'Alfa S.A.', 'prefix': 'ALFA'},
                {
                  'id': companyBeta,
                  'name': 'Beta sp. z o.o.',
                  'prefix': 'BETA',
                },
              ],
            ),
          ),
        )
        ..on('GET', '/reports/r-all/download', (_) => pdfFile('RAP-2026-0001'));
      await pumpApp(
        tester,
        api: api,
        location: '/c/all/reports?ci=ci-1&assignee=u-1&status=verified',
        overrides: [fileServiceProvider.overrideWithValue(FakeFileService())],
      );

      expect(find.textContaining('Alfa S.A., Beta sp. z o.o.'), findsOneWidget);
      // CI and people filters belong to one company
      expect(find.byKey(const ValueKey('report-filter-ci')), findsNothing);
      expect(
        find.byKey(const ValueKey('report-filter-assignee')),
        findsNothing,
      );
      expect(
        api.calls('GET', '/reports').last.query.containsKey('company_id'),
        isFalse,
      );

      await tester.tap(_generate());
      await tester.pumpAndSettle();
      final body = api.calls('POST', '/reports').single.json;
      expect(body.containsKey('company_id'), isTrue);
      expect(body['company_id'], isNull);
      final filters = body['filters'] as Map;
      expect(filters['status'], ['verified']);
      expect(filters['ci'], isEmpty);
      expect(filters['assignee'], isNull);
    });

    testWidgets('"Wszystkie spółki" without the auditor role: no access', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api(
        me: meJson(alfaRoles: ['approver'], betaRoles: []),
      );
      await pumpApp(tester, api: api, location: '/c/all/reports');

      expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
      expect(api.calls('GET', '/reports'), isEmpty);
    });
  });

  testWidgets('narrow screen: form and list without overflow', (tester) async {
    setSurfaceSize(tester, const Size(420, 1800));
    await pumpApp(
      tester,
      api: _api(
        list: [
          reportJson(),
          reportJson(id: 'r-f', status: 'failed', error: 'Błąd generowania.'),
        ],
      ),
      location: _reports,
    );
    expect(_generate(), findsOneWidget);
    expect(find.byKey(const ValueKey('reports-table')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  group('form', () {
    testWidgets('period validation: reversed and missing period block it', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api();
      await pumpApp(
        tester,
        api: api,
        location: '$_reports?from=2026-10-31&to=2026-10-01',
      );

      expect(
        find.text('Początek okresu nie może być późniejszy niż jego koniec.'),
        findsOneWidget,
      );
      expect(_enabled(tester, _generate()), isFalse);

      await tester.tap(find.byTooltip('Wyczyść filtr: Od'));
      await tester.pumpAndSettle();
      expect(find.text('Podaj początek okresu.'), findsOneWidget);
      expect(_enabled(tester, _generate()), isFalse);

      await tester.tap(find.byTooltip('Wyczyść filtr: Do'));
      await tester.pumpAndSettle();
      expect(
        find.text('Podaj okres raportu (początek i koniec).'),
        findsOneWidget,
      );

      await tester.tap(find.byKey(const ValueKey('report-quarter')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('report-period-error')), findsNothing);
      expect(_enabled(tester, _generate()), isTrue);
      expect(api.calls('POST', '/reports'), isEmpty);
    });

    testWidgets('without a period in the URL: the current quarter', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, api: _api(), location: _reports);
      expect(find.byKey(const ValueKey('report-period-error')), findsNothing);
      expect(_enabled(tester, _generate()), isTrue);
    });

    testWidgets('register filters pre-fill the form; body in UTC; 201 → file', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api()
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse(
            201,
            reportJson(id: 'r-new', number: 'RAP-ALFA-2026-0005'),
          ),
        )
        ..on(
          'GET',
          '/reports/r-new/download',
          (_) => pdfFile('RAP-ALFA-2026-0005'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location:
            '$_reports?from=2026-10-01&to=2026-10-31&status=verified'
            '&type=emergency&period_by=implemented&q=zapora&ci=ci-1'
            '&approved_by=system',
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      expect(find.text('Od: 01.10.2026'), findsOneWidget);
      expect(find.text('Do: 31.10.2026'), findsOneWidget);
      expect(find.text('Status: Zweryfikowana'), findsOneWidget);
      expect(find.text('Typ: Awaryjna'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('report-include-audit')));
      await tester.pumpAndSettle();
      await tester.tap(_generate());
      await tester.pumpAndSettle();

      final body = api.calls('POST', '/reports').single.json;
      expect(body['kind'], 'register');
      expect(body['company_id'], companyAlfa);
      expect(body['change_id'], isNull);
      // Warsaw days, `to` inclusive → exclusive start of 1 Nov (CET)
      expect(body['period_from'], '2026-09-30T22:00:00.000Z');
      expect(body['period_to'], '2026-10-31T23:00:00.000Z');
      expect(body['include_audit_trail'], isTrue);
      expect(body['filters'], {
        'period_by': 'implemented',
        'status': ['verified'],
        'type': ['emergency'],
        'category': <String>[],
        'ci': ['ci-1'],
        'assignee': null,
        'approver': null,
        'approved_by': 'system',
        'q': 'zapora',
      });
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0005.pdf');
      expect(files.saved.single.contentType, 'application/pdf');
      expect(api.calls('GET', '/reports/r-new/download'), hasLength(1));
      expect(find.byKey(const ValueKey('report-ordered-done')), findsOneWidget);
    });

    testWidgets('report.too_large: Polish message with the numbers', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _api()
        ..on(
          'POST',
          '/reports',
          (_) => FakeResponse.problem(
            422,
            'report.too_large',
            'Raport obejmowałby 6120 zmian (maksymalnie 5000). Zawęź okres '
                'lub filtry.',
            {'change_count': 6120, 'max_changes': 5000},
          ),
        );
      await pumpApp(tester, api: api, location: _reports);
      await tester.tap(_generate());
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('report-error')), findsOneWidget);
      expect(
        find.text(
          'Raport obejmowałby 6120 zmian (maksymalnie 5000). Zawęź okres lub '
          'filtry.',
        ),
        findsOneWidget,
      );
    });
  });

  group('list', () {
    testWidgets('statuses, Warsaw time, short sha256, download only done', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api =
          _api(
            list: [
              reportJson(id: 'r-done', number: 'RAP-ALFA-2026-0003'),
              reportJson(
                id: 'r-failed',
                number: 'RAP-ALFA-2026-0002',
                status: 'failed',
                error: 'Utracono uprawnienie do eksportu.',
              ),
              reportJson(
                id: 'r-csv',
                number: 'RAP-ALFA-2026-0004',
                format: 'csv',
                periodFrom: null,
                periodTo: null,
              ),
            ],
          )..on(
            'GET',
            '/reports/r-done/download',
            (_) => pdfFile('RAP-ALFA-2026-0003'),
          );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _reports,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      expect(find.text('RAP-ALFA-2026-0003'), findsOneWidget);
      expect(find.text('Raport rejestru (PDF)'), findsNWidgets(2));
      expect(find.text('Raport rejestru (CSV)'), findsOneWidget);
      // 09:15 UTC on 3 Nov = 10:15 CET
      expect(find.text('03.11.2026 10:15'), findsNWidgets(3));
      expect(find.text('01.10.2026 – 31.10.2026'), findsNWidgets(2));
      expect(find.text('9f2c1a1a…1a1a1a1a'), findsNWidgets(2));
      expect(find.byTooltip('9f2c${'1a' * 30}'), findsNWidgets(2));
      expect(
        find.byKey(const ValueKey('report-status-done-r-done')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('report-status-failed-r-failed')),
        findsOneWidget,
      );
      expect(find.text('Utracono uprawnienie do eksportu.'), findsOneWidget);
      expect(
        find.text('Wyświetlono 1–3 z 3', findRichText: true),
        findsOneWidget,
      );

      final failedDownload = find.byKey(
        const ValueKey('report-download-r-failed'),
      );
      expect(_enabled(tester, failedDownload), isFalse);
      await tester.tap(find.byKey(const ValueKey('report-download-r-done')));
      await tester.pumpAndSettle();
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0003.pdf');
    });

    testWidgets('pagination requests the next page', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults(me: _auditorMe())
        ..reply('GET', '/reports', {
          ...page([reportJson()], total: 45),
          'limit': reportPageSize,
        });
      await pumpApp(tester, api: api, location: _reports);

      expect(find.text('Strona 1 z 3'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('reports-next')));
      await tester.pumpAndSettle();
      expect(api.calls('GET', '/reports').last.query['offset'], ['20']);
      expect(find.text('Strona 2 z 3'), findsOneWidget);
    });
  });

  group('polling', () {
    testWidgets('202 pending → polled every 2 s → done → downloaded', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      var polls = 0;
      final pending = reportJson(
        id: 'r-bg',
        number: 'RAP-ALFA-2026-0006',
        status: 'pending',
        changeCount: 412,
      );
      final api = _api()
        ..on('POST', '/reports', (_) => FakeResponse(202, pending))
        ..on('GET', '/reports/r-bg', (_) {
          polls++;
          return FakeResponse(
            200,
            polls < 2
                ? pending
                : reportJson(
                    id: 'r-bg',
                    number: 'RAP-ALFA-2026-0006',
                    changeCount: 412,
                  ),
          );
        })
        ..on(
          'GET',
          '/reports/r-bg/download',
          (_) => pdfFile('RAP-ALFA-2026-0006'),
        );
      final files = FakeFileService();
      await pumpApp(
        tester,
        api: api,
        location: _reports,
        overrides: [fileServiceProvider.overrideWithValue(files)],
      );

      await tester.tap(_generate());
      for (var i = 0; i < 5; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      expect(
        find.byKey(const ValueKey('report-ordered-pending')),
        findsOneWidget,
      );
      expect(files.saved, isEmpty);

      await tester.pump(const Duration(seconds: 2));
      await tester.pump();
      expect(polls, 1);
      expect(files.saved, isEmpty);

      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();
      expect(polls, 2);
      expect(find.byKey(const ValueKey('report-ordered-done')), findsOneWidget);
      expect(files.saved.single.filename, 'RAP-ALFA-2026-0006.pdf');

      // finished: no more polling
      await tester.pump(const Duration(seconds: 10));
      expect(polls, 2);
    });

    testWidgets('a pending report in the list stops being polled when the '
        'screen is left', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _api(
        list: [reportJson(id: 'r-p', status: 'pending', changeCount: 300)],
      )..reply('GET', '/reports/r-p', reportJson(id: 'r-p', status: 'pending'));
      final router = await pumpApp(tester, api: api, location: _reports);

      expect(
        find.byKey(const ValueKey('report-status-pending-r-p')),
        findsOneWidget,
      );
      await tester.pump(const Duration(seconds: 2));
      await tester.pump();
      expect(api.calls('GET', '/reports/r-p'), hasLength(1));

      router.go('/c/ALFA/changes');
      await tester.pumpAndSettle();
      await tester.pump(const Duration(seconds: 10));
      expect(api.calls('GET', '/reports/r-p'), hasLength(1));
    });

    testWidgets('polling gives up after the time limit', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _api(
        list: [reportJson(id: 'r-p', status: 'pending', changeCount: 300)],
      )..reply('GET', '/reports/r-p', reportJson(id: 'r-p', status: 'pending'));
      await pumpApp(
        tester,
        api: api,
        location: _reports,
        overrides: [
          reportPollingProvider.overrideWithValue(
            const ReportPolling(
              interval: Duration(seconds: 2),
              timeout: Duration(seconds: 4),
            ),
          ),
        ],
      );

      for (var i = 0; i < 4; i++) {
        await tester.pump(const Duration(seconds: 2));
      }
      await tester.pump();
      expect(api.calls('GET', '/reports/r-p'), hasLength(2));
      expect(
        find.text('Generowanie — odśwież listę, aby sprawdzić status'),
        findsOneWidget,
      );
      await _leave(tester);
    });
  });
}
