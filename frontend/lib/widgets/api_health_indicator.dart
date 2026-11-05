import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/health.dart';
import '../core/theme.dart';

/// Shows whether the API answers `GET /api/v1/health`.
///
/// Status and version are on separate lines, so nothing is cut off in the
/// 232 px side panel (the one-line "API: połączono (v0.1.0)" was truncated).
class ApiHealthIndicator extends ConsumerWidget {
  const ApiHealthIndicator({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(apiHealthProvider);

    final (Color dot, String label, String? version) = switch (health) {
      AsyncData(:final value) => (
        AppColors.indicatorOk,
        'API: połączono',
        value.version == null || value.version!.isEmpty
            ? null
            : 'v${value.version}',
      ),
      AsyncError() => (AppColors.indicatorError, 'API: brak połączenia', null),
      _ => (AppColors.indicatorPending, 'API: sprawdzanie…', null),
    };
    final full = version == null ? label : '$label ($version)';

    return Tooltip(
      message: '$full — kliknij, aby sprawdzić ponownie',
      child: Semantics(
        label: full,
        button: true,
        excludeSemantics: true,
        child: InkWell(
          key: const ValueKey('api-health'),
          borderRadius: AppRadii.smallAll,
          onTap: () => ref.invalidate(apiHealthProvider),
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              minHeight: AppSizes.minTouchTarget,
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: dot,
                      shape: BoxShape.circle,
                    ),
                    child: const SizedBox.square(dimension: 8),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          label,
                          maxLines: 1,
                          softWrap: false,
                          overflow: TextOverflow.fade,
                          style: const TextStyle(
                            fontFamily: AppFonts.mono,
                            fontSize: 12,
                            color: AppColors.sidebarTextMuted,
                          ),
                        ),
                        if (version != null)
                          Text(
                            version,
                            maxLines: 1,
                            softWrap: false,
                            overflow: TextOverflow.fade,
                            style: const TextStyle(
                              fontFamily: AppFonts.mono,
                              fontSize: 11,
                              color: AppColors.sidebarTextMuted,
                            ),
                          ),
                      ],
                    ),
                  ),
                  const Icon(
                    Icons.refresh,
                    size: 16,
                    color: AppColors.sidebarTextMuted,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
