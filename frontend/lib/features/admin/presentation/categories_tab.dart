import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_error.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../data/admin_api.dart';
import '../data/validation.dart';
import 'admin_shell.dart';
import 'companies_tab.dart' show approvalRule;

/// Activity filter of the dictionary tabs (`?status=active|inactive`).
enum ActivityFilter {
  all(null, 'Wszystkie'),
  active('active', 'Aktywne'),
  inactive('inactive', 'Nieaktywne');

  const ActivityFilter(this.query, this.label);

  final String? query;
  final String label;

  static ActivityFilter parse(String? value) => switch (value) {
    'active' => active,
    'inactive' => inactive,
    _ => all,
  };

  bool matches(bool isActive) => switch (this) {
    all => true,
    active => isActive,
    inactive => !isActive,
  };
}

/// Segmented activity filter writing `?status=` into the URL.
class ActivityFilterBar extends StatelessWidget {
  const ActivityFilterBar({required this.value, required this.path, super.key});

  final ActivityFilter value;
  final String path;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<ActivityFilter>(
      key: const ValueKey('activity-filter'),
      showSelectedIcon: false,
      segments: [
        for (final f in ActivityFilter.values)
          ButtonSegment(value: f, label: Text(f.label)),
      ],
      selected: {value},
      onSelectionChanged: (selection) {
        final f = selection.first;
        context.go(
          Uri(
            path: path,
            queryParameters: f.query == null ? null : {'status': f.query},
          ).toString(),
        );
      },
    );
  }
}

/// `/admin/categories` — two-level tree of change categories (§4.1, §13).
class AdminCategoriesPage extends StatelessWidget {
  const AdminCategoriesPage({required this.filter, super.key});

  final ActivityFilter filter;

  @override
  Widget build(BuildContext context) =>
      AdminGate(builder: (context, me) => _CategoriesView(filter: filter));
}

class _CategoriesView extends ConsumerWidget {
  const _CategoriesView({required this.filter});

  final ActivityFilter filter;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(allCategoriesProvider);
    return AdminTabsFrame(
      tab: AdminTab.categories,
      actions: [
        IconButton(
          tooltip: 'Odśwież',
          onPressed: () => ref.invalidate(allCategoriesProvider),
          icon: const Icon(Icons.refresh),
        ),
        FilledButton.icon(
          key: const ValueKey('new-category'),
          onPressed: () => showCategoryEditor(context, ref),
          icon: const Icon(Icons.add),
          label: const Text('Nowa kategoria'),
        ),
      ],
      children: [
        const MessageBanner(
          message:
              'Podkategoria może tylko zaostrzyć wymóg zatwierdzenia: w '
              'kategorii wymagającej zatwierdzenia obowiązuje on także we '
              'wszystkich podkategoriach, a w kategorii standardowej '
              'podkategoria może go wprowadzić (np. konta uprzywilejowane). '
              'Kod i kategoria nadrzędna są niezmienne; kategorii się nie '
              'usuwa — dezaktywuje.',
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: ActivityFilterBar(value: filter, path: '/admin/categories'),
        ),
        const SizedBox(height: 12),
        switch (categories) {
          AsyncError(:final error) => ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(allCategoriesProvider),
          ),
          AsyncData(:final value) => CategoryTree(
            categories: value,
            filter: filter,
          ),
          _ => const LoadingPanel(),
        },
      ],
    );
  }
}

/// Tree: each top-level category followed by its subcategories. A parent
/// that does not match the filter is still shown (dimmed) when one of its
/// subcategories does.
class CategoryTree extends ConsumerWidget {
  const CategoryTree({
    required this.categories,
    required this.filter,
    super.key,
  });

  final List<Category> categories;
  final ActivityFilter filter;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final top = [
      for (final c in categories)
        if (c.parentId == null) c,
    ];
    final children = <String, List<Category>>{};
    for (final c in categories) {
      if (c.parentId != null) (children[c.parentId!] ??= []).add(c);
    }
    final rows = <Widget>[];
    for (final parent in top) {
      final subs = [
        for (final s in children[parent.id] ?? const <Category>[])
          if (filter.matches(s.isActive)) s,
      ];
      final parentMatches = filter.matches(parent.isActive);
      if (!parentMatches && subs.isEmpty) continue;
      rows.add(
        _CategoryRow(category: parent, parent: null, dimmed: !parentMatches),
      );
      for (final sub in subs) {
        rows.add(_CategoryRow(category: sub, parent: parent));
      }
    }
    return Card(
      child: rows.isEmpty
          ? const Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Brak kategorii spełniających kryteria.',
                style: TextStyle(color: AppColors.textSecondary),
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < rows.length; i++) ...[
                  if (i > 0) const Divider(),
                  rows[i],
                ],
              ],
            ),
    );
  }
}

const double _subIndent = 32;

class _CategoryRow extends ConsumerWidget {
  const _CategoryRow({
    required this.category,
    required this.parent,
    this.dimmed = false,
  });

  final Category category;
  final Category? parent;
  final bool dimmed;

  Future<void> _toggleActive(BuildContext context, WidgetRef ref) async {
    final activate = !category.isActive;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          activate
              ? 'Aktywować kategorię ${category.code}?'
              : 'Dezaktywować kategorię ${category.code}?',
        ),
        content: Text(
          activate
              ? 'Kategoria znów będzie dostępna dla nowych zmian w spółkach, '
                    'w których jest udostępniona.'
              : 'Nieaktywnej kategorii nie można wybrać w nowych zmianach ani '
                    'udostępnić kolejnej spółce. Istniejące zmiany ją '
                    'zachowują. ${parent == null ? 'Podkategorie nie są '
                              'dezaktywowane automatycznie.' : ''}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('toggle-confirm'),
            onPressed: () => Navigator.pop(context, true),
            child: Text(activate ? 'Aktywuj' : 'Dezaktywuj'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      await ref.read(adminApiProvider).updateCategory(category.id, {
        'is_active': activate,
      });
      ref.invalidate(allCategoriesProvider);
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sub = parent != null;
    final inherited = sub && parent!.requiresApproval;
    final rule = sub && inherited && !category.requiresApproval
        ? 'wymaga zatwierdzenia (z kategorii)'
        : approvalRule(category).split(' · ').first;
    final color = dimmed || !category.isActive
        ? AppColors.textSecondary
        : AppColors.text;
    final info = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: '${category.code}  ',
                style: AppFonts.monoStyle(
                  fontWeight: FontWeight.w500,
                  color: color,
                ),
              ),
              TextSpan(
                text: category.name,
                style: TextStyle(
                  color: color,
                  fontWeight: sub ? FontWeight.w400 : FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Wrap(
          spacing: 6,
          runSpacing: 4,
          children: [
            Tag(
              label: rule,
              colors: category.requiresApproval || inherited
                  ? AppFeedbackColors.info
                  : AppFeedbackColors.neutral,
            ),
            Tag(
              label:
                  'ryzyko domyślne: '
                  '${Risks.label(category.defaultRisk).toLowerCase()}',
            ),
            if (category.requiresCiOwnerConsent)
              const Tag(
                label: 'zgoda właściciela CI',
                colors: AppFeedbackColors.warning,
              ),
            if (!category.isActive)
              const ActiveTag(active: false, inactiveLabel: 'Nieaktywna'),
          ],
        ),
      ],
    );
    final actions = Wrap(
      spacing: 4,
      children: [
        if (!sub && category.isActive)
          TextButton(
            key: ValueKey('add-sub-${category.code}'),
            onPressed: () => showCategoryEditor(context, ref, parent: category),
            child: const Text('Dodaj podkategorię'),
          ),
        TextButton(
          key: ValueKey('edit-${category.code}'),
          onPressed: () => showCategoryEditor(
            context,
            ref,
            category: category,
            parent: parent,
          ),
          child: const Text('Edytuj'),
        ),
        TextButton(
          key: ValueKey('toggle-${category.code}'),
          style: TextButton.styleFrom(
            foregroundColor: category.isActive
                ? AppColors.danger
                : AppColors.accent,
          ),
          onPressed: () => _toggleActive(context, ref),
          child: Text(category.isActive ? 'Dezaktywuj' : 'Aktywuj'),
        ),
      ],
    );
    // Left-aligned rows; every subcategory has the same fixed indent.
    return Padding(
      key: ValueKey('category-${category.code}'),
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (sub)
            const SizedBox(
              width: _subIndent,
              child: Padding(
                padding: EdgeInsets.only(top: 2),
                child: Icon(
                  Icons.subdirectory_arrow_right,
                  size: 18,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) => constraints.maxWidth < 640
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [info, const SizedBox(height: 4), actions],
                    )
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: info),
                        const SizedBox(width: 12),
                        actions,
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

/// New category ([category] null; subcategory when [parent] is given) or
/// edit of an existing one (code and parent are read-only).
Future<void> showCategoryEditor(
  BuildContext context,
  WidgetRef ref, {
  Category? category,
  Category? parent,
}) async {
  final saved = await showFormDialog<Category>(
    context,
    builder: (context) => _CategoryEditor(category: category, parent: parent),
  );
  if (saved == null) return;
  ref.invalidate(allCategoriesProvider);
  ref.invalidate(topCategoriesProvider);
  if (context.mounted) {
    showInfoSnack(
      context,
      category == null
          ? 'Dodano kategorię ${saved.code}.'
          : 'Zapisano kategorię ${saved.code}.',
    );
  }
}

class _CategoryEditor extends ConsumerStatefulWidget {
  const _CategoryEditor({required this.category, required this.parent});

  final Category? category;
  final Category? parent;

  @override
  ConsumerState<_CategoryEditor> createState() => _CategoryEditorState();
}

class _CategoryEditorState extends ConsumerState<_CategoryEditor> {
  final _form = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.category?.code ?? '');
  late final _name = TextEditingController(text: widget.category?.name ?? '');
  late bool _requiresApproval =
      widget.category?.requiresApproval ??
      widget.parent?.requiresApproval ??
      true;
  late String _risk =
      widget.category?.defaultRisk ?? widget.parent?.defaultRisk ?? 'medium';
  late bool _consent =
      widget.category?.requiresCiOwnerConsent ??
      widget.parent?.requiresCiOwnerConsent ??
      false;
  final Map<String, String> _serverErrors = {};
  Object? _error;
  bool _busy = false;

  bool get _creating => widget.category == null;
  bool get _sub => widget.parent != null;

  /// The parent requires approval: the subcategory cannot lift it.
  bool get _inherited => _sub && widget.parent!.requiresApproval;

  bool get _dirty {
    final c = widget.category;
    if (c == null) {
      return _code.text.isNotEmpty || _name.text.trim().isNotEmpty;
    }
    return _name.text.trim() != c.name ||
        _requiresApproval != c.requiresApproval ||
        _risk != c.defaultRisk ||
        _consent != c.requiresCiOwnerConsent;
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    super.dispose();
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
      final c = widget.category;
      final Category saved;
      if (c == null) {
        saved = await api.createCategory({
          'code': _code.text,
          'name': _name.text.trim(),
          'parent_id': ?widget.parent?.id,
          'requires_approval': _requiresApproval,
          'default_risk': _risk,
          'requires_ci_owner_consent': _consent,
        });
      } else {
        saved = await api.updateCategory(c.id, {
          if (_name.text.trim() != c.name) 'name': _name.text.trim(),
          if (_requiresApproval != c.requiresApproval)
            'requires_approval': _requiresApproval,
          if (_risk != c.defaultRisk) 'default_risk': _risk,
          if (_consent != c.requiresCiOwnerConsent)
            'requires_ci_owner_consent': _consent,
        });
      }
      if (mounted) Navigator.pop(context, saved);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        _error = error;
        final field = problem.code == 'category.code_taken'
            ? 'code'
            : problem.field;
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
    final title = _creating
        ? (_sub
              ? 'Nowa podkategoria: ${widget.parent!.name}'
              : 'Nowa kategoria')
        : 'Edycja: ${widget.category!.code}';
    return GuardedDialog(
      dirty: _dirty,
      child: AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 480,
          child: Form(
            key: _form,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    key: const ValueKey('category-code'),
                    controller: _code,
                    readOnly: !_creating,
                    style: AppFonts.monoStyle(),
                    decoration: InputDecoration(
                      labelText: 'Kod *',
                      helperText: _creating
                          ? (_sub
                                ? 'Np. ${widget.parent!.code}-PRIV. Kodu nie '
                                      'można później zmienić.'
                                : 'Np. NET. Kodu nie można później zmienić.')
                          : 'Kod jest niezmienny.',
                      fillColor: _creating ? null : AppColors.surfaceMuted,
                      suffixIcon: _creating
                          ? null
                          : const Icon(Icons.lock_outline),
                    ),
                    onChanged: (_) => setState(_serverErrors.clear),
                    validator: (v) =>
                        _serverErrors['code'] ??
                        (_creating ? validateCategoryCode(v ?? '') : null),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    key: const ValueKey('category-name'),
                    controller: _name,
                    maxLength: nameMaxLength,
                    decoration: const InputDecoration(labelText: 'Nazwa *'),
                    onChanged: (_) => setState(_serverErrors.clear),
                    validator: (v) =>
                        _serverErrors['name'] ?? validateName(v ?? ''),
                  ),
                  if (_sub)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        'Kategoria nadrzędna: ${widget.parent!.code} — '
                        '${widget.parent!.name}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                    ),
                  CheckboxListTile(
                    key: const ValueKey('category-requires-approval'),
                    value: _inherited || _requiresApproval,
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    title: const Text('Wymaga zatwierdzenia'),
                    subtitle: Text(
                      _inherited
                          ? 'Kategoria nadrzędna wymaga zatwierdzenia — '
                                'podkategoria nie może znieść tego wymogu.'
                          : _sub
                          ? 'Podkategoria może wprowadzić wymóg zatwierdzenia '
                                'w kategorii standardowej.'
                          : 'Bez zatwierdzenia zmiana standardowa jest '
                                'zatwierdzana automatycznie.',
                    ),
                    onChanged: _inherited
                        ? null
                        : (v) => setState(() => _requiresApproval = v ?? false),
                  ),
                  CheckboxListTile(
                    key: const ValueKey('category-consent'),
                    value: _consent,
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    title: const Text('Wymaga zgody właściciela obiektu (CI)'),
                    subtitle: const Text(
                      'Przed zatwierdzeniem zgodę muszą wyrazić właściciele '
                      'obiektów, których dotyczy zmiana (np. systemy OT).',
                    ),
                    onChanged: (v) => setState(() => _consent = v ?? false),
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    key: const ValueKey('category-risk'),
                    initialValue: _risk,
                    decoration: const InputDecoration(
                      labelText: 'Domyślne ryzyko',
                      helperText: 'Podpowiedź w formularzu zmiany.',
                    ),
                    items: [
                      for (final r in Risks.all)
                        DropdownMenuItem(value: r, child: Text(Risks.label(r))),
                    ],
                    onChanged: (v) => setState(() => _risk = v ?? _risk),
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
            key: const ValueKey('category-save'),
            onPressed: _busy || (!_creating && !_dirty) ? null : _submit,
            child: Text(_creating ? 'Dodaj' : 'Zapisz'),
          ),
        ],
      ),
    );
  }
}
