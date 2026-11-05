import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/change_status.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../../../widgets/status_pill.dart';
import '../data/changes_api.dart';
import '../data/models.dart';

/// Correction of a frozen change (CLAUDE.md §4.2, ADR 0021): a NEW draft with
/// `supersedes_change_id` pointing at the original.
abstract final class ChangeCorrection {
  /// Statuses in which the record is frozen (`FROZEN_STATUSES` of the
  /// backend domain, ADR 0012 §6) — the UI offers a correction only there.
  /// The API itself accepts `supersedes_change_id` for any change of the
  /// same company (ADR 0013 §1); this is the UI's rule.
  static const Set<ChangeStatus> correctableStatuses = {
    ChangeStatus.implemented,
    ChangeStatus.verified,
    ChangeStatus.rolledBack,
    ChangeStatus.rejected,
    ChangeStatus.cancelled,
  };

  static const String titlePrefix = 'Korekta: ';

  /// API limit of `title` (`TITLE_MAX`).
  static const int titleMax = 500;

  static bool isCorrectable(Change change) =>
      correctableStatuses.contains(change.statusValue);

  /// Title of the correction: `Korekta: <title>` (not doubled for a
  /// correction of a correction), at most [titleMax] characters.
  static String title(Change original) {
    final base = (original.title ?? '').trim();
    final text = base.isEmpty
        ? '$titlePrefix${original.number}'
        : base.startsWith(titlePrefix)
        ? base
        : '$titlePrefix$base';
    return text.length <= titleMax ? text : text.substring(0, titleMax);
  }

  /// Body of `POST /companies/{cid}/changes` for the correction of
  /// [original]: its substantive fields, CI and people — without the service
  /// window and the lifecycle dates (the correction is planned anew).
  ///
  /// [memberIds]: user ids of the company members; people who are no longer
  /// members are left out (the API refuses them with `change.user_not_found`).
  /// Null = copy all. Without an approver the API suggests the default one.
  static Map<String, Object?> draftFields(
    Change original, {
    Set<String>? memberIds,
  }) {
    String? person(UserRef? ref) {
      if (ref == null) return null;
      if (memberIds != null && !memberIds.contains(ref.id)) return null;
      return ref.id;
    }

    final fields = <String, Object?>{
      'supersedes_change_id': original.id,
      'title': title(original),
      'category_id': original.category?.id,
      'subcategory_id': original.subcategory?.id,
      'change_type': original.changeType,
      'risk': original.risk,
      'description': original.description,
      'implementation_plan': original.implementationPlan,
      'rollback_plan': original.rollbackPlan,
      'impact': original.impact,
      'requirement_ref': original.requirementRef,
      'ticket_ref': original.ticketRef,
      'assignee_id': person(original.assignee),
      'approver_id': person(original.approver),
      'verifier_id': person(original.verifier),
      if (original.ci.isNotEmpty)
        'ci_ids': [for (final ci in original.ci) ci.id],
    };
    // Empty values are not sent: a draft may leave them empty, and a missing
    // `approver_id` lets the API fill in the default approver (§4.3).
    fields.removeWhere(
      (_, value) => value == null || (value is String && value.trim().isEmpty),
    );
    return fields;
  }
}

/// Confirmation before creating the correction; true = create.
Future<bool> confirmCorrection(BuildContext context, Change original) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Utworzyć korektę zmiany?'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text.rich(
              TextSpan(
                children: [
                  const TextSpan(text: 'Zmiana '),
                  TextSpan(
                    text: original.number,
                    style: AppFonts.monoStyle(fontSize: 14),
                  ),
                  const TextSpan(
                    text:
                        ' jest zamrożona i nie można jej edytować. Korekta to '
                        'nowa zmiana (szkic z nowym numerem), która wskazuje '
                        'oryginał.',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Do szkicu zostaną skopiowane: tytuł (z dopiskiem „Korekta:”), '
              'kategoria, obiekty (CI), typ i ryzyko, opis, plany, wpływ, '
              'zgłoszenie, podstawa/wymóg oraz osoby. Okno serwisowe trzeba '
              'wyznaczyć od nowa. Korekta przechodzi pełną ścieżkę '
              'zatwierdzania; oryginał pozostaje bez zmian.',
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          key: const ValueKey('correction-cancel'),
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          key: const ValueKey('correction-confirm'),
          onPressed: () => Navigator.pop(context, true),
          child: const Text('Utwórz korektę'),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// Creates the correction draft of [original] and opens its edit form.
/// Errors (problem+json) are shown in Polish; returns whether it succeeded.
Future<bool> createCorrection(
  BuildContext context,
  WidgetRef ref, {
  required String companyId,
  required String prefix,
  required Change original,
}) async {
  final api = ref.read(changesApiProvider);
  try {
    Set<String>? memberIds;
    try {
      final members = await ref.read(membersProvider(companyId).future);
      memberIds = {for (final m in members) m.userId};
    } on Object {
      // Without the member list all people are copied; the API decides.
      memberIds = null;
    }
    final created = await api.createDraft(
      companyId,
      ChangeCorrection.draftFields(original, memberIds: memberIds),
    );
    ref.invalidate(statsProvider(companyId));
    if (!context.mounted) return true;
    showInfoSnack(
      context,
      'Utworzono korektę ${created.number} zmiany ${original.number}.',
    );
    context.go('/c/$prefix/changes/${created.number}/edit');
    return true;
  } on Object catch (error) {
    if (context.mounted) showErrorSnack(context, error);
    return false;
  }
}

/// "Korekta zmiany CHG-…": a link to the corrected original
/// (`supersedes_number` of the card, ADR 0021). Without the number (older
/// API) only a plain label is shown.
class SupersedesLink extends StatelessWidget {
  const SupersedesLink({required this.prefix, required this.change, super.key});

  final String prefix;
  final Change change;

  @override
  Widget build(BuildContext context) {
    final number = change.supersedesNumber;
    if (number == null || number.isEmpty) {
      return const Tag(
        key: ValueKey('supersedes-tag'),
        label: 'Korekta wcześniejszej zmiany',
        colors: AppFeedbackColors.info,
      );
    }
    return TextButton.icon(
      key: const ValueKey('supersedes-link'),
      onPressed: () => context.go('/c/$prefix/changes/$number'),
      icon: const Icon(Icons.history, size: 18),
      label: Text.rich(
        TextSpan(
          children: [
            const TextSpan(text: 'Korekta zmiany '),
            TextSpan(
              text: number,
              style: AppFonts.monoStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.accent,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// "Skorygowana przez: CHG-… (status)" on the original's card: links to its
/// corrections (`superseded_by`, oldest first, ADR 0021). Empty = nothing.
class SupersededByLinks extends StatelessWidget {
  const SupersededByLinks({
    required this.prefix,
    required this.corrections,
    super.key,
  });

  final String prefix;
  final List<LinkedChange> corrections;

  @override
  Widget build(BuildContext context) {
    if (corrections.isEmpty) return const SizedBox.shrink();
    return Wrap(
      key: const ValueKey('superseded-by'),
      spacing: 8,
      runSpacing: 4,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        const Text(
          'Skorygowana przez:',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        for (final correction in corrections)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextButton(
                key: ValueKey('superseded-by-${correction.number}'),
                onPressed: () =>
                    context.go('/c/$prefix/changes/${correction.number}'),
                child: Text(
                  correction.number,
                  style: AppFonts.monoStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.accent,
                  ),
                ),
              ),
              if (correction.statusValue case final status?)
                StatusPill(status: status)
              else
                Tag(label: correction.status, mono: true),
            ],
          ),
      ],
    );
  }
}

/// Form banner of a correction draft: "Korekta zmiany CHG-…".
class CorrectionBanner extends StatelessWidget {
  const CorrectionBanner({
    required this.prefix,
    required this.change,
    super.key,
  });

  final String prefix;
  final Change change;

  @override
  Widget build(BuildContext context) {
    final number = change.supersedesNumber;
    final known = number != null && number.isNotEmpty;
    return MessageBanner(
      key: const ValueKey('correction-banner'),
      title: known ? 'Korekta zmiany $number' : 'Korekta wcześniejszej zmiany',
      message:
          'Ta zmiana koryguje zamrożoną zmianę${known ? ' $number' : ''}. '
          'Pola skopiowano z oryginału — popraw to, czego dotyczy korekta, '
          'wyznacz okno serwisowe i wyślij do zatwierdzenia. Oryginał '
          'pozostaje bez zmian.',
      actions: [
        if (known)
          OutlinedButton(
            key: const ValueKey('correction-original'),
            onPressed: () => context.go('/c/$prefix/changes/$number'),
            child: const Text('Otwórz oryginał'),
          ),
      ],
    );
  }
}
