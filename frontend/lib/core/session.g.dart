// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'session.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_Membership _$MembershipFromJson(Map<String, dynamic> json) => _Membership(
  companyId: json['company_id'] as String,
  companyName: json['company_name'] as String,
  companyPrefix: json['company_prefix'] as String,
  companyStatus: json['company_status'] as String? ?? 'active',
  roles:
      (json['roles'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
);

Map<String, dynamic> _$MembershipToJson(_Membership instance) =>
    <String, dynamic>{
      'company_id': instance.companyId,
      'company_name': instance.companyName,
      'company_prefix': instance.companyPrefix,
      'company_status': instance.companyStatus,
      'roles': instance.roles,
    };

_Me _$MeFromJson(Map<String, dynamic> json) => _Me(
  id: json['id'] as String,
  displayName: json['display_name'] as String,
  externalId: json['external_id'] as String? ?? '',
  email: json['email'] as String? ?? '',
  isAppAdmin: json['is_app_admin'] as bool? ?? false,
  mustChangePassword: json['must_change_password'] as bool? ?? false,
  memberships:
      (json['memberships'] as List<dynamic>?)
          ?.map((e) => Membership.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <Membership>[],
);

Map<String, dynamic> _$MeToJson(_Me instance) => <String, dynamic>{
  'id': instance.id,
  'display_name': instance.displayName,
  'external_id': instance.externalId,
  'email': instance.email,
  'is_app_admin': instance.isAppAdmin,
  'must_change_password': instance.mustChangePassword,
  'memberships': instance.memberships.map((e) => e.toJson()).toList(),
};
