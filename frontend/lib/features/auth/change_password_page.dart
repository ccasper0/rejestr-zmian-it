import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../core/api_client.dart';
import '../../core/api_error.dart';
import '../../core/auth/auth.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';
import 'password_field.dart';

/// Password policy limits (UX only — the backend decides, ADR 0018 §3).
const int passwordMinLength = 12;
const int passwordMaxLength = 128;

/// `/account/password` — change of the own password (local accounts).
///
/// Forced while a temporary password is pending (the router sends every
/// page here; only "Wyloguj" leaves), voluntary from the user menu. On
/// success every session of the user ends on the server and the answer is a
/// new pair of tokens for this tab (ADR 0018 §5).
class ChangePasswordPage extends ConsumerStatefulWidget {
  const ChangePasswordPage({this.from, super.key});

  /// Where to return afterwards (`?from=`, local paths only).
  final String? from;

  @override
  ConsumerState<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends ConsumerState<ChangePasswordPage> {
  final _current = TextEditingController();
  final _new = TextEditingController();
  final _confirm = TextEditingController();
  bool _validated = false;
  bool _busy = false;
  String? _currentServerError;
  String? _newServerError;
  ApiProblem? _error;

  @override
  void dispose() {
    _current.dispose();
    _new.dispose();
    _confirm.dispose();
    super.dispose();
  }

  String get _returnPath => safeReturnPath(widget.from) ?? '/';

  String? get _currentError {
    if (_currentServerError != null) return _currentServerError;
    if (_validated && _current.text.isEmpty) return 'Podaj obecne hasło.';
    return null;
  }

  String? get _newError {
    if (_newServerError != null) return _newServerError;
    if (!_validated) return null;
    final length = _new.text.runes.length;
    if (length < passwordMinLength) {
      return 'Hasło musi mieć co najmniej $passwordMinLength znaków '
          '(wpisano $length).';
    }
    if (length > passwordMaxLength) {
      return 'Hasło może mieć najwyżej $passwordMaxLength znaków.';
    }
    if (_new.text == _current.text) {
      return 'Nowe hasło musi się różnić od obecnego.';
    }
    return null;
  }

  String? get _confirmError {
    if (!_validated) return null;
    if (_confirm.text != _new.text) return 'Hasła nie są takie same.';
    return null;
  }

  void _edited(String _) => setState(() {
    _currentServerError = null;
    _newServerError = null;
  });

  Future<void> _submit() async {
    if (_busy) return;
    setState(() {
      _validated = true;
      _currentServerError = null;
      _newServerError = null;
      _error = null;
    });
    if (_currentError != null || _newError != null || _confirmError != null) {
      return;
    }
    setState(() => _busy = true);
    try {
      final token = await changePassword(
        ref.read(apiClientProvider),
        ref.read(clockProvider)(),
        currentPassword: _current.text,
        newPassword: _new.text,
      );
      // Every previous session (this one too) has ended: a new session.
      ref.read(authControllerProvider.notifier).signIn(token);
      if (!mounted) return;
      showInfoSnack(context, 'Hasło zostało zmienione.');
      context.go(_returnPath);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        final code = problem.code ?? '';
        if (code == 'auth.invalid_current_password') {
          _currentServerError = problem.message;
          _current.clear();
        } else if (code.startsWith('auth.password_') &&
            code != 'auth.password_not_set' &&
            code != 'auth.password_change_required') {
          _newServerError = problem.message;
        } else {
          _error = problem;
        }
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final forced = auth.mustChangePassword;
    final local = auth.token?.isLocalAccount ?? false;
    final me = ref.watch(meProvider).value;
    final error = _error;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: AutofillGroup(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Semantics(
                        header: true,
                        child: const Text(
                          'Zmiana hasła',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      if (me != null)
                        Text(
                          me.email.isEmpty ? me.displayName : me.email,
                          style: AppFonts.monoStyle(
                            fontSize: 13,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      const SizedBox(height: 16),
                      if (!local)
                        const MessageBanner(
                          message:
                              'Zmiana hasła dotyczy kont lokalnych. W trybie '
                              'deweloperskim użytkownicy testowi nie mają '
                              'haseł.',
                        )
                      else ...[
                        if (forced) ...[
                          const MessageBanner(
                            key: ValueKey('password-forced'),
                            kind: BannerKind.warning,
                            title: 'Wymagana zmiana hasła',
                            message:
                                'Logujesz się hasłem tymczasowym. Ustaw '
                                'własne hasło, aby kontynuować pracę.',
                          ),
                          const SizedBox(height: 16),
                        ],
                        if (error != null) ...[
                          ErrorPanel(error: error),
                          const SizedBox(height: 16),
                        ],
                        PasswordField(
                          controller: _current,
                          fieldKey: 'password-current',
                          label: forced
                              ? 'Obecne hasło (tymczasowe)'
                              : 'Obecne hasło',
                          errorText: _currentError,
                          enabled: !_busy,
                          autofocus: true,
                          autofillHints: const [AutofillHints.password],
                          textInputAction: TextInputAction.next,
                          onChanged: _edited,
                        ),
                        const SizedBox(height: 12),
                        PasswordField(
                          controller: _new,
                          fieldKey: 'password-new',
                          label: 'Nowe hasło',
                          errorText: _newError,
                          enabled: !_busy,
                          autofillHints: const [AutofillHints.newPassword],
                          textInputAction: TextInputAction.next,
                          onChanged: _edited,
                        ),
                        const SizedBox(height: 12),
                        PasswordField(
                          controller: _confirm,
                          fieldKey: 'password-confirm',
                          label: 'Powtórz nowe hasło',
                          errorText: _confirmError,
                          enabled: !_busy,
                          autofillHints: const [AutofillHints.newPassword],
                          onChanged: _edited,
                          onSubmitted: (_) => _submit(),
                        ),
                        const SizedBox(height: 16),
                        const _PolicyHints(),
                        const SizedBox(height: 12),
                        const Text(
                          'Po zmianie hasła wszystkie Twoje sesje (także w '
                          'innych kartach i przeglądarkach) zostaną '
                          'zakończone; ta karta pozostanie zalogowana.',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ],
                      const SizedBox(height: 20),
                      Wrap(
                        alignment: WrapAlignment.end,
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          if (forced)
                            TextButton.icon(
                              key: const ValueKey('password-logout'),
                              onPressed: _busy
                                  ? null
                                  : () => signOutToLogin(context, ref),
                              icon: const Icon(Icons.logout),
                              label: const Text('Wyloguj'),
                            )
                          else
                            TextButton(
                              key: const ValueKey('password-cancel'),
                              onPressed: _busy
                                  ? null
                                  : () => context.go(_returnPath),
                              child: Text(local ? 'Anuluj' : 'Wróć'),
                            ),
                          if (local)
                            FilledButton(
                              key: const ValueKey('password-submit'),
                              onPressed: _busy ? null : _submit,
                              child: Text(
                                _busy ? 'Zapisywanie…' : 'Zmień hasło',
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// The policy of `app/domain/passwords.py` in plain words (NIST 800-63B: no
/// composition rules).
class _PolicyHints extends StatelessWidget {
  const _PolicyHints();

  static const List<String> _hints = [
    'od $passwordMinLength do $passwordMaxLength znaków — najlepiej kilka '
        'niepowiązanych słów (fraza),',
    'bez adresu e-mail oraz imienia i nazwiska,',
    'nie z listy popularnych haseł i nie prosty ciąg (powtórzony znak, '
        '„qwerty…”, „1234…”),',
    'inne niż obecne hasło.',
  ];

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: AppRadii.mediumAll,
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Wymagania dla hasła',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            for (final hint in _hints)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  '• $hint',
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
              ),
            const SizedBox(height: 4),
            const Text(
              'Wielkie litery, cyfry ani znaki specjalne nie są wymagane.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}
