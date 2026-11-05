import 'package:flutter/material.dart';

import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../data/models.dart';

/// "Kontrola przed wysłaniem" (§10.3): renders `GET …/readiness` — the
/// backend's §4.3 rules; the frontend does not re-implement them.
class ReadinessPanel extends StatelessWidget {
  const ReadinessPanel({
    required this.readiness,
    this.stale = false,
    this.onCheckTap,
    this.onRefresh,
    super.key,
  });

  /// Null while loading.
  final Readiness? readiness;

  /// The form has unsaved edits: the checks describe the last saved version.
  final bool stale;
  final ValueChanged<ReadinessCheck>? onCheckTap;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final readiness = this.readiness;
    final errors = readiness?.checks.where((c) => c.isError).length ?? 0;
    return SectionCard(
      key: const ValueKey('readiness-panel'),
      title: 'Kontrola przed wysłaniem',
      trailing: onRefresh == null
          ? null
          : IconButton(
              tooltip: 'Odśwież kontrolę',
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh),
            ),
      child: readiness == null
          ? const LoadingPanel(label: 'Sprawdzanie…')
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Tag(
                  key: const ValueKey('readiness-summary'),
                  label: readiness.ok
                      ? 'Gotowa do wysłania'
                      : errors == 1
                      ? '1 pozycja do poprawy'
                      : '$errors pozycji do poprawy',
                  colors: readiness.ok
                      ? AppFeedbackColors.success
                      : AppFeedbackColors.error,
                  icon: readiness.ok
                      ? Icons.check_circle_outline
                      : Icons.error_outline,
                ),
                if (stale) ...[
                  const SizedBox(height: 8),
                  const Text(
                    'Masz niezapisane zmiany — kontrola dotyczy ostatniej '
                    'zapisanej wersji.',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                ReadinessList(checks: readiness.checks, onTap: onCheckTap),
              ],
            ),
    );
  }
}

/// List of checks: ✓ ok, ! warning, ✗ error, with the server's message.
class ReadinessList extends StatelessWidget {
  const ReadinessList({required this.checks, this.onTap, super.key});

  final List<ReadinessCheck> checks;
  final ValueChanged<ReadinessCheck>? onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final check in checks) _CheckRow(check: check, onTap: onTap),
      ],
    );
  }
}

class _CheckRow extends StatelessWidget {
  const _CheckRow({required this.check, this.onTap});

  final ReadinessCheck check;
  final ValueChanged<ReadinessCheck>? onTap;

  @override
  Widget build(BuildContext context) {
    final (IconData icon, StatusColors colors, String state) = check.isError
        ? (Icons.cancel_outlined, AppFeedbackColors.error, 'Błąd')
        : check.isWarning
        ? (Icons.warning_amber_outlined, AppFeedbackColors.warning, 'Uwaga')
        : (Icons.check_circle_outline, AppFeedbackColors.success, 'OK');
    final row = Padding(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: colors.foreground, semanticLabel: state),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              check.messagePl.isEmpty ? check.code : check.messagePl,
              style: TextStyle(
                color: check.isError || check.isWarning
                    ? colors.foreground
                    : AppColors.text,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
    if (onTap == null || check.field == null || !check.isError) return row;
    return InkWell(
      key: ValueKey('check-${check.code}'),
      borderRadius: AppRadii.smallAll,
      onTap: () => onTap!(check),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: AppSizes.minTouchTarget),
        child: row,
      ),
    );
  }
}
