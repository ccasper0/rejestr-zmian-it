import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../core/time.dart';

part 'register_filters.freezed.dart';

/// Register filters — the single state of the register screen, mirrored 1:1
/// in the URL query string (§10.1: filters are shareable and survive reload).
///
/// URL parameters (all optional):
///
/// | URL | API | meaning |
/// |---|---|---|
/// | `q` | `q` | number, title, ticket |
/// | `status` (repeated) | `status` | status codes |
/// | `type` (repeated) | `type` | change types |
/// | `category` (repeated) | `category` | category ids |
/// | `ci` (repeated) | `ci` | CI ids |
/// | `assignee` | `assignee` | user id |
/// | `approved_by` | `approved_by` | user id or `system` |
/// | `from`, `to` | `period_from`, `period_to` | Warsaw days `yyyy-MM-dd`, both inclusive in the URL |
/// | `period_by` | `period_by` | `created` (default) or `implemented` |
/// | `sort` | `sort` | e.g. `-created_at` (default) |
/// | `page` | `offset` | 1-based page |
@freezed
abstract class RegisterFilters with _$RegisterFilters {
  const RegisterFilters._();

  const factory RegisterFilters({
    @Default('') String q,
    @Default(<String>[]) List<String> statuses,
    @Default(<String>[]) List<String> types,
    @Default(<String>[]) List<String> categories,
    @Default(<String>[]) List<String> cis,
    String? assignee,
    String? approvedBy,
    String? from,
    String? to,
    @Default(RegisterFilters.defaultPeriodBy) String periodBy,
    @Default(RegisterFilters.defaultSort) String sort,
    @Default(1) int page,
  }) = _RegisterFilters;

  static const String defaultSort = '-created_at';
  static const String defaultPeriodBy = 'created';
  static const int pageSize = 50;

  /// Sort keys of the API (`changes_service.SortKey`) with Polish labels.
  static const Map<String, String> sortLabels = {
    '-created_at': 'Najnowsze',
    'created_at': 'Najstarsze',
    '-number': 'Numer malejąco',
    'number': 'Numer rosnąco',
    '-implemented_at': 'Wdrożenie: najnowsze',
    'implemented_at': 'Wdrożenie: najstarsze',
    'title': 'Tytuł A–Z',
    '-title': 'Tytuł Z–A',
    'status': 'Status',
  };

  static const Set<String> statusValues = {
    'draft',
    'pending_approval',
    'approved',
    'implemented',
    'verified',
    'rejected',
    'rolled_back',
    'cancelled',
  };
  static const Set<String> typeValues = {'standard', 'normal', 'emergency'};

  static final RegExp _day = RegExp(r'^\d{4}-\d{2}-\d{2}$');

  /// Reads the URL (`Uri.queryParametersAll`); invalid values are dropped.
  factory RegisterFilters.fromQuery(Map<String, List<String>> query) {
    String? single(String key) {
      final values = query[key];
      if (values == null || values.isEmpty) return null;
      final value = values.first.trim();
      return value.isEmpty ? null : value;
    }

    List<String> many(String key, [Set<String>? allowed]) {
      final seen = <String>{};
      return [
        for (final raw in query[key] ?? const <String>[])
          for (final part in raw.split(','))
            if (part.trim().isNotEmpty &&
                (allowed == null || allowed.contains(part.trim())) &&
                seen.add(part.trim()))
              part.trim(),
      ];
    }

    String? day(String key) {
      final value = single(key);
      return value != null &&
              _day.hasMatch(value) &&
              WarsawTime.startOfIsoDay(value) != null
          ? value
          : null;
    }

    final sort = single('sort');
    final periodBy = single('period_by');
    final page = int.tryParse(single('page') ?? '');
    return RegisterFilters(
      q: single('q') ?? '',
      statuses: many('status', statusValues),
      types: many('type', typeValues),
      categories: many('category'),
      cis: many('ci'),
      assignee: single('assignee'),
      approvedBy: single('approved_by'),
      from: day('from'),
      to: day('to'),
      periodBy: periodBy == 'implemented' ? 'implemented' : defaultPeriodBy,
      sort: sortLabels.containsKey(sort) ? sort! : defaultSort,
      page: page != null && page > 0 ? page : 1,
    );
  }

  /// Query string of the URL (defaults omitted, so the plain URL stays clean).
  Map<String, Object> toQuery() => {
    if (q.trim().isNotEmpty) 'q': q.trim(),
    if (statuses.isNotEmpty) 'status': statuses,
    if (types.isNotEmpty) 'type': types,
    if (categories.isNotEmpty) 'category': categories,
    if (cis.isNotEmpty) 'ci': cis,
    'assignee': ?assignee,
    'approved_by': ?approvedBy,
    'from': ?from,
    'to': ?to,
    if (periodBy != defaultPeriodBy) 'period_by': periodBy,
    if (sort != defaultSort) 'sort': sort,
    if (page > 1) 'page': '$page',
  };

  /// Register location with these filters.
  String location(String prefix) => Uri(
    path: '/c/$prefix/changes',
    queryParameters: toQuery().isEmpty ? null : toQuery(),
  ).toString();

  /// Query parameters of `GET /companies/{cid}/changes`.
  Map<String, dynamic> toApiQuery() {
    final fromInstant = WarsawTime.startOfIsoDay(from);
    final toDay = WarsawTime.startOfIsoDay(to);
    // `to` is inclusive in the UI; the API's `period_to` is exclusive.
    DateTime? toInstant;
    if (toDay != null) {
      final local = WarsawTime.toWarsaw(toDay);
      toInstant = WarsawTime.fromWarsaw(local.year, local.month, local.day + 1);
    }
    return {
      if (q.trim().isNotEmpty) 'q': q.trim(),
      if (statuses.isNotEmpty) 'status': statuses,
      if (types.isNotEmpty) 'type': types,
      if (categories.isNotEmpty) 'category': categories,
      if (cis.isNotEmpty) 'ci': cis,
      'assignee': ?assignee,
      'approved_by': ?approvedBy,
      if (fromInstant != null) 'period_from': WarsawTime.toApi(fromInstant),
      if (toInstant != null) 'period_to': WarsawTime.toApi(toInstant),
      if (fromInstant != null || toInstant != null) 'period_by': periodBy,
      'sort': sort,
      'limit': pageSize,
      'offset': (page - 1) * pageSize,
    };
  }

  bool get hasFilters =>
      q.trim().isNotEmpty ||
      statuses.isNotEmpty ||
      types.isNotEmpty ||
      categories.isNotEmpty ||
      cis.isNotEmpty ||
      assignee != null ||
      approvedBy != null ||
      from != null ||
      to != null;

  /// Clears filters, keeps the sort order.
  RegisterFilters cleared() => RegisterFilters(sort: sort);
}
