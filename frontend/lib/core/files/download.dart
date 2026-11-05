import 'dart:typed_data';

import 'package:dio/dio.dart';

/// A file fetched from the API (report PDF/CSV) with the metadata of its
/// response headers.
class DownloadedFile {
  const DownloadedFile({
    required this.bytes,
    required this.filename,
    this.contentType,
    this.reportId,
    this.reportNumber,
    this.dataSha256,
    this.contentSha256,
  });

  final Uint8List bytes;
  final String filename;
  final String? contentType;

  /// `X-Report-Id`, `X-Report-Number`, `X-Data-SHA256`, `X-Content-SHA256`
  /// (ADR 0017 §7, §10).
  final String? reportId;
  final String? reportNumber;
  final String? dataSha256;
  final String? contentSha256;
}

/// GETs [path] as bytes through the API client — with the `Authorization`
/// header, so never as a bare link — and names the file after
/// `Content-Disposition` (exposed by the API's CORS), else after
/// `X-Report-Number`, else [fallbackName].
Future<DownloadedFile> fetchFile(
  Dio dio,
  String path, {
  Map<String, dynamic>? query,
  required String fallbackName,
}) async {
  final response = await dio.get<List<int>>(
    path,
    queryParameters: query,
    options: Options(responseType: ResponseType.bytes),
  );
  final headers = response.headers;
  String? header(String name) {
    final value = headers.value(name)?.trim();
    return value == null || value.isEmpty ? null : value;
  }

  final contentType = header(Headers.contentTypeHeader);
  final number = header('x-report-number');
  final fromDisposition = filenameFromContentDisposition(
    header('content-disposition'),
  );
  final fromNumber = number == null
      ? null
      : safeFilename('$number.${_extensionOf(contentType, fallbackName)}');
  return DownloadedFile(
    bytes: Uint8List.fromList(response.data ?? const []),
    filename: fromDisposition ?? fromNumber ?? safeFilename(fallbackName)!,
    contentType: contentType,
    reportId: header('x-report-id'),
    reportNumber: number,
    dataSha256: header('x-data-sha256'),
    contentSha256: header('x-content-sha256'),
  );
}

String _extensionOf(String? contentType, String fallbackName) {
  final type = contentType?.split(';').first.trim().toLowerCase();
  if (type == 'application/pdf') return 'pdf';
  if (type == 'text/csv') return 'csv';
  final dot = fallbackName.lastIndexOf('.');
  return dot < 0 ? 'bin' : fallbackName.substring(dot + 1);
}

/// File name of a `Content-Disposition` header (`filename*=UTF-8''…`
/// preferred over `filename="…"`); null when absent or unusable.
String? filenameFromContentDisposition(String? header) {
  if (header == null) return null;
  final extended = RegExp(
    r"""filename\*\s*=\s*([\w-]+)'[^']*'([^;]+)""",
    caseSensitive: false,
  ).firstMatch(header);
  if (extended != null) {
    try {
      final name = safeFilename(Uri.decodeComponent(extended[2]!.trim()));
      if (name != null) return name;
    } on Object {
      // malformed percent-encoding: fall back to `filename=`
    }
  }
  final quoted = RegExp(
    r'filename\s*=\s*"((?:[^"\\]|\\.)*)"',
    caseSensitive: false,
  ).firstMatch(header);
  if (quoted != null) {
    return safeFilename(
      quoted[1]!.replaceAllMapped(RegExp(r'\\(.)'), (m) => m[1]!),
    );
  }
  final token = RegExp(
    r'filename\s*=\s*([^;\s]+)',
    caseSensitive: false,
  ).firstMatch(header);
  return token == null ? null : safeFilename(token[1]!);
}

/// A file name without path parts or control characters; null when empty.
String? safeFilename(String name) {
  final base = name.split(RegExp(r'[\\/]')).last;
  final cleaned = base.replaceAll(RegExp(r'[\x00-\x1f\x7f]'), '').trim();
  if (cleaned.isEmpty || cleaned == '.' || cleaned == '..') return null;
  return cleaned;
}
