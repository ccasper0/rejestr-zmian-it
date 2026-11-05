import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:rejestr_zmian/app/app.dart';
import 'package:rejestr_zmian/app/router.dart';
import 'package:rejestr_zmian/core/api_client.dart';
import 'package:rejestr_zmian/core/auth/auth.dart';
import 'package:rejestr_zmian/core/auth/token_storage.dart';
import 'package:rejestr_zmian/core/config.dart';
import 'package:rejestr_zmian/core/files/file_service.dart';
import 'package:rejestr_zmian/core/health.dart';
import 'package:rejestr_zmian/core/time.dart';

/// Health provider override returning a successful response.
Override healthOk({String? version = '0.1.0'}) =>
    apiHealthProvider.overrideWith((ref) async => HealthInfo(version: version));

/// Health provider override simulating an unreachable API.
Override healthFailing() => apiHealthProvider.overrideWith(
  (ref) async => throw Exception('connection refused'),
);

void setSurfaceSize(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

/// A recorded request to [FakeApi].
class RecordedRequest {
  RecordedRequest(this.method, this.path, this.query, this.data, this.headers);

  final String method;
  final String path;
  final Map<String, List<String>> query;
  final Object? data;
  final Map<String, dynamic> headers;

  Map<String, dynamic> get json =>
      data is Map ? Map<String, dynamic>.from(data! as Map) : const {};

  @override
  String toString() => '$method $path $query';
}

/// Fake response: status + JSON body (or problem+json), or a file.
class FakeResponse {
  const FakeResponse(this.status, [this.body, this.headers = const {}])
    : bytes = null;

  FakeResponse.problem(
    this.status,
    String code,
    String detail, [
    Map<String, Object?> extra = const {},
    this.headers = const {},
  ]) : body = {'code': code, 'detail': detail, 'status': status, ...extra},
       bytes = null;

  /// A response with the body of `test/fixtures/api/[name].json`.
  FakeResponse.fixture(this.status, String name, [this.headers = const {}])
    : body = apiFixture(name),
      bytes = null;

  /// A binary download (report PDF/CSV) with its response headers.
  const FakeResponse.file(
    List<int> this.bytes, {
    this.status = 200,
    this.headers = const {},
  }) : body = null;

  final int status;
  final Object? body;
  final List<int>? bytes;

  /// Extra response headers (`Content-Disposition`, `X-Report-Number`, …).
  final Map<String, String> headers;
}

typedef FakeHandler = FakeResponse Function(RecordedRequest request);

/// Dio adapter answering by method + path (relative to `/api/v1`).
///
/// Handlers registered later win, so a test can override a default route.
class FakeApi implements HttpClientAdapter {
  final List<(String, RegExp, FakeHandler)> _routes = [];
  final List<RecordedRequest> requests = [];

  /// Artificial latency per `'METHOD /path'` (overlapping requests).
  final Map<String, Duration> latency = {};

  void on(String method, String pathPattern, FakeHandler handler) =>
      _routes.insert(0, (method, RegExp('^$pathPattern\$'), handler));

  void reply(
    String method,
    String pathPattern,
    Object? body, [
    int status = 200,
  ]) => on(method, pathPattern, (_) => FakeResponse(status, body));

  List<RecordedRequest> calls(String method, String pathPattern) {
    final pattern = RegExp('^$pathPattern\$');
    return [
      for (final r in requests)
        if (r.method == method && pattern.hasMatch(r.path)) r,
    ];
  }

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    var path = options.uri.path;
    if (path.startsWith('/api/v1')) path = path.substring('/api/v1'.length);
    final request = RecordedRequest(
      options.method,
      path,
      options.uri.queryParametersAll,
      options.data,
      options.headers,
    );
    requests.add(request);
    final delay = latency['${options.method} $path'];
    if (delay != null) await Future<void>.delayed(delay);
    for (final (method, pattern, handler) in _routes) {
      if (method == options.method && pattern.hasMatch(path)) {
        final response = handler(request);
        final extra = {
          for (final e in response.headers.entries)
            e.key.toLowerCase(): [e.value],
        };
        if (response.bytes case final bytes?) {
          return ResponseBody.fromBytes(bytes, response.status, headers: extra);
        }
        final problem = response.status >= 400;
        return ResponseBody.fromString(
          jsonEncode(response.body),
          response.status,
          headers: {
            Headers.contentTypeHeader: [
              problem ? 'application/problem+json' : Headers.jsonContentType,
            ],
            ...extra,
          },
        );
      }
    }
    return ResponseBody.fromString(
      jsonEncode({'code': 'http.not_found', 'detail': 'Brak trasy w teście.'}),
      404,
      headers: {
        Headers.contentTypeHeader: ['application/problem+json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// Records files saved in the "browser" (downloads); [picked] is what the
/// file chooser returns.
class FakeFileService implements FileService {
  FakeFileService({this.picked});

  final PickedFile? picked;
  final List<({String filename, Uint8List bytes, String? contentType})> saved =
      [];

  @override
  Future<PickedFile?> pickFile() async => picked;

  @override
  void saveFile(String filename, Uint8List bytes, {String? contentType}) =>
      saved.add((filename: filename, bytes: bytes, contentType: contentType));
}

/// A valid, non-expired token in storage = signed-in user.
TokenStorage signedInStorage() => MemoryTokenStorage(
  AuthToken(
    accessToken: 'test-token',
    expiresAt: DateTime.now().toUtc().add(const Duration(hours: 8)),
  ).encode(),
);

/// A local-account session (`SessionTokensOut`, ADR 0018) in storage.
TokenStorage localSessionStorage({
  String accessToken = 'access-1',
  String refreshToken = 'refresh-1',
  bool mustChangePassword = false,
  Duration accessValidFor = const Duration(minutes: 15),
}) {
  final now = DateTime.now().toUtc();
  return MemoryTokenStorage(
    AuthToken(
      accessToken: accessToken,
      expiresAt: now.add(accessValidFor),
      refreshToken: refreshToken,
      refreshExpiresAt: now.add(const Duration(hours: 2)),
      sessionExpiresAt: now.add(const Duration(hours: 12)),
      mustChangePassword: mustChangePassword,
    ).encode(),
  );
}

/// `SessionTokensOut` as returned by login/refresh/password change.
Map<String, Object?> sessionTokensJson({
  String accessToken = 'access-2',
  String refreshToken = 'refresh-2',
  bool mustChangePassword = false,
}) => {
  ...apiFixture('auth_tokens')! as Map<String, Object?>,
  'access_token': accessToken,
  'refresh_token': refreshToken,
  'must_change_password': mustChangePassword,
};

/// A JSON fixture of `test/fixtures/api/` (real or schema-based answers).
Object? apiFixture(String name) =>
    jsonDecode(File('test/fixtures/api/$name.json').readAsStringSync());

List<Override> apiOverrides(
  FakeApi api, {
  bool signedIn = true,
  TokenStorage? storage,
  Override? health,
}) {
  WarsawTime.ensureInitialized();
  return [
    httpClientAdapterProvider.overrideWithValue(api),
    apiBaseUrlProvider.overrideWithValue('http://api.test/api/v1'),
    tokenStorageProvider.overrideWithValue(
      storage ?? (signedIn ? signedInStorage() : MemoryTokenStorage()),
    ),
    authModeSettingProvider.overrideWithValue(AuthModeSetting.auto),
    health ?? healthOk(),
  ];
}

/// Pumps the whole app at [location]; returns the router for URL checks.
Future<GoRouter> pumpApp(
  WidgetTester tester, {
  String location = '/c/ALFA/changes',
  FakeApi? api,
  bool signedIn = true,
  TokenStorage? storage,
  Override? health,
  List<Override> overrides = const [],
}) async {
  final fake = api ?? (FakeApi()..installDefaults());
  final container = ProviderContainer(
    retry: (retryCount, error) => null,
    overrides: [
      ...apiOverrides(
        fake,
        signedIn: signedIn,
        storage: storage,
        health: health,
      ),
      initialLocationProvider.overrideWithValue(location),
      ...overrides,
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const RejestrApp()),
  );
  await tester.pumpAndSettle();
  return container.read(routerProvider);
}

/// Unmounts the app and lets requests started on dispose (background save
/// of a dirty form) finish, so no timers are left pending.
Future<void> unmountApp(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pumpAndSettle();
  await tester.pump(const Duration(seconds: 1));
}

String currentPath(GoRouter router) =>
    router.routerDelegate.currentConfiguration.uri.path;

Uri currentUri(GoRouter router) =>
    router.routerDelegate.currentConfiguration.uri;

// ------------------------------------------------------------------ fixtures

const companyAlfa = 'c-alfa';
const companyBeta = 'c-beta';
const userEditor = 'u-editor';
const userApprover = 'u-approver';
const userAuditor = 'u-auditor';

Map<String, Object?> meJson({
  String id = userEditor,
  String name = 'Ewa Edytorska',
  bool admin = false,
  List<String> alfaRoles = const ['editor'],
  List<String> betaRoles = const ['editor'],
}) => {
  'id': id,
  'external_id': 'dev-$id',
  'email': '$id@example.com',
  'display_name': name,
  'is_app_admin': admin,
  'memberships': [
    if (alfaRoles.isNotEmpty)
      {
        'company_id': companyAlfa,
        'company_name': 'Alfa S.A.',
        'company_prefix': 'ALFA',
        'company_status': 'active',
        'roles': alfaRoles,
      },
    if (betaRoles.isNotEmpty)
      {
        'company_id': companyBeta,
        'company_name': 'Beta sp. z o.o.',
        'company_prefix': 'BETA',
        'company_status': 'active',
        'roles': betaRoles,
      },
  ],
};

Map<String, Object?> userRef(String id, String name) => {
  'id': id,
  'display_name': name,
};

Map<String, Object?> changeJson({
  String id = 'ch-1',
  String number = 'CHG-ALFA-2026-0001',
  String? title = 'Aktualizacja reguł zapory',
  String status = 'draft',
  String? type = 'normal',
  String? risk = 'medium',
  String? rollbackPlan = 'Przywrócenie kopii konfiguracji.',
  List<String> allowedActions = const ['submit', 'cancel'],
  List<String>? editableFields,
  int version = 1,
  bool autoApproved = false,
  Map<String, Object?>? approvedBy,
  String? approvedAt,
  String? implementedAt,
  List<Map<String, Object?>> consents = const [],
  String access = 'member',
  List<Map<String, Object?>> ci = const [
    {
      'id': 'ci-1',
      'identifier': 'FW-01',
      'name': 'Zapora brzegowa',
      'ci_type_code': 'firewall',
      'is_active': true,
      'snapshot': false,
      'current_identifier': 'FW-01',
      'current_name': 'Zapora brzegowa',
      'owner': null,
      'consented': false,
    },
  ],
}) => {
  'id': id,
  'company_id': companyAlfa,
  'number': number,
  'title': title,
  'status': status,
  'change_type': type,
  'risk': risk,
  'category': {'id': 'cat-fw', 'code': 'FW', 'name': 'Firewall / sieć'},
  'subcategory': null,
  'ci': ci,
  'requested_by': userRef(userEditor, 'Ewa Edytorska'),
  'assignee': userRef(userEditor, 'Ewa Edytorska'),
  'approver': userRef(userApprover, 'Jan Zatwierdzający'),
  'verifier': null,
  'window_start': '2026-11-02T18:00:00Z',
  'window_end': '2026-11-02T20:00:00Z',
  'approved_at': approvedAt,
  'approved_by': approvedBy,
  'auto_approved': autoApproved,
  'implemented_at': implementedAt,
  'verified_at': null,
  'rejected_at': null,
  'deviations': <Object?>[],
  'created_at': '2026-10-29T08:00:00Z',
  'updated_at': '2026-10-29T08:00:00Z',
  'description': 'Otwarcie portu 443 dla nowego serwera.',
  'implementation_plan': '1. Kopia konfiguracji. 2. Reguła. 3. Test.',
  'rollback_plan': rollbackPlan,
  'impact': 'Brak przerwy.',
  'requirement_ref': 'ISO/IEC 27001:2022 A.8.32',
  'ticket_ref': 'SD-1234',
  'supersedes_change_id': null,
  'supersedes_number': null,
  'superseded_by': <Object?>[],
  'version': version,
  'allowed_actions': allowedActions,
  'editable_fields':
      editableFields ??
      (status == 'draft'
          ? const [
              'approver_id',
              'assignee_id',
              'category_id',
              'change_type',
              'ci_ids',
              'description',
              'impact',
              'implementation_plan',
              'requirement_ref',
              'risk',
              'rollback_plan',
              'subcategory_id',
              'ticket_ref',
              'title',
              'verifier_id',
              'window_end',
              'window_start',
            ]
          : const <String>[]),
  'access': access,
  'suggested_approver_id': userApprover,
  'consents': consents,
  'comments': <Object?>[],
};

Map<String, Object?> page(List<Object?> items, {int? total}) => {
  'items': items,
  'total': total ?? items.length,
  'limit': 50,
  'offset': 0,
};

Map<String, Object?> readinessJson({required bool ok}) => {
  'ok': ok,
  'checks': [
    {
      'code': 'title.required',
      'ok': true,
      'level': 'ok',
      'message_pl': 'Tytuł zmiany jest podany.',
      'field': 'title',
    },
    {
      'code': 'rollback_plan.required_high_risk',
      'ok': ok,
      'level': ok ? 'ok' : 'error',
      'message_pl': 'Przy wysokim ryzyku podano plan wycofania.',
      'field': 'rollback_plan',
    },
  ],
};

extension FakeApiDefaults on FakeApi {
  /// Routes every screen needs (editor in ALFA and BETA, empty register).
  void installDefaults({Map<String, Object?>? me}) {
    reply('GET', '/me', me ?? meJson());
    reply('GET', '/auth/dev/users', [
      {
        'external_id': 'dev-editor',
        'display_name': 'Ewa Edytorska',
        'email': 'editor@example.com',
        'is_app_admin': false,
        'is_active': true,
      },
    ]);
    reply('POST', '/auth/dev/token', {
      'access_token': 'new-token',
      'token_type': 'Bearer',
      'expires_in': 28800,
    });
    reply('POST', '/auth/logout', null, 204);
    reply('GET', '/companies/[^/]+/stats', {
      'pending_approval': 2,
      'approved_not_implemented': 1,
      'emergency_last_30_days': 1,
      'implemented_not_verified': 3,
      'emergency_not_approved_in_24h': 1,
      'implemented_outside_window': 0,
      'by_status': <String, int>{},
    });
    reply('GET', '/companies/[^/]+/changes', page([]));
    reply(
      'GET',
      '/companies/[^/]+/members',
      page([
        {
          'user_id': userEditor,
          'display_name': 'Ewa Edytorska',
          'email': 'editor@example.com',
          'is_active': true,
          'roles': ['editor'],
        },
        {
          'user_id': userApprover,
          'display_name': 'Jan Zatwierdzający',
          'email': 'approver@example.com',
          'is_active': true,
          'roles': ['approver'],
        },
      ]),
    );
    reply('GET', '/companies/[^/]+/categories', {
      'items': [
        {
          'category_id': 'cat-fw',
          'code': 'FW',
          'name': 'Firewall / sieć',
          'requires_approval': true,
          'default_risk': 'medium',
          'is_active': true,
          'approver_override_id': null,
        },
        {
          'category_id': 'cat-acc',
          'code': 'ACC',
          'name': 'Konta i uprawnienia',
          'requires_approval': false,
          'default_risk': 'low',
          'is_active': true,
          'approver_override_id': null,
        },
      ],
    });
    reply('GET', '/categories', page([]));
    reply('GET', '/ci-types', page([]));
    reply('GET', '/companies/[^/]+/ci', page([]));
    reply('GET', '/companies/[^/]+/audit/status', {
      'status': 'ok',
      'ok': true,
      'checked_at': '2026-10-30T02:30:00Z',
      'verified_head_seq': 70,
      'head_seq': 71,
    });
    reply('GET', '/companies/[^/]+/changes/[^/]+/attachments', <Object?>[]);
    reply('GET', '/companies/[^/]+/changes/[^/]+/audit', page([]));
  }
}
