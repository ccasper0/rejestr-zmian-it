import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'app/app.dart';
import 'core/time.dart';

void main() {
  // Clean URLs (`/c/ALFA/changes` instead of `/#/c/ALFA/changes`);
  // nginx must fall back to index.html for unknown paths.
  usePathUrlStrategy();
  WarsawTime.ensureInitialized();
  runApp(const ProviderScope(retry: retryTransient, child: RejestrApp()));
}

/// Riverpod retries failed providers by default; only transient failures
/// (network, 5xx) are worth it — 4xx answers (404, 403, 409) are final.
Duration? retryTransient(int retryCount, Object error) {
  if (retryCount >= 2 || error is! DioException) return null;
  final status = error.response?.statusCode;
  if (status != null && status < 500) return null;
  return Duration(milliseconds: 500 * (retryCount + 1));
}
