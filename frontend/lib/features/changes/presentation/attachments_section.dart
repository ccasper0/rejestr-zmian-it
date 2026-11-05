import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/files/file_service.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../data/changes_api.dart';
import '../data/models.dart';

/// Attachments of a change with sha256, download and (optional) upload.
///
/// Attachments are evidence, not change fields: they are never overwritten
/// (a new version = a new attachment) and every download is audited
/// (ADR 0013 §4). Without [canDownload] (the app admin's read-only view,
/// ADR 0016 §4) only the metadata and the full sha256 are shown.
class AttachmentsSection extends ConsumerStatefulWidget {
  const AttachmentsSection({
    required this.companyId,
    required this.changeId,
    required this.canUpload,
    this.canDownload = true,
    this.showDropZone = false,
    super.key,
  });

  final String companyId;
  final String changeId;
  final bool canUpload;

  /// Download of the file (audited in the company chain).
  final bool canDownload;

  /// Form variant: a framed upload zone (§10.3 "strefa załączników").
  final bool showDropZone;

  @override
  ConsumerState<AttachmentsSection> createState() => _AttachmentsSectionState();
}

class _AttachmentsSectionState extends ConsumerState<AttachmentsSection> {
  bool _uploading = false;
  String? _downloading;

  /// Last failed upload (413 too large, 415 type not allowed, …): stays
  /// visible next to the button — the list of allowed types is long.
  ({String filename, ApiProblem problem})? _uploadError;

  (String, String) get _key => (widget.companyId, widget.changeId);

  Future<void> _upload() async {
    final files = ref.read(fileServiceProvider);
    final picked = await files.pickFile();
    if (picked == null || !mounted) return;
    setState(() {
      _uploading = true;
      _uploadError = null;
    });
    try {
      await ref
          .read(changesApiProvider)
          .uploadAttachment(
            widget.companyId,
            widget.changeId,
            filename: picked.name,
            bytes: picked.bytes,
            contentType: picked.contentType,
          );
      ref
        ..invalidate(attachmentsProvider(_key))
        ..invalidate(auditTrailProvider(_key));
      if (mounted) showInfoSnack(context, 'Dodano załącznik ${picked.name}.');
    } on Object catch (error) {
      if (mounted) {
        setState(
          () => _uploadError = (
            filename: picked.name,
            problem: ApiProblem.from(error),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _download(Attachment attachment) async {
    setState(() => _downloading = attachment.id);
    try {
      final bytes = await ref
          .read(changesApiProvider)
          .downloadAttachment(widget.companyId, widget.changeId, attachment.id);
      ref
          .read(fileServiceProvider)
          .saveFile(
            attachment.filename,
            bytes,
            contentType: attachment.contentType,
          );
      ref.invalidate(auditTrailProvider(_key));
    } on Object catch (error) {
      if (mounted) showErrorSnack(context, error);
    } finally {
      if (mounted) setState(() => _downloading = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final attachments = ref.watch(attachmentsProvider(_key));
    final uploadButton = OutlinedButton.icon(
      key: const ValueKey('attachment-upload'),
      onPressed: _uploading ? null : _upload,
      icon: _uploading
          ? const SizedBox.square(
              dimension: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.attach_file),
      label: Text(_uploading ? 'Wysyłanie…' : 'Dodaj plik'),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        switch (attachments) {
          AsyncError(:final error) => ErrorPanel(
            error: error,
            onRetry: () => ref.invalidate(attachmentsProvider(_key)),
          ),
          AsyncData(:final value) when value.isEmpty => const Text(
            'Brak załączników.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          AsyncData(:final value) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final a in value)
                _AttachmentRow(
                  attachment: a,
                  busy: _downloading == a.id,
                  onDownload: widget.canDownload ? () => _download(a) : null,
                ),
            ],
          ),
          _ => const LinearProgressIndicator(minHeight: 2),
        },
        if (widget.canUpload) ...[
          if (_uploadError case final failed?) ...[
            const SizedBox(height: 8),
            MessageBanner(
              key: const ValueKey('attachment-upload-error'),
              kind: BannerKind.error,
              title: 'Nie dodano pliku ${failed.filename}',
              message: failed.problem.message,
              details: failed.problem.code == 'attachment.type_not_allowed'
                  ? 'Typ pliku jest rozpoznawany po jego zawartości, nie po '
                        'rozszerzeniu nazwy.'
                  : failed.problem.detail,
              actions: [
                TextButton(
                  onPressed: () => setState(() => _uploadError = null),
                  child: const Text('Zamknij'),
                ),
              ],
            ),
          ],
          const SizedBox(height: 8),
          if (widget.showDropZone)
            DecoratedBox(
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: AppRadii.mediumAll,
                border: Border.all(color: AppColors.border, width: 1.5),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const Icon(
                      Icons.upload_file_outlined,
                      color: AppColors.textSecondary,
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Dowody: zrzuty ekranu, eksporty konfiguracji, protokoły. '
                      'Każdy plik dostaje skrót sha256; nowa wersja to nowy '
                      'załącznik.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 8),
                    uploadButton,
                  ],
                ),
              ),
            )
          else
            Align(alignment: Alignment.centerLeft, child: uploadButton),
        ],
      ],
    );
  }
}

class _AttachmentRow extends StatelessWidget {
  const _AttachmentRow({
    required this.attachment,
    required this.busy,
    required this.onDownload,
  });

  final Attachment attachment;
  final bool busy;

  /// `null`: no download (full sha256 shown instead, selectable).
  final VoidCallback? onDownload;

  @override
  Widget build(BuildContext context) {
    final meta = AppFonts.monoStyle(
      fontSize: 12,
      color: AppColors.textSecondary,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          const Icon(
            Icons.description_outlined,
            color: AppColors.textSecondary,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(attachment.filename, overflow: TextOverflow.ellipsis),
                Text(
                  '${formatBytes(attachment.size)} · '
                  '${WarsawTime.format(attachment.createdAt)} · '
                  '${attachment.uploadedBy.displayName}',
                  style: meta,
                ),
                if (onDownload == null)
                  // For checking a file obtained another way (ADR 0016 §4).
                  SelectableText(
                    'sha256 ${attachment.sha256}',
                    key: ValueKey('attachment-sha256-${attachment.id}'),
                    style: meta,
                  )
                else
                  Tooltip(
                    message: 'sha256: ${attachment.sha256}',
                    child: Text(
                      'sha256 ${attachment.sha256.substring(0, attachment.sha256.length.clamp(0, 16))}…',
                      style: meta,
                    ),
                  ),
              ],
            ),
          ),
          if (onDownload case final download?)
            IconButton(
              key: ValueKey('attachment-download-${attachment.id}'),
              tooltip: 'Pobierz ${attachment.filename}',
              onPressed: busy ? null : download,
              icon: busy
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.download_outlined),
            ),
        ],
      ),
    );
  }
}
