import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_error.dart';

/// An application-wide notice about the service itself (not about one
/// screen): 429 `request.rate_limited` from nginx (with the time from
/// `Retry-After`) or 503 `api.unavailable` (ADR 0019 §8).
@immutable
class ServiceNotice {
  const ServiceNotice({
    required this.code,
    required this.message,
    required this.sequence,
  });

  final String code;
  final String message;

  /// Distinguishes two notices with the same text.
  final int sequence;
}

/// The latest [ServiceNotice]; the app shows it as a snackbar. A burst of
/// failing requests (one screen loads several resources) produces one
/// notice per code every [_quietPeriod].
class ServiceNoticeController extends Notifier<ServiceNotice?> {
  static const Duration _quietPeriod = Duration(seconds: 10);

  final Map<String, DateTime> _lastShown = {};
  int _sequence = 0;

  @override
  ServiceNotice? build() => null;

  void report(ApiProblem problem, {DateTime? now}) {
    final code = problem.code;
    if (code == null) return;
    final at = now ?? DateTime.now();
    final last = _lastShown[code];
    if (last != null && at.difference(last) < _quietPeriod) return;
    _lastShown[code] = at;
    state = ServiceNotice(
      code: code,
      message: problem.message,
      sequence: ++_sequence,
    );
  }
}

final serviceNoticeProvider =
    NotifierProvider<ServiceNoticeController, ServiceNotice?>(
      ServiceNoticeController.new,
    );
