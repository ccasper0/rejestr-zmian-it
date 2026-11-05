import 'dart:async';

import 'package:data_table_2/data_table_2.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/auth.dart';
import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../../changes/data/changes_api.dart';
import '../data/admin_api.dart';
import '../data/admin_models.dart';
import 'account_dialogs.dart';
import 'admin_shell.dart';
import 'role_dialogs.dart';

/// After a change of an account: every view of the user directory.
void invalidateUserViews(WidgetRef ref, String userId) {
  ref
    ..invalidate(userDetailProvider(userId))
    ..invalidate(usersPageProvider)
    ..invalidate(userDirectoryProvider);
}

/// `/admin/users?q=&page=` — user directory (`GET /users`), search and page
/// in the URL; local accounts are created here (ADR 0018 §5).
class AdminUsersPage extends StatelessWidget {
  const AdminUsersPage({required this.q, required this.page, super.key});

  final String q;
  final int page;

  /// URL → (q, page); invalid page = 1.
  static (String, int) parse(Map<String, String> query) {
    final page = int.tryParse(query['page'] ?? '');
    return ((query['q'] ?? '').trim(), page != null && page > 0 ? page : 1);
  }

  static String location(String q, int page) {
    final query = {
      if (q.trim().isNotEmpty) 'q': q.trim(),
      if (page > 1) 'page': '$page',
    };
    return Uri(
      path: '/admin/users',
      queryParameters: query.isEmpty ? null : query,
    ).toString();
  }

  @override
  Widget build(BuildContext context) => AdminGate(
    builder: (context, me) => _UsersView(q: q, page: page),
  );
}

class _UsersView extends ConsumerStatefulWidget {
  const _UsersView({required this.q, required this.page});

  final String q;
  final int page;

  @override
  ConsumerState<_UsersView> createState() => _UsersViewState();
}

class _UsersViewState extends ConsumerState<_UsersView> {
  late final _search = TextEditingController(text: widget.q);
  Timer? _debounce;

  @override
  void didUpdateWidget(covariant _UsersView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.q != _search.text.trim() && _debounce == null) {
      _search.text = widget.q;
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      _debounce = null;
      if (value.trim() != widget.q) {
        context.go(AdminUsersPage.location(value, 1));
      }
    });
  }

  Future<void> _create() async {
    final created = await showCreateUserDialog(context);
    if (created == null || !mounted) return;
    ref
      ..invalidate(usersPageProvider)
      ..invalidate(userDirectoryProvider);
    await showTemporaryPasswordDialog(
      context,
      userName: created.user.displayName,
      email: created.user.email,
      temporaryPassword: created.temporaryPassword,
      reset: false,
      expiresAt: created.user.tempPasswordExpiresAt,
    );
  }

  @override
  Widget build(BuildContext context) {
    final page = ref.watch(usersPageProvider((widget.q, widget.page)));
    final now = ref.watch(clockProvider)();
    final rows = page.value?.items ?? const <UserAccount>[];
    final total = page.value?.total;
    final pages = total == null
        ? 1
        : ((total + usersPageSize - 1) ~/ usersPageSize).clamp(1, 1 << 30);
    return PageBody(
      children: [
        PageHeader(
          title: 'Użytkownicy i role',
          subtitle: 'Administracja',
          actions: [
            IconButton(
              tooltip: 'Odśwież',
              onPressed: () =>
                  ref.invalidate(usersPageProvider((widget.q, widget.page))),
              icon: const Icon(Icons.refresh),
            ),
            FilledButton.icon(
              key: const ValueKey('user-create'),
              onPressed: _create,
              icon: const Icon(Icons.person_add_alt_1_outlined),
              label: const Text('Nowy użytkownik'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Konta lokalne (e-mail i hasło) zakłada administrator; hasło '
          'tymczasowe jest pokazywane tylko raz. Wybierz osobę, aby zarządzać '
          'kontem i jej rolami w spółkach.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: 360,
          child: TextField(
            key: const ValueKey('users-search'),
            controller: _search,
            onChanged: _onSearch,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Szukaj: nazwisko, e-mail, identyfikator',
              isDense: true,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              switch (page) {
                AsyncError(:final error) => Padding(
                  padding: const EdgeInsets.all(16),
                  child: ErrorPanel(
                    error: error,
                    onRetry: () => ref.invalidate(
                      usersPageProvider((widget.q, widget.page)),
                    ),
                  ),
                ),
                AsyncData() || AsyncLoading(hasValue: true) => SizedBox(
                  height: rows.isEmpty ? 160 : 48 + rows.length * 64 + 8,
                  child: DataTable2(
                    key: const ValueKey('users-table'),
                    minWidth: 820,
                    headingRowHeight: 48,
                    dataRowHeight: 64,
                    columnSpacing: 12,
                    horizontalMargin: 12,
                    showCheckboxColumn: false,
                    headingTextStyle: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                    empty: const Center(
                      child: Text(
                        'Brak użytkowników spełniających kryteria.',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    ),
                    columns: const [
                      DataColumn2(
                        label: Text('Użytkownik'),
                        size: ColumnSize.L,
                      ),
                      DataColumn2(label: Text('E-mail'), size: ColumnSize.L),
                      DataColumn2(
                        label: Text('Stan konta'),
                        size: ColumnSize.L,
                      ),
                    ],
                    rows: [
                      for (final user in rows)
                        DataRow2(
                          key: ValueKey('user-row-${user.id}'),
                          onTap: () => context.go(
                            '/admin/users/${Uri.encodeComponent(user.id)}',
                          ),
                          cells: [
                            DataCell(Text(user.displayName)),
                            DataCell(
                              Text(
                                user.email,
                                style: AppFonts.monoStyle(fontSize: 13),
                              ),
                            ),
                            DataCell(
                              AccountStateTags(
                                key: ValueKey('user-state-${user.id}'),
                                account: user,
                                now: now,
                                isAppAdmin: user.isAppAdmin,
                              ),
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
                _ => const LoadingPanel(),
              },
              const Divider(),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 6,
                ),
                child: Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      total == null ? 'Wczytywanie…' : 'Użytkowników: $total',
                    ),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        IconButton(
                          tooltip: 'Poprzednia strona',
                          onPressed: widget.page > 1
                              ? () => context.go(
                                  AdminUsersPage.location(
                                    widget.q,
                                    widget.page - 1,
                                  ),
                                )
                              : null,
                          icon: const Icon(Icons.chevron_left),
                        ),
                        Text(
                          'Strona ${widget.page} z $pages',
                          style: AppFonts.monoStyle(fontSize: 13),
                        ),
                        IconButton(
                          tooltip: 'Następna strona',
                          onPressed: widget.page < pages
                              ? () => context.go(
                                  AdminUsersPage.location(
                                    widget.q,
                                    widget.page + 1,
                                  ),
                                )
                              : null,
                          icon: const Icon(Icons.chevron_right),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// `/admin/users/:userId` — one user with roles in every company; roles are
/// edited per company as a FULL set (`PUT /companies/{id}/members/{user}`).
class AdminUserDetailPage extends StatelessWidget {
  const AdminUserDetailPage({required this.userId, super.key});

  final String userId;

  @override
  Widget build(BuildContext context) => AdminGate(
    builder: (context, me) => _UserDetailView(userId: userId, me: me),
  );
}

class _UserDetailView extends ConsumerWidget {
  const _UserDetailView({required this.userId, required this.me});

  final String userId;
  final Me me;

  Future<void> _editRoles(
    BuildContext context,
    WidgetRef ref,
    UserDetail user, {
    required String companyId,
    required String companyName,
    required List<String> current,
  }) async {
    final roles = await showRoleEditor(
      context,
      companyName: companyName,
      userName: user.displayName,
      current: current,
      isSelf: user.id == me.id,
      userActive: user.isActive,
    );
    if (roles == null || !context.mounted) return;
    try {
      await ref
          .read(adminApiProvider)
          .setMemberRoles(companyId, user.id, roles);
      ref.invalidate(userDetailProvider(user.id));
      ref.invalidate(membersProvider(companyId));
      ref.invalidate(adminCompaniesProvider);
      if (user.id == me.id) ref.invalidate(meProvider);
      if (context.mounted) {
        showInfoSnack(context, 'Zapisano role w spółce $companyName.');
      }
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  Future<void> _addCompany(
    BuildContext context,
    WidgetRef ref,
    UserDetail user,
  ) async {
    final companies = await ref.read(adminCompaniesProvider.future);
    if (!context.mounted) return;
    final member = {for (final m in user.memberships) m.companyId};
    final candidates = [
      for (final c in companies)
        if (!member.contains(c.id)) c,
    ];
    final company = await showDialog<AdminCompany>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Nadaj rolę w spółce'),
        children: [
          if (candidates.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Użytkownik ma już rolę we wszystkich spółkach.'),
            ),
          for (final c in candidates)
            SimpleDialogOption(
              key: ValueKey('pick-company-${c.prefix}'),
              onPressed: () => Navigator.pop(context, c),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Text(
                  '${c.name} (${c.prefix})'
                  '${c.isArchived ? ' — zarchiwizowana' : ''}',
                ),
              ),
            ),
        ],
      ),
    );
    if (company == null || !context.mounted) return;
    await _editRoles(
      context,
      ref,
      user,
      companyId: company.id,
      companyName: company.name,
      current: const [],
    );
  }

  Future<void> _patch(
    BuildContext context,
    WidgetRef ref,
    UserDetail user, {
    String? displayName,
    bool? isActive,
    bool? isAppAdmin,
    required String done,
  }) async {
    try {
      await ref
          .read(adminApiProvider)
          .updateUser(
            user.id,
            displayName: displayName,
            isActive: isActive,
            isAppAdmin: isAppAdmin,
          );
      invalidateUserViews(ref, user.id);
      if (context.mounted) showInfoSnack(context, done);
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  Future<void> _rename(
    BuildContext context,
    WidgetRef ref,
    UserDetail user,
  ) async {
    final name = await showEditNameDialog(context, current: user.displayName);
    if (name == null || !context.mounted) return;
    await _patch(
      context,
      ref,
      user,
      displayName: name,
      done: 'Zapisano nazwę użytkownika.',
    );
  }

  Future<void> _setActive(
    BuildContext context,
    WidgetRef ref,
    UserDetail user,
    bool active,
  ) async {
    if (!active &&
        !await confirmAccountAction(
          context,
          title: 'Dezaktywować konto?',
          message:
              '${user.displayName} (${user.email}) zostanie natychmiast '
              'wylogowany ze wszystkich sesji i nie będzie mógł się '
              'zalogować. Role w spółkach pozostaną zapisane, ale '
              'nieaktywnemu użytkownikowi nie można nadawać nowych. Konto '
              'można później aktywować ponownie.',
          confirmLabel: 'Dezaktywuj',
        )) {
      return;
    }
    if (!context.mounted) return;
    await _patch(
      context,
      ref,
      user,
      isActive: active,
      done: active ? 'Konto aktywowano.' : 'Konto dezaktywowano.',
    );
  }

  Future<void> _setAdmin(
    BuildContext context,
    WidgetRef ref,
    UserDetail user,
    bool admin,
  ) async {
    final confirmed = await confirmAccountAction(
      context,
      title: admin
          ? 'Nadać uprawnienia administratora?'
          : 'Odebrać uprawnienia administratora?',
      message: admin
          ? '${user.displayName} będzie zarządzać spółkami, słownikami, '
                'użytkownikami i rolami. Uprawnienia administratora nie dają '
                'ról w spółkach.'
          : '${user.displayName} straci dostęp do administracji aplikacji '
                '(spółki, słowniki, użytkownicy i role). Role w spółkach '
                'pozostaną bez zmian.',
      confirmLabel: admin ? 'Nadaj uprawnienia' : 'Odbierz uprawnienia',
      danger: !admin,
    );
    if (!confirmed || !context.mounted) return;
    await _patch(
      context,
      ref,
      user,
      isAppAdmin: admin,
      done: admin
          ? 'Nadano uprawnienia administratora.'
          : 'Odebrano uprawnienia administratora.',
    );
  }

  Future<void> _resetPassword(
    BuildContext context,
    WidgetRef ref,
    UserDetail user,
  ) async {
    final confirmed = await confirmAccountAction(
      context,
      title: 'Zresetować hasło?',
      message:
          'Dla ${user.displayName} zostanie wygenerowane nowe hasło '
          'tymczasowe. Obecne hasło przestanie działać, wszystkie sesje '
          'użytkownika zostaną zakończone, a blokada konta zdjęta.',
      confirmLabel: 'Resetuj hasło',
    );
    if (!confirmed || !context.mounted) return;
    try {
      final result = await ref.read(adminApiProvider).resetPassword(user.id);
      invalidateUserViews(ref, user.id);
      if (!context.mounted) return;
      await showTemporaryPasswordDialog(
        context,
        userName: result.user.displayName,
        email: result.user.email,
        temporaryPassword: result.temporaryPassword,
        reset: true,
        expiresAt: result.user.tempPasswordExpiresAt,
      );
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(userDetailProvider(userId));
    final now = ref.watch(clockProvider)();
    final back = TextButton.icon(
      onPressed: () => context.go('/admin/users'),
      icon: const Icon(Icons.arrow_back),
      label: const Text('Użytkownicy i role'),
    );
    return switch (detail) {
      AsyncError(:final error) => PageBody(
        children: [
          Align(alignment: Alignment.centerLeft, child: back),
          ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(userDetailProvider(userId)),
          ),
        ],
      ),
      AsyncData(:final value) => PageBody(
        maxWidth: 1100,
        children: [
          PageHeader(
            leading: back,
            title: value.displayName,
            subtitle: value.email,
            actions: [
              OutlinedButton.icon(
                key: const ValueKey('user-add-company'),
                onPressed: () => _addCompany(context, ref, value),
                icon: const Icon(Icons.add),
                label: const Text('Nadaj rolę w spółce'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              ActiveTag(active: value.isActive),
              if (value.isAppAdmin)
                const Tag(
                  label: 'Administrator',
                  colors: AppFeedbackColors.info,
                ),
              Tag(label: value.externalId, mono: true),
            ],
          ),
          const SizedBox(height: 16),
          _AccountSection(
            user: value,
            isSelf: value.id == me.id,
            now: now,
            onRename: () => _rename(context, ref, value),
            onResetPassword: () => _resetPassword(context, ref, value),
            onSetActive: (active) => _setActive(context, ref, value, active),
            onSetAdmin: (admin) => _setAdmin(context, ref, value, admin),
          ),
          if (!value.isActive) ...[
            const SizedBox(height: 12),
            const MessageBanner(
              kind: BannerKind.warning,
              message:
                  'Konto jest nieaktywne — można tylko odbierać role, nie '
                  'nadawać nowych.',
            ),
          ],
          if (value.id == me.id) ...[
            const SizedBox(height: 12),
            const MessageBanner(
              kind: BannerKind.warning,
              message:
                  'To Twoje konto. Nadanie sobie roli w spółce jest '
                  'dozwolone, ale narusza domyślny rozdział obowiązków i '
                  'zostanie zapisane w dzienniku audytu.',
            ),
          ],
          const SizedBox(height: 16),
          SectionCard(
            title: 'Role w spółkach',
            child: value.memberships.isEmpty
                ? const Text(
                    'Brak ról w spółkach.',
                    style: TextStyle(color: AppColors.textSecondary),
                  )
                : Column(
                    children: [
                      for (final m in value.memberships)
                        ListTile(
                          key: ValueKey('membership-${m.companyPrefix}'),
                          contentPadding: EdgeInsets.zero,
                          title: Text.rich(
                            TextSpan(
                              children: [
                                TextSpan(text: m.companyName),
                                TextSpan(
                                  text: '  ${m.companyPrefix}',
                                  style: AppFonts.monoStyle(
                                    fontSize: 13,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                                if (m.isArchived)
                                  const TextSpan(
                                    text: '  (zarchiwizowana)',
                                    style: TextStyle(
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          subtitle: Wrap(
                            spacing: 4,
                            runSpacing: 4,
                            children: [
                              for (final role in membershipRoles)
                                if (m.roles.contains(role))
                                  Tag(label: Roles.label(role)),
                            ],
                          ),
                          trailing: TextButton(
                            key: ValueKey('edit-roles-${m.companyPrefix}'),
                            onPressed: () => _editRoles(
                              context,
                              ref,
                              value,
                              companyId: m.companyId,
                              companyName: m.companyName,
                              current: m.roles,
                            ),
                            child: const Text('Zmień role'),
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
      _ => const LoadingPanel(),
    };
  }
}

/// "Konto": password state and the account actions (ADR 0018 §5). The
/// admin's own account: no reset (own password — user menu), no
/// deactivation and no removal of the admin role (409 in the API anyway).
class _AccountSection extends StatelessWidget {
  const _AccountSection({
    required this.user,
    required this.isSelf,
    required this.now,
    required this.onRename,
    required this.onResetPassword,
    required this.onSetActive,
    required this.onSetAdmin,
  });

  final UserDetail user;
  final bool isSelf;
  final DateTime now;
  final VoidCallback onRename;
  final VoidCallback onResetPassword;
  final ValueChanged<bool> onSetActive;
  final ValueChanged<bool> onSetAdmin;

  @override
  Widget build(BuildContext context) {
    final changedAt = user.passwordChangedAt;
    return SectionCard(
      title: 'Konto',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AccountStateTags(
            key: const ValueKey('account-state'),
            account: user,
            now: now,
          ),
          const SizedBox(height: 8),
          Text.rich(
            TextSpan(
              children: [
                const TextSpan(text: 'Hasło zmienione: '),
                TextSpan(
                  text: changedAt == null ? '—' : WarsawTime.format(changedAt),
                  style: AppFonts.monoStyle(fontSize: 13),
                ),
              ],
            ),
            style: const TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                key: const ValueKey('user-rename'),
                onPressed: onRename,
                icon: const Icon(Icons.edit_outlined, size: 18),
                label: const Text('Zmień nazwę'),
              ),
              OutlinedButton.icon(
                key: const ValueKey('user-reset-password'),
                onPressed: isSelf ? null : onResetPassword,
                icon: const Icon(Icons.lock_reset_outlined, size: 18),
                label: Text(
                  user.hasPassword ? 'Resetuj hasło' : 'Nadaj hasło tymczasowe',
                ),
              ),
              if (user.isActive)
                OutlinedButton.icon(
                  key: const ValueKey('user-deactivate'),
                  onPressed: isSelf ? null : () => onSetActive(false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                  ),
                  icon: const Icon(Icons.person_off_outlined, size: 18),
                  label: const Text('Dezaktywuj'),
                )
              else
                OutlinedButton.icon(
                  key: const ValueKey('user-activate'),
                  onPressed: () => onSetActive(true),
                  icon: const Icon(Icons.person_outline, size: 18),
                  label: const Text('Aktywuj'),
                ),
              if (user.isAppAdmin)
                OutlinedButton.icon(
                  key: const ValueKey('user-revoke-admin'),
                  onPressed: isSelf ? null : () => onSetAdmin(false),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                  ),
                  icon: const Icon(Icons.remove_moderator_outlined, size: 18),
                  label: const Text('Odbierz uprawnienia administratora'),
                )
              else
                OutlinedButton.icon(
                  key: const ValueKey('user-grant-admin'),
                  onPressed: user.isActive ? () => onSetAdmin(true) : null,
                  icon: const Icon(
                    Icons.admin_panel_settings_outlined,
                    size: 18,
                  ),
                  label: const Text('Nadaj uprawnienia administratora'),
                ),
            ],
          ),
          if (isSelf) ...[
            const SizedBox(height: 8),
            const Text(
              'Własnego konta nie dezaktywujesz i nie odbierzesz sobie '
              'uprawnień administratora; własne hasło zmienisz w menu konta '
              '(na dole panelu nawigacji).',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }
}
