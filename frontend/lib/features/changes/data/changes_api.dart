import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import 'models.dart';
import 'register_filters.dart';

/// Typed access to the change endpoints (CLAUDE.md §8, ADR 0013 §7).
///
/// Status changes go exclusively through [performAction]
/// (`POST …/actions/{action}`); the frontend never sends `status`.
class ChangesApi {
  ChangesApi(this._dio);

  final Dio _dio;

  /// One path segment built from data (ids, numbers, actions): percent-encoded
  /// so `/`, `?`, `#` cannot change the request path; dot segments, which
  /// URL resolution would collapse (`by-number/..` = `changes`), and empty
  /// segments are refused. Every interpolated path segment goes through here.
  static String seg(String value) {
    if (value.isEmpty || value == '.' || value == '..') {
      throw ArgumentError.value(value, 'value', 'Invalid path segment');
    }
    return Uri.encodeComponent(value);
  }

  /// Large enough for one page of members/CI/audit (API max 500).
  static const int maxLimit = 500;

  String _changes(String companyId) => '/companies/${seg(companyId)}/changes';

  Future<Map<String, dynamic>> _getMap(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: query,
    );
    return response.data ?? const {};
  }

  /// All pages of a paginated endpoint (members, audit trail).
  Future<List<T>> _all<T>(
    String path,
    T Function(Map<String, dynamic>) item, {
    Map<String, dynamic> query = const {},
  }) async {
    final result = <T>[];
    var offset = 0;
    while (true) {
      final page = PageResult.fromJson(
        await _getMap(
          path,
          query: {...query, 'limit': maxLimit, 'offset': offset},
        ),
        item,
      );
      result.addAll(page.items);
      offset += page.items.length;
      if (page.items.isEmpty || offset >= page.total) return result;
    }
  }

  // ------------------------------------------------------------- register

  Future<PageResult<Change>> listChanges(
    String companyId,
    RegisterFilters filters,
  ) async => PageResult.fromJson(
    await _getMap(_changes(companyId), query: filters.toApiQuery()),
    Change.fromJson,
  );

  Future<ChangeStats> stats(String companyId) async =>
      ChangeStats.fromJson(await _getMap('/companies/${seg(companyId)}/stats'));

  // ------------------------------------------------------------- card

  Future<Change> getByNumber(String companyId, String number) async =>
      Change.fromJson(
        await _getMap('${_changes(companyId)}/by-number/${seg(number)}'),
      );

  Future<Change> getChange(String companyId, String changeId) async =>
      Change.fromJson(await _getMap('${_changes(companyId)}/${seg(changeId)}'));

  /// New draft with its number (fields may be empty, §10.3).
  Future<Change> createDraft(
    String companyId, [
    Map<String, Object?> fields = const {},
  ]) async {
    final response = await _dio.post<Map<String, dynamic>>(
      _changes(companyId),
      data: fields,
    );
    return Change.fromJson(response.data ?? const {});
  }

  /// PATCH of the given fields, guarded by [version] (409 when stale).
  Future<Change> update(
    String companyId,
    String changeId, {
    required int version,
    required Map<String, Object?> fields,
  }) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '${_changes(companyId)}/${seg(changeId)}',
      data: {...fields, 'version': version},
    );
    return Change.fromJson(response.data ?? const {});
  }

  Future<Readiness> readiness(String companyId, String changeId) async =>
      Readiness.fromJson(
        await _getMap('${_changes(companyId)}/${seg(changeId)}/readiness'),
      );

  /// `submit|return|approve|reject|implement|verify|rollback|cancel|consent`.
  Future<ActionResult> performAction(
    String companyId,
    String changeId,
    String action, {
    required int version,
    String? comment,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '${_changes(companyId)}/${seg(changeId)}/actions/${seg(action)}',
      data: {
        'version': version,
        if (comment != null && comment.trim().isNotEmpty) 'comment': comment,
      },
    );
    return ActionResult.fromJson(response.data ?? const {});
  }

  Future<List<AuditEntry>> auditTrail(String companyId, String changeId) =>
      _all(
        '${_changes(companyId)}/${seg(changeId)}/audit',
        AuditEntry.fromJson,
      );

  Future<ChainStatus> chainStatus(String companyId) async =>
      ChainStatus.fromJson(
        await _getMap('/companies/${seg(companyId)}/audit/status'),
      );

  Future<ChangeComment> addComment(
    String companyId,
    String changeId,
    String body,
  ) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '${_changes(companyId)}/${seg(changeId)}/comments',
      data: {'body': body},
    );
    return ChangeComment.fromJson(response.data ?? const {});
  }

  // ------------------------------------------------------------- attachments

  Future<List<Attachment>> attachments(
    String companyId,
    String changeId,
  ) async {
    final response = await _dio.get<List<Object?>>(
      '${_changes(companyId)}/${seg(changeId)}/attachments',
    );
    return [
      for (final item in response.data ?? const <Object?>[])
        if (item is Map) Attachment.fromJson(Map<String, dynamic>.from(item)),
    ];
  }

  Future<Attachment> uploadAttachment(
    String companyId,
    String changeId, {
    required String filename,
    required Uint8List bytes,
    String? contentType,
  }) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: contentType == null || contentType.isEmpty
            ? null
            : DioMediaType.parse(contentType),
      ),
    });
    final response = await _dio.post<Map<String, dynamic>>(
      '${_changes(companyId)}/${seg(changeId)}/attachments',
      data: form,
    );
    return Attachment.fromJson(response.data ?? const {});
  }

  /// File bytes (the download is audited by the API, ADR 0013 §4).
  Future<Uint8List> downloadAttachment(
    String companyId,
    String changeId,
    String attachmentId,
  ) async {
    final response = await _dio.get<List<int>>(
      '${_changes(companyId)}/${seg(changeId)}/attachments/${seg(attachmentId)}',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data ?? const []);
  }

  // ------------------------------------------------------------- company data

  Future<List<Member>> members(String companyId) =>
      _all('/companies/${seg(companyId)}/members', Member.fromJson);

  Future<List<CompanyCategory>> companyCategories(String companyId) async {
    final json = await _getMap('/companies/${seg(companyId)}/categories');
    return [
      for (final item in (json['items'] as List<Object?>? ?? const []))
        if (item is Map)
          CompanyCategory.fromJson(Map<String, dynamic>.from(item)),
    ];
  }

  Future<List<Category>> subcategories(String parentId) async =>
      PageResult.fromJson(
        await _getMap(
          '/categories',
          query: {'parent_id': parentId, 'active': true, 'limit': maxLimit},
        ),
        Category.fromJson,
      ).items;

  /// Top-level categories of the global dictionary (flags such as
  /// `requires_ci_owner_consent` are not in the company list).
  Future<List<Category>> topCategories() async => PageResult.fromJson(
    await _getMap('/categories', query: {'top_level': true, 'limit': maxLimit}),
    Category.fromJson,
  ).items;

  Future<PageResult<CiItem>> listCi(
    String companyId, {
    String? q,
    bool? active,
    int limit = 50,
  }) async => PageResult.fromJson(
    await _getMap(
      '/companies/${seg(companyId)}/ci',
      query: {
        if (q != null && q.trim().isNotEmpty) 'q': q.trim(),
        'active': ?active,
        'limit': limit,
      },
    ),
    CiItem.fromJson,
  );

  Future<List<CiType>> ciTypes() async => PageResult.fromJson(
    await _getMap('/ci-types', query: {'active': true, 'limit': maxLimit}),
    CiType.fromJson,
  ).items;

  Future<CiItem> createCi(
    String companyId, {
    required String ciTypeId,
    required String identifier,
    required String name,
    String? description,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/companies/${seg(companyId)}/ci',
      data: {
        'ci_type_id': ciTypeId,
        'identifier': identifier,
        'name': name,
        if (description != null && description.trim().isNotEmpty)
          'description': description,
      },
    );
    return CiItem.fromJson(response.data ?? const {});
  }
}

final changesApiProvider = Provider<ChangesApi>(
  (ref) => ChangesApi(ref.watch(apiClientProvider)),
);

// ----------------------------------------------------------------- providers
// Keys are records (structural equality). autoDispose: data is refetched when
// a screen is opened again.

final registerProvider = FutureProvider.autoDispose
    .family<PageResult<Change>, (String, RegisterFilters)>(
      (ref, key) => ref.watch(changesApiProvider).listChanges(key.$1, key.$2),
    );

final statsProvider = FutureProvider.autoDispose.family<ChangeStats, String>(
  (ref, companyId) => ref.watch(changesApiProvider).stats(companyId),
);

/// Card by number (`/c/:prefix/changes/:number`).
final changeByNumberProvider = FutureProvider.autoDispose
    .family<Change, (String, String)>(
      (ref, key) => ref.watch(changesApiProvider).getByNumber(key.$1, key.$2),
    );

final auditTrailProvider = FutureProvider.autoDispose
    .family<List<AuditEntry>, (String, String)>(
      (ref, key) => ref.watch(changesApiProvider).auditTrail(key.$1, key.$2),
    );

final chainStatusProvider = FutureProvider.autoDispose
    .family<ChainStatus, String>(
      (ref, companyId) => ref.watch(changesApiProvider).chainStatus(companyId),
    );

final attachmentsProvider = FutureProvider.autoDispose
    .family<List<Attachment>, (String, String)>(
      (ref, key) => ref.watch(changesApiProvider).attachments(key.$1, key.$2),
    );

final readinessProvider = FutureProvider.autoDispose
    .family<Readiness, (String, String)>(
      (ref, key) => ref.watch(changesApiProvider).readiness(key.$1, key.$2),
    );

final membersProvider = FutureProvider.autoDispose.family<List<Member>, String>(
  (ref, companyId) => ref.watch(changesApiProvider).members(companyId),
);

final companyCategoriesProvider = FutureProvider.autoDispose
    .family<List<CompanyCategory>, String>(
      (ref, companyId) =>
          ref.watch(changesApiProvider).companyCategories(companyId),
    );

final subcategoriesProvider = FutureProvider.autoDispose
    .family<List<Category>, String>(
      (ref, parentId) => ref.watch(changesApiProvider).subcategories(parentId),
    );

final topCategoriesProvider = FutureProvider.autoDispose<List<Category>>(
  (ref) => ref.watch(changesApiProvider).topCategories(),
);

final ciTypesProvider = FutureProvider.autoDispose<List<CiType>>(
  (ref) => ref.watch(changesApiProvider).ciTypes(),
);
