import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/change_status.dart';
import 'package:rejestr_zmian/core/theme.dart';
import 'package:rejestr_zmian/widgets/status_pill.dart';

void main() {
  const expected = {
    ChangeStatus.draft: ('Szkic', Color(0xFFECEEF1), Color(0xFF3D4450)),
    ChangeStatus.pendingApproval: (
      'Do zatwierdzenia',
      Color(0xFFFDF0D5),
      Color(0xFF7A4B00),
    ),
    ChangeStatus.approved: (
      'Zatwierdzona',
      Color(0xFFDCE7FD),
      Color(0xFF1E3A8A),
    ),
    ChangeStatus.implemented: (
      'Wdrożona',
      Color(0xFFE2F0FB),
      Color(0xFF0B4A6F),
    ),
    ChangeStatus.verified: (
      'Zweryfikowana',
      Color(0xFFDDF3E4),
      Color(0xFF14532D),
    ),
    ChangeStatus.rejected: ('Odrzucona', Color(0xFFFBE1E1), Color(0xFF8A1C1C)),
    ChangeStatus.rolledBack: ('Wycofana', Color(0xFFFBE1E1), Color(0xFF8A1C1C)),
    ChangeStatus.cancelled: ('Anulowana', Color(0xFFECEEF1), Color(0xFF3D4450)),
  };

  test('every status has an expected label and colours', () {
    expect(expected.keys, containsAll(ChangeStatus.values));
  });

  for (final MapEntry(key: status, value: (label, bg, fg))
      in expected.entries) {
    testWidgets('StatusPill ${status.apiValue} shows "$label"', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light(),
          home: Scaffold(body: StatusPill(status: status)),
        ),
      );

      final text = tester.widget<Text>(find.text(label));
      expect(text.style?.color, fg);

      final box = tester.widget<DecoratedBox>(
        find
            .ancestor(of: find.text(label), matching: find.byType(DecoratedBox))
            .first,
      );
      expect((box.decoration as BoxDecoration).color, bg);
    });
  }

  test('ChangeStatus.tryParse maps API values', () {
    expect(
      ChangeStatus.tryParse('pending_approval'),
      ChangeStatus.pendingApproval,
    );
    expect(ChangeStatus.tryParse('rolled_back'), ChangeStatus.rolledBack);
    expect(ChangeStatus.tryParse('nonsense'), isNull);
  });
}
