import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/time.dart';

void main() {
  setUpAll(WarsawTime.ensureInitialized);

  group('WarsawTime.format (dd.MM.yyyy HH:mm, Europe/Warsaw)', () {
    test('winter time is UTC+1', () {
      expect(
        WarsawTime.format(DateTime.utc(2026, 1, 15, 12, 5)),
        '15.01.2026 13:05',
      );
    });

    test('summer time is UTC+2', () {
      expect(
        WarsawTime.format(DateTime.utc(2026, 7, 1, 22, 30)),
        '02.07.2026 00:30',
      );
    });

    test('spring forward: 29.03.2026 02:00 CET -> 03:00 CEST', () {
      expect(
        WarsawTime.format(DateTime.utc(2026, 3, 29, 0, 59)),
        '29.03.2026 01:59',
      );
      expect(
        WarsawTime.format(DateTime.utc(2026, 3, 29, 1, 0)),
        '29.03.2026 03:00',
      );
    });

    test('fall back: 25.10.2026 03:00 CEST -> 02:00 CET (02:xx twice)', () {
      expect(
        WarsawTime.format(DateTime.utc(2026, 10, 25, 0, 30)),
        '25.10.2026 02:30',
      );
      expect(
        WarsawTime.format(DateTime.utc(2026, 10, 25, 1, 30)),
        '25.10.2026 02:30',
      );
      expect(
        WarsawTime.format(DateTime.utc(2026, 10, 25, 2, 0)),
        '25.10.2026 03:00',
      );
    });

    test('does not depend on the machine time zone (local DateTime input)', () {
      final instant = DateTime.utc(2026, 12, 31, 23, 30);
      expect(WarsawTime.format(instant.toLocal()), '01.01.2027 00:30');
    });

    test('rules hold beyond the truncated 10-year database (until 2037)', () {
      // The package's full database ends in 2037 (ADR 0014 §4).
      expect(
        WarsawTime.format(DateTime.utc(2037, 7, 1, 10)),
        '01.07.2037 12:00',
      );
    });

    test('null renders as a dash', () {
      expect(WarsawTime.format(null), '—');
    });
  });

  group('Warsaw wall clock -> UTC', () {
    test('summer and winter offsets', () {
      expect(
        WarsawTime.fromWarsaw(2026, 7, 1, 12),
        DateTime.utc(2026, 7, 1, 10),
      );
      expect(
        WarsawTime.fromWarsaw(2026, 12, 1, 12),
        DateTime.utc(2026, 12, 1, 11),
      );
    });

    test('start of day of the DST switch days', () {
      expect(
        WarsawTime.startOfIsoDay('2026-03-29'),
        DateTime.utc(2026, 3, 28, 23),
      );
      expect(
        WarsawTime.startOfIsoDay('2026-10-25'),
        DateTime.utc(2026, 10, 24, 22),
      );
    });

    test('invalid days are rejected', () {
      expect(WarsawTime.startOfIsoDay('2026-13-01'), isNull);
      expect(WarsawTime.startOfIsoDay('2026-02-31'), isNull);
      expect(WarsawTime.startOfIsoDay('2026-02-29'), isNull);
      expect(WarsawTime.startOfIsoDay('2028-02-29'), isNotNull);
      expect(WarsawTime.startOfIsoDay('jutro'), isNull);
    });

    test(
      'fromWarsaw returns a plain UTC DateTime equal to parsed API time',
      () {
        final picked = WarsawTime.fromWarsaw(2026, 11, 15, 19);
        final fromApi = DateTime.parse('2026-11-15T18:00:00.000000Z');
        expect(picked.runtimeType, DateTime.utc(2026).runtimeType);
        expect(picked.isUtc, isTrue);
        expect(picked, fromApi);
        expect(WarsawTime.sameInstant(picked, fromApi), isTrue);
        expect(WarsawTime.sameInstant(null, null), isTrue);
        expect(WarsawTime.sameInstant(picked, null), isFalse);
      },
    );

    test('toApi is ISO 8601 UTC with Z', () {
      expect(
        WarsawTime.toApi(WarsawTime.fromWarsaw(2026, 11, 2, 19)),
        '2026-11-02T18:00:00.000Z',
      );
    });
  });
}
