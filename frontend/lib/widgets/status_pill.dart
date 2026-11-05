import 'package:flutter/material.dart';

import '../core/change_status.dart';
import '../core/theme.dart';

/// Coloured pill showing a change status with its Polish label.
class StatusPill extends StatelessWidget {
  const StatusPill({required this.status, super.key});

  final ChangeStatus status;

  @override
  Widget build(BuildContext context) {
    final colors = AppStatusColors.of(status);
    return Semantics(
      label: 'Status: ${status.label}',
      excludeSemantics: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: colors.background,
          borderRadius: const BorderRadius.all(Radius.circular(999)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
          child: Text(
            status.label,
            maxLines: 1,
            style: TextStyle(
              fontFamily: AppFonts.sans,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: colors.foreground,
              height: 1.4,
            ),
          ),
        ),
      ),
    );
  }
}
