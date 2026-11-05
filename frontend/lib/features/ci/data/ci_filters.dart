import 'package:freezed_annotation/freezed_annotation.dart';

part 'ci_filters.freezed.dart';

/// Filters of the CI inventory — mirrored 1:1 in the URL query string.
///
/// | URL | API (`GET /companies/{cid}/ci`) |
/// |---|---|
/// | `q` | `q` (identifier and name) |
/// | `type` (repeated) | `type` (CI type codes) |
/// | `status` = `active` / `inactive` (absent = all) | `active` = true / false |
/// | `page` (1-based) | `offset`, `limit` |
@freezed
abstract class CiFilters with _$CiFilters {
  const CiFilters._();

  const factory CiFilters({
    @Default('') String q,
    @Default(<String>[]) List<String> types,
    bool? active,
    @Default(1) int page,
  }) = _CiFilters;

  static const int pageSize = 50;
  static final RegExp _typeCode = RegExp(r'^[a-z][a-z0-9_]{1,31}$');

  factory CiFilters.fromQuery(Map<String, List<String>> query) {
    String? one(String key) {
      final values = query[key];
      if (values == null || values.isEmpty) return null;
      final value = values.first.trim();
      return value.isEmpty ? null : value;
    }

    final seen = <String>{};
    final page = int.tryParse(one('page') ?? '');
    return CiFilters(
      q: one('q') ?? '',
      types: [
        for (final raw in query['type'] ?? const <String>[])
          for (final part in raw.split(','))
            if (_typeCode.hasMatch(part.trim()) && seen.add(part.trim()))
              part.trim(),
      ],
      active: switch (one('status')) {
        'active' => true,
        'inactive' => false,
        _ => null,
      },
      page: page != null && page > 0 ? page : 1,
    );
  }

  Map<String, Object> toQuery() => {
    if (q.trim().isNotEmpty) 'q': q.trim(),
    if (types.isNotEmpty) 'type': types,
    if (active != null) 'status': active! ? 'active' : 'inactive',
    if (page > 1) 'page': '$page',
  };

  String location(String prefix) => Uri(
    path: '/c/$prefix/ci',
    queryParameters: toQuery().isEmpty ? null : toQuery(),
  ).toString();

  Map<String, dynamic> toApiQuery() => {
    if (q.trim().isNotEmpty) 'q': q.trim(),
    if (types.isNotEmpty) 'type': types,
    'active': ?active,
    'limit': pageSize,
    'offset': (page - 1) * pageSize,
  };

  bool get hasFilters =>
      q.trim().isNotEmpty || types.isNotEmpty || active != null;
}
