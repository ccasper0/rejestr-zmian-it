import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/api_client.dart';
import 'package:rejestr_zmian/core/health.dart';
import 'package:rejestr_zmian/core/theme.dart';
import 'package:rejestr_zmian/widgets/api_health_indicator.dart';

import '../helpers.dart';

/// Dio adapter answering every request with a fixed JSON body.
class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.statusCode, this.body);

  final int statusCode;
  final Map<String, Object?> body;
  final List<Uri> requested = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requested.add(options.uri);
    return ResponseBody.fromString(
      jsonEncode(body),
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Widget _host(List<Override> overrides) => ProviderScope(
  retry: (retryCount, error) => null,
  overrides: overrides,
  child: MaterialApp(
    theme: AppTheme.light(),
    home: const Scaffold(
      backgroundColor: AppColors.sidebar,
      body: Center(
        child: SizedBox(
          width: AppSizes.sidebarWidth - 16,
          child: ApiHealthIndicator(),
        ),
      ),
    ),
  ),
);

void main() {
  testWidgets('shows connected state with API version', (tester) async {
    await tester.pumpWidget(_host([healthOk(version: '1.2.3')]));
    await tester.pumpAndSettle();

    expect(find.text('API: połączono'), findsOneWidget);
    expect(find.text('v1.2.3'), findsOneWidget);
  });

  testWidgets('shows connected state without version', (tester) async {
    await tester.pumpWidget(_host([healthOk(version: null)]));
    await tester.pumpAndSettle();

    expect(find.text('API: połączono'), findsOneWidget);
    expect(find.textContaining('v'), findsNothing);
  });

  testWidgets('long version is not cut off in the 232 px panel', (
    tester,
  ) async {
    await tester.pumpWidget(_host([healthOk(version: '0.1.0+build.42')]));
    await tester.pumpAndSettle();
    expect(find.text('API: połączono'), findsOneWidget);
    expect(find.text('v0.1.0+build.42'), findsOneWidget);
  });

  testWidgets('shows error state when API is unreachable', (tester) async {
    await tester.pumpWidget(_host([healthFailing()]));
    await tester.pumpAndSettle();

    expect(find.text('API: brak połączenia'), findsOneWidget);
  });

  testWidgets('calls GET {API_URL}/api/v1/health and parses the response', (
    tester,
  ) async {
    final adapter = _FakeAdapter(200, {'status': 'ok', 'version': '0.1.0'});
    final dio = createApiClient(baseUrl: 'http://api.test/api/v1')
      ..httpClientAdapter = adapter;

    await tester.pumpWidget(_host([apiClientProvider.overrideWithValue(dio)]));
    await tester.pumpAndSettle();

    expect(find.text('v0.1.0'), findsOneWidget);
    expect(
      adapter.requested.single.toString(),
      'http://api.test/api/v1/health',
    );
  });

  testWidgets('HTTP 503 from health endpoint shows error state', (
    tester,
  ) async {
    final dio = createApiClient(baseUrl: 'http://api.test/api/v1')
      ..httpClientAdapter = _FakeAdapter(503, {'status': 'down'});

    await tester.pumpWidget(_host([apiClientProvider.overrideWithValue(dio)]));
    await tester.pumpAndSettle();

    expect(find.text('API: brak połączenia'), findsOneWidget);
  });

  test('HealthInfo.fromJson tolerates extra fields', () {
    final info = HealthInfo.fromJson({
      'status': 'ok',
      'version': '0.1.0',
      'db': 'ok',
    });
    expect(info.version, '0.1.0');
  });
}
