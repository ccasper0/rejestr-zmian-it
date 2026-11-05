import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../core/time.dart';
import '../../changes/data/register_filters.dart';
import 'report_models.dart';

part 'report_form.freezed.dart';

/// Parameters of a register report on the screen "Raporty i eksport".
///
/// The period is a pair of Warsaw calendar days (`yyyy-MM-dd`, both
/// inclusive, like the register's `from`/`to` — ADR 0014 §5); the API gets
/// `[period_from, period_to)` in UTC. Validation here only mirrors the
/// backend for UX (`report.period_required`, `report.invalid_period`).
@freezed
abstract class ReportForm with _$ReportForm {
  const ReportForm._();

  const factory ReportForm({
    String? from,
    String? to,
    @Default(RegisterFilters.defaultPeriodBy) String periodBy,
    @Default(<String>[]) List<String> statuses,
    @Default(<String>[]) List<String> types,
    @Default(<String>[]) List<String> categories,
    @Default(<String>[]) List<String> cis,
    String? assignee,
    String? approvedBy,
    @Default('') String q,
    @Default(false) bool includeAuditTrail,
  }) = _ReportForm;

  /// The register's filters (link "Eksport PDF"); without a period in them
  /// the current quarter up to today ([now], Warsaw).
  factory ReportForm.fromRegister(RegisterFilters filters, {DateTime? now}) {
    final hasPeriod = filters.from != null || filters.to != null;
    final (defaultFrom, defaultTo) = currentQuarter(now ?? DateTime.now());
    return ReportForm(
      from: hasPeriod ? filters.from : defaultFrom,
      to: hasPeriod ? filters.to : defaultTo,
      periodBy: filters.periodBy,
      statuses: filters.statuses,
      types: filters.types,
      categories: filters.categories,
      cis: filters.cis,
      assignee: filters.assignee,
      approvedBy: filters.approvedBy,
      q: filters.q,
    );
  }

  /// First day of the Warsaw quarter of [now] and the day of [now].
  static (String, String) currentQuarter(DateTime now) {
    final local = WarsawTime.toWarsaw(now);
    final quarterMonth = ((local.month - 1) ~/ 3) * 3 + 1;
    final start = WarsawTime.fromWarsaw(local.year, quarterMonth, 1);
    return (WarsawTime.isoDay(start), WarsawTime.isoDay(now));
  }

  DateTime? get fromInstant => WarsawTime.startOfIsoDay(from);

  /// Start of the day after [to] (the API's `period_to` is exclusive).
  DateTime? get toExclusive {
    final day = WarsawTime.startOfIsoDay(to);
    if (day == null) return null;
    final local = WarsawTime.toWarsaw(day);
    return WarsawTime.fromWarsaw(local.year, local.month, local.day + 1);
  }

  /// Polish error of the period, null when valid.
  String? get periodError {
    final start = fromInstant;
    final end = WarsawTime.startOfIsoDay(to);
    if (start == null && end == null) {
      return 'Podaj okres raportu (początek i koniec).';
    }
    if (start == null) return 'Podaj początek okresu.';
    if (end == null) return 'Podaj koniec okresu.';
    if (end.isBefore(start)) {
      return 'Początek okresu nie może być późniejszy niż jego koniec.';
    }
    return null;
  }

  bool get isValid => periodError == null;

  bool get hasFilters =>
      statuses.isNotEmpty ||
      types.isNotEmpty ||
      categories.isNotEmpty ||
      cis.isNotEmpty ||
      assignee != null ||
      approvedBy != null ||
      q.trim().isNotEmpty;

  /// Filters that apply to one company only (CI, people; `system` as the
  /// approver is company-independent) are dropped for the
  /// multi-company report ([companyId] null).
  ReportRequest toRequest({required String? companyId}) {
    final single = companyId != null;
    return ReportRequest(
      kind: ReportKinds.register,
      companyId: companyId,
      periodFrom: fromInstant,
      periodTo: toExclusive,
      includeAuditTrail: includeAuditTrail,
      filters: ReportFilterSet(
        periodBy: periodBy,
        status: statuses,
        type: types,
        category: categories,
        ci: single ? cis : const [],
        assignee: single ? assignee : null,
        approvedBy: single || approvedBy == 'system' ? approvedBy : null,
        q: q.trim().isEmpty ? null : q.trim(),
      ),
    );
  }
}
