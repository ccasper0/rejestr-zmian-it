// Contract test: real responses of the local backend (AUTH_MODE=dev + seed,
// dumped to test/fixtures/api/*.json, see README "Scenariusz akceptacyjny")
// must parse into the Dart models. A renamed or removed field in the API
// fails here instead of in the browser.
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/api_error.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';
import 'package:rejestr_zmian/core/session.dart';
import 'package:rejestr_zmian/features/admin/data/admin_models.dart';
import 'package:rejestr_zmian/features/audit/data/audit_filters.dart';
import 'package:rejestr_zmian/features/audit/data/audit_models.dart';
import 'package:rejestr_zmian/features/changes/data/models.dart';
import 'package:rejestr_zmian/features/changes/presentation/correction.dart';
import 'package:rejestr_zmian/features/reports/data/report_models.dart';

Object? fixture(String name) =>
    jsonDecode(File('test/fixtures/api/$name.json').readAsStringSync());

Map<String, dynamic> map(String name) => fixture(name)! as Map<String, dynamic>;

PageResult<T> pageOf<T>(String name, T Function(Map<String, dynamic>) item) =>
    PageResult.fromJson(map(name), item);

ApiProblem problemOf(String name, int status) {
  final options = RequestOptions(path: '/x');
  return ApiProblem.from(
    DioException(
      requestOptions: options,
      type: DioExceptionType.badResponse,
      response: Response(
        requestOptions: options,
        statusCode: status,
        data: fixture(name),
      ),
    ),
  );
}

void main() {
  test('/auth/dev/users and /me', () {
    final users = parseDevUsers(fixture('dev_users')! as List<Object?>);
    expect(users.map((u) => u.externalId), contains('dev-editor'));
    final me = Me.fromJson(map('me'));
    expect(me.membershipFor('ALFA')?.roles, contains('editor'));
  });

  test('register page and stats', () {
    final page = pageOf('changes_page', Change.fromJson);
    expect(page.items, isNotEmpty);
    expect(page.total, greaterThanOrEqualTo(page.items.length));
    for (final change in page.items) {
      expect(change.number, startsWith('CHG-ALFA-'));
      expect(change.statusValue, isNotNull);
      // Register rows carry no access mode (ADR 0016).
      expect(change.access, ChangeAccess.unknown);
    }
    final stats = ChangeStats.fromJson(map('stats'));
    expect(stats.byStatus.values.fold<int>(0, (a, b) => a + b), greaterThan(0));
  });

  test('verified card: actual approver, versions, comments, attachments', () {
    final change = Change.fromJson(map('change_verified'));
    expect(change.status, 'verified');
    expect(change.access, ChangeAccess.member);
    expect(change.approvedBy, isNotNull);
    expect(change.autoApproved, isFalse);
    expect(change.version, greaterThan(1));
    expect(change.comments, isNotEmpty);
    expect(change.ci.single.snapshot, isTrue);
    final attachments = [
      for (final a in fixture('attachments')! as List<Object?>)
        Attachment.fromJson(a! as Map<String, dynamic>),
    ];
    expect(attachments.first.sha256, hasLength(64));
  });

  test('draft card, readiness, audit trail and chain status', () {
    final draft = Change.fromJson(map('change_draft'));
    expect(draft.editableFields, contains('rollback_plan'));
    expect(draft.allowedActions, contains('submit'));
    expect(draft.access, ChangeAccess.member);
    final readiness = Readiness.fromJson(map('readiness'));
    expect(readiness.checks, isNotEmpty);
    final trail = pageOf('audit_trail', AuditEntry.fromJson).items;
    expect(trail.first.action, 'create');
    expect(trail.every((e) => e.hashValid), isTrue);
    expect(trail.any((e) => e.context['action'] == 'verify'), isTrue);
    final status = ChainStatus.fromJson(map('audit_status'));
    expect(['ok', 'stale', 'broken', 'unknown'], contains(status.status));
  });

  test('company data: members, categories, CI, CI types', () {
    expect(pageOf('members', Member.fromJson).items, isNotEmpty);
    final categories = [
      for (final c in map('company_categories')['items'] as List<Object?>)
        CompanyCategory.fromJson(c! as Map<String, dynamic>),
    ];
    expect(categories.map((c) => c.code), contains('FW'));
    expect(pageOf('categories_top', Category.fromJson).items, isNotEmpty);
    final subs = pageOf('categories_sub', Category.fromJson).items;
    expect(subs.every((s) => s.parentId != null), isTrue);
    expect(pageOf('ci_page', CiItem.fromJson).items, isNotEmpty);
    expect(pageOf('ci_types', CiType.fromJson).items, isNotEmpty);
  });

  test('create draft and action result', () {
    final created = Change.fromJson(map('change_created'));
    expect(created.status, 'draft');
    expect(created.version, 1);
    final result = ActionResult.fromJson(map('action_result'));
    expect(result.toStatus, 'cancelled');
    expect(result.change.status, 'cancelled');
    expect(created.access, ChangeAccess.member);
    expect(result.change.access, ChangeAccess.member);
  });

  test('problem+json: version conflict and not_ready', () {
    final conflict = problemOf('problem_version_conflict', 409);
    expect(conflict.isVersionConflict, isTrue);
    expect(conflict.currentVersion, isNotNull);
    final notReady = problemOf('problem_not_ready', 422);
    expect(notReady.isNotReady, isTrue);
    final checks = [
      for (final c in notReady.checks) ReadinessCheck.fromJson(c),
    ];
    expect(checks.any((c) => c.isError), isTrue);
  });
  // Stage 6 (tool/dump_admin_fixtures.py): admin, CI and audit log.
  test('admin: companies with counters, users, user detail', () {
    final companies = pageOf('companies_admin', AdminCompany.fromJson).items;
    final alfa = companies.firstWhere((c) => c.prefix == 'ALFA');
    expect(alfa.counts.allCi, greaterThanOrEqualTo(alfa.counts.activeCi));
    expect(alfa.counts.activeCi, greaterThan(0));
    expect(alfa.myRoles, isEmpty); // the admin has no role in ALFA
    final users = pageOf('users_page', UserAccount.fromJson).items;
    expect(users.any((u) => u.isAppAdmin), isTrue);
    final detail = UserDetail.fromJson(map('user_detail'));
    expect(detail.memberships, isNotEmpty);
    expect(detail.memberships.first.roles, isNotEmpty);
  });

  test('permission matrix and the whole category dictionary', () {
    final matrix = PermissionMatrix.fromJson(map('permission_matrix'));
    expect(matrix.roles, [
      'app_admin',
      'approver',
      'editor',
      'auditor',
      'viewer',
    ]);
    final approve = matrix.actions.firstWhere(
      (a) => a.action == 'change.approve',
    );
    expect(approve.roles, ['approver']);
    // ADR 0016 §5: the admin's read-only register path is noted.
    final view = matrix.actions.firstWhere((a) => a.action == 'register.view');
    expect(view.roles, contains('app_admin'));
    expect(view.note, contains('tylko odczyt'));
    expect(matrix.actions.every((a) => a.label.isNotEmpty), isTrue);
    expect(
      matrix.changeActions.map((r) => r.action),
      containsAll(['submit', 'approve', 'consent']),
    );
    final categories = pageOf('categories_all', Category.fromJson).items;
    expect(categories.any((c) => c.parentId == null), isTrue);
    expect(categories.any((c) => c.parentId != null), isTrue);
  });

  test('audit log pages and verification', () {
    for (final name in ['audit_page', 'audit_global_page']) {
      final entries = pageOf(name, AuditLogEntry.fromJson).items;
      expect(entries, isNotEmpty, reason: name);
      for (final e in entries) {
        expect(e.hash, hasLength(64));
        expect(e.prevHash, hasLength(64));
        // every entity type and action of the API has a Polish label
        expect(AuditFilters.entityTypes, contains(e.entityType));
        expect(AuditFilters.actions, contains(e.action));
      }
      // newest first
      expect(entries.first.seq, greaterThan(entries.last.seq));
    }
    expect(
      pageOf('audit_global_page', AuditLogEntry.fromJson).items.first.companyId,
      isNull,
    );
    final verify = VerifyResult.fromJson(map('verify_result'));
    expect(verify.chain, 'company');
    expect(verify.ok, isTrue);
    expect(verify.auditEntry!.seq, greaterThan(verify.headSeq));
  });

  test('problem+json: duplicate company name', () {
    final problem = problemOf('problem_company_name_taken', 409);
    expect(problem.code, 'company.name_taken');
    expect(problem.message, 'Spółka o tej nazwie już istnieje.');
  });

  // Stage 7 (ADR 0017 §10). The local stack ran the pre-stage-7 API when
  // these were written, so they follow backend/app/schemas/reports.py by hand
  // (refresh: tool/dump_report_fixtures.py).
  test('reports: done, pending (multi-company), list with every status', () {
    final done = Report.fromJson(map('report_done'));
    expect(done.isDone, isTrue);
    expect(done.kind, ReportKinds.register);
    expect(done.company?.prefix, 'ALFA');
    expect(done.dataSha256, hasLength(64));
    expect(done.downloadUrl, '/api/v1/reports/${done.id}/download');
    expect(done.periodFrom!.isUtc, isTrue);
    expect(done.filters['period_by'], 'implemented');

    final pending = Report.fromJson(map('report_pending'));
    expect(pending.isPending, isTrue);
    expect(pending.isAggregate, isTrue);
    expect(pending.number, startsWith('RAP-2026-'));
    expect(pending.companies.map((c) => c.prefix), ['ALFA', 'BETA']);
    expect(pending.downloadUrl, isNull);

    final page = pageOf('reports_page', Report.fromJson);
    expect(page.items.map((r) => r.status).toSet(), {
      'done',
      'failed',
      'pending',
    });
    expect(page.items.map((r) => r.format).toSet(), {'pdf', 'csv'});
    final card = page.items.firstWhere((r) => r.kind == 'change_card');
    expect(card.changeNumber, startsWith('CHG-ALFA-'));
    final failed = page.items.firstWhere((r) => r.isFailed);
    expect(failed.error, isNotEmpty);
  });

  test('report request body matches ReportCreate (extra="forbid")', () {
    final json = const ReportRequest(
      kind: 'register',
      companyId: 'c-1',
    ).toJson();
    expect(json.keys.toSet(), {
      'kind',
      'company_id',
      'change_id',
      'period_from',
      'period_to',
      'filters',
      'include_audit_trail',
    });
    expect((json['filters'] as Map).keys.toSet(), {
      'period_by',
      'status',
      'type',
      'category',
      'ci',
      'assignee',
      'approver',
      'approved_by',
      'q',
    });
  });

  test('problem+json: report too large — Polish message with numbers', () {
    final problem = problemOf('problem_report_too_large', 422);
    expect(problem.code, 'report.too_large');
    expect(
      problem.message,
      'Raport obejmowałby 6120 zmian (maksymalnie 5000). Zawęź okres lub '
      'filtry.',
    );
  });

  // Local accounts (ADR 0018) and hardening (ADR 0019): these fixtures are
  // written from backend/app/schemas/identity.py, app/api/v1/{auth,users}.py,
  // app/services/attachments.py and the nginx error bodies — the local stack
  // runs AUTH_MODE=dev, so there is no real local account to dump from.
  test('SessionTokensOut → AuthToken (refresh, session end, temporary)', () {
    final now = DateTime.utc(2026, 11, 3, 8);
    final token = AuthToken.fromResponse(map('auth_tokens'), now);
    expect(token.expiresAt, DateTime.utc(2026, 11, 3, 8, 15));
    expect(token.refreshToken, isNotEmpty);
    expect(token.refreshExpiresAt, DateTime.utc(2026, 11, 3, 10));
    expect(token.sessionExpiresAt, DateTime.utc(2026, 11, 3, 20));
    expect(token.isLocalAccount, isTrue);
    expect(token.mustChangePassword, isFalse);
    expect(AuthToken.decode(token.encode())?.refreshToken, token.refreshToken);
    expect(
      AuthToken.fromResponse(
        map('auth_tokens_temporary'),
        now,
      ).mustChangePassword,
      isTrue,
    );
  });

  test('UserWithTemporaryPasswordOut and UserOut password state', () {
    final created = UserWithTemporaryPassword.fromJson(map('user_created'));
    expect(created.temporaryPassword, matches(r'^(\w{5}-){3}\w{5}$'));
    expect(created.user.hasPassword, isTrue);
    expect(created.user.mustChangePassword, isTrue);
    expect(created.user.lockedUntil, isNull);
    expect(created.user.tempPasswordExpiresAt, DateTime.utc(2026, 11, 10, 8));
    // Older answers (before ADR 0018) still parse: state defaults.
    final dev = pageOf('users_page', UserAccount.fromJson).items.first;
    expect(dev.hasPassword, isFalse);
    expect(dev.tempPasswordExpiresAt, isNull);
  });

  test('problem+json of auth, attachments and nginx — Polish messages', () {
    expect(
      problemOf('problem_invalid_credentials', 401).message,
      'Nieprawidłowy e-mail lub hasło albo konto jest zablokowane/nieaktywne.',
    );
    expect(
      problemOf('problem_too_many_attempts', 429).message,
      startsWith('Zbyt wiele nieudanych prób logowania'),
    );
    expect(
      problemOf('problem_password_too_common', 422).code,
      'auth.password_too_common',
    );
    final type = problemOf('problem_attachment_type', 415);
    expect(type.message, contains('(program Windows)'));
    expect(type.message, contains('MSG (Outlook)'));
    expect(
      problemOf('problem_attachment_too_large', 413).message,
      'Plik jest zbyt duży (maksymalnie 25 MB).',
    );
    expect(
      problemOf('problem_rate_limited', 429).message,
      'Przekroczono limit żądań. Odczekaj chwilę i spróbuj ponownie.',
    );
    expect(problemOf('problem_api_unavailable', 503).code, 'api.unavailable');
    expect(
      problemOf('problem_temporary_password_expired', 401).message,
      'Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie '
      'hasła.',
    );
    expect(
      problemOf('problem_last_admin', 409).message,
      startsWith('To ostatni aktywny administrator aplikacji'),
    );
  });

  test('correction of a frozen change (ADR 0021)', () {
    final original = Change.fromJson(map('change_correction_original'));
    final correction = Change.fromJson(map('change_correction'));
    expect(ChangeCorrection.isCorrectable(original), isTrue);
    expect(ChangeCorrection.isCorrectable(correction), isFalse);
    expect(correction.status, 'draft');
    expect(correction.supersedesChangeId, original.id);
    expect(correction.supersedesNumber, original.number);
    expect(original.supersedesNumber, isNull);
    final link = original.supersededBy.single;
    expect(link.id, correction.id);
    expect(link.number, correction.number);
    expect(link.statusValue, isNotNull);
    expect(correction.title, ChangeCorrection.title(original));
    expect(correction.windowStart, isNull);
    expect(correction.ci.map((c) => c.id), original.ci.map((c) => c.id));
    // the body the card sends: every key is a field of ChangeCreate
    final body = ChangeCorrection.draftFields(original);
    expect(body['supersedes_change_id'], original.id);
    expect(body.keys, isNot(contains('window_start')));
    expect(body.keys, isNot(contains('window_end')));
    expect(correction.category?.id, body['category_id']);
    expect(correction.assignee?.id, body['assignee_id']);
    expect(correction.verifier?.id, body['verifier_id']);
  });
}
