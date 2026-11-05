import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import 'api_client.dart';
import 'auth/auth.dart';

part 'session.freezed.dart';
part 'session.g.dart';

/// Membership of the current user in a company (`GET /me`).
@freezed
abstract class Membership with _$Membership {
  const Membership._();

  const factory Membership({
    required String companyId,
    required String companyName,
    required String companyPrefix,
    @Default('active') String companyStatus,
    @Default(<String>[]) List<String> roles,
  }) = _Membership;

  factory Membership.fromJson(Map<String, dynamic> json) =>
      _$MembershipFromJson(json);

  bool get isArchived => companyStatus == 'archived';
  bool hasRole(String role) => roles.contains(role);

  /// Matrix §5 `change.edit_draft` / `change.assign`: editor, approver.
  bool get canEditChanges => hasRole(Roles.editor) || hasRole(Roles.approver);
}

/// Profile of the signed-in user (`GET /me`).
@freezed
abstract class Me with _$Me {
  const Me._();

  const factory Me({
    required String id,
    required String displayName,
    @Default('') String externalId,
    @Default('') String email,
    @Default(false) bool isAppAdmin,
    // A temporary password must be changed first (ADR 0018 §5).
    @Default(false) bool mustChangePassword,
    @Default(<Membership>[]) List<Membership> memberships,
  }) = _Me;

  factory Me.fromJson(Map<String, dynamic> json) => _$MeFromJson(json);

  Membership? membershipFor(String? prefix) {
    for (final membership in memberships) {
      if (membership.companyPrefix == prefix) return membership;
    }
    return null;
  }

  /// Companies where the user is an auditor (cross-company view, ADR 0002).
  List<Membership> get auditorMemberships => [
    for (final membership in memberships)
      if (membership.hasRole(Roles.auditor)) membership,
  ];

  bool get isAuditor => auditorMemberships.isNotEmpty;

  /// Matrix §5 `ci.manage`: app admin, approver, editor.
  bool canManageCi(String prefix) =>
      isAppAdmin || (membershipFor(prefix)?.canEditChanges ?? false);

  /// Matrix §5 `export.register` (register PDF and CSV): app admin — also
  /// without a role in the company (ADR 0017 §4) — approver, auditor.
  bool canExportRegister(String prefix) {
    if (isAppAdmin) return true;
    final m = membershipFor(prefix);
    return m != null && (m.hasRole(Roles.approver) || m.hasRole(Roles.auditor));
  }

  /// Matrix §5 `export.change_card`: as [canExportRegister] plus the editor.
  bool canExportChangeCard(String prefix) =>
      canExportRegister(prefix) ||
      (membershipFor(prefix)?.hasRole(Roles.editor) ?? false);

  /// Role label for the side panel (roles in [prefix], or admin).
  String roleLabel(String? prefix) {
    final labels = <String>[
      if (isAppAdmin) 'Administrator',
      ...?membershipFor(prefix)?.roles.map(Roles.label),
    ];
    if (labels.isEmpty) return 'Brak ról w tej spółce';
    return labels.join(' · ');
  }
}

/// Membership roles (CLAUDE.md §4.1) with Polish labels.
abstract final class Roles {
  static const String editor = 'editor';
  static const String approver = 'approver';
  static const String auditor = 'auditor';
  static const String viewer = 'viewer';
  static const String appAdmin = 'app_admin';

  static String label(String role) => switch (role) {
    editor => 'Edytor',
    approver => 'Zatwierdzający',
    auditor => 'Audytor',
    viewer => 'Obserwator',
    appAdmin => 'Administrator',
    _ => role,
  };
}

/// Pseudo-prefix for the auditor's cross-company view (ADR 0002).
///
/// Lowercase on purpose: real prefixes are 2–8 uppercase letters A–Z, so it
/// can never collide with a company prefix.
const String allCompaniesPrefix = 'all';
const String allCompaniesLabel = 'Wszystkie spółki (audytor)';

/// The signed-in user's profile; reloaded with every new session (login,
/// password change) — not when the tokens of a session are refreshed.
final meProvider = FutureProvider<Me>((ref) async {
  final (signedIn, _) = ref.watch(
    authControllerProvider.select((s) => (s.isSignedIn, s.epoch)),
  );
  if (!signedIn) throw StateError('Not signed in');
  final dio = ref.watch(apiClientProvider);
  final response = await dio.get<Map<String, dynamic>>('/me');
  final me = Me.fromJson(response.data ?? const {});
  // The server knows best whether a temporary password is still pending.
  ref
      .read(authControllerProvider.notifier)
      .setMustChangePassword(me.mustChangePassword);
  return me;
});

/// Membership for a URL prefix (null: unknown prefix / no access / `all`).
final membershipProvider = Provider.family<Membership?, String>((ref, prefix) {
  return ref.watch(meProvider).value?.membershipFor(prefix);
});

/// Display name for a prefix from the URL (or the prefix itself if unknown).
String companyLabel(Me? me, String prefix) {
  if (prefix == allCompaniesPrefix) return allCompaniesLabel;
  return me?.membershipFor(prefix)?.companyName ?? prefix;
}
