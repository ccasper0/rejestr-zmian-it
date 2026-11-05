import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/audit_timeline.dart';
import '../../../widgets/common.dart';
import '../../../widgets/company_gate.dart';
import '../../../widgets/company_scope.dart';
import '../../admin/data/admin_api.dart';
import '../../admin/data/admin_models.dart';
import '../../admin/presentation/admin_shell.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../../changes/presentation/labels.dart';
import '../../changes/presentation/pickers.dart';
import '../../ci/data/ci_api.dart';
import '../data/audit_api.dart';
import '../data/audit_filters.dart';
import '../data/audit_models.dart';
import 'verify_result_banner.dart';

/// Matrix §5 / ADR 0009 §3: the whole log of a company — the auditor of the
/// company and the app admin of every company (also without a role in it,
/// owner decision 2026-11-02, ADR 0015 §7).
bool canReadCompanyLog(Me me, CompanyRef company) =>
    me.isAppAdmin || (company.membership?.hasRole(Roles.auditor) ?? false);

/// `/c/:prefix/audit` — audit log of the company's chain.
class AuditLogPage extends ConsumerWidget {
  const AuditLogPage({required this.prefix, required this.filters, super.key});

  final String prefix;
  final AuditFilters filters;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isAdmin = ref.watch(meProvider).value?.isAppAdmin ?? false;
    if (prefix == allCompaniesPrefix && isAdmin) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
            child: MessageBanner(
              message:
                  'Łańcuch globalny (spółki, słowniki, użytkownicy, logowania) '
                  'jest dostępny dla administratora.',
              actions: [
                FilledButton(
                  key: const ValueKey('open-global-audit'),
                  onPressed: () => context.go('/admin/audit'),
                  child: const Text('Łańcuch globalny'),
                ),
              ],
            ),
          ),
          Expanded(
            child: CompanyGate(
              prefix: prefix,
              section: 'audit',
              builder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
        ],
      );
    }
    return AdminAwareCompanyGate(
      prefix: prefix,
      section: 'audit',
      builder: (context, me, company) {
        if (!canReadCompanyLog(me, company)) {
          return const NoAccessPanel(
            message:
                'Cały dziennik audytu spółki przeglądają audytor i '
                'administrator. Ścieżka audytu pojedynczej zmiany jest na jej '
                'karcie.',
          );
        }
        return AuditLogView(
          companyId: company.id,
          title: company.name,
          basePath: '/c/${company.prefix}/audit',
          filters: filters,
          // Same roles as reading (§5: audit.verify = app_admin, auditor).
          canVerify: canReadCompanyLog(me, company),
          showGlobalLink: me.isAppAdmin,
        );
      },
    );
  }
}

/// `/admin/audit` — the global chain (app admin only, ADR 0006 §6).
class GlobalAuditLogPage extends StatelessWidget {
  const GlobalAuditLogPage({required this.filters, super.key});

  final AuditFilters filters;

  @override
  Widget build(BuildContext context) => AdminGate(
    builder: (context, me) => AuditLogView(
      companyId: null,
      title: 'Łańcuch globalny',
      basePath: '/admin/audit',
      filters: filters,
      canVerify: true,
    ),
  );
}

/// Entries of one chain (newest first) with filters in the URL.
class AuditLogView extends ConsumerStatefulWidget {
  const AuditLogView({
    required this.companyId,
    required this.title,
    required this.basePath,
    required this.filters,
    required this.canVerify,
    this.showGlobalLink = false,
    super.key,
  });

  /// null = the global chain.
  final String? companyId;
  final String title;
  final String basePath;
  final AuditFilters filters;
  final bool canVerify;
  final bool showGlobalLink;

  @override
  ConsumerState<AuditLogView> createState() => _AuditLogViewState();
}

class _AuditLogViewState extends ConsumerState<AuditLogView> {
  VerifyResult? _result;
  bool _verifying = false;

  AuditFilters get _filters => widget.filters;

  void _apply(AuditFilters filters, {bool keepPage = false}) {
    final next = keepPage ? filters : filters.copyWith(page: 1);
    context.go(next.location(widget.basePath));
  }

  Future<void> _verify() async {
    setState(() => _verifying = true);
    try {
      final result = await ref.read(auditApiProvider).verify(widget.companyId);
      if (!mounted) return;
      setState(() => _result = result);
      // The verification is itself a new entry; the badge has a new verdict.
      ref.invalidate(auditLogProvider((widget.companyId, _filters)));
      final companyId = widget.companyId;
      if (companyId != null) ref.invalidate(chainStatusProvider(companyId));
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final companyId = widget.companyId;
    final key = (companyId, _filters);
    final page = ref.watch(auditLogProvider(key));
    final status = companyId == null
        ? null
        : ref.watch(chainStatusProvider(companyId)).value;
    final actors = companyId == null
        ? [
            for (final u
                in ref.watch(userDirectoryProvider).value ??
                    const <UserAccount>[])
              (u.id, u.displayName),
          ]
        : [
            for (final m
                in ref.watch(membersProvider(companyId)).value ??
                    const <Member>[])
              (m.userId, m.displayName),
          ];
    // Names for ids in diffs (users, categories, CI, CI types) — no UUIDs.
    final names = NameResolver(
      users: {for (final (id, n) in actors) id: n},
      categories: {
        for (final c
            in ref.watch(allCategoriesProvider).value ?? const <Category>[])
          c.id: '${c.code} — ${c.name}',
      },
      cis: {
        if (companyId != null)
          for (final c
              in ref.watch(companyCiAllProvider(companyId)).value ??
                  const <CiItem>[])
            c.id: c.identifier,
      },
    );
    final ciTypes = {
      for (final t in ref.watch(ciTypesAllProvider).value ?? const <CiType>[])
        t.id: t.name,
    };
    final rows = page.value?.items ?? const <AuditLogEntry>[];
    final total = page.value?.total;
    final pages = total == null
        ? 1
        : ((total + AuditFilters.pageSize - 1) ~/ AuditFilters.pageSize).clamp(
            1,
            1 << 30,
          );
    final period = _filters.from == null && _filters.to == null
        ? ''
        : '${_day(_filters.from) ?? '…'} – ${_day(_filters.to) ?? '…'}';

    return PageBody(
      maxWidth: 1200,
      children: [
        PageHeader(
          title: widget.title,
          subtitle: 'Dziennik audytu',
          actions: [
            if (status != null) ChainStatusBadge(status: status),
            IconButton(
              tooltip: 'Odśwież',
              onPressed: () => ref.invalidate(auditLogProvider(key)),
              icon: const Icon(Icons.refresh),
            ),
            if (widget.showGlobalLink)
              OutlinedButton(
                onPressed: () => context.go('/admin/audit'),
                child: const Text('Łańcuch globalny'),
              ),
            if (widget.canVerify)
              FilledButton.icon(
                key: const ValueKey('verify-chain'),
                onPressed: _verifying ? null : _verify,
                icon: const Icon(Icons.verified_outlined),
                label: Text(
                  _verifying ? 'Weryfikowanie…' : 'Zweryfikuj łańcuch',
                ),
              ),
          ],
        ),
        if (_result != null) ...[
          const SizedBox(height: 12),
          VerifyResultBanner(
            result: _result!,
            onClose: () => setState(() => _result = null),
          ),
        ],
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            FilterButton(
              key: const ValueKey('audit-filter-entity'),
              label: 'Obiekt',
              value: AuditFilters.entityTypes[_filters.entityType] ?? '',
              onPressed: () async {
                final picked = await showSingleSelectDialog(
                  context,
                  title: 'Typ obiektu',
                  anyLabel: 'Wszystkie',
                  options: [
                    for (final e in AuditFilters.entityTypes.entries)
                      (e.key, e.value),
                  ],
                  selected: _filters.entityType,
                );
                if (picked != null) {
                  _apply(_filters.copyWith(entityType: picked.value));
                }
              },
              onClear: () => _apply(_filters.copyWith(entityType: null)),
            ),
            FilterButton(
              key: const ValueKey('audit-filter-action'),
              label: 'Akcja',
              value: AuditFilters.actions[_filters.action] ?? '',
              onPressed: () async {
                final picked = await showSingleSelectDialog(
                  context,
                  title: 'Akcja',
                  anyLabel: 'Wszystkie',
                  options: [
                    for (final e in AuditFilters.actions.entries)
                      (e.key, e.value),
                  ],
                  selected: _filters.action,
                );
                if (picked != null) {
                  _apply(_filters.copyWith(action: picked.value));
                }
              },
              onClear: () => _apply(_filters.copyWith(action: null)),
            ),
            FilterButton(
              key: const ValueKey('audit-filter-actor'),
              label: 'Kto',
              value: _filters.actor == null ? '' : names.user(_filters.actor!),
              onPressed: () async {
                final picked = await showSingleSelectDialog(
                  context,
                  title: 'Kto wykonał',
                  options: actors,
                  selected: _filters.actor,
                );
                if (picked != null) {
                  _apply(_filters.copyWith(actor: picked.value));
                }
              },
              onClear: () => _apply(_filters.copyWith(actor: null)),
            ),
            FilterButton(
              key: const ValueKey('audit-filter-period'),
              label: 'Okres',
              value: period,
              onPressed: () async {
                final range = await pickPeriod(
                  context,
                  _filters.from,
                  _filters.to,
                );
                if (range != null) {
                  _apply(_filters.copyWith(from: range.$1, to: range.$2));
                }
              },
              onClear: () => _apply(_filters.copyWith(from: null, to: null)),
            ),
            if (_filters.hasFilters)
              TextButton.icon(
                key: const ValueKey('audit-filters-clear'),
                onPressed: () => _apply(const AuditFilters()),
                icon: const Icon(Icons.filter_alt_off_outlined),
                label: const Text('Wyczyść filtry'),
              ),
          ],
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (page.isLoading && page.hasValue)
                  const LinearProgressIndicator(minHeight: 2),
                switch (page) {
                  AsyncError(:final error) => ErrorPanel(
                    error: error,
                    onRetry: () => ref.invalidate(auditLogProvider(key)),
                  ),
                  AsyncData() || AsyncLoading(hasValue: true) =>
                    rows.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.all(16),
                            child: Text(
                              'Brak wpisów spełniających kryteria.',
                              style: TextStyle(color: AppColors.textSecondary),
                            ),
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              for (var i = 0; i < rows.length; i++) ...[
                                if (i > 0) const Divider(height: 24),
                                AuditLogEntryTile(
                                  entry: rows[i],
                                  names: names,
                                  ciTypes: ciTypes,
                                  broken:
                                      _result != null &&
                                      !_result!.ok &&
                                      _result!.firstBrokenSeq == rows[i].seq,
                                ),
                              ],
                            ],
                          ),
                  _ => const LoadingPanel(),
                },
                const Divider(height: 24),
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      key: const ValueKey('audit-count'),
                      total == null ? 'Wczytywanie…' : 'Wpisów: $total',
                    ),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        IconButton(
                          tooltip: 'Nowsze wpisy',
                          onPressed: _filters.page > 1
                              ? () => _apply(
                                  _filters.copyWith(page: _filters.page - 1),
                                  keepPage: true,
                                )
                              : null,
                          icon: const Icon(Icons.chevron_left),
                        ),
                        Text(
                          'Strona ${_filters.page} z $pages',
                          style: AppFonts.monoStyle(fontSize: 13),
                        ),
                        IconButton(
                          tooltip: 'Starsze wpisy',
                          onPressed: _filters.page < pages
                              ? () => _apply(
                                  _filters.copyWith(page: _filters.page + 1),
                                  keepPage: true,
                                )
                              : null,
                          icon: const Icon(Icons.chevron_right),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  static String? _day(String? iso) {
    final instant = WarsawTime.startOfIsoDay(iso);
    return instant == null ? null : WarsawTime.formatDate(instant);
  }
}

/// One log entry: time + IP (mono), who (roles) — what, diff "before →
/// after", comment, `#seq` and sha256; technical details on demand.
class AuditLogEntryTile extends StatefulWidget {
  const AuditLogEntryTile({
    required this.entry,
    required this.names,
    this.ciTypes = const {},
    this.broken = false,
    super.key,
  });

  final AuditLogEntry entry;
  final NameResolver names;

  /// CI type id → name (diffs of CI).
  final Map<String, String> ciTypes;

  /// First entry that failed the last verification.
  final bool broken;

  @override
  State<AuditLogEntryTile> createState() => _AuditLogEntryTileState();
}

class _AuditLogEntryTileState extends State<AuditLogEntryTile> {
  bool _details = false;

  static const _refKeys = [
    'number',
    'identifier',
    'code',
    'prefix',
    'user_display',
    'filename',
    'report_number',
  ];

  /// Polish label of a diff field of this entry's entity.
  String _label(String field) {
    final entity = widget.entry.entityType;
    if (entity == 'company_category') return 'Kategoria $field';
    if (field == 'description' && entity != 'change') return 'Opis';
    if (field == 'status' && entity == 'company') return 'Status spółki';
    return fieldLabel(field);
  }

  static const _monoFields = {
    'prefix',
    'tax_id',
    'identifier',
    'code',
    'email',
    'external_id',
  };

  /// Display value of a diff side; null = no value on that side.
  String? _value(String field, Object? value) {
    final entity = widget.entry.entityType;
    if (entity == 'company_category') {
      // {"FW": {"before": null, "after": {"approver_override_id": …}}}
      if (value == null) return 'niedostępna';
      final approver = value is Map ? value['approver_override_id'] : null;
      return approver == null
          ? 'dostępna (zatwierdzający: domyślny spółki)'
          : 'dostępna (zatwierdzający: ${widget.names.user('$approver')})';
    }
    if (value == null || (value is List && value.isEmpty)) return null;
    if (value is Map) {
      return value.entries
          .map(
            (e) =>
                '${fieldLabel('${e.key}')}: ${_value('${e.key}', e.value) ?? '—'}',
          )
          .join(', ');
    }
    if (value is List && value.any((v) => v is Map)) return jsonEncode(value);
    if (value is bool) return value ? 'tak' : 'nie';
    switch (field) {
      case 'roles':
        return (value as List).map((r) => Roles.label('$r')).join(', ');
      case 'default_risk':
        return Risks.label('$value');
      case 'default_approver_id':
      case 'owner_user_id':
      case 'approver_override_id':
        return widget.names.user('$value');
      case 'ci_type_id':
        return widget.ciTypes['$value'] ?? NameResolver.shortId('$value');
      case 'parent_id':
        return widget.names.category('$value');
      case 'status' when entity == 'company':
        return switch ('$value') {
          'active' => 'aktywna',
          'archived' => 'zarchiwizowana',
          final other => other,
        };
    }
    return widget.names.value(field, value);
  }

  @override
  Widget build(BuildContext context) {
    final entry = widget.entry;
    final meta = AppFonts.monoStyle(
      fontSize: 12,
      color: AppColors.textSecondary,
    );
    final roles = entry.actorRoles.map(Roles.label).join(', ');
    final actor = entry.actorId == null
        ? 'system'
        : roles.isEmpty
        ? entry.actorDisplay
        : '${entry.actorDisplay} ($roles)';
    final what =
        '${AuditFilters.entityTypes[entry.entityType] ?? entry.entityType}: '
        '${AuditFilters.actions[entry.action] ?? entry.action}';
    final reference = [
      for (final k in _refKeys)
        if (entry.context[k] is String) entry.context[k] as String,
    ].firstOrNull;
    Object? present(Object? v) => v is List && v.isEmpty ? null : v;
    final diff = [
      for (final e in entry.diff.entries)
        if (e.value is Map &&
            (present((e.value as Map)['before']) != null ||
                present((e.value as Map)['after']) != null))
          (e.key, (e.value as Map)['before'], (e.value as Map)['after']),
    ];
    final comment = entry.context['comment'];
    return Column(
      key: ValueKey('audit-entry-${entry.seq}'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              '${WarsawTime.format(entry.occurredAt)} · IP '
              '${entry.ipAddress ?? '—'}',
              style: meta,
            ),
            if (widget.broken)
              const Tag(
                label: 'Pierwszy niezgodny wpis',
                colors: AppFeedbackColors.error,
                icon: Icons.gpp_bad_outlined,
              ),
          ],
        ),
        const SizedBox(height: 2),
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: actor,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              TextSpan(text: ' — $what'),
              if (reference != null)
                TextSpan(
                  text: '  $reference',
                  style: AppFonts.monoStyle(fontWeight: FontWeight.w500),
                ),
            ],
          ),
        ),
        if (diff.isNotEmpty) ...[
          const SizedBox(height: 6),
          DecoratedBox(
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
                  for (final (field, before, after) in diff)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: DiffLine(
                        field: field,
                        label: _label(field),
                        mono: _monoFields.contains(field) ? true : null,
                        before: _value(field, before),
                        after: _value(field, after),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
        if (comment is String && comment.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(
            '„$comment”',
            style: const TextStyle(fontStyle: FontStyle.italic),
          ),
        ],
        const SizedBox(height: 4),
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Tooltip(
              message:
                  'sha256 wpisu: ${entry.hash}\npoprzedni: ${entry.prevHash}',
              child: Text(
                '#${entry.seq} · sha256 ${entry.hash.length > 12 ? '${entry.hash.substring(0, 12)}…' : entry.hash}',
                style: meta,
              ),
            ),
            TextButton(
              onPressed: () => setState(() => _details = !_details),
              child: Text(_details ? 'Ukryj szczegóły' : 'Szczegóły'),
            ),
          ],
        ),
        if (_details)
          SelectableText(
            [
              'request_id: ${entry.requestId}',
              if (entry.entityId != null) 'entity_id: ${entry.entityId}',
              if (entry.userAgent != null) 'user_agent: ${entry.userAgent}',
              'prev_hash: ${entry.prevHash}',
              'hash: ${entry.hash}',
              if (entry.context.isNotEmpty)
                'context: ${const JsonEncoder.withIndent('  ').convert(entry.context)}',
            ].join('\n'),
            style: AppFonts.monoStyle(fontSize: 12),
          ),
      ],
    );
  }
}
