import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/change_status.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../data/changes_api.dart';
import '../data/models.dart';
import 'labels.dart';
import 'readiness_panel.dart';

/// Confirmation dialog of a change action; returns the comment (`''` when
/// none) or null when cancelled.
Future<String?> showActionDialog(
  BuildContext context, {
  required String action,
  required Change change,
}) => showDialog<String>(
  context: context,
  builder: (_) => _ActionDialog(action: action, change: change),
);

class _ActionDialog extends StatefulWidget {
  const _ActionDialog({required this.action, required this.change});

  final String action;
  final Change change;

  @override
  State<_ActionDialog> createState() => _ActionDialogState();
}

class _ActionDialogState extends State<_ActionDialog> {
  final _comment = TextEditingController();
  String? _error;

  bool get _required =>
      ChangeActions.commentRequired(widget.action, widget.change);

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  void _confirm() {
    final text = _comment.text.trim();
    if (_required && text.isEmpty) {
      setState(() => _error = 'Komentarz jest wymagany dla tej operacji.');
      return;
    }
    if (text.length > ChangeActions.maxCommentLength) {
      setState(
        () => _error =
            'Komentarz może mieć najwyżej '
            '${ChangeActions.maxCommentLength} znaków.',
      );
      return;
    }
    Navigator.pop(context, text);
  }

  @override
  Widget build(BuildContext context) {
    final label = ChangeActions.label(widget.action, widget.change);
    final negative = ChangeActions.isNegative(widget.action);
    return AlertDialog(
      title: Text(label),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${widget.change.number} — ${widget.change.title ?? ''}',
              style: AppFonts.monoStyle(fontSize: 13),
            ),
            const SizedBox(height: 8),
            Text(ChangeActions.description(widget.action, widget.change)),
            const SizedBox(height: 16),
            TextField(
              key: const ValueKey('action-comment'),
              controller: _comment,
              minLines: 3,
              maxLines: 6,
              autofocus: true,
              decoration: InputDecoration(
                labelText: _required
                    ? 'Komentarz (wymagany)'
                    : 'Komentarz (opcjonalnie)',
                errorText: _error,
                alignLabelWithHint: true,
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          key: const ValueKey('action-confirm'),
          style: negative
              ? FilledButton.styleFrom(backgroundColor: AppColors.danger)
              : null,
          onPressed: _confirm,
          child: Text(label),
        ),
      ],
    );
  }
}

/// Runs a change action with the card's [Change.version]; handles the
/// conflict (409), not-ready (422 + checks) and other errors in Polish.
///
/// Returns the result, or null when cancelled / failed (already reported).
Future<ActionResult?> runChangeAction(
  BuildContext context,
  WidgetRef ref, {
  required String companyId,
  required Change change,
  required String action,
  String? presetComment,
  bool confirm = true,
}) async {
  var comment = presetComment;
  if (confirm) {
    comment = await showActionDialog(context, action: action, change: change);
    if (comment == null || !context.mounted) return null;
  }
  try {
    final result = await ref
        .read(changesApiProvider)
        .performAction(
          companyId,
          change.id,
          action,
          version: change.version,
          comment: comment,
        );
    if (context.mounted) _reportSuccess(context, result);
    return result;
  } on Object catch (error) {
    // Not awaited: the caller refreshes the card behind the dialog.
    if (context.mounted) unawaited(showActionError(context, error));
    return null;
  }
}

void _reportSuccess(BuildContext context, ActionResult result) {
  final warnings = [
    for (final w in result.warnings)
      if (w['message_pl'] is String) w['message_pl'] as String,
  ];
  final to = ChangeStatus.tryParse(result.toStatus)?.label ?? result.toStatus;
  final message = result.performedBySystem
      ? 'Zmiana standardowa została zatwierdzona automatycznie (system).'
      : result.fromStatus == result.toStatus
      ? 'Zapisano.'
      : 'Status zmiany: $to.';
  showInfoSnack(
    context,
    warnings.isEmpty ? message : '$message Uwaga: ${warnings.join(' ')}',
  );
}

/// Dialog for a failed action / save.
Future<void> showActionError(BuildContext context, Object error) {
  final problem = ApiProblem.from(error);
  final checks = [
    for (final raw in problem.checks)
      if (raw['code'] is String && raw['ok'] is bool)
        ReadinessCheck.fromJson(raw),
  ];
  final title = problem.isVersionConflict
      ? 'Zmiana została zmieniona przez kogoś innego'
      : problem.isNotReady
      ? 'Zmiana nie spełnia warunków'
      : 'Nie udało się wykonać operacji';
  return showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(problem.message),
              if (problem.detail != null) ...[
                const SizedBox(height: 8),
                Text(
                  problem.detail!,
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
              ],
              if (problem.isVersionConflict) ...[
                const SizedBox(height: 8),
                const Text(
                  'Karta została odświeżona. Sprawdź aktualny stan zmiany i '
                  'spróbuj ponownie.',
                ),
              ],
              if (checks.isNotEmpty) ...[
                const SizedBox(height: 12),
                ReadinessList(checks: checks.where((c) => c.isError).toList()),
              ],
            ],
          ),
        ),
      ),
      actions: [
        FilledButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zamknij'),
        ),
      ],
    ),
  );
}
