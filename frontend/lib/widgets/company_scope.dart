import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/session.dart';
import '../features/admin/data/admin_api.dart';
import '../features/admin/presentation/admin_shell.dart';
import 'common.dart';
import 'company_gate.dart';

/// The company a screen works on: through a membership, or — for the app
/// admin without a role in it — through the explicit admin path of the API.
@immutable
class CompanyRef {
  const CompanyRef({
    required this.id,
    required this.name,
    required this.prefix,
    required this.archived,
    this.membership,
  });

  factory CompanyRef.ofMembership(Membership m) => CompanyRef(
    id: m.companyId,
    name: m.companyName,
    prefix: m.companyPrefix,
    archived: m.isArchived,
    membership: m,
  );

  final String id;
  final String name;
  final String prefix;
  final bool archived;
  final Membership? membership;

  /// The app admin without a role in the company (ADR 0015 §1).
  bool get adminPath => membership == null;

  /// Change register and card are read-only on the admin path (ADR 0016).
  bool get canEditChanges => !archived && (membership?.canEditChanges ?? false);
}

/// Like [CompanyGate], but lets the app admin into a company where he has
/// no role — only for screens the API serves on the admin path: CI
/// inventory, audit log (ADR 0015 §1) and the read-only change register and
/// card (ADR 0016). The change form stays behind [CompanyGate] (writes have
/// no admin path in the API).
class AdminAwareCompanyGate extends ConsumerWidget {
  const AdminAwareCompanyGate({
    required this.prefix,
    required this.section,
    required this.builder,
    super.key,
  });

  final String prefix;
  final String section;
  final Widget Function(BuildContext context, Me me, CompanyRef company)
  builder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider).value;
    if (me != null &&
        me.isAppAdmin &&
        prefix != allCompaniesPrefix &&
        me.membershipFor(prefix) == null) {
      return switch (ref.watch(adminCompaniesProvider)) {
        AsyncError(:final error) => PageBody(
          children: [
            ErrorPanel(
              error: error,
              onRetry: () => ref.invalidate(adminCompaniesProvider),
            ),
          ],
        ),
        AsyncData(:final value) => switch (value
            .where((c) => c.prefix == prefix)
            .firstOrNull) {
          null => const NoAccessPanel(message: 'Nie znaleziono spółki.'),
          final c => builder(
            context,
            me,
            CompanyRef(
              id: c.id,
              name: c.name,
              prefix: c.prefix,
              archived: c.isArchived,
            ),
          ),
        },
        _ => const LoadingPanel(),
      };
    }
    return CompanyGate(
      prefix: prefix,
      section: section,
      builder: (context, me, membership) =>
          builder(context, me, CompanyRef.ofMembership(membership)),
    );
  }
}

/// "Podgląd administratora — tylko odczyt": the change register and card of
/// a company where the app admin has no role (ADR 0016).
class AdminReadOnlyBanner extends StatelessWidget {
  const AdminReadOnlyBanner({super.key});

  static const String title = 'Podgląd administratora — tylko odczyt';

  @override
  Widget build(BuildContext context) {
    return const MessageBanner(
      key: ValueKey('admin-read-only'),
      title: title,
      message:
          'Nie masz roli w tej spółce. Bez tworzenia i edycji zmian, akcji, '
          'komentarzy i pobierania plików załączników (widać ich nazwy i '
          'skróty sha256). Eksport PDF i CSV jest dozwolony i trafia do '
          'dziennika audytu spółki. Aby pracować w rejestrze, nadaj sobie '
          'rolę w „Użytkownicy i role” — zostanie to zapisane w dzienniku '
          'audytu.',
    );
  }
}
