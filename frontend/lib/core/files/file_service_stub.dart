import 'dart:typed_data';

import 'file_service.dart';

/// Non-web platforms (tests): no file chooser.
class _UnsupportedFileService implements FileService {
  @override
  Future<PickedFile?> pickFile() async => null;

  @override
  void saveFile(String filename, Uint8List bytes, {String? contentType}) =>
      throw UnsupportedError(
        'Zapisywanie plików jest dostępne w przeglądarce.',
      );
}

FileService createFileService() => _UnsupportedFileService();
