import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../core/time.dart';

part 'audit_filters.freezed.dart';

/// Filters of the audit log browser — mirrored 1:1 in the URL query string.
///
/// | URL | API (`GET /audit`) |
/// |---|---|
/// | `entity` | `entity_type` |
/// | `action` | `action` |
/// | `actor` | `actor_id` |
/// | `from`, `to` (Warsaw days, both inclusive) | `occurred_from`, `occurred_to` (exclusive) |
/// | `page` (1-based) | `offset`, `limit` |
@freezed
abstract class AuditFilters with _$AuditFilters {
  const AuditFilters._();

  const factory AuditFilters({
    String? entityType,
    String? action,
    String? actor,
    String? from,
    String? to,
    @Default(1) int page,
  }) = _AuditFilters;

  static const int pageSize = 50;

  /// `app.domain.audit.EntityType` with Polish labels.
  static const Map<String, String> entityTypes = {
    'change': 'Zmiana',
    'ci': 'Obiekt (CI)',
    'ci_type': 'Typ obiektu',
    'company': 'Spółka',
    'membership': 'Role w spółce',
    'category': 'Kategoria',
    'company_category': 'Kategorie spółki',
    'attachment': 'Załącznik',
    'report': 'Raport',
    'user': 'Użytkownik',
    'auth': 'Logowanie i dostęp',
    'audit': 'Weryfikacja dziennika',
  };

  /// `app.domain.audit.AuditAction` with Polish labels.
  static const Map<String, String> actions = {
    'create': 'Utworzenie',
    'update': 'Edycja',
    'transition': 'Zmiana statusu',
    'archive': 'Archiwizacja',
    'deactivate': 'Dezaktywacja',
    'attach': 'Dodanie załącznika',
    'download': 'Pobranie załącznika',
    'comment': 'Komentarz',
    'export': 'Eksport',
    'login': 'Logowanie',
    'login_failed': 'Nieudane logowanie',
    'logout': 'Wylogowanie',
    'token_refresh': 'Odświeżenie sesji',
    'session_revoke': 'Zakończenie sesji',
    'lockout': 'Blokada konta',
    'password_change': 'Zmiana hasła',
    'password_reset': 'Reset hasła',
    'role_grant': 'Nadanie roli',
    'role_revoke': 'Odebranie roli',
    'access_denied': 'Odmowa dostępu',
    'verify': 'Weryfikacja łańcucha',
  };

  static final RegExp _day = RegExp(r'^\d{4}-\d{2}-\d{2}$');
  static final RegExp _uuid = RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{12}$',
  );

  /// Reads the URL; unknown values are dropped (the API would answer 422).
  factory AuditFilters.fromQuery(Map<String, String> query) {
    String? one(String key, bool Function(String) valid) {
      final value = query[key]?.trim();
      return value != null && value.isNotEmpty && valid(value) ? value : null;
    }

    bool day(String v) =>
        _day.hasMatch(v) && WarsawTime.startOfIsoDay(v) != null;
    final page = int.tryParse(query['page'] ?? '');
    return AuditFilters(
      entityType: one('entity', entityTypes.containsKey),
      action: one('action', actions.containsKey),
      actor: one('actor', _uuid.hasMatch),
      from: one('from', day),
      to: one('to', day),
      page: page != null && page > 0 ? page : 1,
    );
  }

  Map<String, String> toQuery() => {
    'entity': ?entityType,
    'action': ?action,
    'actor': ?actor,
    'from': ?from,
    'to': ?to,
    if (page > 1) 'page': '$page',
  };

  String location(String path) => Uri(
    path: path,
    queryParameters: toQuery().isEmpty ? null : toQuery(),
  ).toString();

  /// Query of `GET /audit` (without `company_id`).
  Map<String, dynamic> toApiQuery() {
    final fromInstant = WarsawTime.startOfIsoDay(from);
    final toDay = WarsawTime.startOfIsoDay(to);
    DateTime? toInstant;
    if (toDay != null) {
      final local = WarsawTime.toWarsaw(toDay);
      toInstant = WarsawTime.fromWarsaw(local.year, local.month, local.day + 1);
    }
    return {
      'entity_type': ?entityType,
      'action': ?action,
      'actor_id': ?actor,
      if (fromInstant != null) 'occurred_from': WarsawTime.toApi(fromInstant),
      if (toInstant != null) 'occurred_to': WarsawTime.toApi(toInstant),
      'limit': pageSize,
      'offset': (page - 1) * pageSize,
    };
  }

  bool get hasFilters =>
      entityType != null ||
      action != null ||
      actor != null ||
      from != null ||
      to != null;
}
