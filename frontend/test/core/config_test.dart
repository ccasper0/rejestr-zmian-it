import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/config.dart';

void main() {
  group('AppConfig.resolveApiOrigin', () {
    test('uses localhost:8000 when API_URL is not defined', () {
      expect(
        AppConfig.resolveApiOrigin(hasValue: false, value: ''),
        'http://localhost:8000',
      );
    });

    test('empty API_URL means same origin (not localhost)', () {
      expect(AppConfig.resolveApiOrigin(hasValue: true, value: ''), '');
      expect(AppConfig.apiBaseUrlFor(''), '/api/v1');
    });

    test('explicit origin is used without trailing slash', () {
      final origin = AppConfig.resolveApiOrigin(
        hasValue: true,
        value: 'http://localhost:8000/',
      );
      expect(origin, 'http://localhost:8000');
      expect(AppConfig.apiBaseUrlFor(origin), 'http://localhost:8000/api/v1');
    });
  });

  test('default build (no define) targets localhost API v1', () {
    expect(AppConfig.apiBaseUrl, 'http://localhost:8000/api/v1');
  });

  test('AUTH_MODE: dev, local, anything else = auto (ask the API)', () {
    expect(AppConfig.parseAuthMode('dev'), AuthModeSetting.dev);
    expect(AppConfig.parseAuthMode(' LOCAL '), AuthModeSetting.local);
    expect(AppConfig.parseAuthMode('oidc'), AuthModeSetting.auto);
    expect(AppConfig.parseAuthMode(''), AuthModeSetting.auto);
  });
}
