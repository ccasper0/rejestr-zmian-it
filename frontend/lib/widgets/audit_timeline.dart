import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../core/time.dart';
import '../features/changes/data/models.dart';
import '../features/changes/presentation/labels.dart';
import 'common.dart';

/// Audit trail of a change (§10.2): timestamp + IP (mono), who (role) —
/// action, diff "before → after", comment, sha256 of the entry.
class AuditTimeline extends StatelessWidget {
  const AuditTimeline({required this.entries, required this.names, super.key});

  final List<AuditEntry> entries;
  final NameResolver names;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const Text(
        'Brak wpisów w dzienniku audytu.',
        style: TextStyle(color: AppColors.textSecondary),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < entries.length; i++)
          _AuditEntryTile(
            entry: entries[i],
            names: names,
            last: i == entries.length - 1,
          ),
      ],
    );
  }
}

class _AuditEntryTile extends StatelessWidget {
  const _AuditEntryTile({
    required this.entry,
    required this.names,
    required this.last,
  });

  final AuditEntry entry;
  final NameResolver names;
  final bool last;

  @override
  Widget build(BuildContext context) {
    final comment = entry.context['comment'];
    final warnings = [
      for (final w in (entry.context['warnings'] as List<Object?>? ?? const []))
        if (w is Map && w['message_pl'] is String) w['message_pl'] as String,
    ];
    // Rows with a value on either side (an empty list counts as no value).
    Object? value(Object? v) => v is List && v.isEmpty ? null : v;
    final diff = [
      for (final e in entry.diff.entries)
        if (e.value is Map &&
            (value((e.value as Map)['before']) != null ||
                value((e.value as Map)['after']) != null))
          (
            e.key,
            value((e.value as Map)['before']),
            value((e.value as Map)['after']),
          ),
    ];
    final meta = AppFonts.monoStyle(
      fontSize: 12,
      color: AppColors.textSecondary,
    );

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 20,
            child: Column(
              children: [
                const SizedBox(height: 4),
                DecoratedBox(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: entry.hashValid
                        ? AppColors.accent
                        : AppColors.diffRemoved,
                  ),
                  child: const SizedBox.square(dimension: 10),
                ),
                if (!last)
                  const Expanded(
                    child: VerticalDivider(width: 10, color: AppColors.border),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${WarsawTime.format(entry.occurredAt)} · '
                    'IP ${entry.ipAddress ?? '—'}',
                    style: meta,
                  ),
                  const SizedBox(height: 2),
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: auditActor(entry),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        TextSpan(text: ' — ${auditActionPhrase(entry)}'),
                      ],
                    ),
                  ),
                  if (diff.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    _DiffBox(rows: diff, names: names),
                  ],
                  if (comment is String && comment.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      '„$comment”',
                      style: const TextStyle(fontStyle: FontStyle.italic),
                    ),
                  ],
                  for (final warning in warnings) ...[
                    const SizedBox(height: 6),
                    Tag(
                      label: warning,
                      colors: AppFeedbackColors.warning,
                      icon: Icons.warning_amber_outlined,
                    ),
                  ],
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Tooltip(
                        message:
                            'sha256 wpisu: ${entry.hash}\n'
                            'poprzedni: ${entry.prevHash}',
                        child: Text(
                          '#${entry.seq} · sha256 ${_short(entry.hash)}',
                          style: meta,
                        ),
                      ),
                      if (!entry.hashValid)
                        const Tag(
                          label: 'Skrót niezgodny z treścią wpisu',
                          colors: AppFeedbackColors.error,
                          icon: Icons.gpp_bad_outlined,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  static String _short(String hash) =>
      hash.length > 12 ? '${hash.substring(0, 12)}…' : hash;
}

class _DiffBox extends StatelessWidget {
  const _DiffBox({required this.rows, required this.names});

  final List<(String, Object?, Object?)> rows;
  final NameResolver names;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: AppRadii.smallAll,
        border: Border.all(color: AppColors.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final (field, before, after) in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: DiffLine(
                  field: field,
                  before: before == null ? null : names.value(field, before),
                  after: after == null ? null : names.value(field, after),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// "Pole: ~~stara~~ → nowa" (old value struck through in red, new in green).
class DiffLine extends StatelessWidget {
  const DiffLine({
    required this.field,
    required this.before,
    required this.after,
    this.label,
    this.mono,
    super.key,
  });

  final String field;
  final String? before;
  final String? after;

  /// Polish label (default: [fieldLabel] of [field]).
  final String? label;

  /// Mono font for the values (default: [isMonoField] of [field]).
  final bool? mono;

  @override
  Widget build(BuildContext context) {
    final family = (mono ?? isMonoField(field)) ? AppFonts.mono : AppFonts.sans;
    return Text.rich(
      TextSpan(
        style: const TextStyle(fontSize: 13),
        children: [
          TextSpan(
            text: '${label ?? fieldLabel(field)}: ',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
          if (before != null)
            TextSpan(
              text: before,
              semanticsLabel: 'przed: $before',
              style: TextStyle(
                fontFamily: family,
                color: AppColors.diffRemoved,
                backgroundColor: AppColors.diffRemovedBackground,
                decoration: TextDecoration.lineThrough,
                decorationColor: AppColors.diffRemoved,
              ),
            ),
          if (before != null && after != null) const TextSpan(text: ' → '),
          if (after != null)
            TextSpan(
              text: after,
              semanticsLabel: 'po: $after',
              style: TextStyle(
                fontFamily: family,
                color: AppColors.diffAdded,
                backgroundColor: AppColors.diffAddedBackground,
              ),
            ),
          if (before == null && after == null) const TextSpan(text: '—'),
        ],
      ),
    );
  }
}

/// "Łańcuch spójny" badge from `GET /companies/{cid}/audit/status`.
class ChainStatusBadge extends StatelessWidget {
  const ChainStatusBadge({required this.status, super.key});

  final ChainStatus status;

  @override
  Widget build(BuildContext context) {
    final checked = status.checkedAt == null
        ? null
        : 'sprawdzono ${WarsawTime.format(status.checkedAt)}';
    final (
      String label,
      StatusColors colors,
      IconData icon,
      String tip,
    ) = switch (status.status) {
      'ok' => (
        'Łańcuch spójny',
        AppFeedbackColors.success,
        Icons.verified_outlined,
        'Ostatnia weryfikacja łańcucha audytu spółki potwierdziła jego '
            'spójność, a nowsze wpisy są spójne.',
      ),
      'broken' => (
        'Łańcuch naruszony',
        AppFeedbackColors.error,
        Icons.gpp_bad_outlined,
        'Weryfikacja wykryła naruszenie łańcucha audytu. Powiadom audytora '
            'lub administratora.',
      ),
      'stale' => (
        'Weryfikacja nieaktualna',
        AppFeedbackColors.warning,
        Icons.history_toggle_off,
        'Ostatnia weryfikacja łańcucha jest zbyt stara lub od niej '
            'dopisano zbyt wiele wpisów — brak aktualnego potwierdzenia.',
      ),
      _ => (
        'Łańcuch niezweryfikowany',
        AppFeedbackColors.neutral,
        Icons.help_outline,
        'Łańcuch audytu tej spółki nie był jeszcze weryfikowany.',
      ),
    };
    return Tooltip(
      message: checked == null ? tip : '$tip\n${_cap(checked)}.',
      child: Wrap(
        spacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Tag(label: label, colors: colors, icon: icon),
          if (checked != null)
            Text(
              checked,
              style: AppFonts.monoStyle(
                fontSize: 12,
                color: AppColors.textSecondary,
              ),
            ),
        ],
      ),
    );
  }

  static String _cap(String s) => s[0].toUpperCase() + s.substring(1);
}
