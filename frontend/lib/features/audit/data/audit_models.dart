import 'package:freezed_annotation/freezed_annotation.dart';

part 'audit_models.freezed.dart';
part 'audit_models.g.dart';

/// One `audit_log` row of `GET /audit` (`AuditEntryOut`, CLAUDE.md §6.1).
///
/// Unlike the change trail (`AuditEntry`), the log browser has no per-entry
/// `hash_valid`: integrity is established by `POST /audit/verify`.
@freezed
abstract class AuditLogEntry with _$AuditLogEntry {
  const factory AuditLogEntry({
    required int id,
    String? companyId,
    required int seq,
    required DateTime occurredAt,
    String? actorId,
    required String actorDisplay,
    @Default(<String>[]) List<String> actorRoles,
    String? ipAddress,
    String? userAgent,
    required String requestId,
    required String entityType,
    String? entityId,
    required String action,
    @Default(<String, dynamic>{}) Map<String, dynamic> diff,
    @Default(<String, dynamic>{}) Map<String, dynamic> context,
    required String prevHash,
    required String hash,
  }) = _AuditLogEntry;

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) =>
      _$AuditLogEntryFromJson(json);
}

@freezed
abstract class AuditEntryRef with _$AuditEntryRef {
  const factory AuditEntryRef({
    String? companyId,
    required int seq,
    required String hash,
  }) = _AuditEntryRef;

  factory AuditEntryRef.fromJson(Map<String, dynamic> json) =>
      _$AuditEntryRefFromJson(json);
}

/// `POST /audit/verify` (ADR 0009 §4).
@freezed
abstract class VerifyResult with _$VerifyResult {
  const factory VerifyResult({
    String? companyId,
    required String chain,
    // Security-relevant: required, never defaulted.
    required bool ok,
    required int checked,
    int? firstBrokenSeq,
    required int headSeq,
    required String headHash,
    DateTime? verifiedAt,
    String? recordedIn,
    AuditEntryRef? auditEntry,
  }) = _VerifyResult;

  factory VerifyResult.fromJson(Map<String, dynamic> json) =>
      _$VerifyResultFromJson(json);
}
