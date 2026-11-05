import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import 'api_client.dart';

part 'health.freezed.dart';
part 'health.g.dart';

/// Response of `GET /api/v1/health`.
@freezed
abstract class HealthInfo with _$HealthInfo {
  const factory HealthInfo({@Default('ok') String status, String? version}) =
      _HealthInfo;

  factory HealthInfo.fromJson(Map<String, dynamic> json) =>
      _$HealthInfoFromJson(json);
}

/// Fetches the API health (the "ping" from stage 0 acceptance criteria).
///
/// Automatic retries are disabled — the indicator offers a manual refresh.
final apiHealthProvider = FutureProvider.autoDispose<HealthInfo>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final response = await dio.get<Map<String, dynamic>>('/health');
  return HealthInfo.fromJson(response.data ?? const {});
}, retry: (retryCount, error) => null);
