import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../../changes/data/models.dart';
import 'audit_filters.dart';
import 'audit_models.dart';

/// `GET /audit` and `POST /audit/verify` (ADR 0009): one chain per call —
/// a company's (`company_id`) or the global one (`null`, app admin only).
class AuditApi {
  AuditApi(this._dio);

  final Dio _dio;

  Future<PageResult<AuditLogEntry>> entries(
    String? companyId,
    AuditFilters filters,
  ) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/audit',
      queryParameters: {'company_id': ?companyId, ...filters.toApiQuery()},
    );
    return PageResult.fromJson(
      response.data ?? const {},
      AuditLogEntry.fromJson,
    );
  }

  /// Recomputes the chain; the verification itself is audited by the API.
  Future<VerifyResult> verify(String? companyId) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/audit/verify',
      queryParameters: {'company_id': ?companyId},
    );
    return VerifyResult.fromJson(response.data ?? const {});
  }
}

final auditApiProvider = Provider<AuditApi>(
  (ref) => AuditApi(ref.watch(apiClientProvider)),
);

/// (company id or null = global chain, filters).
final auditLogProvider = FutureProvider.autoDispose
    .family<PageResult<AuditLogEntry>, (String?, AuditFilters)>(
      (ref, key) => ref.watch(auditApiProvider).entries(key.$1, key.$2),
    );
