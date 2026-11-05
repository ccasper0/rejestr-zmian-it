import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/app/router.dart';
import 'package:rejestr_zmian/core/api_client.dart';
import 'package:rejestr_zmian/features/changes/data/changes_api.dart';

import '../helpers.dart';

const _wide = Size(1280, 900);

void main() {
  group('router: path parameters are validated before any API call', () {
    for (final location in [
      '/c/ALFA/changes/..%2F..%2Fstats',
      '/c/ALFA/changes/..%2Fc-alfa%2Fchanges%2Fch-1%2Fattachments%2Fa-1/edit',
      '/c/ALFA/changes/CHG-ALFA-2026-0001%3Fx=1',
      '/c/AL..FA/changes',
      '/c/alfa/changes',
    ]) {
      testWidgets('"$location" → not found, no API request built from it', (
        tester,
      ) async {
        setSurfaceSize(tester, _wide);
        final api = FakeApi()..installDefaults();
        await pumpApp(tester, api: api, location: location);

        expect(find.text('Nie znaleziono strony'), findsOneWidget);
        // Only the shell's own requests: dio collapses `..`, so checking for
        // fragments is not enough — every request must be expected.
        final allowed = RegExp(r'^/(me|companies/c-(alfa|beta)/stats)$');
        for (final request in api.requests) {
          expect(allowed.hasMatch(request.path), isTrue, reason: '$request');
        }
      });
    }

    test('patterns', () {
      expect(changeNumberPattern.hasMatch('CHG-ALFA-2026-0017'), isTrue);
      expect(changeNumberPattern.hasMatch('CHG-ALFA-2026-0017/..'), isFalse);
      expect(companyPrefixPattern.hasMatch('all'), isTrue);
      expect(companyPrefixPattern.hasMatch('ALFA1'), isFalse);
    });
  });

  group('API client encodes every path segment', () {
    test('slashes and query characters stay inside one segment', () async {
      final api = FakeApi()..installDefaults();
      final dio = createApiClient(baseUrl: 'http://api.test/api/v1')
        ..httpClientAdapter = api;
      api.reply('GET', r'/companies/c-alfa/changes/by-number/.*', changeJson());
      await ChangesApi(dio).getByNumber('c-alfa', '../../ci?x=1#y');

      final request = api.requests.single;
      expect(
        request.path,
        '/companies/c-alfa/changes/by-number/..%2F..%2Fci%3Fx%3D1%23y',
      );
      expect(request.query, isEmpty);
    });

    test('dot segments and empty segments are refused', () {
      expect(() => ChangesApi.seg('..'), throwsArgumentError);
      expect(() => ChangesApi.seg('.'), throwsArgumentError);
      expect(() => ChangesApi.seg(''), throwsArgumentError);
      expect(ChangesApi.seg('CHG-ALFA-2026-0001'), 'CHG-ALFA-2026-0001');
    });
  });

  group('safeReturnPath (login ?from=)', () {
    test('accepts local paths with queries', () {
      expect(
        safeReturnPath('/c/ALFA/changes?status=draft'),
        '/c/ALFA/changes?status=draft',
      );
    });

    test('rejects external, backslash, control chars and login', () {
      for (final from in [
        null,
        'https://evil.example',
        '//evil.example',
        '/\\evil.example',
        '/c/ALFA\\x',
        '/c/ALFA/changes\n',
        '/c/ALFA/\u0000',
        'javascript:alert(1)',
        '/login',
        '/login?from=/x',
      ]) {
        expect(safeReturnPath(from), isNull, reason: '$from');
      }
    });
  });
}
