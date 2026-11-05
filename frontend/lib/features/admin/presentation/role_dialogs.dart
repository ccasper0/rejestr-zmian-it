import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../data/admin_api.dart';
import '../data/admin_models.dart';
import 'admin_shell.dart';

/// Membership roles in the order of the matrix columns (§5).
const List<String> membershipRoles = [
  Roles.approver,
  Roles.editor,
  Roles.auditor,
  Roles.viewer,
];

String roleHint(String role) => switch (role) {
  Roles.editor => 'Tworzy i edytuje zmiany, prowadzi inwentarz CI.',
  Roles.approver =>
    'Zatwierdza i odrzuca zmiany (nie własne), może też je tworzyć.',
  Roles.auditor =>
    'Przegląda rejestr i cały dziennik audytu, weryfikuje łańcuch, eksportuje.',
  Roles.viewer => 'Tylko podgląd rejestru i kart zmian.',
  _ => '',
};

/// Edits the FULL set of roles of [userName] in [companyName]; returns the
/// new set (sent as is in `PUT …/members/{user_id}`), null = cancelled.
///
/// [isSelf]: the admin edits their own roles — segregation of duties (§5):
/// allowed, but the grant is recorded in the audit log, so the dialog warns.
Future<List<String>?> showRoleEditor(
  BuildContext context, {
  required String companyName,
  required String userName,
  required List<String> current,
  bool isSelf = false,
  bool userActive = true,
}) => showFormDialog<List<String>>(
  context,
  builder: (context) => _RoleEditor(
    companyName: companyName,
    userName: userName,
    current: current,
    isSelf: isSelf,
    userActive: userActive,
  ),
);

class _RoleEditor extends StatefulWidget {
  const _RoleEditor({
    required this.companyName,
    required this.userName,
    required this.current,
    required this.isSelf,
    required this.userActive,
  });

  final String companyName;
  final String userName;
  final List<String> current;
  final bool isSelf;
  final bool userActive;

  @override
  State<_RoleEditor> createState() => _RoleEditorState();
}

class _RoleEditorState extends State<_RoleEditor> {
  late final Set<String> _roles = {...widget.current};

  bool get _dirty =>
      _roles.length != widget.current.length ||
      !_roles.containsAll(widget.current);

  List<String> get _granted => [
    for (final r in membershipRoles)
      if (_roles.contains(r) && !widget.current.contains(r)) r,
  ];

  @override
  Widget build(BuildContext context) {
    final granted = _granted;
    final blockedGrant = !widget.userActive && granted.isNotEmpty;
    return GuardedDialog(
      dirty: _dirty,
      child: AlertDialog(
        title: Text('Role: ${widget.userName}'),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Spółka: ${widget.companyName}',
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 8),
                for (final role in membershipRoles)
                  CheckboxListTile(
                    key: ValueKey('role-$role'),
                    value: _roles.contains(role),
                    controlAffinity: ListTileControlAffinity.leading,
                    contentPadding: EdgeInsets.zero,
                    title: Text(Roles.label(role)),
                    subtitle: Text(roleHint(role)),
                    onChanged: (checked) => setState(() {
                      if (checked ?? false) {
                        _roles.add(role);
                      } else {
                        _roles.remove(role);
                      }
                    }),
                  ),
                if (_roles.isEmpty && widget.current.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  const MessageBanner(
                    kind: BannerKind.warning,
                    message: 'Bez żadnej roli użytkownik straci dostęp do tej spółki.',
                  ),
                ],
                if (widget.isSelf && granted.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  const MessageBanner(
                    key: ValueKey('self-grant-warning'),
                    kind: BannerKind.warning,
                    title: 'Nadajesz rolę sobie',
                    message:
                        'Administrator nie jest automatycznie edytorem ani '
                        'zatwierdzającym (rozdział obowiązków). Nadanie roli '
                        'samemu sobie jest dozwolone, ale zostanie zapisane w '
                        'dzienniku audytu spółki jako samodzielne nadanie.',
                  ),
                ],
                if (blockedGrant) ...[
                  const SizedBox(height: 8),
                  const MessageBanner(
                    kind: BannerKind.error,
                    message:
                        'Użytkownik jest nieaktywny — nie można mu nadać nowej '
                        'roli (można tylko odebrać).',
                  ),
                ],
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.maybePop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('roles-save'),
            onPressed: !_dirty || blockedGrant
                ? null
                : () => Navigator.pop(context, [
                    for (final r in membershipRoles)
                      if (_roles.contains(r)) r,
                  ]),
            child: const Text('Zapisz role'),
          ),
        ],
      ),
    );
  }
}

/// Picks a user from the directory (`GET /users?q=`), e.g. a new member or
/// the default approver. [excludeIds] are not offered.
Future<UserAccount?> showUserPicker(
  BuildContext context, {
  required String title,
  Set<String> excludeIds = const {},
  bool activeOnly = true,
}) => showDialog<UserAccount>(
  context: context,
  builder: (context) =>
      _UserPicker(title: title, excludeIds: excludeIds, activeOnly: activeOnly),
);

class _UserPicker extends ConsumerStatefulWidget {
  const _UserPicker({
    required this.title,
    required this.excludeIds,
    required this.activeOnly,
  });

  final String title;
  final Set<String> excludeIds;
  final bool activeOnly;

  @override
  ConsumerState<_UserPicker> createState() => _UserPickerState();
}

class _UserPickerState extends ConsumerState<_UserPicker> {
  final _search = TextEditingController();
  Timer? _debounce;
  String _q = '';

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final page = ref.watch(usersPageProvider((_q, 1)));
    final users = [
      for (final u in page.value?.items ?? const <UserAccount>[])
        if (!widget.excludeIds.contains(u.id)) u,
    ];
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 460,
        height: 420,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const ValueKey('user-picker-search'),
              controller: _search,
              autofocus: true,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Szukaj: nazwisko lub e-mail',
                isDense: true,
              ),
              onChanged: (value) {
                _debounce?.cancel();
                _debounce = Timer(const Duration(milliseconds: 300), () {
                  if (mounted) setState(() => _q = value.trim());
                });
              },
            ),
            const SizedBox(height: 8),
            Expanded(
              child: switch (page) {
                AsyncError(:final error) => ErrorPanel(error: error),
                AsyncData() || AsyncLoading(hasValue: true) =>
                  users.isEmpty
                      ? const Center(
                          child: Text(
                            'Brak użytkowników spełniających kryteria.',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                        )
                      : ListView(
                          children: [
                            for (final user in users)
                              ListTile(
                                key: ValueKey('user-option-${user.id}'),
                                enabled: !widget.activeOnly || user.isActive,
                                title: Text(user.displayName),
                                subtitle: Text(
                                  user.isActive
                                      ? user.email
                                      : '${user.email} · nieaktywny',
                                ),
                                onTap: () => Navigator.pop(context, user),
                              ),
                          ],
                        ),
                _ => const LoadingPanel(),
              },
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Anuluj'),
        ),
      ],
    );
  }
}
