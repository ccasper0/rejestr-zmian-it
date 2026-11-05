import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/theme.dart';
import '../../../widgets/common.dart';
import '../../changes/data/changes_api.dart';
import '../../changes/data/models.dart';
import '../data/admin_api.dart';
import '../data/validation.dart';
import 'admin_shell.dart';
import 'categories_tab.dart' show ActivityFilter, ActivityFilterBar;

/// `/admin/ci-types` — global dictionary of CI types (§4.1).
class AdminCiTypesPage extends StatelessWidget {
  const AdminCiTypesPage({required this.filter, super.key});

  final ActivityFilter filter;

  @override
  Widget build(BuildContext context) =>
      AdminGate(builder: (context, me) => _CiTypesView(filter: filter));
}

class _CiTypesView extends ConsumerWidget {
  const _CiTypesView({required this.filter});

  final ActivityFilter filter;

  Future<void> _toggle(BuildContext context, WidgetRef ref, CiType type) async {
    final activate = !type.isActive;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          activate
              ? 'Aktywować typ ${type.code}?'
              : 'Dezaktywować typ ${type.code}?',
        ),
        content: Text(
          activate
              ? 'Typ znów będzie można wybrać dla nowych obiektów.'
              : 'Nieaktywnego typu nie można wybrać dla nowego obiektu ani '
                    'przy zmianie typu. Istniejące obiekty go zachowują.',
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
      await ref.read(adminApiProvider).updateCiType(type.id, {
        'is_active': activate,
      });
      ref.invalidate(allCiTypesProvider);
      ref.invalidate(ciTypesProvider);
    } on Object catch (error) {
      if (context.mounted) showErrorSnack(context, error);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final types = ref.watch(allCiTypesProvider);
    return AdminTabsFrame(
      tab: AdminTab.ciTypes,
      actions: [
        IconButton(
          tooltip: 'Odśwież',
          onPressed: () => ref.invalidate(allCiTypesProvider),
          icon: const Icon(Icons.refresh),
        ),
        FilledButton.icon(
          key: const ValueKey('new-ci-type'),
          onPressed: () => showCiTypeEditor(context, ref),
          icon: const Icon(Icons.add),
          label: const Text('Nowy typ'),
        ),
      ],
      children: [
        const Text(
          'Kod typu jest niezmienny. Typów się nie usuwa — dezaktywuje.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: ActivityFilterBar(value: filter, path: '/admin/ci-types'),
        ),
        const SizedBox(height: 12),
        switch (types) {
          AsyncError(:final error) => ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(allCiTypesProvider),
          ),
          AsyncData(:final value) => () {
            final shown = [
              for (final t in value)
                if (filter.matches(t.isActive)) t,
            ];
            return Card(
              child: shown.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        'Brak typów spełniających kryteria.',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    )
                  : Column(
                      children: [
                        for (var i = 0; i < shown.length; i++) ...[
                          if (i > 0) const Divider(),
                          ListTile(
                            key: ValueKey('ci-type-${shown[i].code}'),
                            title: Text(shown[i].name),
                            subtitle: Text(
                              shown[i].code,
                              style: AppFonts.monoStyle(
                                fontSize: 13,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            trailing: Wrap(
                              spacing: 4,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                if (!shown[i].isActive)
                                  const ActiveTag(active: false),
                                TextButton(
                                  key: ValueKey('edit-${shown[i].code}'),
                                  onPressed: () => showCiTypeEditor(
                                    context,
                                    ref,
                                    type: shown[i],
                                  ),
                                  child: const Text('Edytuj'),
                                ),
                                TextButton(
                                  key: ValueKey('toggle-${shown[i].code}'),
                                  style: TextButton.styleFrom(
                                    foregroundColor: shown[i].isActive
                                        ? AppColors.danger
                                        : AppColors.accent,
                                  ),
                                  onPressed: () =>
                                      _toggle(context, ref, shown[i]),
                                  child: Text(
                                    shown[i].isActive
                                        ? 'Dezaktywuj'
                                        : 'Aktywuj',
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
            );
          }(),
          _ => const LoadingPanel(),
        },
      ],
    );
  }
}

Future<void> showCiTypeEditor(
  BuildContext context,
  WidgetRef ref, {
  CiType? type,
}) async {
  final saved = await showFormDialog<CiType>(
    context,
    builder: (context) => _CiTypeEditor(type: type),
  );
  if (saved == null) return;
  ref.invalidate(allCiTypesProvider);
  ref.invalidate(ciTypesProvider);
  if (context.mounted) {
    showInfoSnack(
      context,
      type == null
          ? 'Dodano typ ${saved.code}.'
          : 'Zapisano typ ${saved.code}.',
    );
  }
}

class _CiTypeEditor extends ConsumerStatefulWidget {
  const _CiTypeEditor({required this.type});

  final CiType? type;

  @override
  ConsumerState<_CiTypeEditor> createState() => _CiTypeEditorState();
}

class _CiTypeEditorState extends ConsumerState<_CiTypeEditor> {
  final _form = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.type?.code ?? '');
  late final _name = TextEditingController(text: widget.type?.name ?? '');
  final Map<String, String> _serverErrors = {};
  Object? _error;
  bool _busy = false;

  bool get _creating => widget.type == null;

  bool get _dirty => _creating
      ? _code.text.isNotEmpty || _name.text.trim().isNotEmpty
      : _name.text.trim() != widget.type!.name;

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
    try {
      final api = ref.read(adminApiProvider);
      final saved = _creating
          ? await api.createCiType({
              'code': _code.text,
              'name': _name.text.trim(),
            })
          : await api.updateCiType(widget.type!.id, {
              'name': _name.text.trim(),
            });
      if (mounted) Navigator.pop(context, saved);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        _error = error;
        final field = problem.code == 'ci_type.code_taken'
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
    return GuardedDialog(
      dirty: _dirty,
      child: AlertDialog(
        title: Text(
          _creating ? 'Nowy typ obiektu' : 'Edycja: ${widget.type!.code}',
        ),
        content: SizedBox(
          width: 440,
          child: Form(
            key: _form,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  key: const ValueKey('ci-type-code'),
                  controller: _code,
                  readOnly: !_creating,
                  style: AppFonts.monoStyle(),
                  decoration: InputDecoration(
                    labelText: 'Kod *',
                    helperText: _creating
                        ? 'Np. load_balancer. Kodu nie można później zmienić.'
                        : 'Kod jest niezmienny.',
                    fillColor: _creating ? null : AppColors.surfaceMuted,
                    suffixIcon: _creating
                        ? null
                        : const Icon(Icons.lock_outline),
                  ),
                  onChanged: (_) => setState(_serverErrors.clear),
                  validator: (v) =>
                      _serverErrors['code'] ??
                      (_creating ? validateCiTypeCode(v ?? '') : null),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  key: const ValueKey('ci-type-name'),
                  controller: _name,
                  maxLength: nameMaxLength,
                  decoration: const InputDecoration(labelText: 'Nazwa *'),
                  onChanged: (_) => setState(_serverErrors.clear),
                  validator: (v) =>
                      _serverErrors['name'] ?? validateName(v ?? ''),
                ),
                if (_error != null && _serverErrors.isEmpty) ...[
                  const SizedBox(height: 12),
                  ErrorPanel(error: _error!),
                ],
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.maybePop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('ci-type-save'),
            onPressed: _busy || !_dirty ? null : _submit,
            child: Text(_creating ? 'Dodaj' : 'Zapisz'),
          ),
        ],
      ),
    );
  }
}
