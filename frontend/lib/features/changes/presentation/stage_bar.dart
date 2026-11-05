import 'package:flutter/material.dart';

import '../../../core/change_status.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../data/models.dart';

enum StepState { done, current, pending, skipped }

/// One step of the lifecycle bar.
@immutable
class StageStep {
  const StageStep(this.label, this.state, {this.note});

  final String label;
  final StepState state;
  final String? note;
}

/// Steps Szkic → Do zatwierdzenia → Zatwierdzona → Wdrożona → Zweryfikowana
/// for [change], plus the side state (rejected / rolled back / cancelled).
(List<StageStep>, ChangeStatus?) stagesOf(Change change) {
  const main = [
    ChangeStatus.draft,
    ChangeStatus.pendingApproval,
    ChangeStatus.approved,
    ChangeStatus.implemented,
    ChangeStatus.verified,
  ];
  final status = change.statusValue ?? ChangeStatus.draft;
  final approved = change.approvedAt != null;

  // Furthest main step reached; side states stop where they branched off.
  final (int reached, ChangeStatus? side) = switch (status) {
    ChangeStatus.rejected => (1, ChangeStatus.rejected),
    ChangeStatus.rolledBack => (3, ChangeStatus.rolledBack),
    ChangeStatus.cancelled => (approved ? 2 : 0, ChangeStatus.cancelled),
    _ => (main.indexOf(status), null),
  };

  final steps = <StageStep>[];
  for (var i = 0; i < main.length; i++) {
    final step = main[i];
    var state = i < reached
        ? StepState.done
        : i == reached
        ? (side == null ? StepState.current : StepState.done)
        : StepState.pending;
    String? note;
    // Emergency implemented before approval: approval still pending
    // (or skipped for an auto-approved standard change: no pending step).
    if (step == ChangeStatus.pendingApproval &&
        change.autoApproved &&
        i < reached) {
      state = StepState.skipped;
      note = 'pominięte — zatwierdzenie automatyczne';
    }
    if (step == ChangeStatus.pendingApproval &&
        change.isEmergency &&
        !approved &&
        i < reached) {
      state = StepState.skipped;
    }
    if (step == ChangeStatus.approved && i < reached && !approved) {
      state = StepState.skipped;
      note = change.isEmergency ? 'oczekuje na zatwierdzenie po fakcie' : null;
    }
    steps.add(StageStep(step.label, state, note: note));
  }
  return (steps, side);
}

class StageBar extends StatelessWidget {
  const StageBar({required this.change, super.key});

  final Change change;

  @override
  Widget build(BuildContext context) {
    final (steps, side) = stagesOf(change);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 6,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            for (var i = 0; i < steps.length; i++) ...[
              if (i > 0)
                const Icon(
                  Icons.chevron_right,
                  size: 18,
                  color: AppColors.textSecondary,
                ),
              _Step(step: steps[i]),
            ],
            if (side != null) ...[
              const Icon(
                Icons.subdirectory_arrow_right,
                size: 18,
                color: AppColors.textSecondary,
              ),
              Tag(
                key: const ValueKey('stage-side'),
                label: side.label,
                colors: AppStatusColors.of(side),
                icon: Icons.block,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.step});

  final StageStep step;

  @override
  Widget build(BuildContext context) {
    final (
      IconData icon,
      StatusColors colors,
      String state,
    ) = switch (step.state) {
      StepState.done => (
        Icons.check_circle,
        AppFeedbackColors.success,
        'zakończony',
      ),
      StepState.current => (
        Icons.radio_button_checked,
        AppFeedbackColors.info,
        'bieżący',
      ),
      StepState.skipped => (
        Icons.remove_circle_outline,
        AppFeedbackColors.warning,
        'pominięty',
      ),
      StepState.pending => (
        Icons.radio_button_unchecked,
        AppFeedbackColors.neutral,
        'oczekujący',
      ),
    };
    return Semantics(
      label:
          'Etap ${step.label}: $state${step.note == null ? '' : ', ${step.note}'}',
      excludeSemantics: true,
      child: Tag(
        label: step.label,
        colors: colors,
        icon: icon,
        tooltip: step.note,
      ),
    );
  }
}
