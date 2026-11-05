import 'package:data_table_2/data_table_2.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_error.dart';
import '../../../core/navigation/exit_guard.dart';
import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../../audit/data/audit_api.dart';
import '../../audit/presentation/verify_result_banner.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../data/admin_api.dart';
import '../data/admin_models.dart';
import '../data/validation.dart';
import 'admin_shell.dart';
import 'role_dialogs.dart';

/// `/admin/companies` — companies table + "Nowa spółka" / edit panel (§10.4).
class AdminCompaniesPage extends StatelessWidget {
  const AdminCompaniesPage({super.key});

  @override
  Widget build(BuildContext context) =>
      AdminGate(builder: (context, me) => _CompaniesView(me: me));
}

class _CompaniesView extends ConsumerStatefulWidget {
  const _CompaniesView({required this.me});

  final Me me;

  @override
  ConsumerState<_CompaniesView> createState() => _CompaniesViewState();
}

/// Which panel is open: none, the "new company" form, or a company's edit.
sealed class _Panel {
  const _Panel();
}

class _NoPanel extends _Panel {
  const _NoPanel();
}

class _NewPanel extends _Panel {
  const _NewPanel();
}

class _EditPanel extends _Panel {
  const _EditPanel(
    this.companyId, {
    this.notice,
    this.noticeIsWarning = false,
    this.created,
  });

  final String companyId;

  /// The company just created — shown until the refreshed list has it.
  final AdminCompany? created;

  /// Shown on top of the panel (e.g. right after creation).
  final String? notice;
  final bool noticeIsWarning;
}

class _CompaniesViewState extends ConsumerState<_CompaniesView> {
  _Panel _panel = const _NoPanel();

  /// A new key per opened panel: another company never reuses the state
  /// (controllers) of the previous one.
  var _panelKey = GlobalKey<_CompanyPanelState>();
  late final ExitGuard _exitGuard;

  @override
  void initState() {
    super.initState();
    _exitGuard = ref.read(exitGuardProvider)..current = _confirmExit;
    setLeaveWarning(() => _panelKey.currentState?.dirty ?? false);
  }

  @override
  void dispose() {
    if (_exitGuard.current == _confirmExit) _exitGuard.current = null;
    setLeaveWarning(null);
    super.dispose();
  }

  /// Leaving the page (another route): unsaved panel edits ask first.
  Future<bool> _confirmExit() async {
    final panel = _panelKey.currentState;
    if (panel == null || !panel.dirty || !mounted) return true;
    return confirmDiscard(context);
  }

  Future<void> _open(_Panel panel) async {
    final current = _panelKey.currentState;
    if (current != null && current.dirty && !await confirmDiscard(context)) {
      return;
    }
    if (mounted) {
      setState(() {
        _panel = panel;
        _panelKey = GlobalKey<_CompanyPanelState>();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final companies = ref.watch(adminCompaniesProvider);
    // Side panel only when the table keeps ~620 px next to it.
    final wide = MediaQuery.sizeOf(context).width >= 1400;
    final selectedId = switch (_panel) {
      _EditPanel(:final companyId) => companyId,
      _ => null,
    };
    final table = _CompaniesTable(
      companies: companies,
      selectedId: selectedId,
      onSelect: (company) => _open(_EditPanel(company.id)),
      onRetry: () => ref.invalidate(adminCompaniesProvider),
    );
    final panel = switch (_panel) {
      _NoPanel() => null,
      _NewPanel() => CompanyPanel(
        key: _panelKey,
        company: null,
        me: widget.me,
        onClose: () => _open(const _NoPanel()),
        onCreated: (company, notice, warning) => setState(() {
          _panel = _EditPanel(
            company.id,
            notice: notice,
            noticeIsWarning: warning,
            created: company,
          );
          _panelKey = GlobalKey<_CompanyPanelState>();
        }),
      ),
      _EditPanel(
        :final companyId,
        :final notice,
        :final noticeIsWarning,
        :final created,
      ) =>
        switch (companies.value?.where((c) => c.id == companyId).firstOrNull ??
            created) {
          null => null,
          final company => CompanyPanel(
            key: _panelKey,
            company: company,
            notice: notice,
            noticeIsWarning: noticeIsWarning,
            me: widget.me,
            onClose: () => _open(const _NoPanel()),
            onCreated: (_, _, _) {},
          ),
        },
    };

    return AdminTabsFrame(
      tab: AdminTab.companies,
      actions: [
        IconButton(
          tooltip: 'Odśwież',
          onPressed: () => ref.invalidate(adminCompaniesProvider),
          icon: const Icon(Icons.refresh),
        ),
        FilledButton.icon(
          key: const ValueKey('new-company'),
          onPressed: () => _open(const _NewPanel()),
          icon: const Icon(Icons.add),
          label: const Text('Nowa spółka'),
        ),
      ],
      children: [
        if (panel == null)
          table
        else if (wide)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: table),
              const SizedBox(width: 16),
              SizedBox(width: 480, child: panel),
            ],
          )
        else ...[
          panel,
          const SizedBox(height: 16),
          table,
        ],
      ],
    );
  }
}

// --------------------------------------------------------------------- table

class _CompaniesTable extends StatelessWidget {
  const _CompaniesTable({
    required this.companies,
    required this.selectedId,
    required this.onSelect,
    required this.onRetry,
  });

  final AsyncValue<List<AdminCompany>> companies;
  final String? selectedId;
  final ValueChanged<AdminCompany> onSelect;
  final VoidCallback onRetry;

  static const double _rowHeight = 60;

  @override
  Widget build(BuildContext context) {
    final rows = companies.value ?? const <AdminCompany>[];
    final mono = AppFonts.monoStyle(fontSize: 13);
    final body = switch (companies) {
      AsyncError(:final error) => Padding(
        padding: const EdgeInsets.all(16),
        child: ErrorPanel(error: error, onRetry: onRetry),
      ),
      AsyncData() || AsyncLoading(hasValue: true) => SizedBox(
        height: rows.isEmpty ? 160 : 48 + rows.length * _rowHeight + 8,
        child: DataTable2(
          key: const ValueKey('companies-table'),
          minWidth: 620,
          headingRowHeight: 48,
          dataRowHeight: _rowHeight,
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
              'Brak spółek. Dodaj pierwszą spółkę.',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
          columns: const [
            DataColumn2(label: Text('Spółka'), size: ColumnSize.L),
            DataColumn2(label: Text('Prefiks ID'), fixedWidth: 110),
            DataColumn2(label: Text('Obiekty'), fixedWidth: 80, numeric: true),
            DataColumn2(label: Text('Edytorzy'), fixedWidth: 84, numeric: true),
            DataColumn2(
              label: Text('Zatwierdzający'),
              fixedWidth: 124,
              numeric: true,
            ),
            DataColumn2(label: Text('Status'), fixedWidth: 130),
          ],
          rows: [
            for (final company in rows)
              DataRow2(
                key: ValueKey('company-row-${company.prefix}'),
                selected: company.id == selectedId,
                onTap: () => onSelect(company),
                cells: [
                  DataCell(
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          company.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w500),
                        ),
                        Text(
                          [
                            if (company.taxId != null) 'NIP ${company.taxId}',
                            if (company.isKscEntity) 'uoKSC',
                          ].join(' · '),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AppFonts.monoStyle(
                            fontSize: 12,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  DataCell(Text(company.prefix, style: mono)),
                  DataCell(
                    Tooltip(
                      message:
                          'Aktywne obiekty: ${company.counts.activeCi} '
                          '(wszystkie: ${company.counts.allCi})',
                      child: Text('${company.counts.activeCi}', style: mono),
                    ),
                  ),
                  DataCell(Text('${company.counts.editors}', style: mono)),
                  DataCell(Text('${company.counts.approvers}', style: mono)),
                  DataCell(
                    ActiveTag(
                      active: !company.isArchived,
                      activeLabel: 'Aktywna',
                      inactiveLabel: 'Zarchiwizowana',
                    ),
                  ),
                ],
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
          if (companies.isLoading && companies.hasValue)
            const LinearProgressIndicator(minHeight: 2),
          body,
        ],
      ),
    );
  }
}

// --------------------------------------------------------------------- panel

/// "Nowa spółka" ([company] null) or the edit panel of an existing company.
///
/// Creating is two API calls (ADR 0015 §3): `POST /companies`, then — if
/// categories were ticked — `PUT /companies/{id}/categories`. Per-category
/// approvers need the approver role in the company (ADR 0011 §4), so they
/// are set in the edit panel after the roles are granted.
class CompanyPanel extends ConsumerStatefulWidget {
  const CompanyPanel({
    required this.company,
    required this.me,
    required this.onClose,
    required this.onCreated,
    this.notice,
    this.noticeIsWarning = false,
    super.key,
  });

  final AdminCompany? company;
  final Me me;
  final String? notice;
  final bool noticeIsWarning;
  final VoidCallback onClose;
  final void Function(AdminCompany company, String notice, bool warning)
  onCreated;

  @override
  ConsumerState<CompanyPanel> createState() => _CompanyPanelState();
}

class _CompanyPanelState extends ConsumerState<CompanyPanel> {
  final _form = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.company?.name ?? '');
  late final _prefix = TextEditingController(
    text: widget.company?.prefix ?? '',
  );
  late final _nip = TextEditingController(text: widget.company?.taxId ?? '');
  late bool _ksc = widget.company?.isKscEntity ?? false;
  late String? _approverId = widget.company?.defaultApproverId;
  String? _approverName;

  /// Ticked categories of a new company (null = not initialised yet).
  Set<String>? _newCategories;

  final Map<String, String> _serverErrors = {};
  bool _busy = false;
  Object? _error;

  bool get _creating => widget.company == null;

  final _categoriesKey = GlobalKey<_CompanyCategoriesSectionState>();

  bool get _dataDirty {
    final c = widget.company;
    if (c == null) {
      return _name.text.trim().isNotEmpty ||
          _prefix.text.isNotEmpty ||
          _nip.text.trim().isNotEmpty ||
          _ksc ||
          _approverId != null;
    }
    return _name.text.trim() != c.name ||
        _nipValue != c.taxId ||
        _ksc != c.isKscEntity ||
        _approverId != c.defaultApproverId;
  }

  /// Unsaved edits anywhere in the panel.
  bool get dirty => _dataDirty || (_categoriesKey.currentState?.dirty ?? false);

  String? get _nipValue {
    final raw = _nip.text.trim();
    if (raw.isEmpty) return null;
    return validateNip(raw) == null ? normalizeNip(raw) : raw;
  }

  @override
  void dispose() {
    _name.dispose();
    _prefix.dispose();
    _nip.dispose();
    super.dispose();
  }

  void _changed() => setState(() => _serverErrors.clear());

  Future<void> _pickApprover() async {
    final user = await showUserPicker(
      context,
      title: 'Domyślny zatwierdzający',
    );
    if (user == null) return;
    setState(() {
      _approverId = user.id;
      _approverName = user.displayName;
    });
  }

  Future<void> _close() async {
    widget.onClose();
  }

  Map<String, String> _fieldErrors(ApiProblem problem) {
    final field = problem.field;
    final mapped = switch (problem.code) {
      'company.name_taken' => 'name',
      'company.prefix_taken' || 'company.prefix_immutable' => 'prefix',
      _ => field,
    };
    return {?mapped: problem.detail ?? problem.message};
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
      _serverErrors.clear();
    });
    final api = ref.read(adminApiProvider);
    try {
      if (_creating) {
        await _create(api);
      } else {
        await _save(api);
      }
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        _error = error;
        _serverErrors.addAll(_fieldErrors(problem));
      });
      _form.currentState?.validate();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _create(AdminApi api) async {
    final company = await api.createCompany({
      'name': _name.text.trim(),
      'prefix': _prefix.text,
      'tax_id': _nipValue,
      'is_ksc_entity': _ksc,
      'default_approver_id': _approverId,
    });
    final categories = _newCategories ?? const <String>{};
    var warning = false;
    var notice =
        'Utworzono spółkę ${company.name}. Następny krok: nadaj role '
        '(sekcja „Członkowie”), a potem — jeśli trzeba — wskaż '
        'zatwierdzających dla kategorii.';
    if (categories.isNotEmpty) {
      try {
        await api.setCompanyCategories(company.id, [
          for (final id in categories)
            (categoryId: id, approverOverrideId: null),
        ]);
      } on Object catch (error) {
        warning = true;
        notice =
            'Utworzono spółkę ${company.name}, ale nie zapisano kategorii: '
            '${ApiProblem.from(error).fullMessage} Zaznacz je ponownie w '
            'sekcji „Kategorie dostępne w spółce”.';
      }
    }
    ref.invalidate(adminCompaniesProvider);
    ref.invalidate(meProvider);
    if (!mounted) return;
    showInfoSnack(context, 'Utworzono spółkę ${company.name}.');
    widget.onCreated(company, notice, warning);
  }

  Future<void> _save(AdminApi api) async {
    final c = widget.company!;
    final fields = <String, Object?>{
      if (_name.text.trim() != c.name) 'name': _name.text.trim(),
      if (_nipValue != c.taxId) 'tax_id': _nipValue,
      if (_ksc != c.isKscEntity) 'is_ksc_entity': _ksc,
      if (_approverId != c.defaultApproverId)
        'default_approver_id': _approverId,
    };
    if (fields.isEmpty) return;
    await api.updateCompany(c.id, fields);
    ref.invalidate(adminCompaniesProvider);
    ref.invalidate(meProvider);
    if (mounted) showInfoSnack(context, 'Zapisano dane spółki.');
  }

  Future<void> _archive() async {
    final c = widget.company!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _ArchiveDialog(company: c),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(adminApiProvider).archiveCompany(c.id);
      ref.invalidate(adminCompaniesProvider);
      ref.invalidate(meProvider);
      if (mounted) showInfoSnack(context, 'Zarchiwizowano spółkę ${c.name}.');
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final company = widget.company;
    final year = WarsawTime.toWarsaw(DateTime.now()).year;
    final approverId = _approverId;
    final approverName =
        _approverName ??
        (approverId == null
            ? null
            : ref.watch(userDetailProvider(approverId)).value?.displayName);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          title: _creating ? 'Nowa spółka' : company!.name,
          trailing: IconButton(
            tooltip: 'Zamknij panel',
            onPressed: _close,
            icon: const Icon(Icons.close),
          ),
          child: Form(
            key: _form,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (widget.notice != null) ...[
                  MessageBanner(
                    key: const ValueKey('company-notice'),
                    kind: widget.noticeIsWarning
                        ? BannerKind.warning
                        : BannerKind.success,
                    message: widget.notice!,
                  ),
                  const SizedBox(height: 12),
                ],
                if (company?.isArchived ?? false) ...[
                  const MessageBanner(
                    kind: BannerKind.warning,
                    title: 'Spółka zarchiwizowana',
                    message:
                        'Rejestr zmian i inwentarz CI są tylko do odczytu. '
                        'Dane spółki, kategorie i role może nadal zmieniać '
                        'administrator.',
                  ),
                  const SizedBox(height: 12),
                ],
                TextFormField(
                  key: const ValueKey('company-name'),
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Nazwa *'),
                  maxLength: nameMaxLength,
                  onChanged: (_) => _changed(),
                  validator: (v) =>
                      _serverErrors['name'] ?? validateCompanyName(v ?? ''),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  key: const ValueKey('company-prefix'),
                  controller: _prefix,
                  readOnly: !_creating,
                  style: AppFonts.monoStyle(),
                  inputFormatters: [
                    _UpperCaseFormatter(),
                    LengthLimitingTextInputFormatter(8),
                  ],
                  decoration: InputDecoration(
                    labelText: 'Prefiks ID *',
                    helperText: _creating
                        ? 'Od 2 do 8 wielkich liter A–Z. Nie można go '
                              'później zmienić.'
                        : 'Prefiks jest niezmienny po utworzeniu spółki.',
                    suffixIcon: _creating
                        ? null
                        : const Tooltip(
                            message: 'Prefiks jest niezmienny',
                            child: Icon(Icons.lock_outline),
                          ),
                    fillColor: _creating ? null : AppColors.surfaceMuted,
                  ),
                  onChanged: (_) => _changed(),
                  validator: (v) =>
                      _serverErrors['prefix'] ??
                      (_creating ? validatePrefix(v ?? '') : null),
                ),
                const SizedBox(height: 6),
                Text.rich(
                  key: const ValueKey('prefix-preview'),
                  TextSpan(
                    children: [
                      const TextSpan(
                        text: 'Przykładowy numer zmiany: ',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                      TextSpan(
                        text: exampleChangeNumber(
                          companyPrefixRule.hasMatch(_prefix.text)
                              ? _prefix.text
                              : '',
                          year,
                        ),
                        style: AppFonts.monoStyle(fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  key: const ValueKey('company-nip'),
                  controller: _nip,
                  style: AppFonts.monoStyle(),
                  decoration: const InputDecoration(
                    labelText: 'NIP',
                    helperText:
                        'Opcjonalny; 10 cyfr z poprawną sumą kontrolną.',
                  ),
                  onChanged: (_) => _changed(),
                  validator: (v) =>
                      _serverErrors['tax_id'] ?? validateNip(v ?? ''),
                ),
                const SizedBox(height: 12),
                _ApproverField(
                  name: approverId == null ? null : (approverName ?? '…'),
                  error: _serverErrors['default_approver_id'],
                  onPick: _pickApprover,
                  onClear: () => setState(() {
                    _approverId = null;
                    _approverName = null;
                  }),
                ),
                const SizedBox(height: 4),
                CheckboxListTile(
                  key: const ValueKey('company-ksc'),
                  value: _ksc,
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  title: const Text('Podmiot objęty uoKSC'),
                  subtitle: const Text(
                    'Zmiany wymagają wtedy podstawy/wymogu i osoby '
                    'weryfikującej.',
                  ),
                  onChanged: (v) => setState(() => _ksc = v ?? false),
                ),
                if (_creating) ...[
                  const SizedBox(height: 8),
                  _NewCompanyCategories(
                    selected: _newCategories,
                    onChanged: (value) =>
                        setState(() => _newCategories = value),
                  ),
                ],
                if (_error != null && _serverErrors.isEmpty) ...[
                  const SizedBox(height: 12),
                  ErrorPanel(error: _error!),
                ],
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.end,
                  children: [
                    OutlinedButton(
                      onPressed: _busy ? null : _close,
                      child: const Text('Anuluj'),
                    ),
                    FilledButton(
                      key: const ValueKey('company-save'),
                      onPressed: _busy || (!_creating && !_dataDirty)
                          ? null
                          : _submit,
                      child: Text(_creating ? 'Utwórz spółkę' : 'Zapisz dane'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        if (company != null) ...[
          const SizedBox(height: 16),
          _CompanyCategoriesSection(
            key: _categoriesKey,
            company: company,
            onDirtyChanged: () => setState(() {}),
          ),
          const SizedBox(height: 16),
          CompanyMembersSection(company: company, me: widget.me),
          const SizedBox(height: 16),
          _ChainSection(company: company),
          if (!company.isArchived) ...[
            const SizedBox(height: 16),
            SectionCard(
              title: 'Archiwizacja',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Spółek się nie usuwa — archiwizacja zamraża rejestr i '
                    'inwentarz, historia pozostaje dostępna.',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    key: const ValueKey('company-archive'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.danger,
                    ),
                    onPressed: _busy ? null : _archive,
                    icon: const Icon(Icons.archive_outlined),
                    label: const Text('Archiwizuj spółkę'),
                  ),
                ],
              ),
            ),
          ],
        ],
      ],
    );
  }
}

class _UpperCaseFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) => newValue.copyWith(text: newValue.text.toUpperCase());
}

class _ApproverField extends StatelessWidget {
  const _ApproverField({
    required this.name,
    required this.onPick,
    required this.onClear,
    this.error,
  });

  final String? name;
  final String? error;
  final VoidCallback onPick;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return InputDecorator(
      decoration: InputDecoration(
        labelText: 'Domyślny zatwierdzający',
        helperText:
            'Podpowiadany w nowych zmianach, gdy kategoria nie ma własnego '
            'zatwierdzającego. Powinien mieć rolę zatwierdzającego w spółce.',
        helperMaxLines: 3,
        errorText: error,
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              name ?? 'nie wskazano',
              key: const ValueKey('company-approver'),
              style: TextStyle(
                color: name == null ? AppColors.textSecondary : AppColors.text,
              ),
            ),
          ),
          TextButton(
            key: const ValueKey('company-approver-pick'),
            onPressed: onPick,
            child: const Text('Wybierz'),
          ),
          if (name != null)
            IconButton(
              tooltip: 'Usuń domyślnego zatwierdzającego',
              onPressed: onClear,
              icon: const Icon(Icons.close, size: 18),
            ),
        ],
      ),
    );
  }
}

/// Rule of a category for the checkbox lists (§10.4).
String approvalRule(Category category) => [
  category.requiresApproval
      ? 'wymaga zatwierdzenia'
      : 'standard — bez zatwierdzenia',
  if (category.requiresCiOwnerConsent) 'zgoda właściciela CI',
].join(' · ');

/// Category checkboxes of a NEW company (top-level, active).
class _NewCompanyCategories extends ConsumerWidget {
  const _NewCompanyCategories({
    required this.selected,
    required this.onChanged,
  });

  final Set<String>? selected;
  final ValueChanged<Set<String>> onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final all = ref.watch(allCategoriesProvider);
    return switch (all) {
      AsyncError(:final error) => ErrorPanel(
        error: error,
        onRetry: () => ref.invalidate(allCategoriesProvider),
      ),
      AsyncData(:final value) => () {
        final top = [
          for (final c in value)
            if (c.parentId == null && c.isActive) c,
        ];
        final current = selected ?? {for (final c in top) c.id};
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Text(
                  'Kategorie dostępne w spółce',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                Wrap(
                  children: [
                    TextButton(
                      onPressed: () => onChanged({for (final c in top) c.id}),
                      child: const Text('Wszystkie'),
                    ),
                    TextButton(
                      onPressed: () => onChanged({}),
                      child: const Text('Żadna'),
                    ),
                  ],
                ),
              ],
            ),
            const Text(
              'Podkategorie są dostępne razem z kategorią. Zatwierdzających '
              'dla kategorii wskażesz po nadaniu ról w spółce.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            for (final category in top)
              CheckboxListTile(
                key: ValueKey('new-category-${category.code}'),
                value: current.contains(category.id),
                dense: true,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: '${category.code}  ',
                        style: AppFonts.monoStyle(fontWeight: FontWeight.w500),
                      ),
                      TextSpan(text: category.name),
                    ],
                  ),
                ),
                subtitle: Text(approvalRule(category)),
                onChanged: (checked) {
                  final next = {...current};
                  if (checked ?? false) {
                    next.add(category.id);
                  } else {
                    next.remove(category.id);
                  }
                  onChanged(next);
                },
              ),
          ],
        );
      }(),
      _ => const LoadingPanel(label: 'Wczytywanie kategorii…'),
    };
  }
}

/// Categories available in an existing company + per-category approver
/// (`PUT /companies/{id}/categories`, full list).
class _CompanyCategoriesSection extends ConsumerStatefulWidget {
  const _CompanyCategoriesSection({
    required this.company,
    required this.onDirtyChanged,
    super.key,
  });

  final AdminCompany company;
  final VoidCallback onDirtyChanged;

  @override
  ConsumerState<_CompanyCategoriesSection> createState() =>
      _CompanyCategoriesSectionState();
}

class _CompanyCategoriesSectionState
    extends ConsumerState<_CompanyCategoriesSection> {
  /// category id → approver override (null = company default).
  Map<String, String?>? _edited;
  Map<String, String?>? _saved;
  bool _busy = false;
  Object? _error;

  bool get dirty {
    final edited = _edited;
    final saved = _saved;
    if (edited == null || saved == null) return false;
    if (edited.length != saved.length) return true;
    for (final entry in edited.entries) {
      if (!saved.containsKey(entry.key) || saved[entry.key] != entry.value) {
        return true;
      }
    }
    return false;
  }

  void _update(void Function(Map<String, String?>) change) {
    setState(() => change(_edited!));
    widget.onDirtyChanged();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await ref.read(adminApiProvider).setCompanyCategories(
        widget.company.id,
        [
          for (final e in _edited!.entries)
            (categoryId: e.key, approverOverrideId: e.value),
        ],
      );
      final saved = {
        for (final c in result) c.categoryId: c.approverOverrideId,
      };
      setState(() {
        _saved = saved;
        _edited = {...saved};
      });
      ref.invalidate(companyCategoriesProvider(widget.company.id));
      widget.onDirtyChanged();
      if (mounted) showInfoSnack(context, 'Zapisano kategorie spółki.');
    } on Object catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final companyId = widget.company.id;
    final assigned = ref.watch(companyCategoriesProvider(companyId));
    final all = ref.watch(allCategoriesProvider);
    final members = ref.watch(membersProvider(companyId));
    final approvers = [
      for (final m in members.value ?? const <Member>[])
        if (m.canApprove && m.isActive) m,
    ];

    if (assigned case AsyncData(:final value) when _saved == null) {
      _saved = {for (final c in value) c.categoryId: c.approverOverrideId};
      _edited = {..._saved!};
    }
    final error = assigned.error ?? all.error;
    if (error != null) {
      return SectionCard(
        title: 'Kategorie dostępne w spółce',
        child: ErrorPanel(
          error: error,
          onRetry: () {
            ref.invalidate(companyCategoriesProvider(companyId));
            ref.invalidate(allCategoriesProvider);
          },
        ),
      );
    }
    final edited = _edited;
    final categories = all.value;
    if (edited == null || categories == null) {
      return const SectionCard(
        title: 'Kategorie dostępne w spółce',
        child: LoadingPanel(),
      );
    }
    final top = [
      for (final c in categories)
        if (c.parentId == null && (c.isActive || edited.containsKey(c.id))) c,
    ];
    final memberName = {
      for (final m in members.value ?? const <Member>[])
        m.userId: m.displayName,
    };

    return SectionCard(
      title: 'Kategorie dostępne w spółce',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            approvers.isEmpty
                ? 'Zatwierdzającego dla kategorii można wskazać spośród osób z '
                      'rolą zatwierdzającego w spółce — najpierw nadaj tę rolę '
                      '(sekcja „Członkowie”).'
                : 'Zatwierdzający kategorii zastępuje domyślnego '
                      'zatwierdzającego spółki. Do wyboru są osoby z rolą '
                      'zatwierdzającego w spółce.',
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 8),
          for (final category in top)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  CheckboxListTile(
                    key: ValueKey('company-category-${category.code}'),
                    value: edited.containsKey(category.id),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    // An inactive category can be kept but not added again.
                    enabled:
                        category.isActive || edited.containsKey(category.id),
                    title: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: '${category.code}  ',
                            style: AppFonts.monoStyle(
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          TextSpan(text: category.name),
                          if (!category.isActive)
                            const TextSpan(
                              text: '  (nieaktywna w słowniku)',
                              style: TextStyle(color: AppColors.danger),
                            ),
                        ],
                      ),
                    ),
                    subtitle: Text(approvalRule(category)),
                    onChanged: (checked) => _update((m) {
                      if (checked ?? false) {
                        m[category.id] = null;
                      } else {
                        m.remove(category.id);
                      }
                    }),
                  ),
                  if (edited.containsKey(category.id) &&
                      category.requiresApproval)
                    Padding(
                      padding: const EdgeInsets.only(left: 48, bottom: 4),
                      child: DropdownButtonFormField<String?>(
                        key: ValueKey('override-${category.code}'),
                        initialValue: edited[category.id],
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Zatwierdzający dla kategorii',
                          isDense: true,
                        ),
                        items: [
                          const DropdownMenuItem<String?>(
                            child: Text('domyślny zatwierdzający spółki'),
                          ),
                          for (final m in approvers)
                            DropdownMenuItem<String?>(
                              value: m.userId,
                              child: Text(m.displayName),
                            ),
                          // Stale override (e.g. role revoked): still shown.
                          if (edited[category.id] != null &&
                              !approvers.any(
                                (m) => m.userId == edited[category.id],
                              ))
                            DropdownMenuItem<String?>(
                              value: edited[category.id],
                              child: Text(
                                '${memberName[edited[category.id]] ?? 'osoba spoza spółki'} '
                                '(bez roli zatwierdzającego)',
                              ),
                            ),
                        ],
                        onChanged: (value) =>
                            _update((m) => m[category.id] = value),
                      ),
                    ),
                ],
              ),
            ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            ErrorPanel(error: _error!),
          ],
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton(
              key: const ValueKey('company-categories-save'),
              onPressed: _busy || !dirty ? null : _save,
              child: const Text('Zapisz kategorie'),
            ),
          ),
        ],
      ),
    );
  }
}

/// Members of a company with their roles (`GET /companies/{id}/members`);
/// roles are set as a FULL set (`PUT …/members/{user_id}`).
class CompanyMembersSection extends ConsumerWidget {
  const CompanyMembersSection({
    required this.company,
    required this.me,
    super.key,
  });

  final AdminCompany company;
  final Me me;

  Future<void> _edit(
    BuildContext context,
    WidgetRef ref, {
    required String userId,
    required String name,
    required List<String> current,
    required bool active,
  }) async {
    final roles = await showRoleEditor(
      context,
      companyName: company.name,
      userName: name,
      current: current,
      isSelf: userId == me.id,
      userActive: active,
    );
    if (roles == null || !context.mounted) return;
    try {
      await ref
          .read(adminApiProvider)
          .setMemberRoles(company.id, userId, roles);
      ref.invalidate(membersProvider(company.id));
      ref.invalidate(adminCompaniesProvider);
      ref.invalidate(userDetailProvider(userId));
      if (userId == me.id) ref.invalidate(meProvider);
      if (context.mounted) {
        showInfoSnack(
          context,
          roles.isEmpty
              ? 'Odebrano wszystkie role: $name.'
              : 'Zapisano role: $name.',
        );
      }
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final members = ref.watch(membersProvider(company.id));
    return SectionCard(
      title: 'Członkowie i role',
      trailing: OutlinedButton.icon(
        key: const ValueKey('member-add'),
        onPressed: () async {
          final existing = {
            for (final m in members.value ?? const <Member>[]) m.userId,
          };
          final user = await showUserPicker(
            context,
            title: 'Dodaj osobę do spółki',
            excludeIds: existing,
          );
          if (user == null || !context.mounted) return;
          await _edit(
            context,
            ref,
            userId: user.id,
            name: user.displayName,
            current: const [],
            active: user.isActive,
          );
        },
        icon: const Icon(Icons.person_add_alt_outlined),
        label: const Text('Dodaj osobę'),
      ),
      child: switch (members) {
        AsyncError(:final error) => ErrorPanel(
          error: error,
          onRetry: () => ref.invalidate(membersProvider(company.id)),
        ),
        AsyncData(:final value) when value.isEmpty => const Text(
          'Spółka nie ma jeszcze członków.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        AsyncData(:final value) => Column(
          children: [
            for (final member in value)
              ListTile(
                key: ValueKey('member-${member.userId}'),
                contentPadding: EdgeInsets.zero,
                title: Text(
                  member.isActive
                      ? member.displayName
                      : '${member.displayName} (nieaktywny)',
                ),
                subtitle: Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: [
                    for (final role in membershipRoles)
                      if (member.roles.contains(role))
                        Tag(label: Roles.label(role)),
                  ],
                ),
                trailing: TextButton(
                  onPressed: () => _edit(
                    context,
                    ref,
                    userId: member.userId,
                    name: member.displayName,
                    current: member.roles,
                    active: member.isActive,
                  ),
                  child: const Text('Zmień role'),
                ),
              ),
          ],
        ),
        _ => const LoadingPanel(),
      },
    );
  }
}

class _ChainSection extends ConsumerStatefulWidget {
  const _ChainSection({required this.company});

  final AdminCompany company;

  @override
  ConsumerState<_ChainSection> createState() => _ChainSectionState();
}

class _ChainSectionState extends ConsumerState<_ChainSection> {
  bool _busy = false;

  Future<void> _verify() async {
    setState(() => _busy = true);
    try {
      final result = await ref.read(auditApiProvider).verify(widget.company.id);
      if (!mounted) return;
      await showVerifyResultDialog(context, result);
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Route segments built from data are encoded, like in router.dart.
    final prefix = Uri.encodeComponent(widget.company.prefix);
    return SectionCard(
      title: 'Dziennik audytu spółki',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Weryfikacja przelicza łańcuch skrótów i zapisuje swój wynik w '
            'dzienniku. Administrator przegląda dziennik każdej spółki.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                key: const ValueKey('company-verify'),
                onPressed: _busy ? null : _verify,
                icon: const Icon(Icons.verified_outlined),
                label: const Text('Zweryfikuj łańcuch'),
              ),
              OutlinedButton(
                key: const ValueKey('company-open-audit'),
                onPressed: () => context.go('/c/$prefix/audit'),
                child: const Text('Dziennik audytu'),
              ),
              OutlinedButton(
                key: const ValueKey('company-open-ci'),
                onPressed: () => context.go('/c/$prefix/ci'),
                child: const Text('Obiekty (CI)'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ArchiveDialog extends StatefulWidget {
  const _ArchiveDialog({required this.company});

  final AdminCompany company;

  @override
  State<_ArchiveDialog> createState() => _ArchiveDialogState();
}

class _ArchiveDialogState extends State<_ArchiveDialog> {
  final _confirm = TextEditingController();

  @override
  void dispose() {
    _confirm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final prefix = widget.company.prefix;
    return AlertDialog(
      title: Text('Archiwizować spółkę ${widget.company.name}?'),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Skutki archiwizacji:'),
              const SizedBox(height: 6),
              for (final line in const [
                'nie można tworzyć nowych zmian ani wykonywać akcji na '
                    'istniejących — rejestr zmian jest tylko do odczytu;',
                'nie można dodawać komentarzy ani załączników;',
                'inwentarz obiektów (CI) zostaje zamrożony;',
                'członkowie zachowują dostęp do odczytu historii i dziennika '
                    'audytu;',
                'archiwizacji nie można cofnąć w aplikacji; zostanie zapisana '
                    'w dzienniku audytu.',
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $line'),
                ),
              const SizedBox(height: 12),
              Text('Aby potwierdzić, wpisz prefiks spółki ($prefix):'),
              const SizedBox(height: 6),
              TextField(
                key: const ValueKey('archive-confirm-prefix'),
                controller: _confirm,
                style: AppFonts.monoStyle(),
                onChanged: (_) => setState(() {}),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          key: const ValueKey('archive-confirm'),
          style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
          onPressed: _confirm.text.trim().toUpperCase() == prefix
              ? () => Navigator.pop(context, true)
              : null,
          child: const Text('Archiwizuj'),
        ),
      ],
    );
  }
}
