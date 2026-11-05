// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_UserRef _$UserRefFromJson(Map<String, dynamic> json) => _UserRef(
  id: json['id'] as String,
  displayName: json['display_name'] as String,
);

Map<String, dynamic> _$UserRefToJson(_UserRef instance) => <String, dynamic>{
  'id': instance.id,
  'display_name': instance.displayName,
};

_CategoryRef _$CategoryRefFromJson(Map<String, dynamic> json) => _CategoryRef(
  id: json['id'] as String,
  code: json['code'] as String,
  name: json['name'] as String,
);

Map<String, dynamic> _$CategoryRefToJson(_CategoryRef instance) =>
    <String, dynamic>{
      'id': instance.id,
      'code': instance.code,
      'name': instance.name,
    };

_ChangeCi _$ChangeCiFromJson(Map<String, dynamic> json) => _ChangeCi(
  id: json['id'] as String,
  identifier: json['identifier'] as String,
  name: json['name'] as String,
  ciTypeCode: json['ci_type_code'] as String? ?? '',
  isActive: json['is_active'] as bool? ?? true,
  snapshot: json['snapshot'] as bool? ?? false,
  currentIdentifier: json['current_identifier'] as String?,
  currentName: json['current_name'] as String?,
  owner: json['owner'] == null
      ? null
      : UserRef.fromJson(json['owner'] as Map<String, dynamic>),
  consented: json['consented'] as bool? ?? false,
);

Map<String, dynamic> _$ChangeCiToJson(_ChangeCi instance) => <String, dynamic>{
  'id': instance.id,
  'identifier': instance.identifier,
  'name': instance.name,
  'ci_type_code': instance.ciTypeCode,
  'is_active': instance.isActive,
  'snapshot': instance.snapshot,
  'current_identifier': instance.currentIdentifier,
  'current_name': instance.currentName,
  'owner': instance.owner?.toJson(),
  'consented': instance.consented,
};

_Deviation _$DeviationFromJson(Map<String, dynamic> json) => _Deviation(
  kind: json['kind'] as String,
  critical: json['critical'] as bool? ?? false,
  messagePl: json['message_pl'] as String? ?? '',
);

Map<String, dynamic> _$DeviationToJson(_Deviation instance) =>
    <String, dynamic>{
      'kind': instance.kind,
      'critical': instance.critical,
      'message_pl': instance.messagePl,
    };

_Consent _$ConsentFromJson(Map<String, dynamic> json) => _Consent(
  ciId: json['ci_id'] as String,
  owner: UserRef.fromJson(json['owner'] as Map<String, dynamic>),
  consentedAt: DateTime.parse(json['consented_at'] as String),
  valid: json['valid'] as bool,
  byRequesterOrAssignee: json['by_requester_or_assignee'] as bool,
);

Map<String, dynamic> _$ConsentToJson(_Consent instance) => <String, dynamic>{
  'ci_id': instance.ciId,
  'owner': instance.owner.toJson(),
  'consented_at': instance.consentedAt.toIso8601String(),
  'valid': instance.valid,
  'by_requester_or_assignee': instance.byRequesterOrAssignee,
};

_ChangeComment _$ChangeCommentFromJson(Map<String, dynamic> json) =>
    _ChangeComment(
      id: json['id'] as String,
      author: UserRef.fromJson(json['author'] as Map<String, dynamic>),
      body: json['body'] as String,
      action: json['action'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ChangeCommentToJson(_ChangeComment instance) =>
    <String, dynamic>{
      'id': instance.id,
      'author': instance.author.toJson(),
      'body': instance.body,
      'action': instance.action,
      'created_at': instance.createdAt.toIso8601String(),
    };

_LinkedChange _$LinkedChangeFromJson(Map<String, dynamic> json) =>
    _LinkedChange(
      id: json['id'] as String,
      number: json['number'] as String,
      status: json['status'] as String,
    );

Map<String, dynamic> _$LinkedChangeToJson(_LinkedChange instance) =>
    <String, dynamic>{
      'id': instance.id,
      'number': instance.number,
      'status': instance.status,
    };

_Change _$ChangeFromJson(Map<String, dynamic> json) => _Change(
  id: json['id'] as String,
  companyId: json['company_id'] as String,
  number: json['number'] as String,
  title: json['title'] as String?,
  status: json['status'] as String,
  changeType: json['change_type'] as String?,
  risk: json['risk'] as String?,
  category: json['category'] == null
      ? null
      : CategoryRef.fromJson(json['category'] as Map<String, dynamic>),
  subcategory: json['subcategory'] == null
      ? null
      : CategoryRef.fromJson(json['subcategory'] as Map<String, dynamic>),
  ci:
      (json['ci'] as List<dynamic>?)
          ?.map((e) => ChangeCi.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <ChangeCi>[],
  requestedBy: UserRef.fromJson(json['requested_by'] as Map<String, dynamic>),
  assignee: json['assignee'] == null
      ? null
      : UserRef.fromJson(json['assignee'] as Map<String, dynamic>),
  approver: json['approver'] == null
      ? null
      : UserRef.fromJson(json['approver'] as Map<String, dynamic>),
  verifier: json['verifier'] == null
      ? null
      : UserRef.fromJson(json['verifier'] as Map<String, dynamic>),
  windowStart: json['window_start'] == null
      ? null
      : DateTime.parse(json['window_start'] as String),
  windowEnd: json['window_end'] == null
      ? null
      : DateTime.parse(json['window_end'] as String),
  approvedAt: json['approved_at'] == null
      ? null
      : DateTime.parse(json['approved_at'] as String),
  approvedBy: json['approved_by'] == null
      ? null
      : UserRef.fromJson(json['approved_by'] as Map<String, dynamic>),
  autoApproved: json['auto_approved'] as bool? ?? false,
  implementedAt: json['implemented_at'] == null
      ? null
      : DateTime.parse(json['implemented_at'] as String),
  verifiedAt: json['verified_at'] == null
      ? null
      : DateTime.parse(json['verified_at'] as String),
  rejectedAt: json['rejected_at'] == null
      ? null
      : DateTime.parse(json['rejected_at'] as String),
  deviations:
      (json['deviations'] as List<dynamic>?)
          ?.map((e) => Deviation.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <Deviation>[],
  createdAt: DateTime.parse(json['created_at'] as String),
  updatedAt: DateTime.parse(json['updated_at'] as String),
  description: json['description'] as String?,
  implementationPlan: json['implementation_plan'] as String?,
  rollbackPlan: json['rollback_plan'] as String?,
  impact: json['impact'] as String?,
  requirementRef: json['requirement_ref'] as String?,
  ticketRef: json['ticket_ref'] as String?,
  supersedesChangeId: json['supersedes_change_id'] as String?,
  supersedesNumber: json['supersedes_number'] as String?,
  supersededBy:
      (json['superseded_by'] as List<dynamic>?)
          ?.map((e) => LinkedChange.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <LinkedChange>[],
  version: (json['version'] as num?)?.toInt() ?? 0,
  allowedActions:
      (json['allowed_actions'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const <String>[],
  editableFields:
      (json['editable_fields'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const <String>[],
  access:
      $enumDecodeNullable(
        _$ChangeAccessEnumMap,
        json['access'],
        unknownValue: ChangeAccess.unknown,
      ) ??
      ChangeAccess.unknown,
  suggestedApproverId: json['suggested_approver_id'] as String?,
  consents:
      (json['consents'] as List<dynamic>?)
          ?.map((e) => Consent.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <Consent>[],
  comments:
      (json['comments'] as List<dynamic>?)
          ?.map((e) => ChangeComment.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <ChangeComment>[],
);

Map<String, dynamic> _$ChangeToJson(_Change instance) => <String, dynamic>{
  'id': instance.id,
  'company_id': instance.companyId,
  'number': instance.number,
  'title': instance.title,
  'status': instance.status,
  'change_type': instance.changeType,
  'risk': instance.risk,
  'category': instance.category?.toJson(),
  'subcategory': instance.subcategory?.toJson(),
  'ci': instance.ci.map((e) => e.toJson()).toList(),
  'requested_by': instance.requestedBy.toJson(),
  'assignee': instance.assignee?.toJson(),
  'approver': instance.approver?.toJson(),
  'verifier': instance.verifier?.toJson(),
  'window_start': instance.windowStart?.toIso8601String(),
  'window_end': instance.windowEnd?.toIso8601String(),
  'approved_at': instance.approvedAt?.toIso8601String(),
  'approved_by': instance.approvedBy?.toJson(),
  'auto_approved': instance.autoApproved,
  'implemented_at': instance.implementedAt?.toIso8601String(),
  'verified_at': instance.verifiedAt?.toIso8601String(),
  'rejected_at': instance.rejectedAt?.toIso8601String(),
  'deviations': instance.deviations.map((e) => e.toJson()).toList(),
  'created_at': instance.createdAt.toIso8601String(),
  'updated_at': instance.updatedAt.toIso8601String(),
  'description': instance.description,
  'implementation_plan': instance.implementationPlan,
  'rollback_plan': instance.rollbackPlan,
  'impact': instance.impact,
  'requirement_ref': instance.requirementRef,
  'ticket_ref': instance.ticketRef,
  'supersedes_change_id': instance.supersedesChangeId,
  'supersedes_number': instance.supersedesNumber,
  'superseded_by': instance.supersededBy.map((e) => e.toJson()).toList(),
  'version': instance.version,
  'allowed_actions': instance.allowedActions,
  'editable_fields': instance.editableFields,
  'access': _$ChangeAccessEnumMap[instance.access]!,
  'suggested_approver_id': instance.suggestedApproverId,
  'consents': instance.consents.map((e) => e.toJson()).toList(),
  'comments': instance.comments.map((e) => e.toJson()).toList(),
};

const _$ChangeAccessEnumMap = {
  ChangeAccess.member: 'member',
  ChangeAccess.adminReadOnly: 'admin_read_only',
  ChangeAccess.unknown: 'unknown',
};

_ReadinessCheck _$ReadinessCheckFromJson(Map<String, dynamic> json) =>
    _ReadinessCheck(
      code: json['code'] as String,
      ok: json['ok'] as bool,
      level: json['level'] as String? ?? 'ok',
      messagePl: json['message_pl'] as String? ?? '',
      field: json['field'] as String?,
    );

Map<String, dynamic> _$ReadinessCheckToJson(_ReadinessCheck instance) =>
    <String, dynamic>{
      'code': instance.code,
      'ok': instance.ok,
      'level': instance.level,
      'message_pl': instance.messagePl,
      'field': instance.field,
    };

_Readiness _$ReadinessFromJson(Map<String, dynamic> json) => _Readiness(
  ok: json['ok'] as bool,
  checks:
      (json['checks'] as List<dynamic>?)
          ?.map((e) => ReadinessCheck.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <ReadinessCheck>[],
);

Map<String, dynamic> _$ReadinessToJson(_Readiness instance) =>
    <String, dynamic>{
      'ok': instance.ok,
      'checks': instance.checks.map((e) => e.toJson()).toList(),
    };

_ActionResult _$ActionResultFromJson(Map<String, dynamic> json) =>
    _ActionResult(
      action: json['action'] as String,
      fromStatus: json['from_status'] as String,
      toStatus: json['to_status'] as String,
      performedBySystem: json['performed_by_system'] as bool? ?? false,
      warnings:
          (json['warnings'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const <Map<String, dynamic>>[],
      change: Change.fromJson(json['change'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$ActionResultToJson(_ActionResult instance) =>
    <String, dynamic>{
      'action': instance.action,
      'from_status': instance.fromStatus,
      'to_status': instance.toStatus,
      'performed_by_system': instance.performedBySystem,
      'warnings': instance.warnings,
      'change': instance.change.toJson(),
    };

_Attachment _$AttachmentFromJson(Map<String, dynamic> json) => _Attachment(
  id: json['id'] as String,
  changeId: json['change_id'] as String,
  filename: json['filename'] as String,
  contentType: json['content_type'] as String? ?? 'application/octet-stream',
  size: (json['size'] as num).toInt(),
  sha256: json['sha256'] as String,
  uploadedBy: UserRef.fromJson(json['uploaded_by'] as Map<String, dynamic>),
  createdAt: DateTime.parse(json['created_at'] as String),
);

Map<String, dynamic> _$AttachmentToJson(_Attachment instance) =>
    <String, dynamic>{
      'id': instance.id,
      'change_id': instance.changeId,
      'filename': instance.filename,
      'content_type': instance.contentType,
      'size': instance.size,
      'sha256': instance.sha256,
      'uploaded_by': instance.uploadedBy.toJson(),
      'created_at': instance.createdAt.toIso8601String(),
    };

_ChangeStats _$ChangeStatsFromJson(Map<String, dynamic> json) => _ChangeStats(
  pendingApproval: (json['pending_approval'] as num?)?.toInt() ?? 0,
  approvedNotImplemented:
      (json['approved_not_implemented'] as num?)?.toInt() ?? 0,
  emergencyLast30Days: (json['emergency_last_30_days'] as num?)?.toInt() ?? 0,
  implementedNotVerified:
      (json['implemented_not_verified'] as num?)?.toInt() ?? 0,
  emergencyNotApprovedIn24h:
      (json['emergency_not_approved_in_24h'] as num?)?.toInt() ?? 0,
  implementedOutsideWindow:
      (json['implemented_outside_window'] as num?)?.toInt() ?? 0,
  byStatus:
      (json['by_status'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, (e as num).toInt()),
      ) ??
      const <String, int>{},
);

Map<String, dynamic> _$ChangeStatsToJson(_ChangeStats instance) =>
    <String, dynamic>{
      'pending_approval': instance.pendingApproval,
      'approved_not_implemented': instance.approvedNotImplemented,
      'emergency_last_30_days': instance.emergencyLast30Days,
      'implemented_not_verified': instance.implementedNotVerified,
      'emergency_not_approved_in_24h': instance.emergencyNotApprovedIn24h,
      'implemented_outside_window': instance.implementedOutsideWindow,
      'by_status': instance.byStatus,
    };

_AuditEntry _$AuditEntryFromJson(Map<String, dynamic> json) => _AuditEntry(
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
  requestId: json['request_id'] as String? ?? '',
  entityType: json['entity_type'] as String,
  entityId: json['entity_id'] as String?,
  action: json['action'] as String,
  diff: json['diff'] as Map<String, dynamic>? ?? const <String, dynamic>{},
  context:
      json['context'] as Map<String, dynamic>? ?? const <String, dynamic>{},
  prevHash: json['prev_hash'] as String? ?? '',
  hash: json['hash'] as String,
  hashValid: json['hash_valid'] as bool,
);

Map<String, dynamic> _$AuditEntryToJson(_AuditEntry instance) =>
    <String, dynamic>{
      'seq': instance.seq,
      'occurred_at': instance.occurredAt.toIso8601String(),
      'actor_id': instance.actorId,
      'actor_display': instance.actorDisplay,
      'actor_roles': instance.actorRoles,
      'ip_address': instance.ipAddress,
      'request_id': instance.requestId,
      'entity_type': instance.entityType,
      'entity_id': instance.entityId,
      'action': instance.action,
      'diff': instance.diff,
      'context': instance.context,
      'prev_hash': instance.prevHash,
      'hash': instance.hash,
      'hash_valid': instance.hashValid,
    };

_ChainStatus _$ChainStatusFromJson(Map<String, dynamic> json) => _ChainStatus(
  status: json['status'] as String,
  ok: json['ok'] as bool?,
  checkedAt: json['checked_at'] == null
      ? null
      : DateTime.parse(json['checked_at'] as String),
  verifiedHeadSeq: (json['verified_head_seq'] as num?)?.toInt(),
  headSeq: (json['head_seq'] as num?)?.toInt() ?? 0,
);

Map<String, dynamic> _$ChainStatusToJson(_ChainStatus instance) =>
    <String, dynamic>{
      'status': instance.status,
      'ok': instance.ok,
      'checked_at': instance.checkedAt?.toIso8601String(),
      'verified_head_seq': instance.verifiedHeadSeq,
      'head_seq': instance.headSeq,
    };

_Member _$MemberFromJson(Map<String, dynamic> json) => _Member(
  userId: json['user_id'] as String,
  displayName: json['display_name'] as String,
  email: json['email'] as String? ?? '',
  isActive: json['is_active'] as bool? ?? true,
  roles:
      (json['roles'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
);

Map<String, dynamic> _$MemberToJson(_Member instance) => <String, dynamic>{
  'user_id': instance.userId,
  'display_name': instance.displayName,
  'email': instance.email,
  'is_active': instance.isActive,
  'roles': instance.roles,
};

_CompanyCategory _$CompanyCategoryFromJson(Map<String, dynamic> json) =>
    _CompanyCategory(
      categoryId: json['category_id'] as String,
      code: json['code'] as String,
      name: json['name'] as String,
      requiresApproval: json['requires_approval'] as bool? ?? true,
      defaultRisk: json['default_risk'] as String? ?? 'medium',
      isActive: json['is_active'] as bool? ?? true,
      approverOverrideId: json['approver_override_id'] as String?,
    );

Map<String, dynamic> _$CompanyCategoryToJson(_CompanyCategory instance) =>
    <String, dynamic>{
      'category_id': instance.categoryId,
      'code': instance.code,
      'name': instance.name,
      'requires_approval': instance.requiresApproval,
      'default_risk': instance.defaultRisk,
      'is_active': instance.isActive,
      'approver_override_id': instance.approverOverrideId,
    };

_Category _$CategoryFromJson(Map<String, dynamic> json) => _Category(
  id: json['id'] as String,
  code: json['code'] as String,
  name: json['name'] as String,
  parentId: json['parent_id'] as String?,
  requiresApproval: json['requires_approval'] as bool? ?? true,
  requiresCiOwnerConsent: json['requires_ci_owner_consent'] as bool? ?? false,
  defaultRisk: json['default_risk'] as String? ?? 'medium',
  isActive: json['is_active'] as bool? ?? true,
);

Map<String, dynamic> _$CategoryToJson(_Category instance) => <String, dynamic>{
  'id': instance.id,
  'code': instance.code,
  'name': instance.name,
  'parent_id': instance.parentId,
  'requires_approval': instance.requiresApproval,
  'requires_ci_owner_consent': instance.requiresCiOwnerConsent,
  'default_risk': instance.defaultRisk,
  'is_active': instance.isActive,
};

_CiItem _$CiItemFromJson(Map<String, dynamic> json) => _CiItem(
  id: json['id'] as String,
  companyId: json['company_id'] as String,
  ciTypeId: json['ci_type_id'] as String,
  ciTypeCode: json['ci_type_code'] as String? ?? '',
  ciTypeName: json['ci_type_name'] as String? ?? '',
  identifier: json['identifier'] as String,
  name: json['name'] as String,
  description: json['description'] as String?,
  ownerUserId: json['owner_user_id'] as String?,
  isActive: json['is_active'] as bool? ?? true,
);

Map<String, dynamic> _$CiItemToJson(_CiItem instance) => <String, dynamic>{
  'id': instance.id,
  'company_id': instance.companyId,
  'ci_type_id': instance.ciTypeId,
  'ci_type_code': instance.ciTypeCode,
  'ci_type_name': instance.ciTypeName,
  'identifier': instance.identifier,
  'name': instance.name,
  'description': instance.description,
  'owner_user_id': instance.ownerUserId,
  'is_active': instance.isActive,
};

_CiType _$CiTypeFromJson(Map<String, dynamic> json) => _CiType(
  id: json['id'] as String,
  code: json['code'] as String,
  name: json['name'] as String,
  isActive: json['is_active'] as bool? ?? true,
);

Map<String, dynamic> _$CiTypeToJson(_CiType instance) => <String, dynamic>{
  'id': instance.id,
  'code': instance.code,
  'name': instance.name,
  'is_active': instance.isActive,
};
