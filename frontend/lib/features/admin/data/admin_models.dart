import 'package:freezed_annotation/freezed_annotation.dart';

part 'admin_models.freezed.dart';
part 'admin_models.g.dart';

// Schemas mirror backend/app/schemas/{identity,permissions,audit}.py — the
// backend is the source of truth for the contract (ADR 0015).

/// Counters of the admin companies table (`counts` of `GET /companies`).
@freezed
abstract class CompanyCounts with _$CompanyCounts {
  const factory CompanyCounts({
    @Default(0) int activeCi,
    @Default(0) int allCi,
    @Default(0) int editors,
    @Default(0) int approvers,
    @Default(0) int auditors,
    @Default(0) int viewers,
  }) = _CompanyCounts;

  factory CompanyCounts.fromJson(Map<String, dynamic> json) =>
      _$CompanyCountsFromJson(json);
}

/// A company (`CompanyListItem` of `GET /companies`, or `CompanyOut` of
/// create/update/archive — without `my_roles`/`counts`).
@freezed
abstract class AdminCompany with _$AdminCompany {
  const AdminCompany._();

  const factory AdminCompany({
    required String id,
    required String name,
    String? taxId,
    required String prefix,
    required String status,
    @Default(false) bool isKscEntity,
    String? defaultApproverId,
    required DateTime createdAt,
    required DateTime updatedAt,
    @Default(<String>[]) List<String> myRoles,
    @Default(CompanyCounts()) CompanyCounts counts,
  }) = _AdminCompany;

  factory AdminCompany.fromJson(Map<String, dynamic> json) =>
      _$AdminCompanyFromJson(json);

  bool get isArchived => status == 'archived';
}

/// Password state of a local account (`UserOut`, ADR 0018 §5) — never the
/// hash.
abstract interface class AccountState {
  bool get isActive;
  bool get hasPassword;
  bool get mustChangePassword;
  DateTime? get lockedUntil;

  /// End of validity of a pending temporary password (set exactly when
  /// [mustChangePassword]; ADR 0020 §9).
  DateTime? get tempPasswordExpiresAt;
}

/// A user of the directory (`GET /users`, `UserOut`).
@freezed
abstract class UserAccount with _$UserAccount implements AccountState {
  const factory UserAccount({
    required String id,
    @Default('') String externalId,
    @Default('') String email,
    required String displayName,
    @Default(false) bool isAppAdmin,
    required bool isActive,
    DateTime? createdAt,
    DateTime? updatedAt,
    @Default(false) bool hasPassword,
    @Default(false) bool mustChangePassword,
    DateTime? passwordChangedAt,
    DateTime? lockedUntil,
    DateTime? tempPasswordExpiresAt,
  }) = _UserAccount;

  factory UserAccount.fromJson(Map<String, dynamic> json) =>
      _$UserAccountFromJson(json);
}

/// `POST /users`, `POST /users/{id}/reset-password`
/// (`UserWithTemporaryPasswordOut`): the temporary password is shown ONCE
/// and never stored by the app.
@freezed
abstract class UserWithTemporaryPassword with _$UserWithTemporaryPassword {
  const factory UserWithTemporaryPassword({
    required UserAccount user,
    required String temporaryPassword,
  }) = _UserWithTemporaryPassword;

  factory UserWithTemporaryPassword.fromJson(Map<String, dynamic> json) =>
      _$UserWithTemporaryPasswordFromJson(json);
}

@freezed
abstract class UserMembership with _$UserMembership {
  const UserMembership._();

  const factory UserMembership({
    required String companyId,
    required String companyName,
    required String companyPrefix,
    @Default('active') String companyStatus,
    @Default(<String>[]) List<String> roles,
  }) = _UserMembership;

  factory UserMembership.fromJson(Map<String, dynamic> json) =>
      _$UserMembershipFromJson(json);

  bool get isArchived => companyStatus == 'archived';
}

/// `GET /users/{id}`: the user with the roles in every company.
@freezed
abstract class UserDetail with _$UserDetail implements AccountState {
  const factory UserDetail({
    required String id,
    @Default('') String externalId,
    @Default('') String email,
    required String displayName,
    @Default(false) bool isAppAdmin,
    required bool isActive,
    @Default(false) bool hasPassword,
    @Default(false) bool mustChangePassword,
    DateTime? passwordChangedAt,
    DateTime? lockedUntil,
    DateTime? tempPasswordExpiresAt,
    @Default(<UserMembership>[]) List<UserMembership> memberships,
  }) = _UserDetail;

  factory UserDetail.fromJson(Map<String, dynamic> json) =>
      _$UserDetailFromJson(json);
}

/// One row of `GET /permissions/matrix`.
@freezed
abstract class MatrixRow with _$MatrixRow {
  const factory MatrixRow({
    required String action,
    required String label,
    String? note,
    @Default(<String>[]) List<String> roles,
  }) = _MatrixRow;

  factory MatrixRow.fromJson(Map<String, dynamic> json) =>
      _$MatrixRowFromJson(json);
}

@freezed
abstract class ChangeActionRule with _$ChangeActionRule {
  const factory ChangeActionRule({
    required String action,
    required String requires,
  }) = _ChangeActionRule;

  factory ChangeActionRule.fromJson(Map<String, dynamic> json) =>
      _$ChangeActionRuleFromJson(json);
}

/// `GET /permissions/matrix` — the RBAC matrix of `app/permissions.py`.
@freezed
abstract class PermissionMatrix with _$PermissionMatrix {
  const factory PermissionMatrix({
    required List<String> roles,
    required List<MatrixRow> actions,
    @Default(<ChangeActionRule>[]) List<ChangeActionRule> changeActions,
  }) = _PermissionMatrix;

  factory PermissionMatrix.fromJson(Map<String, dynamic> json) =>
      _$PermissionMatrixFromJson(json);
}
