// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_HealthInfo _$HealthInfoFromJson(Map<String, dynamic> json) => _HealthInfo(
  status: json['status'] as String? ?? 'ok',
  version: json['version'] as String?,
);

Map<String, dynamic> _$HealthInfoToJson(_HealthInfo instance) =>
    <String, dynamic>{'status': instance.status, 'version': instance.version};
