import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/session.dart';
import '../core/theme.dart';
import 'common.dart';

/// Resolves the company prefix from the URL to the user's membership.
///
/// - `/me` loading or failed → progress / error,
/// - `all` → the auditor's cross-company view ([AllCompaniesView], ADR 0002),
/// - unknown prefix or no membership → "no access" (like the API's 404, it
///   does not reveal whether the company exists).
class CompanyGate extends ConsumerWidget {
  const CompanyGate({
    required this.prefix,
    required this.builder,
    this.section = 'changes',
    super.key,
  });

  final String prefix;
  final String section;
  final Widget Function(BuildContext context, Me me, Membership membership)
  builder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    return switch (me) {
      AsyncData(:final value) => _resolve(context, value),
      AsyncError(:final error) => PageBody(
        children: [
          ErrorPanel(error: error, onRetry: () => ref.invalidate(meProvider)),
        ],
      ),
      _ => const LoadingPanel(),
    };
  }

  Widget _resolve(BuildContext context, Me me) {
    if (prefix == allCompaniesPrefix) {
      return AllCompaniesView(me: me, section: section);
    }
    final membership = me.membershipFor(prefix);
    if (membership == null) {
      return PageBody(
        children: [
          MessageBanner(
            key: const ValueKey('no-access'),
            kind: BannerKind.warning,
            title: 'Brak dostępu',
            message: me.isAppAdmin
                // ADR 0016: the admin path to the register is read-only;
                // creating and editing changes needs a role (segregation of
                // duties).
                ? 'Administrator bez roli w spółce „$prefix” może tylko '
                      'przeglądać jej rejestr zmian — nie tworzy ani nie '
                      'edytuje zmian (rozdział obowiązków). Aby pracować w '
                      'rejestrze, nadaj sobie rolę w „Użytkownicy i role” — '
                      'zostanie to zapisane w dzienniku audytu.'
                : 'Spółka „$prefix” nie istnieje albo nie masz w niej żadnej '
                      'roli.',
            actions: [
              if (me.isAppAdmin)
                OutlinedButton(
                  key: const ValueKey('no-access-register'),
                  onPressed: () => context.go('/c/$prefix/changes'),
                  child: const Text('Przejdź do rejestru (tylko odczyt)'),
                )
              else if (me.memberships.isNotEmpty)
                OutlinedButton(
                  onPressed: () => context.go(
                    '/c/${me.memberships.first.companyPrefix}/changes',
                  ),
                  child: Text(
                    'Przejdź do: ${me.memberships.first.companyName}',
                  ),
                ),
            ],
          ),
        ],
      );
    }
    return builder(context, me, membership);
  }
}

/// `/c/all/...` — the auditor's cross-company view (ADR 0002).
///
/// The API has no cross-company register endpoint (only the auditor's
/// multi-company PDF report, `/c/all/reports`, ADR 0017 §2), so this view
/// lists the auditor's companies instead of pretending to show a merged
/// register.
class AllCompaniesView extends StatelessWidget {
  const AllCompaniesView({
    required this.me,
    this.section = 'changes',
    super.key,
  });

  final Me me;
  final String section;

  @override
  Widget build(BuildContext context) {
    final companies = me.auditorMemberships;
    return PageBody(
      children: [
        const PageHeader(
          title: allCompaniesLabel,
          subtitle: 'Widok zbiorczy spółek, w których masz rolę audytora',
        ),
        const SizedBox(height: 16),
        MessageBanner(
          message:
              'Zbiorczego rejestru wszystkich spółek nie ma — wybierz spółkę, '
              'aby przejrzeć jej rejestr. Raport zbiorczy PDF wszystkich '
              'Twoich spółek wygenerujesz w „Raporty i eksport”.',
          actions: [
            OutlinedButton.icon(
              key: const ValueKey('all-companies-reports'),
              onPressed: () => context.go('/c/$allCompaniesPrefix/reports'),
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: const Text('Raport zbiorczy'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (companies.isEmpty)
          const Text(
            'Nie masz roli audytora w żadnej spółce.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final company in companies)
              SizedBox(
                width: 280,
                child: Card(
                  child: InkWell(
                    borderRadius: AppRadii.mediumAll,
                    onTap: () =>
                        context.go('/c/${company.companyPrefix}/$section'),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            company.companyName,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            company.companyPrefix,
                            style: AppFonts.monoStyle(
                              fontSize: 13,
                              color: AppColors.textSecondary,
                            ),
                          ),
                          if (company.isArchived)
                            const Padding(
                              padding: EdgeInsets.only(top: 6),
                              child: Tag(label: 'Zarchiwizowana'),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }
}
