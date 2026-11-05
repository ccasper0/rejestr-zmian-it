import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

import 'file_service.dart';

class _BrowserFileService implements FileService {
  @override
  Future<PickedFile?> pickFile() {
    final completer = Completer<PickedFile?>();
    final input = web.HTMLInputElement()..type = 'file';

    Future<void> read() async {
      final file = input.files?.item(0);
      if (file == null) {
        if (!completer.isCompleted) completer.complete(null);
        return;
      }
      try {
        final buffer = await file.arrayBuffer().toDart;
        if (!completer.isCompleted) {
          completer.complete(
            PickedFile(
              name: file.name,
              bytes: buffer.toDart.asUint8List(),
              contentType: file.type.isEmpty ? null : file.type,
            ),
          );
        }
      } on Object catch (error, stack) {
        if (!completer.isCompleted) completer.completeError(error, stack);
      }
    }

    input
      ..addEventListener(
        'change',
        ((web.Event _) {
          unawaited(read());
        }).toJS,
      )
      ..addEventListener(
        'cancel',
        ((web.Event _) {
          if (!completer.isCompleted) completer.complete(null);
        }).toJS,
      )
      ..click();
    return completer.future;
  }

  @override
  void saveFile(String filename, Uint8List bytes, {String? contentType}) {
    final blob = web.Blob(
      [bytes.toJS].toJS,
      web.BlobPropertyBag(type: contentType ?? 'application/octet-stream'),
    );
    final url = web.URL.createObjectURL(blob);
    final anchor = web.HTMLAnchorElement()
      ..href = url
      ..download = filename
      ..style.display = 'none';
    web.document.body?.append(anchor);
    anchor.click();
    anchor.remove();
    Timer(const Duration(seconds: 30), () => web.URL.revokeObjectURL(url));
  }
}

FileService createFileService() => _BrowserFileService();
