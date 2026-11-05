// Error codes of ADR 0019 §8 in the UI: 415/413 at the attachment upload,
// 429 request.rate_limited and 503 api.unavailable as app-wide notices.
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/files/file_service.dart';

import '../helpers.dart';

const _wide = Size(1500, 1400);
const _number = 'CHG-ALFA-2026-0001';
const _cardPath = '/c/ALFA/changes/$_number';
const _byNumber = '/companies/c-alfa/changes/by-number/$_number';
const _upload = '/companies/c-alfa/changes/ch-1/attachments';

Future<FakeApi> _uploadWith(WidgetTester tester, FakeResponse answer) async {
  setSurfaceSize(tester, _wide);
  final api = FakeApi()
    ..installDefaults()
    ..reply('GET', _byNumber, changeJson())
    ..on('POST', _upload, (_) => answer);
  final files = FakeFileService(
    picked: PickedFile(
      name: 'raport.pdf',
      bytes: Uint8List.fromList([0x4d, 0x5a, 0x90, 0x00]),
      contentType: 'application/pdf',
    ),
  );
  await pumpApp(
    tester,
    api: api,
    location: _cardPath,
    overrides: [fileServiceProvider.overrideWithValue(files)],
  );
  await tester.tap(find.byKey(const ValueKey('attachment-upload')));
  await tester.pumpAndSettle();
  return api;
}

Finder _inError(String text) => find.descendant(
  of: find.byKey(const ValueKey('attachment-upload-error')),
  matching: find.text(text),
);

void main() {
  testWidgets('415 attachment.type_not_allowed: detected type and the '
      'allowed types with Polish names', (tester) async {
    final api = await _uploadWith(
      tester,
      FakeResponse.fixture(415, 'problem_attachment_type'),
    );

    expect(api.calls('POST', _upload), hasLength(1));
    expect(_inError('Nie dodano pliku raport.pdf'), findsOneWidget);
    expect(
      _inError(
        'Niedozwolony typ pliku (program Windows). Dozwolone typy '
        'załączników: CSV, DOCX, EML (e-mail), JPEG, JSON, MSG (Outlook), '
        'ODS, ODT, PDF, PNG, XLSX, XML, ZIP, tekst (TXT, LOG).',
      ),
      findsOneWidget,
    );
    expect(
      _inError(
        'Typ pliku jest rozpoznawany po jego zawartości, nie po rozszerzeniu '
        'nazwy.',
      ),
      findsOneWidget,
    );

    await tester.tap(
      find.descendant(
        of: find.byKey(const ValueKey('attachment-upload-error')),
        matching: find.text('Zamknij'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('attachment-upload-error')), findsNothing);
  });

  testWidgets('413 attachment.too_large: the limit in MB', (tester) async {
    await _uploadWith(
      tester,
      FakeResponse.fixture(413, 'problem_attachment_too_large'),
    );

    expect(
      _inError('Plik jest zbyt duży (maksymalnie 25 MB).'),
      findsOneWidget,
    );
  });

  testWidgets('413 from nginx (body above client_max_body_size)', (
    tester,
  ) async {
    await _uploadWith(
      tester,
      FakeResponse.problem(
        413,
        'attachment.too_large',
        'Przesłany plik jest zbyt duży.',
      ),
    );

    expect(_inError('Plik jest zbyt duży.'), findsOneWidget);
  });

  testWidgets('429 request.rate_limited: app-wide snackbar with the time '
      'from Retry-After', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()
      ..installDefaults()
      ..on(
        'GET',
        '/companies/[^/]+/changes',
        (_) => FakeResponse.fixture(429, 'problem_rate_limited', {
          'Retry-After': '90',
        }),
      );
    await pumpApp(tester, api: api);

    expect(
      find.descendant(
        of: find.byKey(const ValueKey('service-notice-request.rate_limited')),
        matching: find.text(
          'Przekroczono limit żądań. Spróbuj ponownie za 2 min.',
        ),
      ),
      findsOneWidget,
    );
  });

  testWidgets('503 api.unavailable: app-wide snackbar', (tester) async {
    setSurfaceSize(tester, _wide);
    final api = FakeApi()
      ..installDefaults()
      ..on(
        'GET',
        '/companies/[^/]+/changes',
        (_) => FakeResponse.fixture(503, 'problem_api_unavailable'),
      );
    await pumpApp(tester, api: api);

    expect(
      find.byKey(const ValueKey('service-notice-api.unavailable')),
      findsOneWidget,
    );
  });
}
