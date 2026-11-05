import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/auth.dart';
import '../core/navigation/exit_guard.dart';
import '../features/admin/presentation/categories_tab.dart';
import '../features/admin/presentation/ci_types_tab.dart';
import '../features/admin/presentation/companies_tab.dart';
import '../features/admin/presentation/permissions_tab.dart';
import '../features/admin/presentation/users_page.dart';
import '../features/audit/data/audit_filters.dart';
import '../features/audit/presentation/audit_log_page.dart';
import '../features/auth/change_password_page.dart';
import '../features/auth/login_page.dart';
import '../features/changes/data/register_filters.dart';
import '../features/changes/presentation/change_card_page.dart';
import '../features/changes/presentation/change_form_page.dart';
import '../features/changes/presentation/register_page.dart';
import '../features/ci/data/ci_filters.dart';
import '../features/ci/presentation/ci_inventory_page.dart';
import '../features/reports/presentation/reports_page.dart';
import '../widgets/app_shell.dart';
import '../widgets/placeholder_page.dart';
import 'home_page.dart';

/// Path of the password change (forced after a temporary password, or
/// chosen from the user menu; ADR 0018 §5).
const String changePasswordPath = '/account/password';

/// Where to go after login: only local paths (no open redirect).
///
/// Rejects `//host`, backslashes (browsers treat `/\host` like `//host`),
/// control characters, anything with a scheme or authority, `/login` and
/// the password change itself.
String? safeReturnPath(String? from) {
  if (from == null || !from.startsWith('/') || from.startsWith('//')) {
    return null;
  }
  if (from.contains('\\') || RegExp(r'[\x00-\x1f\x7f]').hasMatch(from)) {
    return null;
  }
  final uri = Uri.tryParse(from);
  if (uri == null || uri.hasScheme || uri.hasAuthority) return null;
  if (uri.path == '/login' || uri.path.startsWith('/login/')) return null;
  if (uri.path == changePasswordPath) return null;
  return from;
}

/// Company prefix in the URL: 2-8 letters A-Z (CLAUDE.md §4.1) or the
/// auditor's pseudo-prefix `all` (ADR 0002).
final RegExp companyPrefixPattern = RegExp(r'^([A-Z]{2,8}|all)$');

/// Change number in the URL (`CHG-{PREFIX}-{YYYY}-{NNNN}`, §4.1).
final RegExp changeNumberPattern = RegExp(
  r'^CHG-[A-Z]{2,8}-[0-9]{4}-[0-9]{4,}$',
);

/// User id in the URL (`/admin/users/:userId`): a UUID.
final RegExp uuidPattern = RegExp(
  r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
);

/// Path parameters are validated before they reach any API path: a
/// decoded `..%2F` must never become part of a request (ADR 0014 §6).
bool validPathParameters(Map<String, String> parameters) {
  final prefix = parameters['prefix'];
  final number = parameters['number'];
  final userId = parameters['userId'];
  if (prefix != null && !companyPrefixPattern.hasMatch(prefix)) return false;
  if (number != null && !changeNumberPattern.hasMatch(number)) return false;
  if (userId != null && !uuidPattern.hasMatch(userId)) return false;
  return true;
}

/// `path?from=target` (without `from` when the target is the home page).
String _withFrom(String path, String? target) => target == null || target == '/'
    ? path
    : Uri(path: path, queryParameters: {'from': target}).toString();

/// Deliberate sign-out: ends the session and opens `/login` without `from`,
/// so the next person signing in on this browser does not land on the
/// previous user's page (`from` is kept only for an expired session).
Future<void> signOutToLogin(BuildContext context, WidgetRef ref) async {
  final router = GoRouter.of(context);
  await ref.read(authControllerProvider.notifier).logout();
  router.go('/login');
}

/// Builds the application router.
///
/// The selected company lives in the URL: `/c/{prefix}/...`. Without a
/// session every page redirects to `/login?from=…` ([isSignedIn]); while a
/// temporary password must be changed ([mustChangePassword]) every page
/// redirects to [changePasswordPath]. The router re-evaluates on
/// [refreshListenable].
GoRouter createRouter({
  String initialLocation = '/',
  Listenable? refreshListenable,
  bool Function()? isSignedIn,
  bool Function()? mustChangePassword,
  ExitGuard? exitGuard,
}) {
  Page<void> page(GoRouterState state, Widget child) => NoTransitionPage<void>(
    key: state.pageKey,
    child: validPathParameters(state.pathParameters)
        ? child
        : PlaceholderPage(
            title: 'Nie znaleziono strony',
            subtitle: state.uri.path,
          ),
  );

  String prefixOf(GoRouterState state) => state.pathParameters['prefix']!;

  return GoRouter(
    initialLocation: initialLocation,
    refreshListenable: refreshListenable,
    redirect: (context, state) {
      final signedIn = isSignedIn?.call() ?? true;
      final path = state.uri.path;
      final atLogin = path == '/login';
      if (!signedIn) {
        return atLogin ? null : _withFrom('/login', state.uri.toString());
      }
      final target = atLogin
          ? safeReturnPath(state.uri.queryParameters['from']) ?? '/'
          : null;
      if ((mustChangePassword?.call() ?? false) && path != changePasswordPath) {
        // Only /me, the password change and logout work until then.
        return _withFrom(changePasswordPath, target ?? state.uri.toString());
      }
      return target;
    },
    routes: [
      GoRoute(
        path: '/login',
        pageBuilder: (_, state) => page(state, const LoginPage()),
      ),
      GoRoute(
        path: changePasswordPath,
        pageBuilder: (_, state) => page(
          state,
          ChangePasswordPage(from: state.uri.queryParameters['from']),
        ),
      ),
      GoRoute(
        path: '/',
        pageBuilder: (_, state) => page(state, const HomePage()),
      ),
      GoRoute(
        path: '/c/:prefix',
        redirect: (_, state) =>
            '/c/${Uri.encodeComponent(prefixOf(state))}/changes',
      ),
      GoRoute(
        path: '/c/:prefix/approvals',
        redirect: (_, state) =>
            const RegisterFilters(statuses: ['pending_approval'])
                .location(Uri.encodeComponent(prefixOf(state))),
      ),
      GoRoute(path: '/admin', redirect: (_, _) => '/admin/companies'),
      ShellRoute(
        builder: (context, state, child) =>
            AppShell(location: state.uri.path, child: child),
        routes: [
          GoRoute(
            path: '/c/:prefix/changes',
            pageBuilder: (_, state) => page(
              state,
              RegisterPage(
                prefix: prefixOf(state),
                filters: RegisterFilters.fromQuery(
                  state.uri.queryParametersAll,
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/c/:prefix/changes/new',
            pageBuilder: (_, state) =>
                page(state, NewChangePage(prefix: prefixOf(state))),
          ),
          GoRoute(
            path: '/c/:prefix/changes/:number',
            pageBuilder: (_, state) => page(
              state,
              ChangeCardPage(
                prefix: prefixOf(state),
                number: state.pathParameters['number']!,
              ),
            ),
          ),
          GoRoute(
            path: '/c/:prefix/changes/:number/edit',
            // Unsaved form edits: the form saves first or keeps the user.
            onExit: (_, _) => exitGuard?.allowExit() ?? true,
            pageBuilder: (_, state) => page(
              state,
              ChangeFormPage(
                prefix: prefixOf(state),
                number: state.pathParameters['number']!,
              ),
            ),
          ),
          GoRoute(
            path: '/c/:prefix/ci',
            pageBuilder: (_, state) => page(
              state,
              CiInventoryPage(
                prefix: prefixOf(state),
                filters: CiFilters.fromQuery(state.uri.queryParametersAll),
              ),
            ),
          ),
          GoRoute(
            path: '/c/:prefix/reports',
            // Filters of the register ("Eksport PDF") pre-fill the form.
            pageBuilder: (_, state) => page(
              state,
              ReportsPage(
                prefix: prefixOf(state),
                initial: RegisterFilters.fromQuery(
                  state.uri.queryParametersAll,
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/c/:prefix/audit',
            pageBuilder: (_, state) => page(
              state,
              AuditLogPage(
                prefix: prefixOf(state),
                filters: AuditFilters.fromQuery(state.uri.queryParameters),
              ),
            ),
          ),
          GoRoute(
            path: '/admin/companies',
            // Unsaved edits of the company panel ask before leaving.
            onExit: (_, _) => exitGuard?.allowExit() ?? true,
            pageBuilder: (_, state) => page(state, const AdminCompaniesPage()),
          ),
          GoRoute(
            path: '/admin/categories',
            pageBuilder: (_, state) => page(
              state,
              AdminCategoriesPage(
                filter: ActivityFilter.parse(
                  state.uri.queryParameters['status'],
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/admin/ci-types',
            pageBuilder: (_, state) => page(
              state,
              AdminCiTypesPage(
                filter: ActivityFilter.parse(
                  state.uri.queryParameters['status'],
                ),
              ),
            ),
          ),
          GoRoute(
            path: '/admin/permissions',
            pageBuilder: (_, state) =>
                page(state, const AdminPermissionsPage()),
          ),
          GoRoute(
            path: '/admin/audit',
            pageBuilder: (_, state) => page(
              state,
              GlobalAuditLogPage(
                filters: AuditFilters.fromQuery(state.uri.queryParameters),
              ),
            ),
          ),
          GoRoute(
            path: '/admin/users',
            pageBuilder: (_, state) {
              final (q, p) = AdminUsersPage.parse(state.uri.queryParameters);
              return page(state, AdminUsersPage(q: q, page: p));
            },
          ),
          GoRoute(
            path: '/admin/users/:userId',
            pageBuilder: (_, state) => page(
              state,
              AdminUserDetailPage(userId: state.pathParameters['userId']!),
            ),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: PlaceholderPage(
        title: 'Nie znaleziono strony',
        subtitle: state.uri.toString(),
      ),
    ),
  );
}

/// First location of the app (tests override it).
final initialLocationProvider = Provider<String>((ref) => '/');

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authControllerProvider, (previous, next) {
    if (previous?.isSignedIn != next.isSignedIn ||
        previous?.mustChangePassword != next.mustChangePassword) {
      refresh.value++;
    }
  });
  final router = createRouter(
    initialLocation: ref.read(initialLocationProvider),
    refreshListenable: refresh,
    isSignedIn: () => ref.read(authControllerProvider).isSignedIn,
    mustChangePassword: () =>
        ref.read(authControllerProvider).mustChangePassword,
    exitGuard: ref.read(exitGuardProvider),
  );
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });
  return router;
});
