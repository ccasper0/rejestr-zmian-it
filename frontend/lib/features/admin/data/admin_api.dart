import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import 'admin_models.dart';

/// Typed access to the administration endpoints (CLAUDE.md §8, ADR 0015).
///
/// Every path segment built from data goes through [ChangesApi.seg].
class AdminApi {
  AdminApi(this._dio);

  final Dio _dio;

  static String _seg(String value) => ChangesApi.seg(value);
  static const int _limit = ChangesApi.maxLimit;

  Future<Map<String, dynamic>> _get(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: query,
    );
    return response.data ?? const {};
  }

  Future<Map<String, dynamic>> _send(
    String method,
    String path, [
    Object? data,
  ]) async {
    final response = await _dio.request<Map<String, dynamic>>(
      path,
      data: data,
      options: Options(method: method),
    );
    return response.data ?? const {};
  }

  /// Every page of a paginated endpoint.
  Future<List<T>> _all<T>(
    String path,
    T Function(Map<String, dynamic>) item, {
    Map<String, dynamic> query = const {},
  }) async {
    final result = <T>[];
    while (true) {
      final page = PageResult.fromJson(
        await _get(
          path,
          query: {...query, 'limit': _limit, 'offset': result.length},
        ),
        item,
      );
      result.addAll(page.items);
      if (page.items.isEmpty || result.length >= page.total) return result;
    }
  }

  // ------------------------------------------------------------- companies

  /// All companies (admin path: every company, with counters).
  Future<List<AdminCompany>> companies() =>
      _all('/companies', AdminCompany.fromJson);

  Future<AdminCompany> createCompany(Map<String, Object?> body) async =>
      AdminCompany.fromJson(await _send('POST', '/companies', body));

  /// PATCH of the changed fields only (the prefix is never sent).
  Future<AdminCompany> updateCompany(
    String companyId,
    Map<String, Object?> fields,
  ) async => AdminCompany.fromJson(
    await _send('PATCH', '/companies/${_seg(companyId)}', fields),
  );

  Future<AdminCompany> archiveCompany(String companyId) async =>
      AdminCompany.fromJson(
        await _send('POST', '/companies/${_seg(companyId)}/archive'),
      );

  /// `PUT /companies/{id}/categories` — the FULL list (missing = withdrawn).
  Future<List<CompanyCategory>> setCompanyCategories(
    String companyId,
    List<({String categoryId, String? approverOverrideId})> categories,
  ) async {
    final json = await _send(
      'PUT',
      '/companies/${_seg(companyId)}/categories',
      {
        'categories': [
          for (final c in categories)
            {
              'category_id': c.categoryId,
              'approver_override_id': c.approverOverrideId,
            },
        ],
      },
    );
    return [
      for (final item in (json['items'] as List<Object?>? ?? const []))
        if (item is Map)
          CompanyCategory.fromJson(Map<String, dynamic>.from(item)),
    ];
  }

  /// `PUT /companies/{id}/members/{user_id}` with the FULL set of roles
  /// (`[]` removes the user from the company).
  Future<Member> setMemberRoles(
    String companyId,
    String userId,
    List<String> roles,
  ) async => Member.fromJson(
    await _send(
      'PUT',
      '/companies/${_seg(companyId)}/members/${_seg(userId)}',
      {'roles': roles},
    ),
  );

  // ------------------------------------------------------------- users

  Future<PageResult<UserAccount>> users({
    String? q,
    int limit = 50,
    int offset = 0,
  }) async => PageResult.fromJson(
    await _get(
      '/users',
      query: {
        if (q != null && q.trim().isNotEmpty) 'q': q.trim(),
        'limit': limit,
        'offset': offset,
      },
    ),
    UserAccount.fromJson,
  );

  Future<UserDetail> user(String userId) async =>
      UserDetail.fromJson(await _get('/users/${_seg(userId)}'));

  /// `POST /users`: a local account with a server-generated temporary
  /// password (returned ONCE, ADR 0018 §5).
  Future<UserWithTemporaryPassword> createUser({
    required String email,
    required String displayName,
    bool isAppAdmin = false,
  }) async => UserWithTemporaryPassword.fromJson(
    await _send('POST', '/users', {
      'email': email,
      'display_name': displayName,
      'is_app_admin': isAppAdmin,
    }),
  );

  /// New temporary password (shown once), lockout cleared, sessions ended.
  Future<UserWithTemporaryPassword> resetPassword(String userId) async =>
      UserWithTemporaryPassword.fromJson(
        await _send('POST', '/users/${_seg(userId)}/reset-password'),
      );

  /// `PATCH /users/{id}` with only the given fields.
  Future<UserAccount> updateUser(
    String userId, {
    String? displayName,
    bool? isActive,
    bool? isAppAdmin,
  }) async => UserAccount.fromJson(
    await _send('PATCH', '/users/${_seg(userId)}', {
      'display_name': ?displayName,
      'is_active': ?isActive,
      'is_app_admin': ?isAppAdmin,
    }),
  );

  // ------------------------------------------------------------- dictionaries

  /// The whole category dictionary in tree order (active and inactive).
  Future<List<Category>> categories() => _all('/categories', Category.fromJson);

  Future<Category> createCategory(Map<String, Object?> body) async =>
      Category.fromJson(await _send('POST', '/categories', body));

  Future<Category> updateCategory(
    String categoryId,
    Map<String, Object?> fields,
  ) async => Category.fromJson(
    await _send('PATCH', '/categories/${_seg(categoryId)}', fields),
  );

  Future<List<CiType>> ciTypes() => _all('/ci-types', CiType.fromJson);

  Future<CiType> createCiType(Map<String, Object?> body) async =>
      CiType.fromJson(await _send('POST', '/ci-types', body));

  Future<CiType> updateCiType(
    String ciTypeId,
    Map<String, Object?> fields,
  ) async => CiType.fromJson(
    await _send('PATCH', '/ci-types/${_seg(ciTypeId)}', fields),
  );

  Future<PermissionMatrix> permissionMatrix() async =>
      PermissionMatrix.fromJson(await _get('/permissions/matrix'));
}

final adminApiProvider = Provider<AdminApi>(
  (ref) => AdminApi(ref.watch(apiClientProvider)),
);

final adminCompaniesProvider = FutureProvider.autoDispose<List<AdminCompany>>(
  (ref) => ref.watch(adminApiProvider).companies(),
);

/// Directory page: (search, 1-based page).
final usersPageProvider = FutureProvider.autoDispose
    .family<PageResult<UserAccount>, (String, int)>(
      (ref, key) => ref
          .watch(adminApiProvider)
          .users(
            q: key.$1,
            limit: usersPageSize,
            offset: (key.$2 - 1) * usersPageSize,
          ),
    );

const int usersPageSize = 50;

final userDetailProvider = FutureProvider.autoDispose
    .family<UserDetail, String>(
      (ref, userId) => ref.watch(adminApiProvider).user(userId),
    );

final allCategoriesProvider = FutureProvider.autoDispose<List<Category>>(
  (ref) => ref.watch(adminApiProvider).categories(),
);

final allCiTypesProvider = FutureProvider.autoDispose<List<CiType>>(
  (ref) => ref.watch(adminApiProvider).ciTypes(),
);

final permissionMatrixProvider = FutureProvider.autoDispose<PermissionMatrix>(
  (ref) => ref.watch(adminApiProvider).permissionMatrix(),
);

/// Up to 500 users (names of actors in the global audit chain; admin only).
final userDirectoryProvider = FutureProvider.autoDispose<List<UserAccount>>(
  (ref) async =>
      (await ref.watch(adminApiProvider).users(limit: ChangesApi.maxLimit))
          .items,
);
