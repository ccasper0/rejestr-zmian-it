import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_error.dart';
import '../../core/auth/auth.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'password_field.dart';

/// Login screen. Local accounts (`AUTH_MODE=local`, ADR 0018): e-mail and
/// password (`POST /auth/login`). Dev mode: pick a test user
/// (`GET /auth/dev/users` → `POST /auth/dev/token`).
///
/// After a successful login the router redirect takes the user back to the
/// page they came from (`?from=`).
class LoginPage extends ConsumerWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notice = ref.watch(authControllerProvider.select((s) => s.notice));
    final provider = ref.watch(authProviderProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const _Brand(),
                    const SizedBox(height: 20),
                    if (notice != null) ...[
                      MessageBanner(kind: BannerKind.warning, message: notice),
                      const SizedBox(height: 16),
                    ],
                    switch (provider) {
                      AsyncData(value: final DevAuthProvider dev) => _DevLogin(
                        provider: dev,
                      ),
                      AsyncData(value: final LocalAuthProvider local) =>
                        _LocalLogin(provider: local),
                      AsyncError(:final error) => ErrorPanel(
                        error: error,
                        onRetry: () => ref.invalidate(authProviderProvider),
                      ),
                      _ => const LoadingPanel(
                        label: 'Sprawdzanie metody logowania…',
                      ),
                    },
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const DecoratedBox(
          decoration: BoxDecoration(
            color: AppColors.accent,
            borderRadius: AppRadii.smallAll,
          ),
          child: SizedBox.square(
            dimension: 40,
            child: Icon(
              Icons.published_with_changes,
              color: AppColors.onAccent,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: const Text(
                  'Rejestr zmian IT',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                ),
              ),
              const Text(
                'Zaloguj się, aby kontynuować',
                style: TextStyle(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DevLogin extends ConsumerStatefulWidget {
  const _DevLogin({required this.provider});

  final DevAuthProvider provider;

  @override
  ConsumerState<_DevLogin> createState() => _DevLoginState();
}

class _DevLoginState extends ConsumerState<_DevLogin> {
  late Future<List<DevUser>> _users = widget.provider.users();
  String? _signingIn;
  Object? _error;

  Future<void> _signIn(DevUser user) async {
    setState(() {
      _signingIn = user.externalId;
      _error = null;
    });
    try {
      final token = await widget.provider.signIn(user.externalId);
      ref.read(authControllerProvider.notifier).signIn(token);
    } on Object catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _signingIn = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const MessageBanner(
          kind: BannerKind.warning,
          title: 'Tryb deweloperski',
          message:
              'Logowanie bez hasła jako użytkownik testowy. Ten tryb jest '
              'niedostępny w produkcji.',
        ),
        const SizedBox(height: 16),
        if (_error != null) ...[
          ErrorPanel(error: _error!),
          const SizedBox(height: 12),
        ],
        FutureBuilder<List<DevUser>>(
          future: _users,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return ErrorPanel(
                error: snapshot.error!,
                onRetry: () => setState(() => _users = widget.provider.users()),
              );
            }
            final users = snapshot.data;
            if (users == null) return const LoadingPanel();
            if (users.isEmpty) {
              return const MessageBanner(
                message:
                    'Brak użytkowników testowych. Uruchom '
                    '`python -m app.cli seed` w backendzie.',
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final user in users)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _DevUserButton(
                      user: user,
                      busy: _signingIn == user.externalId,
                      onPressed: _signingIn != null || !user.isActive
                          ? null
                          : () => _signIn(user),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _DevUserButton extends StatelessWidget {
  const _DevUserButton({
    required this.user,
    required this.busy,
    required this.onPressed,
  });

  final DevUser user;
  final bool busy;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      key: ValueKey('dev-user-${user.externalId}'),
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.displayName,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                Text(
                  user.email.isEmpty ? user.externalId : user.email,
                  style: AppFonts.monoStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (user.isAppAdmin)
            const Padding(
              padding: EdgeInsets.only(left: 8),
              child: Tag(
                label: 'Administrator',
                colors: AppFeedbackColors.info,
              ),
            ),
          if (!user.isActive)
            const Padding(
              padding: EdgeInsets.only(left: 8),
              child: Tag(label: 'Nieaktywny'),
            ),
          if (busy)
            const Padding(
              padding: EdgeInsets.only(left: 8),
              child: SizedBox.square(
                dimension: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
        ],
      ),
    );
  }
}

/// E-mail + password (ADR 0018 §6): one answer for every failure (401
/// `auth.invalid_credentials`); 429 (`auth.too_many_attempts` from the API
/// or `request.rate_limited` from nginx) blocks the button until
/// `Retry-After` passes.
class _LocalLogin extends ConsumerStatefulWidget {
  const _LocalLogin({required this.provider});

  final LocalAuthProvider provider;

  @override
  ConsumerState<_LocalLogin> createState() => _LocalLoginState();
}

class _LocalLoginState extends ConsumerState<_LocalLogin> {
  /// Wait when a 429 came without a readable `Retry-After` (e.g. hidden by
  /// CORS when the API is on another origin).
  static const int _defaultWaitSeconds = 30;

  final _email = TextEditingController();
  final _password = TextEditingController();
  final _passwordFocus = FocusNode();
  bool _busy = false;
  bool _validated = false;
  ApiProblem? _error;
  int _waitSeconds = 0;
  Timer? _ticker;

  @override
  void dispose() {
    _ticker?.cancel();
    _email.dispose();
    _password.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  String? get _emailError {
    if (!_validated) return null;
    final email = _email.text.trim();
    if (email.isEmpty) return 'Podaj adres e-mail.';
    if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      return 'Podaj poprawny adres e-mail.';
    }
    return null;
  }

  String? get _passwordError =>
      _validated && _password.text.isEmpty ? 'Podaj hasło.' : null;

  bool get _blocked => _busy || _waitSeconds > 0;

  void _startWait(Duration? retryAfter) {
    _ticker?.cancel();
    final seconds = retryAfter == null
        ? _defaultWaitSeconds
        : (retryAfter.inMilliseconds / 1000).ceil();
    _waitSeconds = seconds < 1 ? 1 : seconds;
    _ticker = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return timer.cancel();
      setState(() => _waitSeconds--);
      if (_waitSeconds <= 0) timer.cancel();
    });
  }

  Future<void> _submit() async {
    if (_blocked) return;
    setState(() => _validated = true);
    if (_emailError != null || _passwordError != null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final token = await widget.provider.signIn(
        email: _email.text.trim(),
        password: _password.text,
      );
      TextInput.finishAutofillContext();
      ref.read(authControllerProvider.notifier).signIn(token);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        _error = problem;
        if (problem.status == 401) _password.clear();
        if (problem.isRateLimited) _startWait(problem.retryAfter);
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _revalidate(String _) {
    if (_validated) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    return AutofillGroup(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (error != null) ...[
            MessageBanner(
              key: const ValueKey('login-error'),
              kind: error.isRateLimited ? BannerKind.warning : BannerKind.error,
              message: error.message,
              details: error.status == 401 || error.isRateLimited
                  ? null
                  : error.detail,
            ),
            const SizedBox(height: 16),
          ],
          TextField(
            key: const ValueKey('login-email'),
            controller: _email,
            enabled: !_busy,
            autofocus: true,
            keyboardType: TextInputType.emailAddress,
            autocorrect: false,
            enableSuggestions: false,
            autofillHints: const [AutofillHints.username, AutofillHints.email],
            textInputAction: TextInputAction.next,
            onChanged: _revalidate,
            onSubmitted: (_) => _password.text.isEmpty
                ? _passwordFocus.requestFocus()
                : _submit(),
            decoration: InputDecoration(
              labelText: 'E-mail',
              errorText: _emailError,
            ),
          ),
          const SizedBox(height: 12),
          PasswordField(
            controller: _password,
            focusNode: _passwordFocus,
            fieldKey: 'login-password',
            label: 'Hasło',
            enabled: !_busy,
            errorText: _passwordError,
            autofillHints: const [AutofillHints.password],
            onChanged: _revalidate,
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 20),
          FilledButton(
            key: const ValueKey('login-submit'),
            onPressed: _blocked ? null : _submit,
            child: _busy
                ? const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      SizedBox(width: 10),
                      Text('Logowanie…'),
                    ],
                  )
                : Text(
                    _waitSeconds > 0
                        ? 'Spróbuj ponownie za '
                              '${formatWait(Duration(seconds: _waitSeconds))}'
                        : 'Zaloguj się',
                  ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Nie pamiętasz hasła lub konto jest zablokowane? Poproś '
            'administratora aplikacji o reset hasła.',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
