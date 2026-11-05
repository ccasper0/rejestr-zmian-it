import 'package:flutter/material.dart';

import '../core/api_error.dart';
import '../core/theme.dart';

/// Small rounded label (type, risk, chain status, roles).
class Tag extends StatelessWidget {
  const Tag({
    required this.label,
    this.colors = AppFeedbackColors.neutral,
    this.borderColor,
    this.icon,
    this.mono = false,
    this.tooltip,
    this.wrap = false,
    super.key,
  });

  /// Allow the label to wrap onto several lines instead of an ellipsis.
  final bool wrap;

  final String label;
  final StatusColors colors;
  final Color? borderColor;
  final IconData? icon;
  final bool mono;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final tag = DecoratedBox(
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: AppRadii.smallAll,
        border: borderColor == null
            ? null
            : Border.all(color: borderColor!, width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 14, color: colors.foreground),
              const SizedBox(width: 4),
            ],
            Flexible(
              child: Text(
                label,
                maxLines: wrap ? null : 1,
                overflow: wrap ? null : TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: mono ? AppFonts.mono : AppFonts.sans,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: colors.foreground,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      ),
    );
    return tooltip == null ? tag : Tooltip(message: tooltip, child: tag);
  }
}

/// White card with a title row (sections of the card and the form).
class SectionCard extends StatelessWidget {
  const SectionCard({
    required this.title,
    required this.child,
    this.trailing,
    this.padding = const EdgeInsets.all(20),
    super.key,
  });

  final String title;
  final Widget? trailing;
  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              alignment: WrapAlignment.spaceBetween,
              children: [
                Semantics(
                  header: true,
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                ?trailing,
              ],
            ),
            const SizedBox(height: 16),
            child,
          ],
        ),
      ),
    );
  }
}

enum BannerKind { info, success, warning, error }

/// Inline message box (warnings, errors, hints).
class MessageBanner extends StatelessWidget {
  const MessageBanner({
    required this.message,
    this.kind = BannerKind.info,
    this.title,
    this.details,
    this.actions = const [],
    super.key,
  });

  final BannerKind kind;
  final String? title;
  final String message;
  final String? details;
  final List<Widget> actions;

  StatusColors get _colors => switch (kind) {
    BannerKind.info => AppFeedbackColors.info,
    BannerKind.success => AppFeedbackColors.success,
    BannerKind.warning => AppFeedbackColors.warning,
    BannerKind.error => AppFeedbackColors.error,
  };

  IconData get _icon => switch (kind) {
    BannerKind.info => Icons.info_outline,
    BannerKind.success => Icons.check_circle_outline,
    BannerKind.warning => Icons.warning_amber_outlined,
    BannerKind.error => Icons.error_outline,
  };

  @override
  Widget build(BuildContext context) {
    final colors = _colors;
    return Semantics(
      liveRegion: kind == BannerKind.error,
      container: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: colors.background,
          borderRadius: AppRadii.mediumAll,
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(_icon, size: 20, color: colors.foreground),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (title != null)
                      Text(
                        title!,
                        style: TextStyle(
                          color: colors.foreground,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    Text(message, style: TextStyle(color: colors.foreground)),
                    if (details != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        details!,
                        style: TextStyle(
                          color: colors.foreground,
                          fontSize: 13,
                        ),
                      ),
                    ],
                    if (actions.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Wrap(spacing: 8, runSpacing: 8, children: actions),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Error of a failed load, in Polish, with an optional retry.
class ErrorPanel extends StatelessWidget {
  const ErrorPanel({required this.error, this.onRetry, super.key});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final problem = ApiProblem.from(error);
    return MessageBanner(
      kind: BannerKind.error,
      message: problem.message,
      details: [
        ?problem.detail,
        if (problem.requestId != null)
          'Identyfikator żądania: ${problem.requestId}',
      ].join('\n').ifNotEmpty,
      actions: [
        if (onRetry != null)
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Spróbuj ponownie'),
          ),
      ],
    );
  }
}

extension on String {
  String? get ifNotEmpty => isEmpty ? null : this;
}

class LoadingPanel extends StatelessWidget {
  const LoadingPanel({this.label = 'Wczytywanie…', super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox.square(
              dimension: 28,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
            const SizedBox(height: 12),
            Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }
}

/// Page frame: scrollable content with the standard padding and max width.
class PageBody extends StatelessWidget {
  const PageBody({required this.children, this.maxWidth = 1440, super.key});

  final List<Widget> children;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 600;
    return SelectionArea(
      child: ListView(
        padding: EdgeInsets.all(narrow ? 12 : 24),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: maxWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: children,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Page title with optional subtitle and trailing actions (wraps on narrow).
class PageHeader extends StatelessWidget {
  const PageHeader({
    required this.title,
    this.subtitle,
    this.actions = const [],
    this.leading,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Wrap(
      spacing: 16,
      runSpacing: 12,
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ?leading,
            Semantics(
              header: true,
              child: Text(
                title,
                style: textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: const TextStyle(color: AppColors.textSecondary),
              ),
          ],
        ),
        if (actions.isNotEmpty)
          Wrap(spacing: 8, runSpacing: 8, children: actions),
      ],
    );
  }
}

/// Shows an API error in a snackbar.
void showErrorSnack(BuildContext context, Object error) {
  final problem = ApiProblem.from(error);
  ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(problem.fullMessage)));
}

void showInfoSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}

/// Human-readable size (`1,2 MB`).
String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  const units = ['KB', 'MB', 'GB'];
  var value = bytes / 1024;
  var unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return '${value.toStringAsFixed(1).replaceAll('.', ',')} ${units[unit]}';
}
