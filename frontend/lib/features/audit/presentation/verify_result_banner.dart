import 'package:flutter/material.dart';

import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../data/audit_models.dart';

/// Result of `POST /audit/verify` (ADR 0009 §4) as a banner.
class VerifyResultBanner extends StatelessWidget {
  const VerifyResultBanner({required this.result, this.onClose, super.key});

  final VerifyResult result;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final chain = result.chain == 'global'
        ? 'Łańcuch globalny'
        : 'Łańcuch spółki';
    final when = result.verifiedAt == null
        ? ''
        : ' Sprawdzono ${WarsawTime.format(result.verifiedAt)}.';
    final recorded = switch (result.recordedIn) {
      'chain' =>
        'Wynik zapisano w weryfikowanym łańcuchu (wpis '
            '#${result.auditEntry?.seq}).',
      'global' =>
        'Łańcuch spółki odrzucił dopisanie — wynik zapisano w '
            'łańcuchu globalnym.',
      _ =>
        'Wyniku nie udało się zapisać w dzienniku — powiadom '
            'administratora.',
    };
    return MessageBanner(
      key: const ValueKey('verify-result'),
      kind: result.ok ? BannerKind.success : BannerKind.error,
      title: result.ok
          ? '$chain spójny'
          : '$chain naruszony — pierwszy niezgodny wpis '
                '#${result.firstBrokenSeq ?? '?'}',
      message:
          'Sprawdzono wpisów: ${result.checked} (do #${result.headSeq}).$when '
          '$recorded',
      details: 'sha256 głowy: ${result.headHash}',
      actions: [
        if (onClose != null)
          TextButton(onPressed: onClose, child: const Text('Ukryj')),
      ],
    );
  }
}

Future<void> showVerifyResultDialog(
  BuildContext context,
  VerifyResult result,
) => showDialog<void>(
  context: context,
  builder: (context) => AlertDialog(
    title: const Text('Weryfikacja łańcucha audytu'),
    content: SizedBox(
      width: 480,
      child: DefaultTextStyle.merge(
        style: const TextStyle(color: AppColors.text),
        child: VerifyResultBanner(result: result),
      ),
    ),
    actions: [
      FilledButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Zamknij'),
      ),
    ],
  ),
);
