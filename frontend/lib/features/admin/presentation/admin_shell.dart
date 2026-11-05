import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';

/// Tabs of "Spółki i słowniki" (§10.4); each tab is its own URL.
enum AdminTab {
  companies('/admin/companies', 'Spółki'),
  categories('/admin/categories', 'Kategorie zmian'),
  ciTypes('/admin/ci-types', 'Typy obiektów (CI)'),
  permissions('/admin/permissions', 'Role i uprawnienia');

  const AdminTab(this.path, this.label);

  final String path;
  final String label;
}

/// Admin screens are for the app admin only (§5). Others see "Brak dostępu"
/// — the API would answer 403 anyway; the screen does not even ask it.
class AdminGate extends ConsumerWidget {
  const AdminGate({required this.builder, super.key});

  final Widget Function(BuildContext context, Me me) builder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    return switch (me) {
      AsyncData(:final value) when value.isAppAdmin => builder(context, value),
      AsyncData() => const NoAccessPanel(
        message:
            'Ten ekran jest dostępny wyłącznie dla administratora aplikacji.',
      ),
      AsyncError(:final error) => PageBody(
        children: [
          ErrorPanel(error: error, onRetry: () => ref.invalidate(meProvider)),
        ],
      ),
      _ => const LoadingPanel(),
    };
  }
}

/// "Brak dostępu" page body.
class NoAccessPanel extends StatelessWidget {
  const NoAccessPanel({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) => PageBody(
    children: [
      MessageBanner(
        key: const ValueKey('no-access'),
        kind: BannerKind.warning,
        title: 'Brak dostępu',
        message: message,
      ),
    ],
  );
}

/// Page frame of the admin tabs: header + tab bar + content.
class AdminTabsFrame extends StatelessWidget {
  const AdminTabsFrame({
    required this.tab,
    required this.children,
    this.actions = const [],
    super.key,
  });

  final AdminTab tab;
  final List<Widget> actions;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return PageBody(
      children: [
        PageHeader(
          title: 'Spółki i słowniki',
          subtitle: 'Administracja',
          actions: actions,
        ),
        const SizedBox(height: 12),
        AdminTabBar(current: tab),
        const SizedBox(height: 16),
        ...children,
      ],
    );
  }
}

class AdminTabBar extends StatelessWidget {
  const AdminTabBar({required this.current, super.key});

  final AdminTab current;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final tab in AdminTab.values)
              _TabButton(
                key: ValueKey('admin-tab-${tab.name}'),
                label: tab.label,
                selected: tab == current,
                onTap: () => context.go(tab.path),
              ),
          ],
        ),
      ),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: InkWell(
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: AppSizes.minTouchTarget),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: selected ? AppColors.accent : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: selected ? AppColors.accent : AppColors.textSecondary,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}

/// Asks before discarding unsaved edits; true = discard.
Future<bool> confirmDiscard(BuildContext context) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('Odrzucić niezapisane zmiany?'),
      content: const Text(
        'Wprowadzone dane nie zostały zapisane i zostaną utracone.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Wróć do edycji'),
        ),
        FilledButton(
          key: const ValueKey('discard-confirm'),
          style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
          onPressed: () => Navigator.pop(context, true),
          child: const Text('Odrzuć zmiany'),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// Dialog with a form: Escape/back with unsaved edits asks first
/// ([confirmDiscard]); the barrier does not close it.
Future<T?> showFormDialog<T>(
  BuildContext context, {
  required Widget Function(BuildContext context) builder,
}) => showDialog<T>(
  context: context,
  barrierDismissible: false,
  builder: builder,
);

/// Wraps a form dialog body: popping with [dirty] edits asks first.
class GuardedDialog extends StatelessWidget {
  const GuardedDialog({required this.dirty, required this.child, super.key});

  final bool dirty;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return PopScope<Object?>(
      canPop: !dirty,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final navigator = Navigator.of(context);
        if (await confirmDiscard(context)) navigator.pop();
      },
      child: child,
    );
  }
}

/// Small yes/no label in tables.
class YesNo extends StatelessWidget {
  const YesNo(this.value, {this.yes = 'tak', this.no = 'nie', super.key});

  final bool value;
  final String yes;
  final String no;

  @override
  Widget build(BuildContext context) => Tag(
    label: value ? yes : no,
    colors: value ? AppFeedbackColors.info : AppFeedbackColors.neutral,
  );
}

/// "Aktywna" / "Nieaktywna" tag.
class ActiveTag extends StatelessWidget {
  const ActiveTag({
    required this.active,
    this.activeLabel = 'Aktywny',
    this.inactiveLabel = 'Nieaktywny',
    super.key,
  });

  final bool active;
  final String activeLabel;
  final String inactiveLabel;

  @override
  Widget build(BuildContext context) => Tag(
    label: active ? activeLabel : inactiveLabel,
    colors: active ? AppFeedbackColors.success : AppFeedbackColors.neutral,
  );
}
