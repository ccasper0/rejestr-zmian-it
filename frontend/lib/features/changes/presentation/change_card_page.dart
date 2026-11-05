import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/session.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/audit_timeline.dart';
import '../../../widgets/common.dart';
import '../../../widgets/company_scope.dart';
import '../../../widgets/status_pill.dart';
import '../../reports/presentation/report_export.dart';
import '../data/changes_api.dart';
import '../data/models.dart';
import 'attachments_section.dart';
import 'change_actions.dart';
import 'correction.dart';
import 'labels.dart';
import 'register_page.dart' show ChangeTypeTag;
import 'stage_bar.dart';

/// Change card (`/c/:prefix/changes/:number`, §10.2).
///
/// The app admin without a role in the company reads it on the API's
/// read-only admin path (ADR 0016): `access = admin_read_only`, no actions,
/// no edit, no comments, no upload or download of attachment files.
class ChangeCardPage extends StatelessWidget {
  const ChangeCardPage({required this.prefix, required this.number, super.key});

  final String prefix;
  final String number;

  @override
  Widget build(BuildContext context) {
    return AdminAwareCompanyGate(
      prefix: prefix,
      section: 'changes',
      builder: (context, me, company) =>
          ChangeCardView(company: company, number: number),
    );
  }
}

class ChangeCardView extends ConsumerWidget {
  const ChangeCardView({
    required this.company,
    required this.number,
    super.key,
  });

  final CompanyRef company;
  final String number;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = (company.id, number);
    final change = ref.watch(changeByNumberProvider(key));
    return switch (change) {
      AsyncData(:final value) => _Card(company: company, change: value),
      AsyncError(:final error) => PageBody(
        children: [
          _Breadcrumb(prefix: company.prefix, number: number),
          const SizedBox(height: 12),
          ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(changeByNumberProvider(key)),
          ),
        ],
      ),
      _ => const LoadingPanel(label: 'Wczytywanie karty zmiany…'),
    };
  }
}

class _Breadcrumb extends StatelessWidget {
  const _Breadcrumb({required this.prefix, required this.number});

  final String prefix;
  final String number;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        TextButton(
          onPressed: () => context.go('/c/$prefix/changes'),
          child: const Text('Rejestr zmian'),
        ),
        const Icon(
          Icons.chevron_right,
          size: 18,
          color: AppColors.textSecondary,
        ),
        const SizedBox(width: 8),
        Text(number, style: AppFonts.monoStyle(fontSize: 14)),
      ],
    );
  }
}

class _Card extends ConsumerStatefulWidget {
  const _Card({required this.company, required this.change});

  final CompanyRef company;
  final Change change;

  @override
  ConsumerState<_Card> createState() => _CardState();
}

class _CardState extends ConsumerState<_Card> {
  bool _busy = false;
  bool _exportingPdf = false;
  bool _correcting = false;

  Change get change => widget.change;
  String get companyId => widget.company.id;

  /// Writes (comment, upload) need a member's role and a member's card; an
  /// unknown `access` is treated as read-only (ADR 0016).
  bool get _canWrite => widget.company.canEditChanges && change.isMemberAccess;

  /// The file download is audited in the company chain — not on the admin's
  /// read-only path (ADR 0016 §4).
  bool get _canDownload => !widget.company.adminPath && change.isMemberAccess;

  bool get _adminReadOnly => widget.company.adminPath || change.isAdminReadOnly;

  void _reload() {
    ref
      ..invalidate(changeByNumberProvider((companyId, change.number)))
      ..invalidate(auditTrailProvider((companyId, change.id)))
      ..invalidate(attachmentsProvider((companyId, change.id)))
      ..invalidate(chainStatusProvider(companyId))
      ..invalidate(statsProvider(companyId));
  }

  /// Matrix §5 `export.change_card`: editor, approver, auditor, app admin —
  /// also on the read-only admin path (the export has its own named admin
  /// path, ADR 0017 §4, §12). Not the viewer.
  bool _canExportPdf(Me? me) =>
      widget.company.adminPath ||
      (me?.canExportChangeCard(widget.company.prefix) ?? false);

  /// "Karta PDF": `POST /reports` (`change_card`), waits while `pending`,
  /// then saves the file.
  Future<void> _exportPdf() async {
    setState(() => _exportingPdf = true);
    try {
      final report = await ref
          .read(reportExporterProvider)
          .changeCard(
            companyId: companyId,
            changeId: change.id,
            isActive: () => mounted,
          );
      if (report != null && mounted) {
        showInfoSnack(
          context,
          'Pobrano kartę zmiany w PDF (raport ${report.number}).',
        );
      }
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _exportingPdf = false);
    }
  }

  /// "Utwórz korektę": a frozen change of a company where the caller may
  /// create changes (editor/approver, member's card, active company) — the
  /// same rule as "Nowa zmiana" in the register (ADR 0021).
  bool get _canCorrect => _canWrite && ChangeCorrection.isCorrectable(change);

  Future<void> _createCorrection() async {
    if (!await confirmCorrection(context, change) || !mounted) return;
    setState(() => _correcting = true);
    final ok = await createCorrection(
      context,
      ref,
      companyId: companyId,
      prefix: widget.company.prefix,
      original: change,
    );
    if (!ok && mounted) setState(() => _correcting = false);
  }

  Future<void> _action(String action) async {
    final comment = await showActionDialog(
      context,
      action: action,
      change: change,
    );
    if (comment == null || !mounted) return;
    setState(() => _busy = true);
    try {
      await runChangeAction(
        context,
        ref,
        companyId: companyId,
        change: change,
        action: action,
        presetComment: comment,
        confirm: false,
      );
    } finally {
      // Success, conflict or error: the card shows the server's state.
      _reload();
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1200;
    final prefix = widget.company.prefix;
    final members =
        ref.watch(membersProvider(companyId)).value ?? const <Member>[];
    final categories =
        ref.watch(companyCategoriesProvider(companyId)).value ??
        const <CompanyCategory>[];
    final names = NameResolver.forChange(
      change,
      members: members,
      categories: categories,
    );

    final left = [
      _DescriptionCard(
        change: change,
        companyId: companyId,
        canUpload: _canWrite,
        canDownload: _canDownload,
      ),
      if (change.consents.isNotEmpty ||
          change.allowedActions.contains('consent') ||
          change.ci.any((c) => c.consented))
        _ConsentsCard(change: change),
      _CommentsCard(
        change: change,
        companyId: companyId,
        canComment: _canWrite,
        onAdded: _reload,
      ),
      _AuditCard(change: change, companyId: companyId, names: names),
    ];
    final right = [
      _ClassificationCard(change: change, company: widget.company),
      _ObjectsCard(change: change),
    ];

    List<Widget> spaced(List<Widget> items) => [
      for (var i = 0; i < items.length; i++) ...[
        if (i > 0) const SizedBox(height: 16),
        items[i],
      ],
    ];

    return Stack(
      children: [
        PageBody(
          children: [
            _Breadcrumb(prefix: prefix, number: change.number),
            const SizedBox(height: 8),
            _Header(change: change, company: widget.company),
            const SizedBox(height: 16),
            _ActionBar(
              change: change,
              prefix: prefix,
              busy: _busy || _correcting,
              readOnly: !change.isMemberAccess,
              onAction: _action,
              onCorrect: _canCorrect ? _createCorrection : null,
              correcting: _correcting,
              onPdf: _canExportPdf(ref.watch(meProvider).value)
                  ? _exportPdf
                  : null,
              pdfBusy: _exportingPdf,
            ),
            if (_adminReadOnly) ...[
              const SizedBox(height: 12),
              const AdminReadOnlyBanner(),
            ],
            if (widget.company.archived) ...[
              const SizedBox(height: 12),
              const MessageBanner(
                kind: BannerKind.warning,
                message: 'Spółka jest zarchiwizowana — zmiana jest tylko do odczytu.',
              ),
            ],
            for (final d in change.deviations) ...[
              const SizedBox(height: 12),
              MessageBanner(
                kind: BannerKind.error,
                title: d.critical ? 'Odstępstwo krytyczne' : 'Odstępstwo',
                message: d.messagePl,
              ),
            ],
            const SizedBox(height: 16),
            StageBar(change: change),
            const SizedBox(height: 16),
            if (wide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: spaced(left),
                    ),
                  ),
                  const SizedBox(width: 16),
                  SizedBox(
                    width: 380,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: spaced(right),
                    ),
                  ),
                ],
              )
            else
              ...spaced([...right, ...left]),
          ],
        ),
        if (_busy || _correcting)
          const Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: LinearProgressIndicator(minHeight: 3),
          ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.change, required this.company});

  final Change change;
  final CompanyRef company;

  @override
  Widget build(BuildContext context) {
    final status = change.statusValue;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              change.number,
              style: AppFonts.monoStyle(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
              ),
            ),
            if (status != null) StatusPill(status: status),
            ChangeTypeTag(type: change.changeType),
            Tag(
              label: 'Ryzyko: ${Risks.label(change.risk)}',
              colors: change.risk == Risks.high
                  ? AppFeedbackColors.error
                  : change.risk == Risks.medium
                  ? AppFeedbackColors.warning
                  : AppFeedbackColors.neutral,
            ),
            if (change.supersedesChangeId != null)
              SupersedesLink(prefix: company.prefix, change: change),
          ],
        ),
        const SizedBox(height: 8),
        Semantics(
          header: true,
          child: Text(
            change.title?.isNotEmpty == true ? change.title! : '(bez tytułu)',
            style: Theme.of(context).textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        if (change.supersededBy.isNotEmpty) ...[
          const SizedBox(height: 4),
          SupersededByLinks(
            prefix: company.prefix,
            corrections: change.supersededBy,
          ),
        ],
      ],
    );
  }
}

/// Buttons strictly from `allowed_actions` (+ edit from `editable_fields`).
class _ActionBar extends StatelessWidget {
  const _ActionBar({
    required this.change,
    required this.prefix,
    required this.busy,
    required this.readOnly,
    required this.onAction,
    this.onPdf,
    this.pdfBusy = false,
    this.onCorrect,
    this.correcting = false,
  });

  /// "Utwórz korektę" (frozen change, ADR 0021); null = hidden.
  final VoidCallback? onCorrect;
  final bool correcting;

  final Change change;
  final String prefix;
  final bool busy;

  /// "Karta PDF"; null = hidden (no export permission).
  final VoidCallback? onPdf;
  final bool pdfBusy;

  /// Not a member's card (ADR 0016): no edit and no actions, whatever the
  /// lists say.
  final bool readOnly;
  final ValueChanged<String> onAction;

  @override
  Widget build(BuildContext context) {
    final actions = [
      if (!readOnly) ...[
        for (final action in ChangeActions.order)
          if (change.allowedActions.contains(action)) action,
        // Unknown future actions from the API are still offered.
        for (final action in change.allowedActions)
          if (!ChangeActions.order.contains(action)) action,
      ],
    ];
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (!readOnly && change.editableFields.isNotEmpty)
          OutlinedButton.icon(
            key: const ValueKey('card-edit'),
            onPressed: busy
                ? null
                : () => context.go('/c/$prefix/changes/${change.number}/edit'),
            icon: const Icon(Icons.edit_outlined),
            label: const Text('Edytuj'),
          ),
        if (onPdf != null)
          OutlinedButton.icon(
            key: const ValueKey('card-pdf'),
            onPressed: pdfBusy ? null : onPdf,
            icon: pdfBusy
                ? const SizedBox.square(
                    dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.picture_as_pdf_outlined),
            label: const Text('Karta PDF'),
          ),
        if (onCorrect != null)
          OutlinedButton.icon(
            key: const ValueKey('card-correction'),
            onPressed: busy ? null : onCorrect,
            icon: correcting
                ? const SizedBox.square(
                    dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.difference_outlined),
            label: const Text('Utwórz korektę'),
          ),
        for (final action in actions)
          if (ChangeActions.isNegative(action))
            OutlinedButton(
              key: ValueKey('action-$action'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.danger,
                side: const BorderSide(color: AppColors.danger),
              ),
              onPressed: busy ? null : () => onAction(action),
              child: Text(ChangeActions.label(action, change)),
            )
          else
            FilledButton(
              key: ValueKey('action-$action'),
              onPressed: busy ? null : () => onAction(action),
              child: Text(ChangeActions.label(action, change)),
            ),
      ],
    );
  }
}

// --------------------------------------------------------------------- left

class _DescriptionCard extends StatelessWidget {
  const _DescriptionCard({
    required this.change,
    required this.companyId,
    required this.canUpload,
    required this.canDownload,
  });

  final Change change;
  final String companyId;
  final bool canUpload;
  final bool canDownload;

  @override
  Widget build(BuildContext context) {
    final cells = <Widget>[
      _Field(label: 'Co i dlaczego', value: change.description),
      _Field(label: 'Zgłoszenie', value: change.ticketRef, mono: true),
      _Field(label: 'Plan wdrożenia', value: change.implementationPlan),
      _Field(
        label: 'Plan wycofania',
        value: change.rollbackPlan,
        missing: change.risk == Risks.high
            ? 'Brak — wymagany przy wysokim ryzyku'
            : null,
      ),
      _Field(label: 'Wpływ', value: change.impact),
      _LabeledBlock(
        label: 'Załączniki',
        child: AttachmentsSection(
          companyId: companyId,
          changeId: change.id,
          canUpload: canUpload,
          canDownload: canDownload,
        ),
      ),
    ];
    return SectionCard(
      title: 'Opis zmiany',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final twoColumns = constraints.maxWidth >= 560;
          if (!twoColumns) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final cell in cells)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: cell,
                  ),
              ],
            );
          }
          final width = (constraints.maxWidth - 24) / 2;
          return Wrap(
            spacing: 24,
            runSpacing: 16,
            children: [
              for (final cell in cells) SizedBox(width: width, child: cell),
            ],
          );
        },
      ),
    );
  }
}

class _LabeledBlock extends StatelessWidget {
  const _LabeledBlock({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AppColors.textSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        child,
      ],
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.label,
    required this.value,
    this.mono = false,
    this.missing,
  });

  final String label;
  final String? value;
  final bool mono;
  final String? missing;

  @override
  Widget build(BuildContext context) {
    final empty = value == null || value!.trim().isEmpty;
    return _LabeledBlock(
      label: label,
      child: Text(
        empty ? (missing ?? '—') : value!,
        style: TextStyle(
          fontFamily: mono && !empty ? AppFonts.mono : null,
          color: empty
              ? (missing != null ? AppColors.danger : AppColors.textSecondary)
              : AppColors.text,
        ),
      ),
    );
  }
}

class _ConsentsCard extends StatelessWidget {
  const _ConsentsCard({required this.change});

  final Change change;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: 'Zgody właścicieli obiektów (CI)',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [for (final ci in change.ci) _consentRow(ci)],
      ),
    );
  }

  Widget _consentRow(ChangeCi ci) {
    final consents = change.consents.where((c) => c.ciId == ci.id).toList();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: ci.identifier,
                  style: AppFonts.monoStyle(fontWeight: FontWeight.w500),
                ),
                TextSpan(
                  text:
                      ' — właściciel: ${ci.owner?.displayName ?? 'brak właściciela'}',
                ),
              ],
            ),
          ),
          const SizedBox(height: 4),
          if (consents.isEmpty)
            const Tag(label: 'Brak zgody', colors: AppFeedbackColors.warning)
          else
            for (final consent in consents)
              Wrap(
                spacing: 8,
                runSpacing: 4,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Tag(
                    label: consent.valid
                        ? 'Zgoda: ${consent.owner.displayName}'
                        : 'Zgoda nieważna (zmienił się właściciel)',
                    colors: consent.valid
                        ? AppFeedbackColors.success
                        : AppFeedbackColors.error,
                  ),
                  Text(
                    WarsawTime.format(consent.consentedAt),
                    style: AppFonts.monoStyle(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  if (consent.byRequesterOrAssignee)
                    const Tag(
                      key: ValueKey('consent-not-independent'),
                      label:
                          'Zgoda niezależna? Właściciel jest zgłaszającym lub '
                          'wykonawcą',
                      colors: AppFeedbackColors.warning,
                      icon: Icons.warning_amber_outlined,
                      tooltip:
                          'Zgodę wyraziła osoba, która jest też zgłaszającym '
                          'lub wykonawcą zmiany — zatwierdzający powinien to '
                          'uwzględnić.',
                    ),
                ],
              ),
        ],
      ),
    );
  }
}

class _CommentsCard extends ConsumerStatefulWidget {
  const _CommentsCard({
    required this.change,
    required this.companyId,
    required this.canComment,
    required this.onAdded,
  });

  final Change change;
  final String companyId;
  final bool canComment;
  final VoidCallback onAdded;

  @override
  ConsumerState<_CommentsCard> createState() => _CommentsCardState();
}

class _CommentsCardState extends ConsumerState<_CommentsCard> {
  final _controller = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final body = _controller.text.trim();
    if (body.isEmpty) return;
    setState(() => _sending = true);
    try {
      await ref
          .read(changesApiProvider)
          .addComment(widget.companyId, widget.change.id, body);
      _controller.clear();
      widget.onAdded();
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final comments = widget.change.comments;
    return SectionCard(
      title: 'Komentarze',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (comments.isEmpty)
            const Text(
              'Brak komentarzy.',
              style: TextStyle(color: AppColors.textSecondary),
            ),
          for (final comment in comments)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        comment.author.displayName,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      Text(
                        WarsawTime.format(comment.createdAt),
                        style: AppFonts.monoStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                        ),
                      ),
                      if (comment.action != null)
                        Tag(label: ChangeActions.noun(comment.action!)),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(comment.body),
                ],
              ),
            ),
          if (widget.canComment) ...[
            const SizedBox(height: 4),
            TextField(
              key: const ValueKey('comment-field'),
              controller: _controller,
              minLines: 2,
              maxLines: 6,
              maxLength: ChangeActions.maxCommentLength,
              decoration: const InputDecoration(
                labelText: 'Nowy komentarz',
                alignLabelWithHint: true,
              ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                key: const ValueKey('comment-send'),
                onPressed: _sending ? null : _send,
                child: Text(_sending ? 'Wysyłanie…' : 'Dodaj komentarz'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _AuditCard extends ConsumerWidget {
  const _AuditCard({
    required this.change,
    required this.companyId,
    required this.names,
  });

  final Change change;
  final String companyId;
  final NameResolver names;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trail = ref.watch(auditTrailProvider((companyId, change.id)));
    final status = ref.watch(chainStatusProvider(companyId));
    return SectionCard(
      key: const ValueKey('audit-card'),
      title: 'Ścieżka audytu',
      trailing: switch (status) {
        AsyncData(:final value) => ChainStatusBadge(status: value),
        AsyncError() => const Tag(
          label: 'Stan łańcucha niedostępny',
          colors: AppFeedbackColors.neutral,
        ),
        _ => null,
      },
      child: switch (trail) {
        AsyncData(:final value) => AuditTimeline(entries: value, names: names),
        AsyncError(:final error) => ErrorPanel(
          error: error,
          onRetry: () =>
              ref.invalidate(auditTrailProvider((companyId, change.id))),
        ),
        _ => const LoadingPanel(),
      },
    );
  }
}

// --------------------------------------------------------------------- right

class _ClassificationCard extends StatelessWidget {
  const _ClassificationCard({required this.change, required this.company});

  final Change change;
  final CompanyRef company;

  @override
  Widget build(BuildContext context) {
    final approvedBy = change.autoApproved
        ? 'system (automatycznie)'
        : change.approvedBy?.displayName;
    final window = change.windowStart == null && change.windowEnd == null
        ? null
        : '${WarsawTime.format(change.windowStart)} – '
              '${WarsawTime.format(change.windowEnd)}';
    final category = change.category == null
        ? null
        : change.subcategory == null
        ? change.category!.name
        : '${change.category!.name} / ${change.subcategory!.name}';
    return SectionCard(
      title: 'Klasyfikacja',
      child: Column(
        children: [
          _Row('Spółka', '${company.name} (${company.prefix})'),
          _Row('Kategoria', category),
          _Row('Typ', ChangeTypes.label(change.changeType)),
          _Row('Ryzyko', Risks.label(change.risk)),
          _Row('Zgłaszający', change.requestedBy.displayName),
          _Row('Wykonawca', change.assignee?.displayName),
          _Row('Zatwierdzający (wskazany)', change.approver?.displayName),
          _Row(
            'Zatwierdził',
            approvedBy == null
                ? null
                : '$approvedBy, ${WarsawTime.format(change.approvedAt)}',
            key: const ValueKey('classification-approved-by'),
          ),
          _Row('Okno serwisowe', window, mono: true),
          _Row(
            'Wdrożenie',
            change.implementedAt == null
                ? null
                : WarsawTime.format(change.implementedAt),
            mono: true,
          ),
          _Row('Weryfikujący', change.verifier?.displayName),
          _Row(
            'Weryfikacja',
            change.verifiedAt == null
                ? null
                : WarsawTime.format(change.verifiedAt),
            mono: true,
          ),
          _Row('Podstawa / wymóg', change.requirementRef),
          _Row(
            'Zarejestrowano',
            WarsawTime.format(change.createdAt),
            mono: true,
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value, {this.mono = false, super.key});

  final String label;
  final String? value;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final empty = value == null || value!.isEmpty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.textSecondary,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              empty ? '—' : value!,
              style: TextStyle(
                fontFamily: mono && !empty ? AppFonts.mono : null,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ObjectsCard extends StatelessWidget {
  const _ObjectsCard({required this.change});

  final Change change;

  @override
  Widget build(BuildContext context) {
    final frozen = change.ci.any((c) => c.snapshot);
    return SectionCard(
      title: 'Obiekty, których dotyczy',
      child: change.ci.isEmpty
          ? const Text(
              'Nie wskazano obiektów.',
              style: TextStyle(color: AppColors.textSecondary),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (frozen)
                  const Padding(
                    padding: EdgeInsets.only(bottom: 8),
                    child: Text(
                      'Stan obiektów z chwili wdrożenia (migawka).',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [for (final ci in change.ci) _CiChip(ci: ci)],
                ),
              ],
            ),
    );
  }
}

class _CiChip extends StatelessWidget {
  const _CiChip({required this.ci});

  final ChangeCi ci;

  @override
  Widget build(BuildContext context) {
    final renamed =
        ci.snapshot &&
        ((ci.currentIdentifier != null &&
                ci.currentIdentifier != ci.identifier) ||
            (ci.currentName != null && ci.currentName != ci.name));
    final tip = [
      ci.name,
      if (ci.ciTypeCode.isNotEmpty) 'Typ: ${ci.ciTypeCode}',
      if (ci.owner != null) 'Właściciel: ${ci.owner!.displayName}',
      if (renamed) 'Obecnie: ${ci.currentIdentifier} — ${ci.currentName}',
      if (!ci.isActive) 'Obiekt nieaktywny',
    ].join('\n');
    return Tooltip(
      message: tip,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.surfaceMuted,
          borderRadius: AppRadii.smallAll,
          border: Border.all(color: AppColors.border),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                ci.identifier,
                style: AppFonts.monoStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                ci.name,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
              if (renamed)
                Text(
                  'obecnie: ${ci.currentIdentifier}',
                  style: AppFonts.monoStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
              if (!ci.isActive)
                const Text(
                  'nieaktywny',
                  style: TextStyle(fontSize: 11, color: AppColors.danger),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
