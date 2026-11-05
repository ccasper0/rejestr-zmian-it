import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../app/router.dart' show changePasswordPath, signOutToLogin;
import '../core/auth/auth.dart';
import '../core/session.dart';
import '../core/theme.dart';
import '../features/admin/data/admin_api.dart';
import '../features/changes/data/changes_api.dart';
import 'api_health_indicator.dart';
import 'company_switcher.dart';

/// Extracts the company prefix from a path like `/c/ALFA/changes`.
String? companyPrefixFromPath(String path) {
  final segments = Uri.parse(path).pathSegments;
  if (segments.length >= 2 && segments.first == 'c') return segments[1];
  return null;
}

/// Company-scoped section, i.e. the part after `/c/{prefix}/`.
String companySectionFromPath(String path) {
  final segments = Uri.parse(path).pathSegments;
  if (segments.length >= 3 && segments.first == 'c') return segments[2];
  return 'changes';
}

/// Common layout: dark side navigation panel (wide screens) or app bar with
/// drawer (narrow screens, < [AppSizes.wideLayoutBreakpoint]).
class AppShell extends ConsumerWidget {
  const AppShell({required this.location, required this.child, super.key});

  /// Current URL path (e.g. `/c/ALFA/changes`).
  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefix = companyPrefixFromPath(location);
    final isWide =
        MediaQuery.sizeOf(context).width >= AppSizes.wideLayoutBreakpoint;

    if (isWide) {
      return Scaffold(
        body: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              width: AppSizes.sidebarWidth,
              child: NavigationPanel(location: location),
            ),
            Expanded(child: child),
          ],
        ),
      );
    }

    final me = ref.watch(meProvider).value;
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 56,
        title: Row(
          children: [
            const Flexible(
              child: Text(
                'Rejestr zmian IT',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
              ),
            ),
            if (prefix != null) ...[
              const SizedBox(width: 12),
              Flexible(
                child: Text(
                  companyLabel(me, prefix),
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.sidebarTextMuted,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      drawer: Drawer(
        shape: const RoundedRectangleBorder(),
        child: Builder(
          builder: (drawerContext) => NavigationPanel(
            location: location,
            onNavigated: () => Scaffold.of(drawerContext).closeDrawer(),
          ),
        ),
      ),
      body: child,
    );
  }
}

/// Content of the dark side panel (also used inside the drawer).
class NavigationPanel extends ConsumerWidget {
  const NavigationPanel({required this.location, this.onNavigated, super.key});

  final String location;

  /// Called after a navigation (used to close the drawer).
  final VoidCallback? onNavigated;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider).value;
    final urlPrefix = companyPrefixFromPath(location);
    // Admin pages are not company-scoped; links use the first company.
    final membership = me?.membershipFor(urlPrefix);
    final adminFirst = me != null && me.isAppAdmin && me.memberships.isEmpty
        ? ref.watch(adminCompaniesProvider).value?.firstOrNull?.prefix
        : null;
    final prefix =
        urlPrefix ??
        (me != null && me.memberships.isNotEmpty
            ? me.memberships.first.companyPrefix
            : adminFirst ?? allCompaniesPrefix);
    // The app admin without a role in the linked company reads its register
    // only (ADR 0016): the approver's work queue is not offered.
    final adminPath =
        me != null &&
        me.isAppAdmin &&
        prefix != allCompaniesPrefix &&
        me.membershipFor(prefix) == null;
    final pendingCount = membership == null
        ? null
        : ref.watch(statsProvider(membership.companyId)).value?.pendingApproval;

    void go(String path) {
      context.go(path);
      onNavigated?.call();
    }

    final companyLinks = [
      (Icons.list_alt_outlined, 'Rejestr zmian', 'changes', null),
      if (!adminPath)
        (
          Icons.fact_check_outlined,
          'Do zatwierdzenia',
          'approvals',
          pendingCount,
        ),
      (Icons.dns_outlined, 'Obiekty (CI)', 'ci', null),
      (Icons.picture_as_pdf_outlined, 'Raporty i eksport', 'reports', null),
      (Icons.history_outlined, 'Dziennik audytu', 'audit', null),
    ];

    return ColoredBox(
      color: AppColors.sidebar,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _Logo(),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
              child: CompanySwitcher(
                selectedPrefix: urlPrefix,
                onSelected: (newPrefix) {
                  final section = companySectionFromPath(location);
                  go('/c/$newPrefix/$section');
                },
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                children: [
                  for (final (icon, label, section, badge) in companyLinks)
                    NavLink(
                      icon: icon,
                      label: label,
                      badge: badge,
                      selected:
                          (urlPrefix != null &&
                              companySectionFromPath(location) == section) ||
                          // The global audit chain (app admin) lives under /admin.
                          (section == 'audit' &&
                              location.startsWith('/admin/audit')),
                      onTap: () => go('/c/$prefix/$section'),
                    ),
                  if (me?.isAppAdmin ?? false) ...[
                    const _SectionHeader('Administracja'),
                    NavLink(
                      icon: Icons.domain_outlined,
                      label: 'Spółki i słowniki',
                      selected:
                          location.startsWith('/admin/') &&
                          !location.startsWith('/admin/users') &&
                          !location.startsWith('/admin/audit'),
                      onTap: () => go('/admin/companies'),
                    ),
                    NavLink(
                      icon: Icons.manage_accounts_outlined,
                      label: 'Użytkownicy i role',
                      selected: location.startsWith('/admin/users'),
                      onTap: () => go('/admin/users'),
                    ),
                  ],
                ],
              ),
            ),
            const Divider(color: AppColors.sidebarDivider),
            const Padding(
              padding: EdgeInsets.fromLTRB(8, 4, 8, 0),
              child: ApiHealthIndicator(),
            ),
            _UserTile(
              name: me?.displayName ?? '…',
              role: me?.roleLabel(urlPrefix) ?? '',
              // Password change: local accounts only (dev users have none).
              onChangePassword:
                  ref.watch(
                    authControllerProvider.select(
                      (s) => s.token?.isLocalAccount ?? false,
                    ),
                  )
                  ? () {
                      context.go(
                        Uri(
                          path: changePasswordPath,
                          queryParameters: {'from': location},
                        ).toString(),
                      );
                      onNavigated?.call();
                    }
                  : null,
              onSignOut: () => signOutToLogin(context, ref),
            ),
          ],
        ),
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(16, 20, 16, 16),
      child: Row(
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              color: AppColors.accent,
              borderRadius: AppRadii.smallAll,
            ),
            child: SizedBox.square(
              dimension: 32,
              child: Icon(
                Icons.published_with_changes,
                size: 20,
                color: AppColors.onAccent,
              ),
            ),
          ),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Rejestr zmian IT',
              style: TextStyle(
                color: AppColors.sidebarText,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 20, 12, 6),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(
          color: AppColors.sidebarTextMuted,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

/// Single navigation entry; the active one is highlighted.
class NavLink extends StatelessWidget {
  const NavLink({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.badge,
    super.key,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final int? badge;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.onAccent : AppColors.sidebarText;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Semantics(
        selected: selected,
        button: true,
        child: Material(
          color: selected ? AppColors.sidebarActive : Colors.transparent,
          borderRadius: AppRadii.smallAll,
          child: InkWell(
            borderRadius: AppRadii.smallAll,
            hoverColor: AppColors.sidebarHover,
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                minHeight: AppSizes.minTouchTarget,
              ),
              child: Row(
                children: [
                  Container(
                    width: 3,
                    height: 20,
                    decoration: BoxDecoration(
                      color: selected
                          ? AppColors.sidebarActiveIndicator
                          : Colors.transparent,
                      borderRadius: const BorderRadius.horizontal(
                        right: Radius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(width: 9),
                  Icon(icon, size: 20, color: color),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: color,
                        fontSize: 14,
                        fontWeight: selected
                            ? FontWeight.w600
                            : FontWeight.w400,
                      ),
                    ),
                  ),
                  if (badge != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 10),
                      child: _CountBadge(count: badge!),
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

class _CountBadge extends StatelessWidget {
  const _CountBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.sidebarActive,
        borderRadius: BorderRadius.all(Radius.circular(999)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        child: Text(
          '$count',
          style: const TextStyle(
            fontFamily: AppFonts.mono,
            fontSize: 12,
            color: AppColors.sidebarText,
          ),
        ),
      ),
    );
  }
}

enum _UserMenuItem { changePassword, signOut }

class _UserTile extends StatelessWidget {
  const _UserTile({
    required this.name,
    required this.role,
    required this.onSignOut,
    this.onChangePassword,
  });

  final String name;
  final String role;
  final VoidCallback onSignOut;

  /// Null: the item is not offered (dev users have no password).
  final VoidCallback? onChangePassword;

  @override
  Widget build(BuildContext context) {
    final initials = name
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty)
        .take(2)
        .map((part) => part[0].toUpperCase())
        .join();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 4, 16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.accent,
            foregroundColor: AppColors.onAccent,
            child: Text(
              initials,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.sidebarText,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  role,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.sidebarTextMuted,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          PopupMenuButton<_UserMenuItem>(
            key: const ValueKey('user-menu'),
            tooltip: 'Menu konta',
            icon: const Icon(Icons.more_vert, color: AppColors.sidebarText),
            onSelected: (item) => switch (item) {
              _UserMenuItem.changePassword => onChangePassword?.call(),
              _UserMenuItem.signOut => onSignOut(),
            },
            itemBuilder: (context) => [
              if (onChangePassword != null)
                const PopupMenuItem(
                  key: ValueKey('change-password'),
                  value: _UserMenuItem.changePassword,
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.password_outlined),
                    title: Text('Zmień hasło'),
                  ),
                ),
              const PopupMenuItem(
                key: ValueKey('sign-out'),
                value: _UserMenuItem.signOut,
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.logout),
                  title: Text('Wyloguj'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
