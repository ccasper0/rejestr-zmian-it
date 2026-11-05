import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../../changes/presentation/labels.dart';
import '../data/admin_api.dart';
import '../data/admin_models.dart';
import 'admin_shell.dart';

/// `/admin/permissions` — the RBAC matrix, read-only, rendered from
/// `GET /permissions/matrix` (one source of truth: `app/permissions.py`).
class AdminPermissionsPage extends StatelessWidget {
  const AdminPermissionsPage({super.key});

  @override
  Widget build(BuildContext context) =>
      AdminGate(builder: (context, me) => const _PermissionsView());
}

class _PermissionsView extends ConsumerWidget {
  const _PermissionsView();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matrix = ref.watch(permissionMatrixProvider);
    return AdminTabsFrame(
      tab: AdminTab.permissions,
      children: [
        const MessageBanner(
          message:
              'Macierz jest tylko do odczytu — pochodzi z konfiguracji '
              'uprawnień serwera. Administrator aplikacji nie jest '
              'automatycznie edytorem ani zatwierdzającym w spółkach '
              '(rozdział obowiązków); role w spółkach nadaje się w module '
              '„Użytkownicy i role”.',
        ),
        const SizedBox(height: 16),
        switch (matrix) {
          AsyncError(:final error) => ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(permissionMatrixProvider),
          ),
          AsyncData(:final value) => _Matrix(matrix: value),
          _ => const LoadingPanel(),
        },
      ],
    );
  }
}

class _Matrix extends StatelessWidget {
  const _Matrix({required this.matrix});

  final PermissionMatrix matrix;

  @override
  Widget build(BuildContext context) {
    const header = TextStyle(
      fontWeight: FontWeight.w600,
      color: AppColors.textSecondary,
      fontSize: 13,
    );
    final labels = {for (final row in matrix.actions) row.action: row.label};
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          clipBehavior: Clip.antiAlias,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              key: const ValueKey('permission-matrix'),
              headingTextStyle: header,
              dataRowMinHeight: 52,
              // Notes can take several lines (e.g. register.view, ADR 0016).
              dataRowMaxHeight: double.infinity,
              columns: [
                const DataColumn(label: Text('Akcja')),
                for (final role in matrix.roles)
                  DataColumn(label: Text(Roles.label(role))),
              ],
              rows: [
                for (final row in matrix.actions)
                  DataRow(
                    key: ValueKey('matrix-${row.action}'),
                    cells: [
                      DataCell(
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 420),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(row.label),
                                if (row.note != null)
                                  Text(
                                    row.note!,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      for (final role in matrix.roles)
                        DataCell(
                          row.roles.contains(role)
                              ? const Icon(
                                  Icons.check,
                                  color: AppColors.accent,
                                  semanticLabel: 'tak',
                                )
                              : const Text(
                                  '—',
                                  semanticsLabel: 'nie',
                                  style: TextStyle(
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                        ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        if (matrix.changeActions.isNotEmpty) ...[
          const SizedBox(height: 16),
          SectionCard(
            title: 'Akcje na zmianie',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Każda akcja wymaga uprawnienia z macierzy; następnie '
                  'maszyna stanów sprawdza rolę na samej zmianie (autor, '
                  'wykonawca, wskazany zatwierdzający, zasada czterech oczu, '
                  'właściciel CI).',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 8),
                for (final rule in matrix.changeActions)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: ChangeActions.noun(rule.action),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          TextSpan(
                            text:
                                ' — ${labels[rule.requires] ?? rule.requires}',
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
