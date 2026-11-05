// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'admin_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_CompanyCounts _$CompanyCountsFromJson(Map<String, dynamic> json) =>
    _CompanyCounts(
      activeCi: (json['active_ci'] as num?)?.toInt() ?? 0,
      allCi: (json['all_ci'] as num?)?.toInt() ?? 0,
      editors: (json['editors'] as num?)?.toInt() ?? 0,
      approvers: (json['approvers'] as num?)?.toInt() ?? 0,
      auditors: (json['auditors'] as num?)?.toInt() ?? 0,
      viewers: (json['viewers'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$CompanyCountsToJson(_CompanyCounts instance) =>
    <String, dynamic>{
      'active_ci': instance.activeCi,
      'all_ci': instance.allCi,
      'editors': instance.editors,
      'approvers': instance.approvers,
      'auditors': instance.auditors,
      'viewers': instance.viewers,
    };

_AdminCompany _$AdminCompanyFromJson(Map<String, dynamic> json) =>
    _AdminCompany(
      id: json['id'] as String,
      name: json['name'] as String,
      taxId: json['tax_id'] as String?,
      prefix: json['prefix'] as String,
      status: json['status'] as String,
      isKscEntity: json['is_ksc_entity'] as bool? ?? false,
      defaultApproverId: json['default_approver_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      myRoles:
          (json['my_roles'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const <String>[],
      counts: json['counts'] == null
          ? const CompanyCounts()
          : CompanyCounts.fromJson(json['counts'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$AdminCompanyToJson(_AdminCompany instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'tax_id': instance.taxId,
      'prefix': instance.prefix,
      'status': instance.status,
      'is_ksc_entity': instance.isKscEntity,
      'default_approver_id': instance.defaultApproverId,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'my_roles': instance.myRoles,
      'counts': instance.counts.toJson(),
    };

_UserAccount _$UserAccountFromJson(Map<String, dynamic> json) => _UserAccount(
  id: json['id'] as String,
  externalId: json['external_id'] as String? ?? '',
  email: json['email'] as String? ?? '',
  displayName: json['display_name'] as String,
  isAppAdmin: json['is_app_admin'] as bool? ?? false,
  isActive: json['is_active'] as bool,
  createdAt: json['created_at'] == null
      ? null
      : DateTime.parse(json['created_at'] as String),
  updatedAt: json['updated_at'] == null
      ? null
      : DateTime.parse(json['updated_at'] as String),
  hasPassword: json['has_password'] as bool? ?? false,
  mustChangePassword: json['must_change_password'] as bool? ?? false,
  passwordChangedAt: json['password_changed_at'] == null
      ? null
      : DateTime.parse(json['password_changed_at'] as String),
  lockedUntil: json['locked_until'] == null
      ? null
      : DateTime.parse(json['locked_until'] as String),
  tempPasswordExpiresAt: json['temp_password_expires_at'] == null
      ? null
      : DateTime.parse(json['temp_password_expires_at'] as String),
);

Map<String, dynamic> _$UserAccountToJson(
  _UserAccount instance,
) => <String, dynamic>{
  'id': instance.id,
  'external_id': instance.externalId,
  'email': instance.email,
  'display_name': instance.displayName,
  'is_app_admin': instance.isAppAdmin,
  'is_active': instance.isActive,
  'created_at': instance.createdAt?.toIso8601String(),
  'updated_at': instance.updatedAt?.toIso8601String(),
  'has_password': instance.hasPassword,
  'must_change_password': instance.mustChangePassword,
  'password_changed_at': instance.passwordChangedAt?.toIso8601String(),
  'locked_until': instance.lockedUntil?.toIso8601String(),
  'temp_password_expires_at': instance.tempPasswordExpiresAt?.toIso8601String(),
};

_UserWithTemporaryPassword _$UserWithTemporaryPasswordFromJson(
  Map<String, dynamic> json,
) => _UserWithTemporaryPassword(
  user: UserAccount.fromJson(json['user'] as Map<String, dynamic>),
  temporaryPassword: json['temporary_password'] as String,
);

Map<String, dynamic> _$UserWithTemporaryPasswordToJson(
  _UserWithTemporaryPassword instance,
) => <String, dynamic>{
  'user': instance.user.toJson(),
  'temporary_password': instance.temporaryPassword,
};

_UserMembership _$UserMembershipFromJson(Map<String, dynamic> json) =>
    _UserMembership(
      companyId: json['company_id'] as String,
      companyName: json['company_name'] as String,
      companyPrefix: json['company_prefix'] as String,
      companyStatus: json['company_status'] as String? ?? 'active',
      roles:
          (json['roles'] as List<dynamic>?)?.map((e) => e as String).toList() ??
          const <String>[],
    );

Map<String, dynamic> _$UserMembershipToJson(_UserMembership instance) =>
    <String, dynamic>{
      'company_id': instance.companyId,
      'company_name': instance.companyName,
      'company_prefix': instance.companyPrefix,
      'company_status': instance.companyStatus,
      'roles': instance.roles,
    };

_UserDetail _$UserDetailFromJson(Map<String, dynamic> json) => _UserDetail(
  id: json['id'] as String,
  externalId: json['external_id'] as String? ?? '',
  email: json['email'] as String? ?? '',
  displayName: json['display_name'] as String,
  isAppAdmin: json['is_app_admin'] as bool? ?? false,
  isActive: json['is_active'] as bool,
  hasPassword: json['has_password'] as bool? ?? false,
  mustChangePassword: json['must_change_password'] as bool? ?? false,
  passwordChangedAt: json['password_changed_at'] == null
      ? null
      : DateTime.parse(json['password_changed_at'] as String),
  lockedUntil: json['locked_until'] == null
      ? null
      : DateTime.parse(json['locked_until'] as String),
  tempPasswordExpiresAt: json['temp_password_expires_at'] == null
      ? null
      : DateTime.parse(json['temp_password_expires_at'] as String),
  memberships:
      (json['memberships'] as List<dynamic>?)
          ?.map((e) => UserMembership.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <UserMembership>[],
);

Map<String, dynamic> _$UserDetailToJson(
  _UserDetail instance,
) => <String, dynamic>{
  'id': instance.id,
  'external_id': instance.externalId,
  'email': instance.email,
  'display_name': instance.displayName,
  'is_app_admin': instance.isAppAdmin,
  'is_active': instance.isActive,
  'has_password': instance.hasPassword,
  'must_change_password': instance.mustChangePassword,
  'password_changed_at': instance.passwordChangedAt?.toIso8601String(),
  'locked_until': instance.lockedUntil?.toIso8601String(),
  'temp_password_expires_at': instance.tempPasswordExpiresAt?.toIso8601String(),
  'memberships': instance.memberships.map((e) => e.toJson()).toList(),
};

_MatrixRow _$MatrixRowFromJson(Map<String, dynamic> json) => _MatrixRow(
  action: json['action'] as String,
  label: json['label'] as String,
  note: json['note'] as String?,
  roles:
      (json['roles'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
);

Map<String, dynamic> _$MatrixRowToJson(_MatrixRow instance) =>
    <String, dynamic>{
      'action': instance.action,
      'label': instance.label,
      'note': instance.note,
      'roles': instance.roles,
    };

_ChangeActionRule _$ChangeActionRuleFromJson(Map<String, dynamic> json) =>
    _ChangeActionRule(
      action: json['action'] as String,
      requires: json['requires'] as String,
    );

Map<String, dynamic> _$ChangeActionRuleToJson(_ChangeActionRule instance) =>
    <String, dynamic>{'action': instance.action, 'requires': instance.requires};

_PermissionMatrix _$PermissionMatrixFromJson(Map<String, dynamic> json) =>
    _PermissionMatrix(
      roles: (json['roles'] as List<dynamic>).map((e) => e as String).toList(),
      actions: (json['actions'] as List<dynamic>)
          .map((e) => MatrixRow.fromJson(e as Map<String, dynamic>))
          .toList(),
      changeActions:
          (json['change_actions'] as List<dynamic>?)
              ?.map((e) => ChangeActionRule.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <ChangeActionRule>[],
    );

Map<String, dynamic> _$PermissionMatrixToJson(_PermissionMatrix instance) =>
    <String, dynamic>{
      'roles': instance.roles,
      'actions': instance.actions.map((e) => e.toJson()).toList(),
      'change_actions': instance.changeActions.map((e) => e.toJson()).toList(),
    };
