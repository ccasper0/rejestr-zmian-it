import 'dart:async';

import 'package:data_table_2/data_table_2.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_error.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../../../widgets/company_scope.dart';
import '../../admin/data/admin_api.dart';
import '../../admin/data/validation.dart';
import '../../admin/presentation/admin_shell.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../../changes/presentation/pickers.dart';
import '../data/ci_api.dart';
import '../data/ci_filters.dart';

/// The company the inventory screen works on.
class CiCompany {
  const CiCompany({
    required this.id,
    required this.name,
    required this.prefix,
    required this.archived,
    required this.canManage,
    this.adminPath = false,
  });

  final String id;
  final String name;
  final String prefix;
  final bool archived;

  /// Matrix §5 `ci.manage` (admin, approver, editor) and not archived.
  final bool canManage;

  /// The app admin without a role in the company (explicit admin path of
  /// the API, ADR 0011 §1).
  final bool adminPath;
}

/// `/c/:prefix/ci` — CI inventory of the company (§10, ADR 0015 §6).
///
/// The app admin manages the inventory of ANY company (§5) — also without a
/// role in it, through the admin path of the API.
class CiInventoryPage extends StatelessWidget {
  const CiInventoryPage({
    required this.prefix,
    required this.filters,
    super.key,
  });

  final String prefix;
  final CiFilters filters;

  @override
  Widget build(BuildContext context) => AdminAwareCompanyGate(
    prefix: prefix,
    section: 'ci',
    builder: (context, me, company) => CiInventoryView(
      company: CiCompany(
        id: company.id,
        name: company.name,
        prefix: company.prefix,
        archived: company.archived,
        canManage: me.canManageCi(prefix) && !company.archived,
        adminPath: company.adminPath,
      ),
      filters: filters,
    ),
  );
}

class CiInventoryView extends ConsumerStatefulWidget {
  const CiInventoryView({
    required this.company,
    required this.filters,
    super.key,
  });

  final CiCompany company;
  final CiFilters filters;

  @override
  ConsumerState<CiInventoryView> createState() => _CiInventoryViewState();
}

class _CiInventoryViewState extends ConsumerState<CiInventoryView> {
  late final _search = TextEditingController(text: widget.filters.q);
  Timer? _debounce;

  CiCompany get _company => widget.company;
  CiFilters get _filters => widget.filters;

  @override
  void didUpdateWidget(covariant CiInventoryView oldWidget) {
    super.didUpdateWidget(oldWidget);
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

  void _apply(CiFilters filters, {bool keepPage = false}) {
    final next = keepPage ? filters : filters.copyWith(page: 1);
    context.go(next.location(_company.prefix));
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      _debounce = null;
      if (value.trim() != _filters.q) {
        _apply(_filters.copyWith(q: value.trim()));
      }
    });
  }

  void _refresh() =>
      ref.invalidate(ciInventoryProvider((_company.id, _filters)));

  Future<void> _edit([CiItem? item]) async {
    final saved = await showFormDialog<CiItem>(
      context,
      builder: (context) => CiEditor(company: _company, item: item),
    );
    if (saved == null || !mounted) return;
    _refresh();
    ref.invalidate(adminCompaniesProvider);
    showInfoSnack(
      context,
      item == null
          ? 'Dodano obiekt ${saved.identifier}.'
          : 'Zapisano obiekt ${saved.identifier}.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final page = ref.watch(ciInventoryProvider((_company.id, _filters)));
    final types = ref.watch(ciTypesAllProvider).value ?? const <CiType>[];
    final members =
        ref.watch(membersProvider(_company.id)).value ?? const <Member>[];
    final owners = {for (final m in members) m.userId: m.displayName};
    final rows = page.value?.items ?? const <CiItem>[];
    final total = page.value?.total;
    final pages = total == null
        ? 1
        : ((total + CiFilters.pageSize - 1) ~/ CiFilters.pageSize).clamp(
            1,
            1 << 30,
          );
    String typeName(String code) =>
        types.where((t) => t.code == code).firstOrNull?.name ?? code;

    return PageBody(
      children: [
        PageHeader(
          title: _company.name,
          subtitle: 'Obiekty (CI)',
          actions: [
            IconButton(
              tooltip: 'Odśwież',
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
            ),
            if (_company.canManage)
              FilledButton.icon(
                key: const ValueKey('new-ci'),
                onPressed: _edit,
                icon: const Icon(Icons.add),
                label: const Text('Nowy obiekt'),
              ),
          ],
        ),
        if (_company.archived) ...[
          const SizedBox(height: 12),
          const MessageBanner(
            kind: BannerKind.warning,
            message:
                'Spółka jest zarchiwizowana — inwentarz jest tylko do odczytu.',
          ),
        ],
        if (_company.adminPath) ...[
          const SizedBox(height: 12),
          const MessageBanner(
            message:
                'Nie masz roli w tej spółce — zarządzasz inwentarzem jako '
                'administrator aplikacji. Operacje trafiają do dziennika '
                'audytu spółki.',
          ),
        ],
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 320,
              child: TextField(
                key: const ValueKey('ci-search'),
                controller: _search,
                onChanged: _onSearch,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'Szukaj: identyfikator, nazwa',
                  isDense: true,
                ),
              ),
            ),
            FilterButton(
              key: const ValueKey('ci-filter-type'),
              label: 'Typ',
              value: _filters.types.isEmpty
                  ? ''
                  : _filters.types.length == 1
                  ? typeName(_filters.types.first)
                  : '${typeName(_filters.types.first)} '
                        '+${_filters.types.length - 1}',
              onPressed: () async {
                final picked = await showMultiSelectDialog(
                  context,
                  title: 'Typ obiektu',
                  options: [for (final t in types) (t.code, t.name)],
                  selected: _filters.types,
                );
                if (picked != null) _apply(_filters.copyWith(types: picked));
              },
              onClear: () => _apply(_filters.copyWith(types: const [])),
            ),
            SegmentedButton<bool?>(
              key: const ValueKey('ci-filter-active'),
              showSelectedIcon: false,
              segments: const [
                ButtonSegment(value: null, label: Text('Wszystkie')),
                ButtonSegment(value: true, label: Text('Aktywne')),
                ButtonSegment(value: false, label: Text('Nieaktywne')),
              ],
              selected: {_filters.active},
              onSelectionChanged: (s) =>
                  _apply(_filters.copyWith(active: s.first)),
            ),
            if (_filters.hasFilters)
              TextButton.icon(
                key: const ValueKey('ci-filters-clear'),
                onPressed: () {
                  _search.clear();
                  _apply(const CiFilters());
                },
                icon: const Icon(Icons.filter_alt_off_outlined),
                label: const Text('Wyczyść filtry'),
              ),
          ],
        ),
        const SizedBox(height: 12),
        Card(
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (page.isLoading && page.hasValue)
                const LinearProgressIndicator(minHeight: 2),
              switch (page) {
                AsyncError(:final error) => Padding(
                  padding: const EdgeInsets.all(16),
                  child: ErrorPanel(error: error, onRetry: _refresh),
                ),
                AsyncData() || AsyncLoading(hasValue: true) => SizedBox(
                  height: rows.isEmpty ? 160 : 48 + rows.length * 56 + 8,
                  child: DataTable2(
                    key: const ValueKey('ci-table'),
                    minWidth: 820,
                    headingRowHeight: 48,
                    dataRowHeight: 56,
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
                        'Brak obiektów spełniających kryteria.',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    ),
                    columns: const [
                      DataColumn2(
                        label: Text('Identyfikator'),
                        fixedWidth: 160,
                      ),
                      DataColumn2(label: Text('Nazwa'), size: ColumnSize.L),
                      DataColumn2(label: Text('Typ')),
                      DataColumn2(label: Text('Właściciel')),
                      DataColumn2(label: Text('Status'), fixedWidth: 120),
                    ],
                    rows: [
                      for (final item in rows)
                        DataRow2(
                          key: ValueKey('ci-row-${item.identifier}'),
                          onTap: _company.canManage ? () => _edit(item) : null,
                          cells: [
                            DataCell(
                              Text(
                                item.identifier,
                                style: AppFonts.monoStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                            DataCell(
                              Tooltip(
                                message: item.description ?? '',
                                child: Text(
                                  item.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                            DataCell(
                              Text(
                                item.ciTypeName.isEmpty
                                    ? item.ciTypeCode
                                    : item.ciTypeName,
                              ),
                            ),
                            DataCell(
                              Text(
                                item.ownerUserId == null
                                    ? '—'
                                    : owners[item.ownerUserId] ?? '…',
                              ),
                            ),
                            DataCell(ActiveTag(active: item.isActive)),
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
                      key: const ValueKey('ci-count'),
                      total == null ? 'Wczytywanie…' : 'Obiektów: $total',
                    ),
                    Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        IconButton(
                          tooltip: 'Poprzednia strona',
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
                          tooltip: 'Następna strona',
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
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// New CI ([item] null) or edit, with deactivation (no deletion, ADR 0011).
class CiEditor extends ConsumerStatefulWidget {
  const CiEditor({required this.company, this.item, super.key});

  final CiCompany company;
  final CiItem? item;

  @override
  ConsumerState<CiEditor> createState() => _CiEditorState();
}

class _CiEditorState extends ConsumerState<CiEditor> {
  final _form = GlobalKey<FormState>();
  late final _identifier = TextEditingController(
    text: widget.item?.identifier ?? '',
  );
  late final _name = TextEditingController(text: widget.item?.name ?? '');
  late final _description = TextEditingController(
    text: widget.item?.description ?? '',
  );
  late String? _typeId = widget.item?.ciTypeId;
  late String? _ownerId = widget.item?.ownerUserId;
  late bool _active = widget.item?.isActive ?? true;
  final Map<String, String> _serverErrors = {};
  Object? _error;
  bool _busy = false;

  bool get _creating => widget.item == null;

  String? get _descriptionValue =>
      _description.text.trim().isEmpty ? null : _description.text.trim();

  Map<String, Object?> get _changes {
    final item = widget.item;
    if (item == null) return const {};
    return {
      if (_typeId != item.ciTypeId) 'ci_type_id': _typeId,
      if (_identifier.text.trim() != item.identifier)
        'identifier': _identifier.text.trim(),
      if (_name.text.trim() != item.name) 'name': _name.text.trim(),
      if (_descriptionValue != item.description)
        'description': _descriptionValue,
      if (_ownerId != item.ownerUserId) 'owner_user_id': _ownerId,
      if (_active != item.isActive) 'is_active': _active,
    };
  }

  bool get _dirty => _creating
      ? _identifier.text.trim().isNotEmpty ||
            _name.text.trim().isNotEmpty ||
            _description.text.trim().isNotEmpty ||
            _typeId != null ||
            _ownerId != null
      : _changes.isNotEmpty;

  @override
  void dispose() {
    _identifier.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  static String? _fieldOf(ApiProblem problem) => switch (problem.code) {
    'ci.identifier_taken' => 'identifier',
    'ci.owner_not_member' || 'ci.owner_locked_by_change' => 'owner_user_id',
    'ci.type_not_found' || 'ci.type_inactive' => 'ci_type_id',
    _ => problem.field,
  };

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
      _serverErrors.clear();
    });
    final api = ref.read(ciApiProvider);
    try {
      final saved = _creating
          ? await api.create(widget.company.id, {
              'ci_type_id': _typeId,
              'identifier': _identifier.text.trim(),
              'name': _name.text.trim(),
              'description': _descriptionValue,
              'owner_user_id': _ownerId,
            })
          : await api.update(widget.company.id, widget.item!.id, _changes);
      if (mounted) Navigator.pop(context, saved);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        _error = error;
        final field = _fieldOf(problem);
        if (field != null) {
          _serverErrors[field] = problem.detail ?? problem.message;
        }
      });
      _form.currentState?.validate();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final types = ref.watch(ciTypesAllProvider).value ?? const <CiType>[];
    final members =
        ref.watch(membersProvider(widget.company.id)).value ?? const <Member>[];
    final typeOptions = [
      for (final t in types)
        if (t.isActive || t.id == widget.item?.ciTypeId) t,
    ];
    final ownerOptions = [
      for (final m in members)
        if (m.isActive || m.userId == widget.item?.ownerUserId) m,
    ];
    return GuardedDialog(
      dirty: _dirty,
      child: AlertDialog(
        title: Text(
          _creating ? 'Nowy obiekt (CI)' : 'Obiekt ${widget.item!.identifier}',
        ),
        content: SizedBox(
          width: 520,
          child: Form(
            key: _form,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    key: const ValueKey('ci-type'),
                    initialValue: _typeId,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Typ *'),
                    items: [
                      for (final t in typeOptions)
                        DropdownMenuItem(
                          value: t.id,
                          child: Text(
                            t.isActive ? t.name : '${t.name} (nieaktywny)',
                          ),
                        ),
                    ],
                    onChanged: (v) => setState(() {
                      _typeId = v;
                      _serverErrors.remove('ci_type_id');
                    }),
                    validator: (v) =>
                        _serverErrors['ci_type_id'] ??
                        (v == null ? 'Wybierz typ obiektu.' : null),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    key: const ValueKey('ci-identifier'),
                    controller: _identifier,
                    style: AppFonts.monoStyle(),
                    maxLength: ciIdentifierMaxLength,
                    decoration: const InputDecoration(
                      labelText: 'Identyfikator *',
                      helperText:
                          'Np. FW-01; unikalny w spółce (bez względu na '
                          'wielkość liter).',
                    ),
                    onChanged: (_) =>
                        setState(() => _serverErrors.remove('identifier')),
                    validator: (v) =>
                        _serverErrors['identifier'] ??
                        validateName(v ?? '', max: ciIdentifierMaxLength),
                  ),
                  TextFormField(
                    key: const ValueKey('ci-name'),
                    controller: _name,
                    maxLength: nameMaxLength,
                    decoration: const InputDecoration(labelText: 'Nazwa *'),
                    onChanged: (_) =>
                        setState(() => _serverErrors.remove('name')),
                    validator: (v) =>
                        _serverErrors['name'] ?? validateName(v ?? ''),
                  ),
                  TextFormField(
                    key: const ValueKey('ci-description'),
                    controller: _description,
                    minLines: 2,
                    maxLines: 5,
                    maxLength: ciDescriptionMaxLength,
                    decoration: const InputDecoration(labelText: 'Opis'),
                    onChanged: (_) => setState(() {}),
                  ),
                  DropdownButtonFormField<String?>(
                    key: const ValueKey('ci-owner'),
                    initialValue: _ownerId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Właściciel',
                      helperText:
                          'Członek spółki (dowolna rola); wyraża zgodę na '
                          'zmiany w kategoriach wymagających zgody właściciela.',
                      helperMaxLines: 2,
                    ),
                    items: [
                      const DropdownMenuItem<String?>(child: Text('brak')),
                      for (final m in ownerOptions)
                        DropdownMenuItem<String?>(
                          value: m.userId,
                          child: Text(m.displayName),
                        ),
                    ],
                    onChanged: (v) => setState(() {
                      _ownerId = v;
                      _serverErrors.remove('owner_user_id');
                    }),
                    validator: (_) => _serverErrors['owner_user_id'],
                  ),
                  if (!_creating)
                    SwitchListTile(
                      key: const ValueKey('ci-active'),
                      value: _active,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Obiekt aktywny'),
                      subtitle: const Text(
                        'Obiektów się nie usuwa. Nieaktywnego nie można '
                        'wybrać w nowej zmianie.',
                      ),
                      onChanged: (v) => setState(() => _active = v),
                    ),
                  if (_error != null && _serverErrors.isEmpty) ...[
                    const SizedBox(height: 12),
                    ErrorPanel(error: _error!),
                  ],
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.maybePop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('ci-save'),
            onPressed: _busy || (!_creating && !_dirty) ? null : _submit,
            child: Text(_creating ? 'Dodaj' : 'Zapisz'),
          ),
        ],
      ),
    );
  }
}
