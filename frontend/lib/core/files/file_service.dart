import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'file_service_stub.dart'
    if (dart.library.js_interop) 'file_service_web.dart'
    as platform;

/// A file chosen by the user.
class PickedFile {
  const PickedFile({required this.name, required this.bytes, this.contentType});

  final String name;
  final Uint8List bytes;
  final String? contentType;
}

/// Browser file access: choosing a file to upload and saving a download.
abstract interface class FileService {
  /// Opens the file chooser; null when cancelled.
  Future<PickedFile?> pickFile();

  /// Saves [bytes] as a download named [filename].
  void saveFile(String filename, Uint8List bytes, {String? contentType});
}

final fileServiceProvider = Provider<FileService>(
  (ref) => platform.createFileService(),
);
