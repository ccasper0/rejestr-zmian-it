import 'dart:async';

import 'package:data_table_2/data_table_2.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/change_status.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../../../widgets/company_scope.dart';
import '../../../widgets/status_pill.dart';
import '../../reports/presentation/report_export.dart';
import '../data/changes_api.dart';
import '../data/models.dart';
import '../data/register_filters.dart';
import 'pickers.dart';

/// Change register (`/c/:prefix/changes`, §10.1). All filters live in the URL.
///
/// The app admin without a role in the company reads it on the API's
/// read-only admin path (ADR 0016): no "Nowa zmiana", a read-only banner.
class RegisterPage extends StatelessWidget {
  const RegisterPage({required this.prefix, required this.filters, super.key});

  final String prefix;
  final RegisterFilters filters;

  @override
  Widget build(BuildContext context) {
    return AdminAwareCompanyGate(
      prefix: prefix,
      section: 'changes',
      builder: (context, me, company) => _RegisterView(
        company: company,
        filters: filters,
        // Matrix §5 `export.register`: app admin (also without a role,
        // ADR 0017 §4), approver, auditor — not the editor or the viewer.
        canExport: company.adminPath || me.canExportRegister(company.prefix),
      ),
    );
  }
}

class _RegisterView extends ConsumerStatefulWidget {
  const _RegisterView({
    required this.company,
    required this.filters,
    required this.canExport,
  });

  final CompanyRef company;
  final RegisterFilters filters;
  final bool canExport;

  @override
  ConsumerState<_RegisterView> createState() => _RegisterViewState();
}

class _RegisterViewState extends ConsumerState<_RegisterView> {
  late final TextEditingController _search = TextEditingController(
    text: widget.filters.q,
  );
  Timer? _debounce;
  bool _exportingCsv = false;

  String get _prefix => widget.company.prefix;
  String get _companyId => widget.company.id;
  RegisterFilters get _filters => widget.filters;

  @override
  void didUpdateWidget(covariant _RegisterView oldWidget) {
    super.didUpdateWidget(oldWidget);
    // URL changed from outside (back button, tile): keep the field in sync.
    if (widget.filters.q != _search.text.trim() && _debounce == null) {
      _search.text = widget.filters.q;
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  /// Every filter change = new URL (page reset unless [keepPage]).
  void _apply(RegisterFilters filters, {bool keepPage = false}) {
    final next = keepPage ? filters : filters.copyWith(page: 1);
    context.go(next.location(_prefix));
  }

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      _debounce = null;
      if (value.trim() != _filters.q) {
        _apply(_filters.copyWith(q: value.trim()));
      }
    });
  }

  void _refresh() {
    ref.invalidate(registerProvider((_companyId, _filters)));
    ref.invalidate(statsProvider(_companyId));
  }

  /// "Eksport PDF": the report screen with the register's filters (sort and
  /// page do not apply to a report).
  void _exportPdf() {
    final query = _filters
        .copyWith(sort: RegisterFilters.defaultSort, page: 1)
        .toQuery();
    context.go(
      Uri(
        path: '/c/$_prefix/reports',
        queryParameters: query.isEmpty ? null : query,
      ).toString(),
    );
  }

  /// "CSV": the register with the current filters (numbered and audited by
  /// the API, ADR 0017 §7).
  Future<void> _exportCsv() async {
    setState(() => _exportingCsv = true);
    try {
      final file = await ref
          .read(reportExporterProvider)
          .registerCsv(_companyId, _filters);
      if (mounted) {
        showInfoSnack(
          context,
          'Pobrano plik ${file.filename}'
          '${file.reportNumber == null ? '' : ' (eksport ${file.reportNumber})'}.',
        );
      }
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _exportingCsv = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final company = widget.company;
    final canCreate = company.canEditChanges;

    return PageBody(
      children: [
        PageHeader(
          title: company.name,
          subtitle: 'Rejestr zmian',
          actions: [
            if (widget.canExport) ...[
              Tooltip(
                message: 'Raport rejestru w PDF z bieżącymi filtrami',
                child: OutlinedButton.icon(
                  key: const ValueKey('register-export-pdf'),
                  onPressed: _exportPdf,
                  icon: const Icon(Icons.picture_as_pdf_outlined),
                  label: const Text('Eksport PDF'),
                ),
              ),
              Tooltip(
                message: 'Rejestr w CSV z bieżącymi filtrami',
                child: OutlinedButton.icon(
                  key: const ValueKey('register-export-csv'),
                  onPressed: _exportingCsv ? null : _exportCsv,
                  icon: _exportingCsv
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.download_outlined),
                  label: const Text('CSV'),
                ),
              ),
            ],
            IconButton(
              tooltip: 'Odśwież',
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
            ),
            if (canCreate)
              FilledButton.icon(
                key: const ValueKey('new-change'),
                onPressed: () => context.go('/c/$_prefix/changes/new'),
                icon: const Icon(Icons.add),
                label: const Text('Nowa zmiana'),
              ),
          ],
        ),
        if (company.adminPath) ...[
          const SizedBox(height: 12),
          const AdminReadOnlyBanner(),
        ],
        if (company.archived) ...[
          const SizedBox(height: 12),
          const MessageBanner(
            kind: BannerKind.warning,
            message:
                'Spółka jest zarchiwizowana — rejestr jest tylko do odczytu.',
          ),
        ],
        const SizedBox(height: 16),
        _StatTiles(companyId: _companyId, onFilter: _apply),
        const SizedBox(height: 16),
        _FilterBar(
          companyId: _companyId,
          filters: _filters,
          search: _search,
          onSearchChanged: _onSearchChanged,
          onApply: _apply,
        ),
        const SizedBox(height: 12),
        _RegisterTable(
          prefix: _prefix,
          companyId: _companyId,
          filters: _filters,
          onApply: _apply,
        ),
      ],
    );
  }
}

// --------------------------------------------------------------------- tiles

class _StatTiles extends ConsumerWidget {
  const _StatTiles({required this.companyId, required this.onFilter});

  final String companyId;
  final void Function(RegisterFilters) onFilter;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(statsProvider(companyId));
    if (stats case AsyncError(:final error)) {
      return ErrorPanel(
        error: error,
        onRetry: () => ref.invalidate(statsProvider(companyId)),
      );
    }
    final value = stats.value;
    final today = DateTime.now();
    final monthAgoInstant = today.subtract(const Duration(days: 30));
    final monthAgo = WarsawTime.isoDay(monthAgoInstant);
    final monthAgoLabel = WarsawTime.formatDate(monthAgoInstant);
    final tiles = [
      _StatTile(
        key: const ValueKey('tile-pending'),
        label: 'Do zatwierdzenia',
        count: value?.pendingApproval,
        onTap: () =>
            onFilter(const RegisterFilters(statuses: ['pending_approval'])),
      ),
      _StatTile(
        key: const ValueKey('tile-approved'),
        label: 'Zatwierdzone niewdrożone',
        count: value?.approvedNotImplemented,
        onTap: () => onFilter(const RegisterFilters(statuses: ['approved'])),
      ),
      _StatTile(
        key: const ValueKey('tile-emergency'),
        label: 'Awaryjne (30 dni)',
        count: value?.emergencyLast30Days,
        alert: (value?.emergencyNotApprovedIn24h ?? 0) > 0
            ? 'w tym bez zatwierdzenia w 24 h: '
                  '${value!.emergencyNotApprovedIn24h}'
            : null,
        hint:
            'Licznik: awaryjne zarejestrowane w ostatnich 30 dniach (bez '
            'anulowanych). Filtr: od $monthAgoLabel, bez anulowanych — '
            'może obejmować część dnia sprzed 30 dni.',
        onTap: () => onFilter(
          RegisterFilters(
            types: const ['emergency'],
            from: monthAgo,
            // Same as the counter (ADR 0013 §8): cancelled changes excluded.
            statuses: [
              for (final s in RegisterFilters.statusValues)
                if (s != 'cancelled') s,
            ],
          ),
        ),
      ),
      _StatTile(
        key: const ValueKey('tile-unverified'),
        label: 'Wdrożone bez weryfikacji',
        count: value?.implementedNotVerified,
        onTap: () => onFilter(const RegisterFilters(statuses: ['implemented'])),
      ),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 900
            ? 4
            : constraints.maxWidth >= 480
            ? 2
            : 1;
        final width = (constraints.maxWidth - 12 * (columns - 1)) / columns;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final tile in tiles) SizedBox(width: width, child: tile),
          ],
        );
      },
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.label,
    required this.count,
    required this.onTap,
    this.alert,
    this.hint,
    super.key,
  });

  final String label;
  final int? count;
  final String? alert;

  /// Tooltip explaining how the tile's filter relates to the counter.
  final String? hint;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final card = Card(
      child: InkWell(
        borderRadius: AppRadii.mediumAll,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 6),
              Text(
                count?.toString() ?? '…',
                style: AppFonts.monoStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w500,
                ),
              ),
              if (alert != null) ...[
                const SizedBox(height: 4),
                Tag(
                  label: alert!,
                  colors: AppFeedbackColors.error,
                  icon: Icons.warning_amber_outlined,
                  wrap: true,
                ),
              ],
            ],
          ),
        ),
      ),
    );
    return hint == null ? card : Tooltip(message: hint, child: card);
  }
}

// --------------------------------------------------------------------- filters

class _FilterBar extends ConsumerWidget {
  const _FilterBar({
    required this.companyId,
    required this.filters,
    required this.search,
    required this.onSearchChanged,
    required this.onApply,
  });

  final String companyId;
  final RegisterFilters filters;
  final TextEditingController search;
  final ValueChanged<String> onSearchChanged;
  final void Function(RegisterFilters) onApply;

  String _summary(List<String> labels) {
    if (labels.isEmpty) return '';
    if (labels.length == 1) return labels.first;
    return '${labels.first} +${labels.length - 1}';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories =
        ref.watch(companyCategoriesProvider(companyId)).value ?? const [];
    final members = ref.watch(membersProvider(companyId)).value ?? const [];
    String memberName(String id) => members
        .firstWhere(
          (m) => m.userId == id,
          orElse: () => Member(userId: id, displayName: 'wybrana osoba'),
        )
        .displayName;

    final period = filters.from == null && filters.to == null
        ? ''
        : '${_day(filters.from) ?? '…'} – ${_day(filters.to) ?? '…'}';

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        SizedBox(
          width: 320,
          child: TextField(
            key: const ValueKey('register-search'),
            controller: search,
            onChanged: onSearchChanged,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Szukaj: numer, tytuł, zgłoszenie',
              isDense: true,
            ),
          ),
        ),
        FilterButton(
          key: const ValueKey('filter-period'),
          label: 'Okres',
          value: period,
          onPressed: () async {
            final range = await pickPeriod(context, filters.from, filters.to);
            if (range != null) {
              onApply(filters.copyWith(from: range.$1, to: range.$2));
            }
          },
          onClear: () => onApply(filters.copyWith(from: null, to: null)),
        ),
        if (filters.from != null || filters.to != null)
          FilterButton(
            key: const ValueKey('filter-period-by'),
            label: 'Data',
            value: filters.periodBy == 'implemented'
                ? 'wdrożenia'
                : 'rejestracji',
            onPressed: () => onApply(
              filters.copyWith(
                periodBy: filters.periodBy == 'implemented'
                    ? 'created'
                    : 'implemented',
              ),
            ),
          ),
        FilterButton(
          key: const ValueKey('filter-category'),
          label: 'Kategoria',
          value: _summary([
            for (final id in filters.categories)
              categories
                  .firstWhere(
                    (c) => c.categoryId == id,
                    orElse: () => CompanyCategory(
                      categoryId: id,
                      code: '?',
                      name: 'wybrana',
                    ),
                  )
                  .name,
          ]),
          onPressed: () async {
            final picked = await showMultiSelectDialog(
              context,
              title: 'Kategoria',
              options: [for (final c in categories) (c.categoryId, c.name)],
              selected: filters.categories,
            );
            if (picked != null) onApply(filters.copyWith(categories: picked));
          },
          onClear: () => onApply(filters.copyWith(categories: const [])),
        ),
        FilterButton(
          key: const ValueKey('filter-ci'),
          label: 'Obiekt',
          value: filters.cis.isEmpty
              ? ''
              : filters.cis.length == 1
              ? '1 obiekt'
              : '${filters.cis.length} obiekty',
          onPressed: () async {
            final picked = await showCiFilterDialog(
              context,
              companyId: companyId,
              selected: filters.cis,
            );
            if (picked != null) onApply(filters.copyWith(cis: picked));
          },
          onClear: () => onApply(filters.copyWith(cis: const [])),
        ),
        FilterButton(
          key: const ValueKey('filter-status'),
          label: 'Status',
          value: _summary([
            for (final s in filters.statuses)
              ChangeStatus.tryParse(s)?.label ?? s,
          ]),
          onPressed: () async {
            final picked = await showMultiSelectDialog(
              context,
              title: 'Status',
              options: [
                for (final s in ChangeStatus.values) (s.apiValue, s.label),
              ],
              selected: filters.statuses,
            );
            if (picked != null) onApply(filters.copyWith(statuses: picked));
          },
          onClear: () => onApply(filters.copyWith(statuses: const [])),
        ),
        FilterButton(
          key: const ValueKey('filter-type'),
          label: 'Typ',
          value: _summary([
            for (final t in filters.types) ChangeTypes.label(t),
          ]),
          onPressed: () async {
            final picked = await showMultiSelectDialog(
              context,
              title: 'Typ zmiany',
              options: [
                for (final t in ChangeTypes.all) (t, ChangeTypes.label(t)),
              ],
              selected: filters.types,
            );
            if (picked != null) onApply(filters.copyWith(types: picked));
          },
          onClear: () => onApply(filters.copyWith(types: const [])),
        ),
        FilterButton(
          key: const ValueKey('filter-assignee'),
          label: 'Wykonawca',
          value: filters.assignee == null ? '' : memberName(filters.assignee!),
          onPressed: () async {
            final picked = await showSingleSelectDialog(
              context,
              title: 'Wykonawca',
              options: [
                for (final m in members)
                  if (m.canWrite) (m.userId, m.displayName),
              ],
              selected: filters.assignee,
            );
            if (picked != null) {
              onApply(filters.copyWith(assignee: picked.value));
            }
          },
          onClear: () => onApply(filters.copyWith(assignee: null)),
        ),
        FilterButton(
          key: const ValueKey('filter-approved-by'),
          label: 'Zatwierdził',
          value: filters.approvedBy == null
              ? ''
              : filters.approvedBy == 'system'
              ? 'system'
              : memberName(filters.approvedBy!),
          onPressed: () async {
            final picked = await showSingleSelectDialog(
              context,
              title: 'Kto faktycznie zatwierdził',
              options: [
                ('system', 'system (automatycznie)'),
                for (final m in members)
                  if (m.canApprove) (m.userId, m.displayName),
              ],
              selected: filters.approvedBy,
            );
            if (picked != null) {
              onApply(filters.copyWith(approvedBy: picked.value));
            }
          },
          onClear: () => onApply(filters.copyWith(approvedBy: null)),
        ),
        if (filters.hasFilters)
          TextButton.icon(
            key: const ValueKey('filters-clear'),
            onPressed: () {
              search.clear();
              onApply(filters.cleared());
            },
            icon: const Icon(Icons.filter_alt_off_outlined),
            label: const Text('Wyczyść filtry'),
          ),
      ],
    );
  }

  static String? _day(String? iso) {
    final instant = WarsawTime.startOfIsoDay(iso);
    return instant == null ? null : WarsawTime.formatDate(instant);
  }
}

// --------------------------------------------------------------------- table

class _RegisterTable extends ConsumerWidget {
  const _RegisterTable({
    required this.prefix,
    required this.companyId,
    required this.filters,
    required this.onApply,
  });

  final String prefix;
  final String companyId;
  final RegisterFilters filters;
  final void Function(RegisterFilters, {bool keepPage}) onApply;

  static const double _rowHeight = 64;
  static const double _headingHeight = 48;

  /// Table column → API sort key.
  static const Map<int, String> _sortColumns = {
    0: 'number',
    1: 'title',
    5: 'status',
    8: 'implemented_at',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final page = ref.watch(registerProvider((companyId, filters)));
    final sortKey = filters.sort.replaceFirst('-', '');
    final ascending = !filters.sort.startsWith('-');
    int? sortColumn;
    _sortColumns.forEach((index, key) {
      if (key == sortKey) sortColumn = index;
    });

    void sortBy(int column, bool asc) {
      final key = _sortColumns[column]!;
      onApply(filters.copyWith(sort: asc ? key : '-$key'));
    }

    DataColumn2 column(
      String label, {
      ColumnSize size = ColumnSize.M,
      double? fixedWidth,
      bool sortable = false,
    }) => DataColumn2(
      label: Text(label),
      size: size,
      fixedWidth: fixedWidth,
      onSort: sortable ? sortBy : null,
    );

    final rows = page.value?.items ?? const <Change>[];
    final body = switch (page) {
      AsyncError(:final error) => Padding(
        padding: const EdgeInsets.all(16),
        child: ErrorPanel(
          error: error,
          onRetry: () => ref.invalidate(registerProvider((companyId, filters))),
        ),
      ),
      AsyncData() || AsyncLoading(hasValue: true) => SizedBox(
        height: rows.isEmpty
            ? 200
            : _headingHeight + rows.length * _rowHeight + 8,
        child: DataTable2(
          key: const ValueKey('register-table'),
          // Fits the content width of a 1440 px screen (minus the 232 px
          // panel); narrower screens scroll horizontally.
          minWidth: 1100,
          lmRatio: 1.6,
          smRatio: 0.7,
          headingRowHeight: _headingHeight,
          dataRowHeight: _rowHeight,
          columnSpacing: 12,
          horizontalMargin: 12,
          dataTextStyle: const TextStyle(fontSize: 13, color: AppColors.text),
          sortColumnIndex: sortColumn,
          sortAscending: ascending,
          headingTextStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
            fontSize: 13,
          ),
          empty: const Center(
            child: Text(
              'Brak zmian spełniających kryteria.',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
          columns: [
            column('ID', fixedWidth: 158, sortable: true),
            column('Zmiana', size: ColumnSize.L, sortable: true),
            column('Kategoria', size: ColumnSize.S),
            column('Obiekt (CI)'),
            column('Typ', fixedWidth: 108),
            column('Status', fixedWidth: 138, sortable: true),
            column('Wykonawca'),
            column('Zatwierdził'),
            column('Wdrożenie', fixedWidth: 128, sortable: true),
          ],
          rows: [
            for (final change in rows)
              DataRow2(
                onTap: () => context.go('/c/$prefix/changes/${change.number}'),
                cells: _cells(context, change),
              ),
          ],
        ),
      ),
      _ => const LoadingPanel(),
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (page.isLoading && page.hasValue)
            const LinearProgressIndicator(minHeight: 2),
          body,
          const Divider(),
          _Footer(
            total: page.value?.total,
            shown: rows.length,
            filters: filters,
            onApply: onApply,
          ),
        ],
      ),
    );
  }

  List<DataCell> _cells(BuildContext context, Change change) {
    const secondary = TextStyle(color: AppColors.textSecondary, fontSize: 12);
    final status = change.statusValue;
    return [
      DataCell(
        Tooltip(
          message: 'Otwórz kartę zmiany',
          child: Text(
            change.number,
            style: AppFonts.monoStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppColors.accent,
            ).copyWith(decoration: TextDecoration.underline),
          ),
        ),
      ),
      DataCell(
        Row(
          children: [
            Expanded(
              child: Text(
                change.title?.isNotEmpty == true
                    ? change.title!
                    : '(bez tytułu)',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (change.deviations.isNotEmpty)
              Tooltip(
                message: change.deviations.map((d) => d.messagePl).join('\n'),
                child: const Icon(
                  Icons.report_outlined,
                  size: 18,
                  semanticLabel: 'Odstępstwo',
                  color: AppColors.danger,
                ),
              ),
          ],
        ),
      ),
      DataCell(
        Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              change.category?.name ?? '—',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            if (change.subcategory != null)
              Text(
                change.subcategory!.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: secondary,
              ),
          ],
        ),
      ),
      DataCell(
        Tooltip(
          message: change.ci
              .map((c) => '${c.identifier} — ${c.name}')
              .join('\n'),
          child: Text(
            change.ci.isEmpty
                ? '—'
                : change.ci.length <= 2
                ? change.ci.map((c) => c.identifier).join(', ')
                : '${change.ci.take(2).map((c) => c.identifier).join(', ')} '
                      '+${change.ci.length - 2}',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppFonts.monoStyle(fontSize: 12),
          ),
        ),
      ),
      DataCell(ChangeTypeTag(type: change.changeType)),
      DataCell(
        status == null ? Text(change.status) : StatusPill(status: status),
      ),
      DataCell(
        Text(
          change.assignee?.displayName ?? '—',
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      DataCell(_ApprovedByCell(change: change)),
      DataCell(
        Text(
          change.implementedAt == null
              ? '—'
              : WarsawTime.format(change.implementedAt),
          style: AppFonts.monoStyle(fontSize: 12),
        ),
      ),
    ];
  }
}

/// Who actually approved (ADR 0012 §4): `approved_by`, or `system` for an
/// auto-approved standard change — never the merely designated approver.
class _ApprovedByCell extends StatelessWidget {
  const _ApprovedByCell({required this.change});

  final Change change;

  @override
  Widget build(BuildContext context) {
    if (change.autoApproved) {
      return const Tooltip(
        message: 'Zmiana standardowa zatwierdzona automatycznie',
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('system'),
            Text(
              '(automatycznie)',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
          ],
        ),
      );
    }
    return Text(
      change.approvedBy?.displayName ?? '—',
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
    );
  }
}

/// Change type tag; emergency highlighted with a red border (§10.1).
class ChangeTypeTag extends StatelessWidget {
  const ChangeTypeTag({required this.type, super.key});

  final String? type;

  @override
  Widget build(BuildContext context) {
    final emergency = type == ChangeTypes.emergency;
    return Tag(
      label: ChangeTypes.label(type),
      colors: emergency ? AppFeedbackColors.error : AppFeedbackColors.neutral,
      borderColor: emergency ? AppColors.emergencyBorder : null,
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({
    required this.total,
    required this.shown,
    required this.filters,
    required this.onApply,
  });

  final int? total;
  final int shown;
  final RegisterFilters filters;
  final void Function(RegisterFilters, {bool keepPage}) onApply;

  @override
  Widget build(BuildContext context) {
    final total = this.total;
    final first = (filters.page - 1) * RegisterFilters.pageSize + 1;
    final last = first + shown - 1;
    final pages = total == null
        ? 1
        : ((total + RegisterFilters.pageSize - 1) ~/ RegisterFilters.pageSize)
              .clamp(1, 1 << 30);
    final mono = AppFonts.monoStyle(fontSize: 13);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Wrap(
        spacing: 16,
        runSpacing: 8,
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Text.rich(
            key: const ValueKey('register-count'),
            total == null
                ? const TextSpan(text: 'Wczytywanie…')
                : total == 0 || shown == 0
                ? TextSpan(
                    children: [
                      const TextSpan(text: 'Zmian: '),
                      TextSpan(text: '$total', style: mono),
                    ],
                  )
                : TextSpan(
                    children: [
                      const TextSpan(text: 'Wyświetlono '),
                      TextSpan(text: '$first–$last', style: mono),
                      const TextSpan(text: ' z '),
                      TextSpan(text: '$total', style: mono),
                    ],
                  ),
          ),
          Wrap(
            spacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Text('Sortowanie:'),
              DropdownButton<String>(
                key: const ValueKey('register-sort'),
                value: filters.sort,
                underline: const SizedBox.shrink(),
                items: [
                  for (final entry in RegisterFilters.sortLabels.entries)
                    DropdownMenuItem(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                ],
                onChanged: (value) {
                  if (value != null) onApply(filters.copyWith(sort: value));
                },
              ),
              IconButton(
                tooltip: 'Poprzednia strona',
                onPressed: filters.page > 1
                    ? () => onApply(
                        filters.copyWith(page: filters.page - 1),
                        keepPage: true,
                      )
                    : null,
                icon: const Icon(Icons.chevron_left),
              ),
              Text('Strona ${filters.page} z $pages', style: mono),
              IconButton(
                tooltip: 'Następna strona',
                onPressed: filters.page < pages
                    ? () => onApply(
                        filters.copyWith(page: filters.page + 1),
                        keepPage: true,
                      )
                    : null,
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
