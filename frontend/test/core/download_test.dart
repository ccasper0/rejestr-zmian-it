import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/files/download.dart';

void main() {
  group('filenameFromContentDisposition', () {
    test('quoted, token and RFC 5987 forms', () {
      expect(
        filenameFromContentDisposition(
          'attachment; filename="RAP-ALFA-2026-0001.pdf"',
        ),
        'RAP-ALFA-2026-0001.pdf',
      );
      expect(
        filenameFromContentDisposition(
          'attachment; filename=RAP-2026-0001.csv',
        ),
        'RAP-2026-0001.csv',
      );
      expect(
        filenameFromContentDisposition(
          "attachment; filename=\"raport.pdf\"; filename*=UTF-8''za%C5%BC%C3%B3%C5%82%C4%87.pdf",
        ),
        'zażółć.pdf',
      );
    });

    test('path parts and control characters are removed; absent → null', () {
      expect(
        filenameFromContentDisposition(
          'attachment; filename="../../etc/x.pdf"',
        ),
        'x.pdf',
      );
      expect(
        // quoted-string escape `\\` = one backslash = a Windows path part
        filenameFromContentDisposition(r'attachment; filename="x\\b.pdf"'),
        'b.pdf',
      );
      expect(filenameFromContentDisposition('attachment'), isNull);
      expect(filenameFromContentDisposition(null), isNull);
      expect(
        filenameFromContentDisposition('attachment; filename=".."'),
        isNull,
      );
    });
  });
}
