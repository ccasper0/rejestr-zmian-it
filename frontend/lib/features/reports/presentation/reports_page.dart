import 'dart:async';

import 'package:data_table_2/data_table_2.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/change_status.dart';
import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../../../widgets/company_scope.dart';
import '../../admin/presentation/admin_shell.dart' show NoAccessPanel;
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../../changes/data/register_filters.dart';
import '../../changes/presentation/pickers.dart';
import '../data/report_form.dart';
import '../data/report_models.dart';
import '../data/reports_api.dart';
import 'report_export.dart';

/// "Raporty i eksport" (§10 screen 5, ADR 0017 §10).
///
/// - `/c/{PREFIX}/reports` — register report of one company (approver,
///   auditor, app admin — also without a role, ADR 0017 §4) and the list of
///   its reports; the editor sees only change cards; the viewer has no
///   access;
/// - `/c/all/reports` — the auditor's multi-company report (`company_id =
///   null`: every company where the user is an auditor).
///
/// The register's filters arrive in the query string (button "Eksport PDF"
/// of the register) and only pre-fill the form.
class ReportsPage extends ConsumerWidget {
  const ReportsPage({
    required this.prefix,
    this.initial = const RegisterFilters(),
    super.key,
  });

  final String prefix;
  final RegisterFilters initial;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (prefix == allCompaniesPrefix) {
      return switch (ref.watch(meProvider)) {
        AsyncData(:final value) =>
          value.isAuditor
              ? ReportsView(
                  key: const ValueKey('reports-all'),
                  scope: ReportScope.allCompanies(value),
                  initial: initial,
                )
              : const NoAccessPanel(
                  message:
                      'Raport zbiorczy „Wszystkie spółki” jest dostępny tylko '
                      'dla użytkowników z rolą audytora.',
                ),
        AsyncError(:final error) => PageBody(
          children: [
            ErrorPanel(error: error, onRetry: () => ref.invalidate(meProvider)),
          ],
        ),
        _ => const LoadingPanel(),
      };
    }
    return AdminAwareCompanyGate(
      prefix: prefix,
      section: 'reports',
      builder: (context, me, company) {
        final scope = ReportScope.company(me, company);
        if (!scope.canExportCard) {
          return const NoAccessPanel(
            message:
                'Raporty i eksport są dostępne dla zatwierdzających, '
                'audytorów i administratorów, a karty zmian w PDF — także dla '
                'edytorów. Rola obserwatora nie obejmuje eksportu.',
          );
        }
        return ReportsView(
          key: ValueKey('reports-${company.id}'),
          scope: scope,
          initial: initial,
        );
      },
    );
  }
}

/// What the screen works on and what the user may do there (matrix §5).
@immutable
class ReportScope {
  const ReportScope({
    required this.companyId,
    required this.title,
    required this.companies,
    required this.canExportRegister,
    required this.canExportCard,
    this.adminPath = false,
  });

  factory ReportScope.company(Me me, CompanyRef company) {
    final register = company.adminPath || me.canExportRegister(company.prefix);
    return ReportScope(
      companyId: company.id,
      title: company.name,
      companies: [company.name],
      adminPath: company.adminPath,
      canExportRegister: register,
      canExportCard: register || me.canExportChangeCard(company.prefix),
    );
  }

  factory ReportScope.allCompanies(Me me) => ReportScope(
    companyId: null,
    title: allCompaniesLabel,
    companies: [for (final m in me.auditorMemberships) m.companyName],
    canExportRegister: true,
    canExportCard: true,
  );

  /// null = the auditor's multi-company report.
  final String? companyId;
  final String title;
  final List<String> companies;
  final bool canExportRegister;
  final bool canExportCard;

  /// The app admin without a role in the company (ADR 0017 §4).
  final bool adminPath;

  bool get isAggregate => companyId == null;
}

class ReportsView extends ConsumerStatefulWidget {
  const ReportsView({required this.scope, required this.initial, super.key});

  final ReportScope scope;
  final RegisterFilters initial;

  @override
  ConsumerState<ReportsView> createState() => _ReportsViewState();
}

class _ReportsViewState extends ConsumerState<ReportsView> {
  late ReportForm _form = ReportForm.fromRegister(widget.initial);
  late final TextEditingController _search = TextEditingController(
    text: _form.q,
  );
  int _offset = 0;
  bool _generating = false;
  Object? _generateError;

  /// The report ordered on this screen (result banner).
  Report? _ordered;

  /// Latest known state of reports polled on this screen (by id).
  final Map<String, Report> _live = {};
  final Set<String> _watching = {};

  /// Pending reports whose polling stopped (time limit, network error).
  final Set<String> _stalled = {};

  /// Ordered here and still pending: saved as soon as they are done.
  final Set<String> _autoDownload = {};
  String? _downloading;

  ReportScope get _scope => widget.scope;

  ReportListKey get _listKey => (
    companyId: _scope.companyId,
    kind: _scope.canExportRegister ? null : ReportKinds.changeCard,
    offset: _offset,
  );

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Report _effective(Report report) => _live[report.id] ?? report;

  void _setForm(ReportForm form) => setState(() => _form = form);

  /// Starts polling every pending report that is not polled yet. Polling
  /// stops when the screen is left (`mounted`), on `done`/`failed` and after
  /// [ReportPolling.timeout].
  void _watchPending(Iterable<Report> reports) {
    for (final report in reports) {
      final current = _effective(report);
      if (!current.isPending ||
          _watching.contains(current.id) ||
          _stalled.contains(current.id)) {
        continue;
      }
      _watching.add(current.id);
      unawaited(_watch(current));
    }
  }

  Future<void> _watch(Report report) async {
    final id = report.id;
    try {
      final done = await waitForReport(
        ref.read(reportsApiProvider),
        ref.read(reportPollingProvider),
        report,
        isActive: () => mounted,
        onUpdate: (r) {
          if (mounted) setState(() => _live[r.id] = r);
        },
      );
      if (!mounted || done == null) return;
      ref.invalidate(reportListProvider);
      if (_autoDownload.remove(id)) await _download(done);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        if (problem.code != 'report.failed') _stalled.add(id);
      });
      if (_autoDownload.remove(id)) showErrorSnack(context, problem);
      ref.invalidate(reportListProvider);
    } finally {
      _watching.remove(id);
    }
  }

  Future<void> _generate() async {
    if (!_form.isValid || _generating) return;
    setState(() {
      _generating = true;
      _generateError = null;
    });
    try {
      final report = await ref
          .read(reportsApiProvider)
          .create(_form.toRequest(companyId: _scope.companyId));
      if (!mounted) return;
      setState(() {
        _ordered = report;
        _live[report.id] = report;
        _offset = 0;
      });
      ref.invalidate(reportListProvider);
      if (report.isDone) {
        await _download(report);
      } else if (report.isPending) {
        _autoDownload.add(report.id);
        _watchPending([report]);
      }
    } on Object catch (error) {
      if (mounted) setState(() => _generateError = error);
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _download(Report report) async {
    setState(() => _downloading = report.id);
    try {
      final file = await ref.read(reportExporterProvider).download(report);
      if (mounted) showInfoSnack(context, 'Pobrano plik ${file.filename}.');
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _downloading = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final list = ref.watch(reportListProvider(_listKey));
    if (list.value case final page?) _watchPending(page.items);

    return PageBody(
      children: [
        PageHeader(
          title: 'Raporty i eksport',
          subtitle: _scope.title,
          actions: [
            IconButton(
              tooltip: 'Odśwież listę',
              onPressed: () => ref.invalidate(reportListProvider),
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        if (_scope.adminPath) ...[
          const SizedBox(height: 12),
          const MessageBanner(
            key: ValueKey('reports-admin-path'),
            message:
                'Nie masz roli w tej spółce. Eksport jest dozwolony dla '
                'administratora i zostanie zapisany w dzienniku audytu '
                'spółki jako eksport administratora.',
          ),
        ],
        const SizedBox(height: 16),
        if (_scope.canExportRegister)
          _ReportForm(
            scope: _scope,
            form: _form,
            search: _search,
            generating: _generating,
            onChanged: _setForm,
            onGenerate: _generate,
          )
        else
          const MessageBanner(
            key: ValueKey('reports-cards-only'),
            message:
                'Raport rejestru (PDF i CSV) generują zatwierdzający, '
                'audytorzy i administratorzy. Kartę zmiany w PDF wygenerujesz '
                'przyciskiem „Karta PDF” na karcie zmiany — pojawi się na tej '
                'liście.',
          ),
        if (_generateError != null) ...[
          const SizedBox(height: 12),
          KeyedSubtree(
            key: const ValueKey('report-error'),
            child: ErrorPanel(error: _generateError!),
          ),
        ],
        if (_ordered case final ordered?) ...[
          const SizedBox(height: 12),
          _OrderedBanner(report: _effective(ordered)),
        ],
        const SizedBox(height: 16),
        _ReportList(
          scope: _scope,
          list: list,
          offset: _offset,
          effective: _effective,
          stalled: _stalled,
          downloading: _downloading,
          onDownload: _download,
          onPage: (offset) => setState(() => _offset = offset),
          onRetry: () => ref.invalidate(reportListProvider(_listKey)),
        ),
      ],
    );
  }
}

// --------------------------------------------------------------------- form

class _ReportForm extends ConsumerWidget {
  const _ReportForm({
    required this.scope,
    required this.form,
    required this.search,
    required this.generating,
    required this.onChanged,
    required this.onGenerate,
  });

  final ReportScope scope;
  final ReportForm form;
  final TextEditingController search;
  final bool generating;
  final ValueChanged<ReportForm> onChanged;
  final VoidCallback onGenerate;

  static String _summary(List<String> labels) {
    if (labels.isEmpty) return '';
    if (labels.length == 1) return labels.first;
    return '${labels.first} +${labels.length - 1}';
  }

  Future<String?> _pickDay(
    BuildContext context,
    String? current,
    String help,
  ) async {
    final instant = WarsawTime.startOfIsoDay(current) ?? DateTime.now();
    final local = WarsawTime.toWarsaw(instant);
    final now = WarsawTime.toWarsaw(DateTime.now());
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(local.year, local.month, local.day),
      firstDate: DateTime(2000),
      lastDate: DateTime(now.year + 5, 12, 31),
      helpText: help,
    );
    if (picked == null) return null;
    return '${picked.year}-${picked.month.toString().padLeft(2, '0')}-'
        '${picked.day.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final companyId = scope.companyId;
    final List<(String, String)> categoryOptions = companyId == null
        ? [
            for (final c
                in ref.watch(topCategoriesProvider).value ?? const <Category>[])
              (c.id, c.name),
          ]
        : [
            for (final c
                in ref.watch(companyCategoriesProvider(companyId)).value ??
                    const <CompanyCategory>[])
              (c.categoryId, c.name),
          ];
    final members = companyId == null
        ? const <Member>[]
        : ref.watch(membersProvider(companyId)).value ?? const <Member>[];
    String memberName(String id) => members
        .firstWhere(
          (m) => m.userId == id,
          orElse: () => Member(userId: id, displayName: 'wybrana osoba'),
        )
        .displayName;
    String categoryName(String id) => categoryOptions
        .firstWhere((o) => o.$1 == id, orElse: () => (id, 'wybrana'))
        .$2;

    final error = form.periodError;
    String day(String? iso) =>
        WarsawTime.formatDate(WarsawTime.startOfIsoDay(iso));

    return SectionCard(
      title: 'Nowy raport rejestru (PDF)',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: scope.isAggregate
                      ? 'Zakres: wszystkie spółki, w których masz rolę '
                            'audytora: '
                      : 'Spółka: ',
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
                TextSpan(
                  text: scope.companies.join(', '),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const _FieldLabel('Okres (czas polski, oba dni włącznie)'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              FilterButton(
                key: const ValueKey('report-from'),
                label: 'Od',
                value: form.from == null ? '' : day(form.from),
                onPressed: () async {
                  final picked = await _pickDay(context, form.from, 'Od dnia');
                  if (picked != null) onChanged(form.copyWith(from: picked));
                },
                onClear: () => onChanged(form.copyWith(from: null)),
              ),
              FilterButton(
                key: const ValueKey('report-to'),
                label: 'Do',
                value: form.to == null ? '' : day(form.to),
                onPressed: () async {
                  final picked = await _pickDay(context, form.to, 'Do dnia');
                  if (picked != null) onChanged(form.copyWith(to: picked));
                },
                onClear: () => onChanged(form.copyWith(to: null)),
              ),
              TextButton(
                key: const ValueKey('report-quarter'),
                onPressed: () {
                  final (from, to) = ReportForm.currentQuarter(DateTime.now());
                  onChanged(form.copyWith(from: from, to: to));
                },
                child: const Text('Bieżący kwartał'),
              ),
            ],
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                error,
                key: const ValueKey('report-period-error'),
                style: const TextStyle(color: AppColors.danger),
              ),
            ),
          const SizedBox(height: 16),
          const _FieldLabel('Okres według daty'),
          SegmentedButton<String>(
            key: const ValueKey('report-period-by'),
            showSelectedIcon: false,
            segments: const [
              ButtonSegment(value: 'created', label: Text('rejestracji')),
              ButtonSegment(value: 'implemented', label: Text('wdrożenia')),
            ],
            selected: {form.periodBy},
            onSelectionChanged: (value) =>
                onChanged(form.copyWith(periodBy: value.first)),
          ),
          const SizedBox(height: 16),
          const _FieldLabel('Filtry'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SizedBox(
                width: 300,
                child: TextField(
                  key: const ValueKey('report-search'),
                  controller: search,
                  onChanged: (value) => onChanged(form.copyWith(q: value)),
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    hintText: 'Szukaj: numer, tytuł, zgłoszenie',
                    isDense: true,
                  ),
                ),
              ),
              FilterButton(
                key: const ValueKey('report-filter-status'),
                label: 'Status',
                value: _summary([
                  for (final s in form.statuses)
                    ChangeStatus.tryParse(s)?.label ?? s,
                ]),
                onPressed: () async {
                  final picked = await showMultiSelectDialog(
                    context,
                    title: 'Status',
                    options: [
                      for (final s in ChangeStatus.values)
                        (s.apiValue, s.label),
                    ],
                    selected: form.statuses,
                  );
                  if (picked != null) {
                    onChanged(form.copyWith(statuses: picked));
                  }
                },
                onClear: () => onChanged(form.copyWith(statuses: const [])),
              ),
              FilterButton(
                key: const ValueKey('report-filter-type'),
                label: 'Typ',
                value: _summary([
                  for (final t in form.types) ChangeTypes.label(t),
                ]),
                onPressed: () async {
                  final picked = await showMultiSelectDialog(
                    context,
                    title: 'Typ zmiany',
                    options: [
                      for (final t in ChangeTypes.all)
                        (t, ChangeTypes.label(t)),
                    ],
                    selected: form.types,
                  );
                  if (picked != null) onChanged(form.copyWith(types: picked));
                },
                onClear: () => onChanged(form.copyWith(types: const [])),
              ),
              FilterButton(
                key: const ValueKey('report-filter-category'),
                label: 'Kategoria',
                value: _summary([
                  for (final id in form.categories) categoryName(id),
                ]),
                onPressed: () async {
                  final picked = await showMultiSelectDialog(
                    context,
                    title: 'Kategoria',
                    options: categoryOptions,
                    selected: form.categories,
                  );
                  if (picked != null) {
                    onChanged(form.copyWith(categories: picked));
                  }
                },
                onClear: () => onChanged(form.copyWith(categories: const [])),
              ),
              if (companyId != null) ...[
                FilterButton(
                  key: const ValueKey('report-filter-ci'),
                  label: 'Obiekt',
                  value: form.cis.isEmpty
                      ? ''
                      : form.cis.length == 1
                      ? '1 obiekt'
                      : '${form.cis.length} obiekty',
                  onPressed: () async {
                    final picked = await showCiFilterDialog(
                      context,
                      companyId: companyId,
                      selected: form.cis,
                    );
                    if (picked != null) onChanged(form.copyWith(cis: picked));
                  },
                  onClear: () => onChanged(form.copyWith(cis: const [])),
                ),
                FilterButton(
                  key: const ValueKey('report-filter-assignee'),
                  label: 'Wykonawca',
                  value: form.assignee == null
                      ? ''
                      : memberName(form.assignee!),
                  onPressed: () async {
                    final picked = await showSingleSelectDialog(
                      context,
                      title: 'Wykonawca',
                      options: [
                        for (final m in members)
                          if (m.canWrite) (m.userId, m.displayName),
                      ],
                      selected: form.assignee,
                    );
                    if (picked != null) {
                      onChanged(form.copyWith(assignee: picked.value));
                    }
                  },
                  onClear: () => onChanged(form.copyWith(assignee: null)),
                ),
              ],
              FilterButton(
                key: const ValueKey('report-filter-approved-by'),
                label: 'Zatwierdził',
                value: form.approvedBy == null
                    ? ''
                    : form.approvedBy == 'system'
                    ? 'system'
                    : companyId == null
                    ? ''
                    : memberName(form.approvedBy!),
                onPressed: () async {
                  final picked = await showSingleSelectDialog(
                    context,
                    title: 'Kto faktycznie zatwierdził',
                    options: [
                      ('system', 'system (automatycznie)'),
                      for (final m in members)
                        if (m.canApprove) (m.userId, m.displayName),
                    ],
                    selected: form.approvedBy,
                  );
                  if (picked != null) {
                    onChanged(form.copyWith(approvedBy: picked.value));
                  }
                },
                onClear: () => onChanged(form.copyWith(approvedBy: null)),
              ),
            ],
          ),
          if (scope.isAggregate)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Filtry obiektu i osób dotyczą jednej spółki — w raporcie '
                'zbiorczym są niedostępne.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ),
          const SizedBox(height: 12),
          CheckboxListTile(
            key: const ValueKey('report-include-audit'),
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            value: form.includeAuditTrail,
            onChanged: (value) =>
                onChanged(form.copyWith(includeAuditTrail: value ?? false)),
            title: const Text('Dołącz załącznik B — pełna ścieżka audytu'),
            subtitle: const Text(
              'Ścieżka audytu każdej zmiany z diffami; raport będzie znacznie '
              'dłuższy.',
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              FilledButton.icon(
                key: const ValueKey('report-generate'),
                onPressed: form.isValid && !generating ? onGenerate : null,
                icon: generating
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.onAccent,
                        ),
                      )
                    : const Icon(Icons.picture_as_pdf_outlined),
                label: Text(generating ? 'Generowanie…' : 'Generuj PDF'),
              ),
              const Text(
                'Duże raporty (powyżej 200 zmian) są generowane w tle — plik '
                'pobierze się, gdy będzie gotowy.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(text, style: const TextStyle(fontWeight: FontWeight.w600)),
  );
}

/// Result of the report ordered on this screen.
class _OrderedBanner extends StatelessWidget {
  const _OrderedBanner({required this.report});

  final Report report;

  @override
  Widget build(BuildContext context) {
    final count = report.changeCount == null
        ? ''
        : ' (zmian: ${report.changeCount})';
    if (report.isPending) {
      return MessageBanner(
        key: const ValueKey('report-ordered-pending'),
        title: 'Raport ${report.number} jest generowany w tle$count',
        message:
            'Plik zostanie pobrany automatycznie, gdy będzie gotowy, jeśli nie '
            'opuścisz tego ekranu. Później pobierzesz go z listy poniżej.',
      );
    }
    if (report.isFailed) {
      return MessageBanner(
        key: const ValueKey('report-ordered-failed'),
        kind: BannerKind.error,
        title: 'Generowanie raportu ${report.number} nie powiodło się',
        message: report.error ?? 'Wygeneruj raport ponownie.',
      );
    }
    return MessageBanner(
      key: const ValueKey('report-ordered-done'),
      kind: BannerKind.success,
      title: 'Wygenerowano raport ${report.number}$count',
      message: 'sha256 danych: ${report.dataSha256 ?? '—'}',
    );
  }
}

// --------------------------------------------------------------------- list

class _ReportList extends StatelessWidget {
  const _ReportList({
    required this.scope,
    required this.list,
    required this.offset,
    required this.effective,
    required this.stalled,
    required this.downloading,
    required this.onDownload,
    required this.onPage,
    required this.onRetry,
  });

  final ReportScope scope;
  final AsyncValue<PageResult<Report>> list;
  final int offset;
  final Report Function(Report) effective;
  final Set<String> stalled;
  final String? downloading;
  final ValueChanged<Report> onDownload;
  final ValueChanged<int> onPage;
  final VoidCallback onRetry;

  static const double _rowHeight = 68;
  static const double _headingHeight = 48;

  @override
  Widget build(BuildContext context) {
    final rows = [for (final r in list.value?.items ?? const <Report>[]) r];
    final body = switch (list) {
      AsyncError(:final error) => Padding(
        padding: const EdgeInsets.all(16),
        child: ErrorPanel(error: error, onRetry: onRetry),
      ),
      AsyncData() || AsyncLoading(hasValue: true) => SizedBox(
        height: rows.isEmpty
            ? 160
            : _headingHeight + rows.length * _rowHeight + 8,
        child: DataTable2(
          key: const ValueKey('reports-table'),
          minWidth: 1400,
          headingRowHeight: _headingHeight,
          dataRowHeight: _rowHeight,
          columnSpacing: 12,
          horizontalMargin: 12,
          dataTextStyle: const TextStyle(fontSize: 13, color: AppColors.text),
          headingTextStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            color: AppColors.textSecondary,
            fontSize: 13,
          ),
          empty: Center(
            child: Text(
              scope.canExportRegister
                  ? 'Nie wygenerowano jeszcze żadnego raportu.'
                  : 'Brak wygenerowanych kart zmian.',
              style: const TextStyle(color: AppColors.textSecondary),
            ),
          ),
          columns: const [
            DataColumn2(label: Text('Numer'), fixedWidth: 176),
            DataColumn2(label: Text('Rodzaj'), fixedWidth: 168),
            DataColumn2(label: Text('Okres'), size: ColumnSize.M),
            DataColumn2(label: Text('Spółka'), size: ColumnSize.M),
            DataColumn2(label: Text('Wygenerował'), size: ColumnSize.M),
            DataColumn2(label: Text('Kiedy'), fixedWidth: 136),
            DataColumn2(label: Text('Zmian'), fixedWidth: 64, numeric: true),
            DataColumn2(label: Text('SHA-256 danych'), fixedWidth: 176),
            DataColumn2(label: Text('Status'), size: ColumnSize.M),
            DataColumn2(label: Text(''), fixedWidth: 120),
          ],
          rows: [
            for (final row in rows)
              DataRow2(cells: _cells(context, effective(row))),
          ],
        ),
      ),
      _ => const LoadingPanel(label: 'Wczytywanie raportów…'),
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
            child: Semantics(
              header: true,
              child: Text(
                scope.canExportRegister
                    ? 'Wygenerowane raporty'
                    : 'Wygenerowane karty zmian',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          if (list.isLoading && list.hasValue)
            const LinearProgressIndicator(minHeight: 2),
          body,
          const Divider(),
          _Pager(total: list.value?.total, offset: offset, onPage: onPage),
        ],
      ),
    );
  }

  List<DataCell> _cells(BuildContext context, Report report) {
    const secondary = TextStyle(color: AppColors.textSecondary, fontSize: 12);
    final mono = AppFonts.monoStyle(fontSize: 12);
    return [
      DataCell(
        Text(
          report.number,
          style: AppFonts.monoStyle(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ),
      DataCell(
        Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${ReportKinds.label(report.kind)} '
              '(${report.format.toUpperCase()})',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            if (report.changeNumber != null)
              Text(
                report.changeNumber!,
                style: mono,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              )
            else if (report.includeAuditTrail)
              const Text(
                'z załącznikiem B',
                style: secondary,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
          ],
        ),
      ),
      DataCell(_PeriodCell(report: report)),
      DataCell(
        report.isAggregate
            ? Tooltip(
                message: report.companies.map((c) => c.name).join('\n'),
                child: Text(
                  'Wszystkie spółki (${report.companies.length})',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              )
            : Text(
                report.company?.name ?? '—',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
      ),
      DataCell(
        Text(
          report.generatedBy.displayName,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      DataCell(Text(WarsawTime.format(report.createdAt), style: mono)),
      DataCell(Text(report.changeCount?.toString() ?? '—', style: mono)),
      DataCell(HashText(hash: report.dataSha256)),
      DataCell(_StatusCell(report: report, stalled: stalled)),
      DataCell(
        TextButton.icon(
          key: ValueKey('report-download-${report.id}'),
          onPressed: report.isDone && downloading == null
              ? () => onDownload(report)
              : null,
          icon: downloading == report.id
              ? const SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.download_outlined, size: 18),
          label: const Text('Pobierz'),
        ),
      ),
    ];
  }
}

class _PeriodCell extends StatelessWidget {
  const _PeriodCell({required this.report});

  final Report report;

  @override
  Widget build(BuildContext context) {
    final from = report.periodFrom;
    final to = report.periodTo;
    if (from == null && to == null) {
      return const Text('—');
    }
    // `period_to` is exclusive: show the last day of the period.
    final last = to?.subtract(const Duration(microseconds: 1));
    final byImplementation = report.filters['period_by'] == 'implemented';
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${from == null ? '…' : WarsawTime.formatDate(from)} – '
          '${last == null ? '…' : WarsawTime.formatDate(last)}',
          style: AppFonts.monoStyle(fontSize: 12),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        Text(
          byImplementation ? 'wg daty wdrożenia' : 'wg daty rejestracji',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}

class _StatusCell extends StatelessWidget {
  const _StatusCell({required this.report, required this.stalled});

  final Report report;
  final Set<String> stalled;

  @override
  Widget build(BuildContext context) {
    if (report.isPending) {
      final paused = stalled.contains(report.id);
      return Row(
        key: ValueKey('report-status-pending-${report.id}'),
        children: [
          // A static icon: the row is refreshed by polling, an endless
          // spinner per row would only distract.
          Icon(
            paused ? Icons.pause_circle_outline : Icons.hourglass_top,
            size: 18,
            color: AppStatusColors.pendingApproval.foreground,
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              paused
                  ? 'Generowanie — odśwież listę, aby sprawdzić status'
                  : ReportStatuses.label(report.status),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      );
    }
    if (report.isFailed) {
      return Column(
        key: ValueKey('report-status-failed-${report.id}'),
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Tag(
            label: 'Błąd',
            colors: AppFeedbackColors.error,
            icon: Icons.error_outline,
          ),
          if (report.error != null)
            Tooltip(
              message: report.error,
              child: Text(
                report.error!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppColors.danger, fontSize: 12),
              ),
            ),
        ],
      );
    }
    return Align(
      alignment: Alignment.centerLeft,
      child: Tag(
        key: ValueKey('report-status-done-${report.id}'),
        label: ReportStatuses.label(report.status),
        colors: AppFeedbackColors.success,
        icon: Icons.check_circle_outline,
      ),
    );
  }
}

/// A sha256 shortened in the table; the full value in the tooltip and in
/// the clipboard (and selectable on the page).
class HashText extends StatelessWidget {
  const HashText({required this.hash, super.key});

  final String? hash;

  static String shorten(String hash) => hash.length <= 16
      ? hash
      : '${hash.substring(0, 8)}…${hash.substring(hash.length - 8)}';

  @override
  Widget build(BuildContext context) {
    final value = hash;
    if (value == null || value.isEmpty) return const Text('—');
    return Row(
      children: [
        Flexible(
          child: Tooltip(
            message: value,
            child: Text(
              shorten(value),
              style: AppFonts.monoStyle(fontSize: 12),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
        IconButton(
          tooltip: 'Kopiuj pełny skrót sha256',
          iconSize: 16,
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: value));
            if (context.mounted) showInfoSnack(context, 'Skopiowano skrót.');
          },
          icon: const Icon(Icons.copy_outlined),
        ),
      ],
    );
  }
}

class _Pager extends StatelessWidget {
  const _Pager({
    required this.total,
    required this.offset,
    required this.onPage,
  });

  final int? total;
  final int offset;
  final ValueChanged<int> onPage;

  @override
  Widget build(BuildContext context) {
    final total = this.total;
    final mono = AppFonts.monoStyle(fontSize: 13);
    final page = offset ~/ reportPageSize + 1;
    final pages = total == null
        ? 1
        : ((total + reportPageSize - 1) ~/ reportPageSize).clamp(1, 1 << 30);
    final last = total == null
        ? offset
        : (offset + reportPageSize).clamp(0, total);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Wrap(
        spacing: 16,
        runSpacing: 8,
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Text.rich(
            key: const ValueKey('reports-count'),
            total == null
                ? const TextSpan(text: 'Wczytywanie…')
                : total == 0
                ? TextSpan(
                    children: [
                      const TextSpan(text: 'Raportów: '),
                      TextSpan(text: '0', style: mono),
                    ],
                  )
                : TextSpan(
                    children: [
                      const TextSpan(text: 'Wyświetlono '),
                      TextSpan(text: '${offset + 1}–$last', style: mono),
                      const TextSpan(text: ' z '),
                      TextSpan(text: '$total', style: mono),
                    ],
                  ),
          ),
          Wrap(
            spacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              IconButton(
                key: const ValueKey('reports-prev'),
                tooltip: 'Poprzednia strona',
                onPressed: page > 1
                    ? () => onPage(offset - reportPageSize)
                    : null,
                icon: const Icon(Icons.chevron_left),
              ),
              Text('Strona $page z $pages', style: mono),
              IconButton(
                key: const ValueKey('reports-next'),
                tooltip: 'Następna strona',
                onPressed: page < pages
                    ? () => onPage(offset + reportPageSize)
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
