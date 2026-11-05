import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/time.dart';
import 'package:rejestr_zmian/features/changes/data/register_filters.dart';

void main() {
  setUpAll(WarsawTime.ensureInitialized);

  test('URL query -> filters -> URL query is lossless', () {
    final uri = Uri.parse(
      '/c/ALFA/changes?q=zapora&status=draft&status=approved&type=emergency'
      '&category=cat-1&ci=ci-1&ci=ci-2&assignee=u-1&approved_by=system'
      '&from=2026-10-01&to=2026-10-31&period_by=implemented&sort=number&page=2',
    );
    final filters = RegisterFilters.fromQuery(uri.queryParametersAll);
    expect(filters.q, 'zapora');
    expect(filters.statuses, ['draft', 'approved']);
    expect(filters.cis, ['ci-1', 'ci-2']);
    expect(filters.approvedBy, 'system');
    expect(filters.periodBy, 'implemented');
    expect(filters.page, 2);
    final again = Uri.parse(filters.location('ALFA'));
    expect(RegisterFilters.fromQuery(again.queryParametersAll), filters);
  });

  test('defaults keep the URL clean', () {
    expect(const RegisterFilters().location('ALFA'), '/c/ALFA/changes');
  });

  test('invalid values from the URL are dropped', () {
    final filters = RegisterFilters.fromQuery({
      'status': ['bogus', 'draft'],
      'type': ['weird'],
      'from': ['2026-02-31x'],
      'sort': ['drop table'],
      'page': ['-3'],
    });
    expect(filters.statuses, ['draft']);
    expect(filters.types, isEmpty);
    expect(filters.from, isNull);
    expect(filters.sort, RegisterFilters.defaultSort);
    expect(filters.page, 1);
  });

  test('API query: Warsaw days to UTC, inclusive "to" becomes exclusive', () {
    const filters = RegisterFilters(
      from: '2026-10-01',
      to: '2026-10-25',
      statuses: ['implemented'],
      page: 3,
    );
    final query = filters.toApiQuery();
    // 1 Oct 00:00 CEST = 30 Sep 22:00 UTC; 26 Oct 00:00 CET = 25 Oct 23:00 UTC.
    expect(query['period_from'], '2026-09-30T22:00:00.000Z');
    expect(query['period_to'], '2026-10-25T23:00:00.000Z');
    expect(query['period_by'], 'created');
    expect(query['status'], ['implemented']);
    expect(query['offset'], 100);
    expect(query['limit'], 50);
  });
}
