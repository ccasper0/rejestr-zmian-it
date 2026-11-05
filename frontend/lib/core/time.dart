import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Dates in the UI: always `Europe/Warsaw`, format `dd.MM.yyyy HH:mm`
/// (CLAUDE.md §11.6). The API speaks UTC (ISO 8601 with `Z`).
///
/// The IANA database (package `timezone`, full variant — the truncated 10y
/// variant would lose DST rules after ~2031) gives correct CET/CEST switches
/// independent of the browser's own time zone.
abstract final class WarsawTime {
  static const String zoneName = 'Europe/Warsaw';
  static tz.Location? _location;

  /// Loads the time zone database (idempotent; called from `main`, and lazily).
  static void ensureInitialized() {
    if (_location != null) return;
    tzdata.initializeTimeZones();
    _location = tz.getLocation(zoneName);
  }

  static tz.Location get location {
    ensureInitialized();
    return _location!;
  }

  /// The instant [utc] as wall-clock time in Warsaw.
  static tz.TZDateTime toWarsaw(DateTime utc) =>
      tz.TZDateTime.from(utc, location);

  /// Wall-clock time in Warsaw → instant as a plain UTC [DateTime].
  ///
  /// Never a `TZDateTime`: its `==` is only true against another
  /// `TZDateTime`, so a returned `TZDateTime` would never equal a parsed API
  /// value (the form looked permanently dirty). Compare instants with
  /// [sameInstant] anyway.
  static DateTime fromWarsaw(
    int year,
    int month,
    int day, [
    int hour = 0,
    int minute = 0,
  ]) => DateTime.fromMicrosecondsSinceEpoch(
    tz.TZDateTime(
      location,
      year,
      month,
      day,
      hour,
      minute,
    ).microsecondsSinceEpoch,
    isUtc: true,
  );

  /// Same instant (null-safe, independent of the DateTime subtype/zone).
  static bool sameInstant(DateTime? a, DateTime? b) {
    if (a == null || b == null) return a == null && b == null;
    return a.isAtSameMomentAs(b);
  }

  /// `dd.MM.yyyy HH:mm` in Warsaw, `—` for null.
  static String format(DateTime? instant) {
    if (instant == null) return '—';
    final local = toWarsaw(instant);
    return '${formatDateOnly(local)} ${_two(local.hour)}:${_two(local.minute)}';
  }

  /// `dd.MM.yyyy` of the Warsaw calendar day of [instant].
  static String formatDate(DateTime? instant) =>
      instant == null ? '—' : formatDateOnly(toWarsaw(instant));

  /// `dd.MM.yyyy` of fields already in local time (no conversion).
  static String formatDateOnly(DateTime local) =>
      '${_two(local.day)}.${_two(local.month)}.${local.year}';

  /// `yyyy-MM-dd` of the Warsaw calendar day (URL query parameters).
  static String isoDay(DateTime instant) {
    final local = toWarsaw(instant);
    return '${local.year}-${_two(local.month)}-${_two(local.day)}';
  }

  /// Start of the Warsaw calendar day `yyyy-MM-dd` as UTC; null if invalid.
  static DateTime? startOfIsoDay(String? value) {
    if (value == null) return null;
    final match = RegExp(r'^(\d{4})-(\d{2})-(\d{2})$').firstMatch(value);
    if (match == null) return null;
    final year = int.parse(match[1]!);
    final month = int.parse(match[2]!);
    final day = int.parse(match[3]!);
    // Reject days that do not exist (2026-02-31 would roll over to March).
    final probe = DateTime.utc(year, month, day);
    if (probe.year != year || probe.month != month || probe.day != day) {
      return null;
    }
    return fromWarsaw(year, month, day);
  }

  /// ISO 8601 UTC with `Z`, as the API expects.
  static String toApi(DateTime instant) => instant.toUtc().toIso8601String();

  static String _two(int value) => value.toString().padLeft(2, '0');
}

/// Parses an API timestamp (ISO 8601) into a UTC [DateTime]; null-tolerant.
DateTime? parseApiDateTime(Object? value) {
  if (value is! String) return null;
  return DateTime.tryParse(value)?.toUtc();
}
