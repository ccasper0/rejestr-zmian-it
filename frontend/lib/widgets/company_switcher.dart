import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/session.dart';
import '../core/theme.dart';
import '../features/admin/data/admin_api.dart';
import '../features/admin/data/admin_models.dart';

/// Dropdown in the side panel selecting the company (prefix in the URL).
class CompanySwitcher extends ConsumerWidget {
  const CompanySwitcher({
    required this.selectedPrefix,
    required this.onSelected,
    super.key,
  });

  /// Prefix from the URL; `null` when the current route is not company-scoped.
  final String? selectedPrefix;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider).value;
    final memberships = me?.memberships ?? const <Membership>[];
    // The app admin sees ALL companies (owner decision 2026-11-02): those
    // without his role open only the admin-path screens (CI, audit log).
    final adminOnly = me != null && me.isAppAdmin
        ? <AdminCompany>[
            for (final c
                in ref.watch(adminCompaniesProvider).value ??
                    const <AdminCompany>[])
              if (me.membershipFor(c.prefix) == null) c,
          ]
        : const <AdminCompany>[];

    final items = <DropdownMenuItem<String>>[
      for (final company in memberships)
        DropdownMenuItem(
          value: company.companyPrefix,
          child: Text(
            company.isArchived
                ? '${company.companyName} (archiwum)'
                : company.companyName,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      for (final company in adminOnly)
        DropdownMenuItem(
          value: company.prefix,
          child: Text(
            '${company.name} (administrator'
            '${company.isArchived ? ', archiwum' : ''})',
            overflow: TextOverflow.ellipsis,
          ),
        ),
      // Cross-company view for auditors (ADR 0002).
      if (me != null && me.isAuditor)
        const DropdownMenuItem(
          value: allCompaniesPrefix,
          child: Text(allCompaniesLabel),
        ),
    ];
    final known = items.any((item) => item.value == selectedPrefix);

    return Semantics(
      label: 'Spółka',
      container: true,
      child: Container(
        constraints: const BoxConstraints(minHeight: AppSizes.minTouchTarget),
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: AppColors.sidebarHover,
          borderRadius: AppRadii.smallAll,
          border: Border.all(color: AppColors.sidebarDivider),
        ),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            key: const ValueKey('company-switcher'),
            value: known ? selectedPrefix : null,
            hint: const Text(
              'Wybierz spółkę',
              style: TextStyle(color: AppColors.sidebarTextMuted),
            ),
            isExpanded: true,
            itemHeight: null,
            dropdownColor: AppColors.sidebarHover,
            borderRadius: AppRadii.smallAll,
            iconEnabledColor: AppColors.sidebarText,
            style: const TextStyle(
              fontFamily: AppFonts.sans,
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: AppColors.sidebarText,
            ),
            items: items,
            onChanged: (value) {
              if (value != null && value != selectedPrefix) onSelected(value);
            },
          ),
        ),
      ),
    );
  }
}
