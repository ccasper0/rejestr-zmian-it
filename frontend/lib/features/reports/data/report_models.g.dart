// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'report_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_ReportCompany _$ReportCompanyFromJson(Map<String, dynamic> json) =>
    _ReportCompany(
      id: json['id'] as String,
      name: json['name'] as String,
      prefix: json['prefix'] as String,
    );

Map<String, dynamic> _$ReportCompanyToJson(_ReportCompany instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'prefix': instance.prefix,
    };

_Report _$ReportFromJson(Map<String, dynamic> json) => _Report(
  id: json['id'] as String,
  number: json['number'] as String,
  kind: json['kind'] as String,
  format: json['format'] as String,
  status: json['status'] as String,
  companyId: json['company_id'] as String?,
  company: json['company'] == null
      ? null
      : ReportCompany.fromJson(json['company'] as Map<String, dynamic>),
  companies:
      (json['companies'] as List<dynamic>?)
          ?.map((e) => ReportCompany.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const <ReportCompany>[],
  changeId: json['change_id'] as String?,
  changeNumber: json['change_number'] as String?,
  periodFrom: json['period_from'] == null
      ? null
      : DateTime.parse(json['period_from'] as String),
  periodTo: json['period_to'] == null
      ? null
      : DateTime.parse(json['period_to'] as String),
  filters:
      json['filters'] as Map<String, dynamic>? ?? const <String, dynamic>{},
  includeAuditTrail: json['include_audit_trail'] as bool? ?? false,
  generatedBy: UserRef.fromJson(json['generated_by'] as Map<String, dynamic>),
  createdAt: DateTime.parse(json['created_at'] as String),
  completedAt: json['completed_at'] == null
      ? null
      : DateTime.parse(json['completed_at'] as String),
  changeCount: (json['change_count'] as num?)?.toInt(),
  dataSha256: json['data_sha256'] as String?,
  fileSha256: json['file_sha256'] as String?,
  size: (json['size'] as num?)?.toInt(),
  error: json['error'] as String?,
  downloadUrl: json['download_url'] as String?,
);

Map<String, dynamic> _$ReportToJson(_Report instance) => <String, dynamic>{
  'id': instance.id,
  'number': instance.number,
  'kind': instance.kind,
  'format': instance.format,
  'status': instance.status,
  'company_id': instance.companyId,
  'company': instance.company?.toJson(),
  'companies': instance.companies.map((e) => e.toJson()).toList(),
  'change_id': instance.changeId,
  'change_number': instance.changeNumber,
  'period_from': instance.periodFrom?.toIso8601String(),
  'period_to': instance.periodTo?.toIso8601String(),
  'filters': instance.filters,
  'include_audit_trail': instance.includeAuditTrail,
  'generated_by': instance.generatedBy.toJson(),
  'created_at': instance.createdAt.toIso8601String(),
  'completed_at': instance.completedAt?.toIso8601String(),
  'change_count': instance.changeCount,
  'data_sha256': instance.dataSha256,
  'file_sha256': instance.fileSha256,
  'size': instance.size,
  'error': instance.error,
  'download_url': instance.downloadUrl,
};

_ReportFilterSet _$ReportFilterSetFromJson(
  Map<String, dynamic> json,
) => _ReportFilterSet(
  periodBy: json['period_by'] as String? ?? 'created',
  status:
      (json['status'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
  type:
      (json['type'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
  category:
      (json['category'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
  ci:
      (json['ci'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const <String>[],
  assignee: json['assignee'] as String?,
  approver: json['approver'] as String?,
  approvedBy: json['approved_by'] as String?,
  q: json['q'] as String?,
);

Map<String, dynamic> _$ReportFilterSetToJson(_ReportFilterSet instance) =>
    <String, dynamic>{
      'period_by': instance.periodBy,
      'status': instance.status,
      'type': instance.type,
      'category': instance.category,
      'ci': instance.ci,
      'assignee': instance.assignee,
      'approver': instance.approver,
      'approved_by': instance.approvedBy,
      'q': instance.q,
    };

_ReportRequest _$ReportRequestFromJson(Map<String, dynamic> json) =>
    _ReportRequest(
      kind: json['kind'] as String,
      companyId: json['company_id'] as String?,
      changeId: json['change_id'] as String?,
      periodFrom: json['period_from'] == null
          ? null
          : DateTime.parse(json['period_from'] as String),
      periodTo: json['period_to'] == null
          ? null
          : DateTime.parse(json['period_to'] as String),
      filters: json['filters'] == null
          ? const ReportFilterSet()
          : ReportFilterSet.fromJson(json['filters'] as Map<String, dynamic>),
      includeAuditTrail: json['include_audit_trail'] as bool? ?? false,
    );

Map<String, dynamic> _$ReportRequestToJson(_ReportRequest instance) =>
    <String, dynamic>{
      'kind': instance.kind,
      'company_id': instance.companyId,
      'change_id': instance.changeId,
      'period_from': instance.periodFrom?.toIso8601String(),
      'period_to': instance.periodTo?.toIso8601String(),
      'filters': instance.filters.toJson(),
      'include_audit_trail': instance.includeAuditTrail,
    };
