import 'dart:convert';

import 'helpers.dart';

/// A `ReportOut` (backend/app/schemas/reports.py).
Map<String, Object?> reportJson({
  String id = 'r-1',
  String number = 'RAP-ALFA-2026-0001',
  String kind = 'register',
  String format = 'pdf',
  String status = 'done',
  String? companyId = companyAlfa,
  List<Map<String, Object?>>? companies,
  String? changeId,
  String? changeNumber,
  String? periodFrom = '2026-09-30T22:00:00.000000Z',
  String? periodTo = '2026-10-31T23:00:00.000000Z',
  String periodBy = 'created',
  bool includeAuditTrail = false,
  String createdAt = '2026-11-03T09:15:00.000000Z',
  int? changeCount = 17,
  String? dataSha256,
  String? error,
  String author = 'Alicja Audytorka',
}) {
  final alfa = {'id': companyAlfa, 'name': 'Alfa S.A.', 'prefix': 'ALFA'};
  final done = status == 'done';
  return {
    'id': id,
    'number': number,
    'kind': kind,
    'format': format,
    'status': status,
    'company_id': companyId,
    'company': companyId == null ? null : alfa,
    'companies': companies ?? [alfa],
    'change_id': changeId,
    'change_number': changeNumber,
    'period_from': periodFrom,
    'period_to': periodTo,
    'filters': kind == 'change_card'
        ? <String, Object?>{}
        : {
            'period_by': periodBy,
            'status': <String>[],
            'type': <String>[],
            'category': <String>[],
            'ci': <String>[],
            'assignee': null,
            'approver': null,
            'approved_by': null,
            'q': null,
          },
    'include_audit_trail': includeAuditTrail,
    'generated_by': {'id': 'u-author', 'display_name': author},
    'created_at': createdAt,
    'completed_at': done ? createdAt : null,
    'change_count': changeCount,
    'data_sha256': done ? (dataSha256 ?? '9f2c${'1a' * 30}') : null,
    'file_sha256': done ? '4be1${'c3' * 30}' : null,
    'size': done ? 1834 : null,
    'error': error,
    'download_url': done ? '/api/v1/reports/$id/download' : null,
  };
}

/// A downloaded PDF named by `Content-Disposition`.
FakeResponse pdfFile(String number) => FakeResponse.file(
  utf8.encode('%PDF-1.7 $number'),
  headers: {
    'content-type': 'application/pdf',
    'content-disposition': 'attachment; filename="$number.pdf"',
    'x-report-number': number,
    'x-data-sha256': '9f2c${'1a' * 30}',
    'x-content-sha256': '4be1${'c3' * 30}',
  },
);
