// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auth.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_DevUser _$DevUserFromJson(Map<String, dynamic> json) => _DevUser(
  externalId: json['external_id'] as String,
  displayName: json['display_name'] as String,
  email: json['email'] as String? ?? '',
  isAppAdmin: json['is_app_admin'] as bool? ?? false,
  isActive: json['is_active'] as bool? ?? true,
);

Map<String, dynamic> _$DevUserToJson(_DevUser instance) => <String, dynamic>{
  'external_id': instance.externalId,
  'display_name': instance.displayName,
  'email': instance.email,
  'is_app_admin': instance.isAppAdmin,
  'is_active': instance.isActive,
};
