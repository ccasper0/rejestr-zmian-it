import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_error.dart';
import '../../../core/auth/auth.dart';
import '../../../core/navigation/exit_guard.dart';
import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/audit_timeline.dart' show DiffLine;
import '../../../widgets/common.dart';
import '../../../widgets/company_gate.dart';
import '../../../widgets/status_pill.dart';
import '../data/changes_api.dart';
import '../data/models.dart';
import 'attachments_section.dart';
import 'change_actions.dart';
import 'change_form_controller.dart';
import 'correction.dart';
import 'labels.dart';
import 'pickers.dart';
import 'readiness_panel.dart';

/// `/c/:prefix/changes/new`: creates a draft right away (the number is
/// assigned immediately, §10.3) and continues in its edit form.
class NewChangePage extends StatelessWidget {
  const NewChangePage({required this.prefix, super.key});

  final String prefix;

  @override
  Widget build(BuildContext context) {
    return CompanyGate(
      prefix: prefix,
      builder: (context, me, membership) =>
          _DraftCreator(membership: membership),
    );
  }
}

class _DraftCreator extends ConsumerStatefulWidget {
  const _DraftCreator({required this.membership});

  final Membership membership;

  @override
  ConsumerState<_DraftCreator> createState() => _DraftCreatorState();
}

class _DraftCreatorState extends ConsumerState<_DraftCreator> {
  Object? _error;
  bool _started = false;

  bool get _allowed =>
      widget.membership.canEditChanges && !widget.membership.isArchived;

  @override
  void initState() {
    super.initState();
    if (_allowed) _create();
  }

  Future<void> _create() async {
    if (_started) return;
    _started = true;
    setState(() => _error = null);
    try {
      final change = await ref
          .read(changesApiProvider)
          .createDraft(widget.membership.companyId);
      ref.invalidate(statsProvider(widget.membership.companyId));
      if (!mounted) return;
      context.go(
        '/c/${widget.membership.companyPrefix}/changes/${change.number}/edit',
      );
    } on Object catch (error) {
      if (mounted) {
        setState(() {
          _error = error;
          _started = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_allowed) {
      return const PageBody(
        children: [
          MessageBanner(
            kind: BannerKind.warning,
            title: 'Brak uprawnień',
            message:
                'Nowe zmiany mogą rejestrować edytorzy i zatwierdzający '
                'aktywnej spółki.',
          ),
        ],
      );
    }
    if (_error != null) {
      return PageBody(
        children: [ErrorPanel(error: _error!, onRetry: _create)],
      );
    }
    return const LoadingPanel(label: 'Tworzenie szkicu i nadawanie numeru…');
  }
}

/// `/c/:prefix/changes/:number/edit`.
class ChangeFormPage extends StatelessWidget {
  const ChangeFormPage({required this.prefix, required this.number, super.key});

  final String prefix;
  final String number;

  @override
  Widget build(BuildContext context) {
    return CompanyGate(
      prefix: prefix,
      builder: (context, me, membership) =>
          _FormLoader(me: me, membership: membership, number: number),
    );
  }
}

class _FormLoader extends ConsumerWidget {
  const _FormLoader({
    required this.me,
    required this.membership,
    required this.number,
  });

  final Me me;
  final Membership membership;
  final String number;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = (membership.companyId, number);
    return switch (ref.watch(changeByNumberProvider(key))) {
      AsyncData(:final value) when value.editableFields.isEmpty => PageBody(
        children: [
          MessageBanner(
            kind: BannerKind.warning,
            title: 'Edycja niedostępna',
            message:
                'Zmiany ${value.number} nie możesz teraz edytować (status, '
                'uprawnienia albo zamrożenie po zatwierdzeniu).',
            actions: [
              OutlinedButton(
                onPressed: () => context.go(
                  '/c/${membership.companyPrefix}/changes/${value.number}',
                ),
                child: const Text('Wróć do karty'),
              ),
            ],
          ),
        ],
      ),
      AsyncData(:final value) => ChangeForm(
        key: ValueKey(value.id),
        me: me,
        membership: membership,
        initial: value,
      ),
      AsyncError(:final error) => PageBody(
        children: [
          ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(changeByNumberProvider(key)),
          ),
        ],
      ),
      _ => const LoadingPanel(label: 'Wczytywanie zmiany…'),
    };
  }
}

/// The change form (§10.3). Public for widget tests.
class ChangeForm extends ConsumerStatefulWidget {
  const ChangeForm({
    required this.me,
    required this.membership,
    required this.initial,
    this.autosaveInterval = const Duration(seconds: 30),
    super.key,
  });

  final Me me;
  final Membership membership;
  final Change initial;
  final Duration autosaveInterval;

  @override
  ConsumerState<ChangeForm> createState() => _ChangeFormState();
}

class _ChangeFormState extends ConsumerState<ChangeForm> {
  late final ChangeFormController c = ChangeFormController(
    api: ref.read(changesApiProvider),
    companyId: widget.membership.companyId,
    initial: widget.initial,
    autosaveInterval: widget.autosaveInterval,
  );
  final Map<String, GlobalKey> _anchors = {};
  final Map<String, FocusNode> _focus = {
    for (final field in ChangeFormController.textFields) field: FocusNode(),
  };

  /// Set when leaving is intended (submit, discard): no exit guard.
  bool _leaving = false;
  bool _submitting = false;

  /// The last attempt to leave failed to save: the banners offer
  /// "Odrzuć zmiany i wyjdź".
  bool _exitBlocked = false;
  late final ExitGuard _exitGuard;

  String get _companyId => widget.membership.companyId;
  String get _prefix => widget.membership.companyPrefix;

  GlobalKey _anchor(String field) => _anchors.putIfAbsent(field, GlobalKey.new);

  @override
  void initState() {
    super.initState();
    c.startAutosave();
    unawaited(c.refreshReadiness());
    _exitGuard = ref.read(exitGuardProvider)..current = _confirmExit;
    setLeaveWarning(() => !_leaving && (c.dirty || c.saving));
  }

  @override
  void dispose() {
    if (_exitGuard.current == _confirmExit) _exitGuard.current = null;
    setLeaveWarning(null);
    c.dispose();
    for (final node in _focus.values) {
      node.dispose();
    }
    super.dispose();
  }

  /// go_router `onExit` of the edit route: unsaved edits are saved (with
  /// await) before leaving; if that fails, the user stays on the form and
  /// the banner explains why, offering "Odrzuć zmiany i wyjdź".
  Future<bool> _confirmExit() async {
    if (_leaving || !mounted) return true;
    // Signed out (401 or "Wyloguj") or a forced password change (403 for
    // every save): nothing can be saved any more.
    final auth = ref.read(authControllerProvider);
    if (!auth.isSignedIn || auth.mustChangePassword) return true;
    if (!c.dirty && !c.saving) return true;
    final saved = await c.saveBeforeLeaving();
    if (saved || !mounted) return true;
    setState(() => _exitBlocked = true);
    showInfoSnack(
      context,
      'Nie udało się zapisać zmian — pozostajesz w formularzu.',
    );
    return false;
  }

  void _goToCard() {
    ref.invalidate(changeByNumberProvider((_companyId, c.base.number)));
    context.go('/c/$_prefix/changes/${c.base.number}');
  }

  /// Leaves to the card without saving (explicit user choice).
  void _leaveDiscarding() {
    _leaving = true;
    _goToCard();
  }

  Future<bool> _confirmDiscard({String? title, String? message}) async {
    final discard = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title ?? 'Odrzucić niezapisane zmiany?'),
        content: Text(
          message ??
              'Zmiany wprowadzone od ostatniego zapisu zostaną utracone. '
                  'Szkic zachowuje numer i ostatnią zapisaną treść.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Wróć do edycji'),
          ),
          FilledButton(
            key: const ValueKey('confirm-discard'),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Odrzuć zmiany'),
          ),
        ],
      ),
    );
    return discard ?? false;
  }

  Future<void> _cancel() async {
    if (c.dirty && !await _confirmDiscard()) return;
    if (!mounted) return;
    _leaveDiscarding();
  }

  Future<void> _discardAndLeave() async {
    if (!await _confirmDiscard() || !mounted) return;
    _leaveDiscarding();
  }

  Future<void> _discardMine() async {
    final ok = await _confirmDiscard(
      title: 'Odrzucić Twoje zmiany?',
      message:
          'Formularz zostanie wczytany w wersji z serwera. Twoje niezapisane '
          'wartości przepadną.',
    );
    if (!ok || !mounted) return;
    try {
      await c.discardMine();
      if (mounted) setState(() => _exitBlocked = false);
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    }
  }

  Future<void> _overwriteWithMine() async {
    try {
      final ok = await c.overwriteWithMine();
      if (!mounted) return;
      if (ok) {
        setState(() => _exitBlocked = false);
        showInfoSnack(context, 'Zapisano Twoje zmiany na nowej wersji.');
      }
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    }
  }

  Future<void> _save() async {
    final ok = await c.save();
    if (!mounted) return;
    if (ok) {
      showInfoSnack(context, 'Zapisano szkic.');
    } else if (c.saveError != null) {
      showErrorSnack(context, c.saveError!);
    }
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      if (!await c.save()) {
        if (mounted && c.saveError != null) {
          showErrorSnack(context, c.saveError!);
        }
        return;
      }
      await c.refreshReadiness();
      if (!mounted) return;
      if (c.readiness?.ok != true) {
        showInfoSnack(
          context,
          'Kontrola przed wysłaniem wykazała pozycje do poprawy.',
        );
        return;
      }
      final result = await runChangeAction(
        context,
        ref,
        companyId: _companyId,
        change: c.base,
        action: 'submit',
      );
      if (result != null && mounted) {
        _leaving = true;
        ref.invalidate(statsProvider(_companyId));
        _goToCard();
      } else if (mounted) {
        await c.refreshReadiness();
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _focusField(ReadinessCheck check) {
    final field = switch (check.field) {
      'window' => 'window_start',
      final String f => f,
      null => null,
    };
    if (field == null) return;
    final target = _anchors[field]?.currentContext;
    if (target != null) {
      unawaited(
        Scrollable.ensureVisible(
          target,
          duration: const Duration(milliseconds: 250),
          alignment: 0.2,
        ),
      );
    }
    _focus[field]?.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) {
        final wide = MediaQuery.sizeOf(context).width >= 1200;
        final readinessPanel = ReadinessPanel(
          readiness: c.readiness,
          stale: c.dirty,
          onCheckTap: _focusField,
          onRefresh: c.refreshReadiness,
        );
        final sections = _sections(context);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _TopBar(
              controller: c,
              prefix: _prefix,
              submitting: _submitting,
              exitBlocked: _exitBlocked,
              onCancel: _cancel,
              onSave: _save,
              onSubmit: _submit,
              onDiscardAndLeave: _discardAndLeave,
              onDiscardMine: _discardMine,
              onOverwriteWithMine: _overwriteWithMine,
              names: NameResolver.forChange(
                c.serverVersion ?? c.base,
                members:
                    ref.watch(membersProvider(_companyId)).value ??
                    const <Member>[],
                categories:
                    ref.watch(companyCategoriesProvider(_companyId)).value ??
                    const <CompanyCategory>[],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1440),
                    child: wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(child: Column(children: sections)),
                              const SizedBox(width: 16),
                              SizedBox(width: 360, child: readinessPanel),
                            ],
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              readinessPanel,
                              const SizedBox(height: 16),
                              ...sections,
                            ],
                          ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  List<Widget> _sections(BuildContext context) {
    final members =
        ref.watch(membersProvider(_companyId)).value ?? const <Member>[];
    final errors = c.inlineErrors;
    return [
      if (c.base.supersedesChangeId != null) ...[
        CorrectionBanner(prefix: _prefix, change: c.base),
        const SizedBox(height: 16),
      ],
      _section1(errors),
      const SizedBox(height: 16),
      _section2(),
      const SizedBox(height: 16),
      _section3(errors),
      const SizedBox(height: 16),
      _section4(members, errors),
    ];
  }

  // ----------------------------------------------------------- 1) scope

  Widget _section1(Map<String, String> errors) {
    final categories =
        ref.watch(companyCategoriesProvider(_companyId)).value ??
        const <CompanyCategory>[];
    final subcategories = c.categoryId == null
        ? const <Category>[]
        : ref.watch(subcategoriesProvider(c.categoryId!)).value ??
              const <Category>[];
    return SectionCard(
      title: '1. Czego dotyczy',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _textField('title', 'Tytuł zmiany', errors: errors),
          const SizedBox(height: 16),
          _ResponsiveRow(
            children: [
              _SelectField(
                key: _anchor('category_id'),
                fieldKey: const ValueKey('field-category_id'),
                label: 'Kategoria',
                value: c.categoryId,
                enabled: c.canEdit('category_id'),
                options: [
                  for (final cat in categories)
                    if (cat.isActive || cat.categoryId == c.categoryId)
                      (cat.categoryId, cat.name),
                  if (c.categoryId != null &&
                      !categories.any((x) => x.categoryId == c.categoryId))
                    (
                      c.categoryId!,
                      c.base.category?.id == c.categoryId
                          ? '${c.base.category!.name} (niedostępna)'
                          : 'wybrana kategoria',
                    ),
                ],
                onChanged: (id) {
                  final cat = categories
                      .where((x) => x.categoryId == id)
                      .firstOrNull;
                  c.setCategory(id, defaultRisk: cat?.defaultRisk);
                },
              ),
              _SelectField(
                key: _anchor('subcategory_id'),
                fieldKey: const ValueKey('field-subcategory_id'),
                label: 'Podkategoria (opcjonalnie)',
                value: c.subcategoryId,
                enabled: c.canEdit('subcategory_id') && c.categoryId != null,
                emptyLabel: '— brak —',
                options: [
                  for (final sub in subcategories) (sub.id, sub.name),
                  if (c.subcategoryId != null &&
                      !subcategories.any((x) => x.id == c.subcategoryId))
                    (c.subcategoryId!, c.base.subcategory?.name ?? 'wybrana'),
                ],
                onChanged: (id) => c.update(() => c.subcategoryId = id),
              ),
            ],
          ),
          const SizedBox(height: 16),
          KeyedSubtree(
            key: _anchor('ci_ids'),
            child: _CiSelector(
              controller: c,
              companyId: _companyId,
              canCreate: widget.me.canManageCi(_prefix),
            ),
          ),
        ],
      ),
    );
  }

  // ----------------------------------------------------------- 2) type, risk

  Widget _section2() {
    return SectionCard(
      title: '2. Typ i ryzyko',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          KeyedSubtree(
            key: _anchor('change_type'),
            child: _TypeCards(
              value: c.changeType,
              enabled: c.canEdit('change_type'),
              onChanged: (type) => c.update(() => c.changeType = type),
            ),
          ),
          const SizedBox(height: 16),
          Text('Ryzyko', key: _anchor('risk')),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: SegmentedButton<String>(
              key: const ValueKey('field-risk'),
              emptySelectionAllowed: true,
              showSelectedIcon: false,
              segments: [
                for (final r in Risks.all)
                  ButtonSegment(
                    value: r,
                    label: Text(Risks.label(r)),
                    tooltip: 'Ryzyko: ${Risks.label(r)}',
                  ),
              ],
              selected: {?c.risk},
              onSelectionChanged: c.canEdit('risk')
                  ? (selection) => c.update(
                      () => c.risk = selection.isEmpty ? null : selection.first,
                    )
                  : null,
            ),
          ),
        ],
      ),
    );
  }

  // ----------------------------------------------------------- 3) plans

  Widget _section3(Map<String, String> errors) {
    final high = c.risk == Risks.high;
    return SectionCard(
      title: '3. Opis i plan',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _textField(
            'description',
            'Opis i uzasadnienie (co i dlaczego)',
            lines: 4,
            errors: errors,
          ),
          const SizedBox(height: 16),
          _textField(
            'implementation_plan',
            'Plan wdrożenia',
            lines: 4,
            errors: errors,
          ),
          const SizedBox(height: 16),
          _textField(
            'rollback_plan',
            high
                ? 'Plan wycofania (wymagany przy wysokim ryzyku)'
                : 'Plan wycofania',
            lines: 3,
            errors: errors,
          ),
          const SizedBox(height: 16),
          _textField(
            'impact',
            'Wpływ (usługi, użytkownicy, przerwa)',
            lines: 2,
            errors: errors,
          ),
        ],
      ),
    );
  }

  // ----------------------------------------------------------- 4) people

  Widget _section4(List<Member> members, Map<String, String> errors) {
    String name(String? id) => id == null
        ? '—'
        : members.where((m) => m.userId == id).firstOrNull?.displayName ??
              (c.base.approver?.id == id ? c.base.approver!.displayName : id);
    List<(String, String)> options(
      bool Function(Member) eligible,
      String? current,
    ) => [
      for (final m in members)
        if ((m.isActive && eligible(m)) || m.userId == current)
          (
            m.userId,
            m.isActive ? m.displayName : '${m.displayName} (nieaktywny)',
          ),
      if (current != null && !members.any((m) => m.userId == current))
        (current, _knownName(current)),
    ];

    final suggested = c.base.suggestedApproverId;
    final autoApproval = _autoApproval();
    return SectionCard(
      title: '4. Osoby, termin, dowody',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ResponsiveRow(
            children: [
              _SelectField(
                key: _anchor('assignee_id'),
                fieldKey: const ValueKey('field-assignee_id'),
                label: 'Wykonawca',
                value: c.assigneeId,
                enabled: c.canEdit('assignee_id'),
                options: options((m) => m.canWrite, c.assigneeId),
                onChanged: (id) => c.update(() => c.assigneeId = id),
              ),
              _SelectField(
                key: _anchor('approver_id'),
                fieldKey: const ValueKey('field-approver_id'),
                label: 'Zatwierdzający',
                value: c.approverId,
                enabled: c.canEdit('approver_id'),
                errorText: errors['approver_id'],
                emptyLabel: '— brak —',
                helper: autoApproval
                    ? 'Zmiana standardowa w tej kategorii zostanie zatwierdzona '
                          'automatycznie (system) — zatwierdzający nie jest '
                          'wymagany.'
                    : suggested != null && suggested != c.approverId
                    ? 'Domyślny zatwierdzający: ${name(suggested)}'
                    : null,
                action:
                    suggested != null &&
                        suggested != c.approverId &&
                        c.canEdit('approver_id')
                    ? TextButton(
                        onPressed: () =>
                            c.update(() => c.approverId = suggested),
                        child: const Text('Ustaw domyślnego'),
                      )
                    : null,
                options: options((m) => m.canApprove, c.approverId),
                onChanged: (id) => c.update(() => c.approverId = id),
              ),
              _SelectField(
                key: _anchor('verifier_id'),
                fieldKey: const ValueKey('field-verifier_id'),
                label: 'Weryfikujący',
                value: c.verifierId,
                enabled: c.canEdit('verifier_id'),
                emptyLabel: '— dowolny uprawniony —',
                options: options((m) => m.canWrite, c.verifierId),
                onChanged: (id) => c.update(() => c.verifierId = id),
              ),
            ],
          ),
          const SizedBox(height: 16),
          KeyedSubtree(
            key: _anchor('window_start'),
            child: _ResponsiveRow(
              children: [
                _DateTimeField(
                  key: const ValueKey('field-window_start'),
                  label: 'Okno serwisowe od (czas polski)',
                  value: c.windowStart,
                  enabled: c.canEdit('window_start'),
                  errorText: errors['window_start'],
                  onChanged: (value) => c.update(() => c.windowStart = value),
                ),
                _DateTimeField(
                  key: const ValueKey('field-window_end'),
                  label: 'Okno serwisowe do (czas polski)',
                  value: c.windowEnd,
                  enabled: c.canEdit('window_end'),
                  errorText: errors['window_end'],
                  onChanged: (value) => c.update(() => c.windowEnd = value),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _ResponsiveRow(
            children: [
              _textField(
                'ticket_ref',
                'Zgłoszenie (np. SD-1234)',
                errors: errors,
                mono: true,
              ),
              _textField(
                'requirement_ref',
                'Podstawa / wymóg (np. ISO/IEC 27001:2022 A.8.32)',
                errors: errors,
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            'Załączniki',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          AttachmentsSection(
            companyId: _companyId,
            changeId: c.base.id,
            canUpload:
                widget.membership.canEditChanges &&
                !widget.membership.isArchived,
            showDropZone: true,
          ),
        ],
      ),
    );
  }

  String _knownName(String id) {
    for (final ref in [c.base.assignee, c.base.approver, c.base.verifier]) {
      if (ref?.id == id) return ref!.displayName;
    }
    return 'wybrana osoba';
  }

  /// Standard change in a category without approval or CI owner consent
  /// (ADR 0012 §2, informational — the backend decides at submit).
  bool _autoApproval() {
    if (c.changeType != ChangeTypes.standard || c.categoryId == null) {
      return false;
    }
    final top = ref.watch(topCategoriesProvider).value;
    final category = top?.where((x) => x.id == c.categoryId).firstOrNull;
    if (category == null) return false;
    final sub = c.subcategoryId == null
        ? null
        : ref
              .watch(subcategoriesProvider(c.categoryId!))
              .value
              ?.where((x) => x.id == c.subcategoryId)
              .firstOrNull;
    final requiresApproval =
        category.requiresApproval || (sub?.requiresApproval ?? false);
    final consent =
        category.requiresCiOwnerConsent ||
        (sub?.requiresCiOwnerConsent ?? false);
    return !requiresApproval && !consent;
  }

  Widget _textField(
    String field,
    String label, {
    int lines = 1,
    required Map<String, String> errors,
    bool mono = false,
  }) {
    final enabled = c.canEdit(field);
    return KeyedSubtree(
      key: _anchor(field),
      child: TextField(
        key: ValueKey('field-$field'),
        controller: c.text(field),
        focusNode: _focus[field],
        enabled: enabled,
        minLines: lines,
        maxLines: lines == 1 ? 1 : lines + 6,
        style: mono ? AppFonts.monoStyle(fontSize: 14) : null,
        decoration: InputDecoration(
          labelText: label,
          alignLabelWithHint: lines > 1,
          errorText: errors[field],
          errorMaxLines: 3,
          helperText: enabled ? null : 'Pole niedostępne do edycji',
          fillColor: enabled ? AppColors.surface : AppColors.surfaceMuted,
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------- parts

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.controller,
    required this.prefix,
    required this.submitting,
    required this.exitBlocked,
    required this.onCancel,
    required this.onSave,
    required this.onSubmit,
    required this.onDiscardAndLeave,
    required this.onDiscardMine,
    required this.onOverwriteWithMine,
    required this.names,
  });

  final bool exitBlocked;
  final VoidCallback onDiscardAndLeave;
  final VoidCallback onDiscardMine;
  final VoidCallback onOverwriteWithMine;
  final NameResolver names;

  final ChangeFormController controller;
  final String prefix;
  final bool submitting;
  final VoidCallback onCancel;
  final VoidCallback onSave;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final c = controller;
    final change = c.base;
    final status = change.statusValue;
    final inlineErrors = c.inlineErrors;
    final canSubmit = change.allowedActions.contains('submit');
    final submitEnabled =
        canSubmit &&
        !submitting &&
        !c.saving &&
        !c.paused &&
        inlineErrors.isEmpty &&
        (c.readiness?.ok ?? false);
    final saveState = c.saving
        ? 'Zapisywanie…'
        : c.conflict != null
        ? 'Konflikt wersji — zapis wstrzymany'
        : c.blocked != null
        ? 'Zapis niemożliwy — autozapis wstrzymany'
        : c.dirty
        ? 'Niezapisane zmiany (autozapis co 30 s)'
        : c.lastSavedAt != null
        ? 'Zapisano ${WarsawTime.format(c.lastSavedAt)}'
        : 'Brak niezapisanych zmian';

    return Material(
      color: AppColors.surface,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: AppColors.border)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: 16,
                runSpacing: 8,
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 8,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Semantics(
                            header: true,
                            child: Text(
                              (change.title ?? '').isEmpty
                                  ? 'Nowa zmiana'
                                  : 'Edycja zmiany',
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          Text(
                            change.number,
                            key: const ValueKey('form-number'),
                            style: AppFonts.monoStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          if (status != null) StatusPill(status: status),
                        ],
                      ),
                      Text(
                        saveState,
                        key: const ValueKey('save-state'),
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      TextButton(
                        key: const ValueKey('form-cancel'),
                        onPressed: onCancel,
                        child: const Text('Anuluj'),
                      ),
                      OutlinedButton(
                        key: const ValueKey('form-save'),
                        onPressed: c.saving || c.paused || !c.dirty
                            ? null
                            : onSave,
                        child: const Text('Zapisz szkic'),
                      ),
                      if (canSubmit)
                        Tooltip(
                          message: submitEnabled
                              ? 'Zapisz i wyślij do zatwierdzenia'
                              : 'Popraw pozycje wskazane w „Kontroli przed '
                                    'wysłaniem”',
                          child: FilledButton(
                            key: const ValueKey('form-submit'),
                            onPressed: submitEnabled ? onSubmit : null,
                            child: Text(
                              submitting
                                  ? 'Wysyłanie…'
                                  : 'Wyślij do zatwierdzenia',
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              if (c.conflict != null) ...[
                const SizedBox(height: 8),
                MessageBanner(
                  key: const ValueKey('conflict-banner'),
                  kind: BannerKind.error,
                  title: 'Ktoś inny zapisał tę zmianę',
                  message:
                      'Zmiana ma już nowszą wersję'
                      '${c.conflict!.currentVersion == null ? '' : ' (${c.conflict!.currentVersion})'}. '
                      'Twoje wartości są nadal w formularzu, ale nie zostały '
                      'zapisane, a autozapis jest wstrzymany. Porównaj je z '
                      'wersją z serwera i zdecyduj.',
                  actions: [
                    FilledButton(
                      key: const ValueKey('conflict-overwrite'),
                      onPressed: onOverwriteWithMine,
                      child: const Text('Zapisz moje na nowej wersji'),
                    ),
                    OutlinedButton(
                      key: const ValueKey('conflict-discard'),
                      onPressed: onDiscardMine,
                      child: const Text('Odrzuć moje zmiany'),
                    ),
                    OutlinedButton(
                      key: const ValueKey('discard-and-leave'),
                      onPressed: onDiscardAndLeave,
                      child: const Text('Odrzuć zmiany i wyjdź'),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _ConflictDiffs(controller: c, names: names),
              ],
              if (c.blocked != null) ...[
                const SizedBox(height: 8),
                MessageBanner(
                  key: const ValueKey('blocked-banner'),
                  kind: BannerKind.error,
                  title: 'Nie można zapisać zmian',
                  message: c.blocked!.message,
                  details: c.blocked!.detail,
                  actions: [
                    OutlinedButton(
                      onPressed: onDiscardMine,
                      child: const Text('Wczytaj stan z serwera'),
                    ),
                    OutlinedButton(
                      key: const ValueKey('discard-and-leave'),
                      onPressed: onDiscardAndLeave,
                      child: const Text('Odrzuć zmiany i wyjdź'),
                    ),
                  ],
                ),
              ],
              if (c.saveError != null && !c.paused) ...[
                const SizedBox(height: 8),
                MessageBanner(
                  key: const ValueKey('save-error-banner'),
                  kind: BannerKind.error,
                  title: 'Nie udało się zapisać',
                  message: c.saveError!.message,
                  details: c.saveError!.detail,
                  actions: [
                    FilledButton(
                      onPressed: onSave,
                      child: const Text('Spróbuj ponownie'),
                    ),
                    if (exitBlocked) ...[
                      OutlinedButton(
                        key: const ValueKey('discard-and-leave'),
                        onPressed: onDiscardAndLeave,
                        child: const Text('Odrzuć zmiany i wyjdź'),
                      ),
                    ],
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Conflict: my value vs. the newer server value, field by field.
class _ConflictDiffs extends StatelessWidget {
  const _ConflictDiffs({required this.controller, required this.names});

  final ChangeFormController controller;
  final NameResolver names;

  @override
  Widget build(BuildContext context) {
    final diffs = controller.conflictDiffs;
    if (controller.serverVersion == null) {
      return const Text(
        'Wczytywanie wersji z serwera…',
        style: TextStyle(color: AppColors.textSecondary),
      );
    }
    if (diffs.isEmpty) {
      return const Text(
        'Twoje wartości nie różnią się od nowej wersji.',
        style: TextStyle(color: AppColors.textSecondary),
      );
    }
    final local = {for (final ci in controller.cis) ci.id: ci.identifier};
    String show(String field, Object? value) {
      if (field == 'ci_ids' && value is List) {
        return value.isEmpty
            ? '—'
            : value.map((id) => local[id] ?? names.ci('$id')).join(', ');
      }
      return names.value(field, value);
    }

    return DecoratedBox(
      key: const ValueKey('conflict-diffs'),
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
            const Text(
              'Różnice (wersja z serwera → Twoja wartość):',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            for (final (field, mine, server) in diffs)
              DiffLine(
                field: field,
                before: show(field, server),
                after: show(field, mine),
              ),
          ],
        ),
      ),
    );
  }
}

/// Two or three fields side by side on wide screens, stacked on narrow.
class _ResponsiveRow extends StatelessWidget {
  const _ResponsiveRow({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 640) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (var i = 0; i < children.length; i++) ...[
                if (i > 0) const SizedBox(height: 16),
                children[i],
              ],
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < children.length; i++) ...[
              if (i > 0) const SizedBox(width: 16),
              Expanded(child: children[i]),
            ],
          ],
        );
      },
    );
  }
}

/// Controlled dropdown (value always from the controller).
class _SelectField extends StatelessWidget {
  const _SelectField({
    required this.fieldKey,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
    this.enabled = true,
    this.emptyLabel,
    this.errorText,
    this.helper,
    this.action,
    super.key,
  });

  final Key fieldKey;
  final String label;
  final String? value;
  final List<(String, String)> options;
  final ValueChanged<String?> onChanged;
  final bool enabled;

  /// Label of the "none" entry; null = no such entry.
  final String? emptyLabel;
  final String? errorText;
  final String? helper;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final items = <DropdownMenuItem<String?>>[
      if (emptyLabel != null || value == null)
        DropdownMenuItem<String?>(
          value: null,
          child: Text(
            emptyLabel ?? 'Wybierz…',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
        ),
      for (final (id, text) in options)
        DropdownMenuItem<String?>(
          value: id,
          child: Text(text, overflow: TextOverflow.ellipsis),
        ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InputDecorator(
          isEmpty: false,
          decoration: InputDecoration(
            labelText: label,
            errorText: errorText,
            errorMaxLines: 3,
            helperText: helper,
            helperMaxLines: 3,
            enabled: enabled,
            fillColor: enabled ? AppColors.surface : AppColors.surfaceMuted,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 4,
            ),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String?>(
              key: fieldKey,
              value: value,
              isExpanded: true,
              items: items,
              onChanged: enabled ? onChanged : null,
            ),
          ),
        ),
        ?action,
      ],
    );
  }
}

class _DateTimeField extends StatelessWidget {
  const _DateTimeField({
    required this.label,
    required this.value,
    required this.onChanged,
    this.enabled = true,
    this.errorText,
    super.key,
  });

  final String label;
  final DateTime? value;
  final ValueChanged<DateTime?> onChanged;
  final bool enabled;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    return InputDecorator(
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
        errorMaxLines: 3,
        enabled: enabled,
        fillColor: enabled ? AppColors.surface : AppColors.surfaceMuted,
        contentPadding: const EdgeInsets.only(left: 12),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              value == null ? 'Nie ustawiono' : WarsawTime.format(value),
              style: value == null
                  ? const TextStyle(color: AppColors.textSecondary)
                  : AppFonts.monoStyle(fontSize: 14),
            ),
          ),
          IconButton(
            tooltip: 'Wybierz datę i godzinę',
            onPressed: enabled
                ? () async {
                    final picked = await pickWarsawDateTime(
                      context,
                      initial: value,
                    );
                    if (picked != null) onChanged(picked);
                  }
                : null,
            icon: const Icon(Icons.event_outlined),
          ),
          if (value != null)
            IconButton(
              tooltip: 'Wyczyść',
              onPressed: enabled ? () => onChanged(null) : null,
              icon: const Icon(Icons.close),
            ),
        ],
      ),
    );
  }
}

/// Three radio cards: Standardowa / Normalna / Awaryjna (§10.3).
class _TypeCards extends StatelessWidget {
  const _TypeCards({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final String? value;
  final bool enabled;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final cards = [
      for (final type in ChangeTypes.all)
        _TypeCard(
          type: type,
          selected: value == type,
          enabled: enabled,
          onTap: () => onChanged(type),
        ),
    ];
    return Semantics(
      label: 'Typ zmiany',
      container: true,
      child: LayoutBuilder(
        builder: (context, constraints) => constraints.maxWidth < 640
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final card in cards)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: card,
                    ),
                ],
              )
            : IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (var i = 0; i < cards.length; i++) ...[
                      if (i > 0) const SizedBox(width: 12),
                      Expanded(child: cards[i]),
                    ],
                  ],
                ),
              ),
      ),
    );
  }
}

class _TypeCard extends StatelessWidget {
  const _TypeCard({
    required this.type,
    required this.selected,
    required this.enabled,
    required this.onTap,
  });

  final String type;
  final bool selected;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final emergency = type == ChangeTypes.emergency;
    final borderColor = selected
        ? (emergency ? AppColors.emergencyBorder : AppColors.accent)
        : AppColors.border;
    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      button: true,
      enabled: enabled,
      label: ChangeTypes.label(type),
      child: Material(
        color: selected
            ? (emergency
                  ? AppStatusColors.negative.background
                  : AppStatusColors.approved.background)
            : AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadii.mediumAll,
          side: BorderSide(color: borderColor, width: selected ? 2 : 1),
        ),
        child: InkWell(
          key: ValueKey('type-card-$type'),
          borderRadius: AppRadii.mediumAll,
          onTap: enabled ? onTap : null,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              minHeight: AppSizes.minTouchTarget,
            ),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    selected
                        ? Icons.radio_button_checked
                        : Icons.radio_button_unchecked,
                    color: selected
                        ? (emergency ? AppColors.danger : AppColors.accent)
                        : AppColors.textSecondary,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ChangeTypes.label(type),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          ChangeTypes.description(type),
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Multi-select of CI with search (chips) and "add CI on the fly".
class _CiSelector extends ConsumerStatefulWidget {
  const _CiSelector({
    required this.controller,
    required this.companyId,
    required this.canCreate,
  });

  final ChangeFormController controller;
  final String companyId;
  final bool canCreate;

  @override
  ConsumerState<_CiSelector> createState() => _CiSelectorState();
}

class _CiSelectorState extends ConsumerState<_CiSelector> {
  final _text = TextEditingController();
  final _focus = FocusNode();

  @override
  void dispose() {
    _text.dispose();
    _focus.dispose();
    super.dispose();
  }

  Future<Iterable<CiItem>> _search(String q) async {
    try {
      final page = await ref
          .read(changesApiProvider)
          .listCi(widget.companyId, q: q, active: true, limit: 20);
      final selected = {for (final c in widget.controller.cis) c.id};
      return page.items.where((item) => !selected.contains(item.id));
    } on Object {
      return const [];
    }
  }

  Future<void> _create() async {
    final created = await showDialog<CiItem>(
      context: context,
      builder: (_) => _NewCiDialog(companyId: widget.companyId),
    );
    if (created != null) {
      widget.controller.addCi(
        CiRef(
          id: created.id,
          identifier: created.identifier,
          name: created.name,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    final enabled = c.canEdit('ci_ids');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('Obiekty (CI), których dotyczy zmiana'),
        const SizedBox(height: 8),
        if (c.cis.isEmpty)
          const Text(
            'Nie wybrano obiektów.',
            style: TextStyle(color: AppColors.textSecondary),
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final ci in c.cis)
                InputChip(
                  key: ValueKey('ci-chip-${ci.identifier}'),
                  label: Text(
                    ci.identifier,
                    style: AppFonts.monoStyle(fontSize: 13),
                  ),
                  tooltip: ci.name,
                  deleteButtonTooltipMessage: 'Usuń ${ci.identifier}',
                  onDeleted: enabled ? () => c.removeCi(ci.id) : null,
                ),
            ],
          ),
        if (enabled) ...[
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: RawAutocomplete<CiItem>(
                  textEditingController: _text,
                  focusNode: _focus,
                  displayStringForOption: (item) =>
                      '${item.identifier} — ${item.name}',
                  optionsBuilder: (value) => _search(value.text),
                  onSelected: (item) {
                    c.addCi(
                      CiRef(
                        id: item.id,
                        identifier: item.identifier,
                        name: item.name,
                      ),
                    );
                    _text.clear();
                  },
                  fieldViewBuilder: (context, controller, focusNode, submit) =>
                      TextField(
                        key: const ValueKey('ci-search'),
                        controller: controller,
                        focusNode: focusNode,
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.search),
                          hintText: 'Szukaj obiektu: identyfikator lub nazwa',
                          isDense: true,
                        ),
                      ),
                  optionsViewBuilder: (context, onSelected, options) => Align(
                    alignment: Alignment.topLeft,
                    child: Material(
                      elevation: 4,
                      borderRadius: AppRadii.smallAll,
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(
                          maxHeight: 280,
                          maxWidth: 520,
                        ),
                        child: ListView(
                          padding: EdgeInsets.zero,
                          shrinkWrap: true,
                          children: [
                            for (final item in options)
                              ListTile(
                                title: Text(
                                  item.identifier,
                                  style: AppFonts.monoStyle(fontSize: 14),
                                ),
                                subtitle: Text(
                                  '${item.name} · ${item.ciTypeName}',
                                ),
                                onTap: () => onSelected(item),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              if (widget.canCreate) ...[
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  key: const ValueKey('ci-create'),
                  onPressed: _create,
                  icon: const Icon(Icons.add),
                  label: const Text('Nowy obiekt'),
                ),
              ],
            ],
          ),
        ],
      ],
    );
  }
}

/// "Add CI on the fly" (`POST /companies/{cid}/ci`, matrix `ci.manage`).
class _NewCiDialog extends ConsumerStatefulWidget {
  const _NewCiDialog({required this.companyId});

  final String companyId;

  @override
  ConsumerState<_NewCiDialog> createState() => _NewCiDialogState();
}

class _NewCiDialogState extends ConsumerState<_NewCiDialog> {
  final _identifier = TextEditingController();
  final _name = TextEditingController();
  final _description = TextEditingController();
  String? _typeId;
  bool _saving = false;
  ApiProblem? _error;

  @override
  void dispose() {
    _identifier.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_typeId == null ||
        _identifier.text.trim().isEmpty ||
        _name.text.trim().isEmpty) {
      setState(
        () => _error = const ApiProblem(
          message: 'Podaj typ, identyfikator i nazwę obiektu.',
        ),
      );
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final item = await ref
          .read(changesApiProvider)
          .createCi(
            widget.companyId,
            ciTypeId: _typeId!,
            identifier: _identifier.text.trim(),
            name: _name.text.trim(),
            description: _description.text,
          );
      if (mounted) Navigator.pop(context, item);
    } on Object catch (error) {
      if (mounted) setState(() => _error = ApiProblem.from(error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final types = ref.watch(ciTypesProvider).value ?? const <CiType>[];
    return AlertDialog(
      title: const Text('Nowy obiekt (CI)'),
      content: SizedBox(
        width: 440,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null) ...[
              MessageBanner(
                kind: BannerKind.error,
                message: _error!.message,
                details: _error!.detail,
              ),
              const SizedBox(height: 12),
            ],
            _SelectField(
              fieldKey: const ValueKey('new-ci-type'),
              label: 'Typ obiektu',
              value: _typeId,
              options: [for (final t in types) (t.id, t.name)],
              onChanged: (id) => setState(() => _typeId = id),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _identifier,
              style: AppFonts.monoStyle(fontSize: 14),
              decoration: const InputDecoration(
                labelText: 'Identyfikator (np. FW-01)',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Nazwa'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _description,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Opis (opcjonalnie)',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          onPressed: _saving ? null : _save,
          child: Text(_saving ? 'Zapisywanie…' : 'Dodaj obiekt'),
        ),
      ],
    );
  }
}
