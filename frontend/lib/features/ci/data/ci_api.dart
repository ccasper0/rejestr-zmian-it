import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import 'ci_filters.dart';

/// CI inventory of a company (`/companies/{cid}/ci`, ADR 0011 §5).
class CiApi {
  CiApi(this._dio);

  final Dio _dio;

  String _base(String companyId) =>
      '/companies/${ChangesApi.seg(companyId)}/ci';

  Future<PageResult<CiItem>> list(String companyId, CiFilters filters) async {
    final response = await _dio.get<Map<String, dynamic>>(
      _base(companyId),
      queryParameters: filters.toApiQuery(),
    );
    return PageResult.fromJson(response.data ?? const {}, CiItem.fromJson);
  }

  Future<CiItem> create(String companyId, Map<String, Object?> body) async {
    final response = await _dio.post<Map<String, dynamic>>(
      _base(companyId),
      data: body,
    );
    return CiItem.fromJson(response.data ?? const {});
  }

  /// PATCH of the changed fields only; `is_active: false` deactivates.
  Future<CiItem> update(
    String companyId,
    String ciId,
    Map<String, Object?> fields,
  ) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '${_base(companyId)}/${ChangesApi.seg(ciId)}',
      data: fields,
    );
    return CiItem.fromJson(response.data ?? const {});
  }
}

final ciApiProvider = Provider<CiApi>(
  (ref) => CiApi(ref.watch(apiClientProvider)),
);

final ciInventoryProvider = FutureProvider.autoDispose
    .family<PageResult<CiItem>, (String, CiFilters)>(
      (ref, key) => ref.watch(ciApiProvider).list(key.$1, key.$2),
    );

/// Every CI type, active and inactive (labels of existing items).
final ciTypesAllProvider = FutureProvider.autoDispose<List<CiType>>((
  ref,
) async {
  final response = await ref
      .watch(apiClientProvider)
      .get<Map<String, dynamic>>(
        '/ci-types',
        queryParameters: {'limit': ChangesApi.maxLimit},
      );
  return PageResult.fromJson(response.data ?? const {}, CiType.fromJson).items;
});

/// Every CI of a company, active and inactive (identifiers in audit diffs).
final companyCiAllProvider = FutureProvider.autoDispose
    .family<List<CiItem>, String>(
      (ref, companyId) async =>
          (await ref
                  .watch(changesApiProvider)
                  .listCi(companyId, limit: ChangesApi.maxLimit))
              .items,
    );
