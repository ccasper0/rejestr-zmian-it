import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../core/change_status.dart';

part 'models.freezed.dart';
part 'models.g.dart';

// Schemas mirror backend/app/schemas/{changes,inventory,identity,audit}.py —
// the backend is the source of truth for the contract.

@freezed
abstract class UserRef with _$UserRef {
  const factory UserRef({required String id, required String displayName}) =
      _UserRef;

  factory UserRef.fromJson(Map<String, dynamic> json) =>
      _$UserRefFromJson(json);
}

@freezed
abstract class CategoryRef with _$CategoryRef {
  const factory CategoryRef({
    required String id,
    required String code,
    required String name,
  }) = _CategoryRef;

  factory CategoryRef.fromJson(Map<String, dynamic> json) =>
      _$CategoryRefFromJson(json);
}

/// A CI of a change; `identifier`/`name` are the snapshot once implemented.
@freezed
abstract class ChangeCi with _$ChangeCi {
  const factory ChangeCi({
    required String id,
    required String identifier,
    required String name,
    @Default('') String ciTypeCode,
    @Default(true) bool isActive,
    @Default(false) bool snapshot,
    String? currentIdentifier,
    String? currentName,
    UserRef? owner,
    @Default(false) bool consented,
  }) = _ChangeCi;

  factory ChangeCi.fromJson(Map<String, dynamic> json) =>
      _$ChangeCiFromJson(json);
}

@freezed
abstract class Deviation with _$Deviation {
  const factory Deviation({
    required String kind,
    @Default(false) bool critical,
    @Default('') String messagePl,
  }) = _Deviation;

  factory Deviation.fromJson(Map<String, dynamic> json) =>
      _$DeviationFromJson(json);
}

/// CI owner consent of the current round (ADR 0012 §5, ADR 0013 §5).
@freezed
abstract class Consent with _$Consent {
  const factory Consent({
    required String ciId,
    required UserRef owner,
    required DateTime consentedAt,
    // Security-relevant flags: required, never defaulted (a missing field
    // must fail parsing rather than show a consent as valid/independent).
    required bool valid,
    required bool byRequesterOrAssignee,
  }) = _Consent;

  factory Consent.fromJson(Map<String, dynamic> json) =>
      _$ConsentFromJson(json);
}

@freezed
abstract class ChangeComment with _$ChangeComment {
  const factory ChangeComment({
    required String id,
    required UserRef author,
    required String body,
    String? action,
    required DateTime createdAt,
  }) = _ChangeComment;

  factory ChangeComment.fromJson(Map<String, dynamic> json) =>
      _$ChangeCommentFromJson(json);
}

/// How the caller reads a change card (`ChangeOut.access`, ADR 0016).
///
/// An unknown value (a newer API) parses as [unknown] and is treated like
/// read-only access: the UI never offers more than it can prove.
@JsonEnum(fieldRename: FieldRename.snake)
enum ChangeAccess {
  /// By the caller's roles in the company.
  member,

  /// The app admin without a role in the company: narrow read-only path
  /// (no actions, no edits, no comments, no attachment download).
  adminReadOnly,

  /// Missing (register rows) or unknown value.
  unknown,
}

/// A correction of a change (`LinkedChangeOut`, ADR 0021).
@freezed
abstract class LinkedChange with _$LinkedChange {
  const LinkedChange._();

  const factory LinkedChange({
    required String id,
    required String number,
    required String status,
  }) = _LinkedChange;

  factory LinkedChange.fromJson(Map<String, dynamic> json) =>
      _$LinkedChangeFromJson(json);

  ChangeStatus? get statusValue => ChangeStatus.tryParse(status);
}

/// A change: a register row (`ChangeSummaryOut`) or the full card
/// (`ChangeOut`; card-only fields default to empty for register rows).
@freezed
abstract class Change with _$Change {
  const Change._();

  const factory Change({
    required String id,
    required String companyId,
    required String number,
    String? title,
    required String status,
    String? changeType,
    String? risk,
    CategoryRef? category,
    CategoryRef? subcategory,
    @Default(<ChangeCi>[]) List<ChangeCi> ci,
    required UserRef requestedBy,
    UserRef? assignee,
    UserRef? approver,
    UserRef? verifier,
    DateTime? windowStart,
    DateTime? windowEnd,
    DateTime? approvedAt,
    UserRef? approvedBy,
    @Default(false) bool autoApproved,
    DateTime? implementedAt,
    DateTime? verifiedAt,
    DateTime? rejectedAt,
    @Default(<Deviation>[]) List<Deviation> deviations,
    required DateTime createdAt,
    required DateTime updatedAt,
    // card only
    String? description,
    String? implementationPlan,
    String? rollbackPlan,
    String? impact,
    String? requirementRef,
    String? ticketRef,
    String? supersedesChangeId,
    String? supersedesNumber,
    @Default(<LinkedChange>[]) List<LinkedChange> supersededBy,
    @Default(0) int version,
    @Default(<String>[]) List<String> allowedActions,
    @Default(<String>[]) List<String> editableFields,
    @JsonKey(unknownEnumValue: ChangeAccess.unknown)
    @Default(ChangeAccess.unknown)
    ChangeAccess access,
    String? suggestedApproverId,
    @Default(<Consent>[]) List<Consent> consents,
    @Default(<ChangeComment>[]) List<ChangeComment> comments,
  }) = _Change;

  factory Change.fromJson(Map<String, dynamic> json) => _$ChangeFromJson(json);

  ChangeStatus? get statusValue => ChangeStatus.tryParse(status);
  bool get isEmergency => changeType == ChangeTypes.emergency;
  bool canEdit(String field) => editableFields.contains(field);

  /// The caller reads the card as a member (writes possible per roles).
  bool get isMemberAccess => access == ChangeAccess.member;

  /// The app admin's read-only view of a company without his role.
  bool get isAdminReadOnly => access == ChangeAccess.adminReadOnly;
}

/// One check of `GET …/readiness` (ADR 0012 §3).
@freezed
abstract class ReadinessCheck with _$ReadinessCheck {
  const ReadinessCheck._();

  const factory ReadinessCheck({
    required String code,
    required bool ok,
    @Default('ok') String level,
    @Default('') String messagePl,
    String? field,
  }) = _ReadinessCheck;

  factory ReadinessCheck.fromJson(Map<String, dynamic> json) =>
      _$ReadinessCheckFromJson(json);

  bool get isError => level == 'error' || !ok;
  bool get isWarning => level == 'warning';
}

@freezed
abstract class Readiness with _$Readiness {
  const factory Readiness({
    required bool ok,
    @Default(<ReadinessCheck>[]) List<ReadinessCheck> checks,
  }) = _Readiness;

  factory Readiness.fromJson(Map<String, dynamic> json) =>
      _$ReadinessFromJson(json);
}

@freezed
abstract class ActionResult with _$ActionResult {
  const factory ActionResult({
    required String action,
    required String fromStatus,
    required String toStatus,
    @Default(false) bool performedBySystem,
    @Default(<Map<String, dynamic>>[]) List<Map<String, dynamic>> warnings,
    required Change change,
  }) = _ActionResult;

  factory ActionResult.fromJson(Map<String, dynamic> json) =>
      _$ActionResultFromJson(json);
}

@freezed
abstract class Attachment with _$Attachment {
  const factory Attachment({
    required String id,
    required String changeId,
    required String filename,
    @Default('application/octet-stream') String contentType,
    required int size,
    required String sha256,
    required UserRef uploadedBy,
    required DateTime createdAt,
  }) = _Attachment;

  factory Attachment.fromJson(Map<String, dynamic> json) =>
      _$AttachmentFromJson(json);
}

/// Register tiles (`GET /companies/{cid}/stats`).
@freezed
abstract class ChangeStats with _$ChangeStats {
  const factory ChangeStats({
    @Default(0) int pendingApproval,
    @Default(0) int approvedNotImplemented,
    @JsonKey(name: 'emergency_last_30_days')
    @Default(0)
    int emergencyLast30Days,
    @Default(0) int implementedNotVerified,
    @JsonKey(name: 'emergency_not_approved_in_24h')
    @Default(0)
    int emergencyNotApprovedIn24h,
    @Default(0) int implementedOutsideWindow,
    @Default(<String, int>{}) Map<String, int> byStatus,
  }) = _ChangeStats;

  factory ChangeStats.fromJson(Map<String, dynamic> json) =>
      _$ChangeStatsFromJson(json);
}

/// Entry of a change's audit trail (`GET …/audit`).
@freezed
abstract class AuditEntry with _$AuditEntry {
  const factory AuditEntry({
    required int seq,
    required DateTime occurredAt,
    String? actorId,
    required String actorDisplay,
    @Default(<String>[]) List<String> actorRoles,
    String? ipAddress,
    @Default('') String requestId,
    required String entityType,
    String? entityId,
    required String action,
    @Default(<String, dynamic>{}) Map<String, dynamic> diff,
    @Default(<String, dynamic>{}) Map<String, dynamic> context,
    @Default('') String prevHash,
    required String hash,
    // Required: a missing flag must not render an entry as intact.
    required bool hashValid,
  }) = _AuditEntry;

  factory AuditEntry.fromJson(Map<String, dynamic> json) =>
      _$AuditEntryFromJson(json);
}

/// "Łańcuch spójny" badge (`GET /companies/{cid}/audit/status`, ADR 0013 §11).
@freezed
abstract class ChainStatus with _$ChainStatus {
  const factory ChainStatus({
    required String status,
    bool? ok,
    DateTime? checkedAt,
    int? verifiedHeadSeq,
    @Default(0) int headSeq,
  }) = _ChainStatus;

  factory ChainStatus.fromJson(Map<String, dynamic> json) =>
      _$ChainStatusFromJson(json);
}

@freezed
abstract class Member with _$Member {
  const Member._();

  const factory Member({
    required String userId,
    required String displayName,
    @Default('') String email,
    @Default(true) bool isActive,
    @Default(<String>[]) List<String> roles,
  }) = _Member;

  factory Member.fromJson(Map<String, dynamic> json) => _$MemberFromJson(json);

  bool get canWrite => roles.contains('editor') || roles.contains('approver');
  bool get canApprove => roles.contains('approver');
}

/// Category available in a company (`GET /companies/{id}/categories`).
@freezed
abstract class CompanyCategory with _$CompanyCategory {
  const factory CompanyCategory({
    required String categoryId,
    required String code,
    required String name,
    @Default(true) bool requiresApproval,
    @Default('medium') String defaultRisk,
    @Default(true) bool isActive,
    String? approverOverrideId,
  }) = _CompanyCategory;

  factory CompanyCategory.fromJson(Map<String, dynamic> json) =>
      _$CompanyCategoryFromJson(json);
}

/// Global category dictionary entry (`GET /categories`).
@freezed
abstract class Category with _$Category {
  const factory Category({
    required String id,
    required String code,
    required String name,
    String? parentId,
    @Default(true) bool requiresApproval,
    @Default(false) bool requiresCiOwnerConsent,
    @Default('medium') String defaultRisk,
    @Default(true) bool isActive,
  }) = _Category;

  factory Category.fromJson(Map<String, dynamic> json) =>
      _$CategoryFromJson(json);
}

@freezed
abstract class CiItem with _$CiItem {
  const factory CiItem({
    required String id,
    required String companyId,
    required String ciTypeId,
    @Default('') String ciTypeCode,
    @Default('') String ciTypeName,
    required String identifier,
    required String name,
    String? description,
    String? ownerUserId,
    @Default(true) bool isActive,
  }) = _CiItem;

  factory CiItem.fromJson(Map<String, dynamic> json) => _$CiItemFromJson(json);
}

@freezed
abstract class CiType with _$CiType {
  const factory CiType({
    required String id,
    required String code,
    required String name,
    @Default(true) bool isActive,
  }) = _CiType;

  factory CiType.fromJson(Map<String, dynamic> json) => _$CiTypeFromJson(json);
}

/// `Page[T]` of the API (`limit/offset/total`).
class PageResult<T> {
  const PageResult({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  factory PageResult.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) item,
  ) => PageResult(
    items: [
      for (final value in (json['items'] as List<Object?>? ?? const []))
        if (value is Map) item(Map<String, dynamic>.from(value)),
    ],
    total: (json['total'] as num?)?.toInt() ?? 0,
    limit: (json['limit'] as num?)?.toInt() ?? 0,
    offset: (json['offset'] as num?)?.toInt() ?? 0,
  );

  final List<T> items;
  final int total;
  final int limit;
  final int offset;
}

/// Change types with Polish labels (CLAUDE.md §4.1, §10.3).
abstract final class ChangeTypes {
  static const String standard = 'standard';
  static const String normal = 'normal';
  static const String emergency = 'emergency';
  static const List<String> all = [standard, normal, emergency];

  static String label(String? value) => switch (value) {
    standard => 'Standardowa',
    normal => 'Normalna',
    emergency => 'Awaryjna',
    null => '—',
    _ => value,
  };

  static String description(String value) => switch (value) {
    standard =>
      'Powtarzalna, o niskim ryzyku, wg ustalonej procedury. Kategoria bez '
          'wymogu zatwierdzenia jest zatwierdzana automatycznie.',
    normal => 'Wymaga oceny i zatwierdzenia przed wdrożeniem.',
    emergency =>
      'Pilna — może zostać wdrożona przed zatwierdzeniem; zatwierdzenie po '
          'fakcie w ciągu 24 h.',
    _ => '',
  };
}

abstract final class Risks {
  static const String low = 'low';
  static const String medium = 'medium';
  static const String high = 'high';
  static const List<String> all = [low, medium, high];

  static String label(String? value) => switch (value) {
    low => 'Niskie',
    medium => 'Średnie',
    high => 'Wysokie',
    null => '—',
    _ => value,
  };
}
