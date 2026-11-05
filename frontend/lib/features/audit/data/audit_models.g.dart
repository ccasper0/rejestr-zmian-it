// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_AuditLogEntry _$AuditLogEntryFromJson(Map<String, dynamic> json) =>
    _AuditLogEntry(
      id: (json['id'] as num).toInt(),
      companyId: json['company_id'] as String?,
      seq: (json['seq'] as num).toInt(),
      occurredAt: DateTime.parse(json['occurred_at'] as String),
      actorId: json['actor_id'] as String?,
      actorDisplay: json['actor_display'] as String,
      actorRoles:
          (json['actor_roles'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const <String>[],
      ipAddress: json['ip_address'] as String?,
      userAgent: json['user_agent'] as String?,
      requestId: json['request_id'] as String,
      entityType: json['entity_type'] as String,
      entityId: json['entity_id'] as String?,
      action: json['action'] as String,
      diff: json['diff'] as Map<String, dynamic>? ?? const <String, dynamic>{},
      context:
          json['context'] as Map<String, dynamic>? ?? const <String, dynamic>{},
      prevHash: json['prev_hash'] as String,
      hash: json['hash'] as String,
    );

Map<String, dynamic> _$AuditLogEntryToJson(_AuditLogEntry instance) =>
    <String, dynamic>{
      'id': instance.id,
      'company_id': instance.companyId,
      'seq': instance.seq,
      'occurred_at': instance.occurredAt.toIso8601String(),
      'actor_id': instance.actorId,
      'actor_display': instance.actorDisplay,
      'actor_roles': instance.actorRoles,
      'ip_address': instance.ipAddress,
      'user_agent': instance.userAgent,
      'request_id': instance.requestId,
      'entity_type': instance.entityType,
      'entity_id': instance.entityId,
      'action': instance.action,
      'diff': instance.diff,
      'context': instance.context,
      'prev_hash': instance.prevHash,
      'hash': instance.hash,
    };

_AuditEntryRef _$AuditEntryRefFromJson(Map<String, dynamic> json) =>
    _AuditEntryRef(
      companyId: json['company_id'] as String?,
      seq: (json['seq'] as num).toInt(),
      hash: json['hash'] as String,
    );

Map<String, dynamic> _$AuditEntryRefToJson(_AuditEntryRef instance) =>
    <String, dynamic>{
      'company_id': instance.companyId,
      'seq': instance.seq,
      'hash': instance.hash,
    };

_VerifyResult _$VerifyResultFromJson(Map<String, dynamic> json) =>
    _VerifyResult(
      companyId: json['company_id'] as String?,
      chain: json['chain'] as String,
      ok: json['ok'] as bool,
      checked: (json['checked'] as num).toInt(),
      firstBrokenSeq: (json['first_broken_seq'] as num?)?.toInt(),
      headSeq: (json['head_seq'] as num).toInt(),
      headHash: json['head_hash'] as String,
      verifiedAt: json['verified_at'] == null
          ? null
          : DateTime.parse(json['verified_at'] as String),
      recordedIn: json['recorded_in'] as String?,
      auditEntry: json['audit_entry'] == null
          ? null
          : AuditEntryRef.fromJson(json['audit_entry'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$VerifyResultToJson(_VerifyResult instance) =>
    <String, dynamic>{
      'company_id': instance.companyId,
      'chain': instance.chain,
      'ok': instance.ok,
      'checked': instance.checked,
      'first_broken_seq': instance.firstBrokenSeq,
      'head_seq': instance.headSeq,
      'head_hash': instance.headHash,
      'verified_at': instance.verifiedAt?.toIso8601String(),
      'recorded_in': instance.recordedIn,
      'audit_entry': instance.auditEntry?.toJson(),
    };
