import 'package:freezed_annotation/freezed_annotation.dart';

import '../../changes/data/models.dart';

part 'report_models.freezed.dart';
part 'report_models.g.dart';

// Schemas mirror backend/app/schemas/reports.py (ADR 0017 §10) — the backend
// is the source of truth for the contract.

/// Report kinds (`ReportKindValue`) with Polish labels.
abstract final class ReportKinds {
  static const String register = 'register';
  static const String changeCard = 'change_card';

  static String label(String kind) => switch (kind) {
    register => 'Raport rejestru',
    changeCard => 'Karta zmiany',
    _ => kind,
  };
}

/// Report statuses (`ReportStatusValue`): `pending → done | failed`.
abstract final class ReportStatuses {
  static const String pending = 'pending';
  static const String done = 'done';
  static const String failed = 'failed';

  static String label(String status) => switch (status) {
    pending => 'Generowanie…',
    done => 'Gotowy',
    failed => 'Błąd',
    _ => status,
  };
}

/// A company of a report (`CompanyRef` of the reports schema).
@freezed
abstract class ReportCompany with _$ReportCompany {
  const factory ReportCompany({
    required String id,
    required String name,
    required String prefix,
  }) = _ReportCompany;

  factory ReportCompany.fromJson(Map<String, dynamic> json) =>
      _$ReportCompanyFromJson(json);
}

/// One export (`ReportOut`): a PDF register report, a PDF change card or a
/// CSV of the register.
@freezed
abstract class Report with _$Report {
  const Report._();

  const factory Report({
    required String id,
    required String number,
    required String kind,
    required String format,
    required String status,

    /// null = the multi-company report of an auditor.
    String? companyId,
    ReportCompany? company,
    @Default(<ReportCompany>[]) List<ReportCompany> companies,
    String? changeId,
    String? changeNumber,
    DateTime? periodFrom,
    DateTime? periodTo,
    @Default(<String, dynamic>{}) Map<String, dynamic> filters,
    @Default(false) bool includeAuditTrail,
    required UserRef generatedBy,
    required DateTime createdAt,
    DateTime? completedAt,
    int? changeCount,
    String? dataSha256,
    String? fileSha256,
    int? size,
    String? error,
    String? downloadUrl,
  }) = _Report;

  factory Report.fromJson(Map<String, dynamic> json) => _$ReportFromJson(json);

  bool get isPending => status == ReportStatuses.pending;
  bool get isDone => status == ReportStatuses.done;
  bool get isFailed => status == ReportStatuses.failed;
  bool get isAggregate => companyId == null;

  /// File name used when the response carries no `Content-Disposition`.
  String get fallbackFilename => '$number.$format';
}

/// Register filters of a report (`ReportFilters`; the period is top-level in
/// [ReportRequest]). Field names must match the API exactly
/// (`extra="forbid"`).
@freezed
abstract class ReportFilterSet with _$ReportFilterSet {
  const factory ReportFilterSet({
    @Default('created') String periodBy,
    @Default(<String>[]) List<String> status,
    @Default(<String>[]) List<String> type,
    @Default(<String>[]) List<String> category,
    @Default(<String>[]) List<String> ci,
    String? assignee,
    String? approver,

    /// User id or `system`.
    String? approvedBy,
    String? q,
  }) = _ReportFilterSet;

  factory ReportFilterSet.fromJson(Map<String, dynamic> json) =>
      _$ReportFilterSetFromJson(json);
}

/// Body of `POST /reports` (`ReportCreate`).
@freezed
abstract class ReportRequest with _$ReportRequest {
  const factory ReportRequest({
    required String kind,

    /// null with `kind = register` = all companies where the user is an
    /// auditor.
    String? companyId,
    String? changeId,
    DateTime? periodFrom,
    DateTime? periodTo,
    @Default(ReportFilterSet()) ReportFilterSet filters,
    @Default(false) bool includeAuditTrail,
  }) = _ReportRequest;

  factory ReportRequest.fromJson(Map<String, dynamic> json) =>
      _$ReportRequestFromJson(json);

  /// The PDF card of one change.
  factory ReportRequest.changeCard({
    required String companyId,
    required String changeId,
  }) => ReportRequest(
    kind: ReportKinds.changeCard,
    companyId: companyId,
    changeId: changeId,
  );
}
