import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/files/download.dart';
import '../../../core/files/file_service.dart';
import '../../changes/data/register_filters.dart';
import '../data/report_models.dart';
import '../data/reports_api.dart';

/// Polls `GET /reports/{id}` every [ReportPolling.interval] until the report
/// is `done` or `failed`.
///
/// Returns null when [isActive] turns false (the user left the screen —
/// polling stops). Throws an [ApiProblem] when the report failed or did not
/// finish within [ReportPolling.timeout].
Future<Report?> waitForReport(
  ReportsApi api,
  ReportPolling polling,
  Report report, {
  required bool Function() isActive,
  void Function(Report)? onUpdate,
}) async {
  var current = report;
  var attempts = 0;
  while (current.isPending) {
    if (attempts >= polling.maxAttempts) throw reportTimeout(current);
    await Future<void>.delayed(polling.interval);
    if (!isActive()) return null;
    attempts++;
    current = await api.get(current.id);
    if (!isActive()) return null;
    onUpdate?.call(current);
  }
  if (current.isFailed) throw reportFailed(current);
  return current;
}

/// The report failed in the worker (`error` from the API as the detail).
ApiProblem reportFailed(Report report) => ApiProblem(
  message:
      'Generowanie raportu ${report.number} nie powiodło się — wygeneruj '
      'raport ponownie.',
  code: 'report.failed',
  detail: report.error,
);

ApiProblem reportTimeout(Report report) => ApiProblem(
  message:
      'Raport ${report.number} jest wciąż generowany. Sprawdź jego status '
      'później na liście raportów.',
  code: 'report.not_ready',
);

/// Downloads a finished report and saves it in the browser.
Future<DownloadedFile> saveReport(Ref ref, Report report) async {
  final file = await ref.read(reportsApiProvider).download(report);
  _save(ref.read(fileServiceProvider), file);
  return file;
}

void _save(FileService files, DownloadedFile file) => files.saveFile(
  file.filename,
  file.bytes,
  contentType: file.contentType ?? 'application/octet-stream',
);

/// Report actions usable from any widget (card PDF, register CSV).
class ReportExporter {
  ReportExporter(this._ref);

  final Ref _ref;

  ReportsApi get _api => _ref.read(reportsApiProvider);

  /// Generates the PDF card of a change, waits if it is `pending` and saves
  /// it. Returns null when [isActive] turned false before the file was ready.
  Future<Report?> changeCard({
    required String companyId,
    required String changeId,
    required bool Function() isActive,
  }) async {
    final created = await _api.create(
      ReportRequest.changeCard(companyId: companyId, changeId: changeId),
    );
    final done = await waitForReport(
      _api,
      _ref.read(reportPollingProvider),
      created,
      isActive: isActive,
    );
    if (done == null) return null;
    await saveReport(_ref, done);
    return done;
  }

  /// Register CSV with the register's filters, saved in the browser.
  Future<DownloadedFile> registerCsv(
    String companyId,
    RegisterFilters filters,
  ) async {
    final file = await _api.exportCsv(companyId, filters);
    _save(_ref.read(fileServiceProvider), file);
    return file;
  }

  /// Saves a finished report from the list.
  Future<DownloadedFile> download(Report report) => saveReport(_ref, report);
}

final reportExporterProvider = Provider<ReportExporter>(ReportExporter.new);
