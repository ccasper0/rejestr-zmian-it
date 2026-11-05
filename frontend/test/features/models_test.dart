import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/features/changes/data/models.dart';

import '../helpers.dart';

void main() {
  final consent = <String, Object?>{
    'ci_id': 'ci-1',
    'owner': {'id': 'u-1', 'display_name': 'Ewa'},
    'consented_at': '2026-10-29T09:00:00Z',
    'valid': true,
    'by_requester_or_assignee': false,
  };

  test('consent flags are required (never defaulted)', () {
    expect(Consent.fromJson(consent).valid, isTrue);
    for (final key in ['valid', 'by_requester_or_assignee']) {
      final missing = Map<String, Object?>.from(consent)..remove(key);
      expect(() => Consent.fromJson(missing), throwsA(anything), reason: key);
    }
  });

  test('audit entry hash_valid is required', () {
    final entry = <String, Object?>{
      'seq': 1,
      'occurred_at': '2026-10-29T09:00:00Z',
      'actor_display': 'system',
      'entity_type': 'change',
      'action': 'create',
      'hash': 'ab',
      'hash_valid': false,
    };
    expect(AuditEntry.fromJson(entry).hashValid, isFalse);
    entry.remove('hash_valid');
    expect(() => AuditEntry.fromJson(entry), throwsA(anything));
  });

  test('card access: member, admin_read_only, unknown fallback', () {
    Change parse(Object? access) =>
        Change.fromJson({...changeJson(), 'access': access});
    expect(parse('member').isMemberAccess, isTrue);
    expect(parse('admin_read_only').isAdminReadOnly, isTrue);
    expect(parse('admin_read_only').isMemberAccess, isFalse);
    // A newer API value or a register row without the field: never "member".
    expect(parse('auditor_read_only').access, ChangeAccess.unknown);
    expect(parse(null).access, ChangeAccess.unknown);
    expect(parse(null).isMemberAccess, isFalse);
  });
}
