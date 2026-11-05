import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_error.dart';
import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../data/admin_api.dart';
import '../data/admin_models.dart';
import 'admin_shell.dart';

/// Labels of the account state (ADR 0018 §5): inactive, password set or
/// not, temporary password pending (valid until … or expired, ADR 0020 §9),
/// locked until … (Europe/Warsaw).
class AccountStateTags extends StatelessWidget {
  const AccountStateTags({
    required this.account,
    required this.now,
    this.isAppAdmin = false,
    super.key,
  });

  final AccountState account;
  final DateTime now;
  final bool isAppAdmin;

  @override
  Widget build(BuildContext context) {
    final locked = account.lockedUntil;
    final tempExpires = account.tempPasswordExpiresAt;
    final pending = account.hasPassword && account.mustChangePassword;
    final tempExpired =
        pending && tempExpires != null && !tempExpires.isAfter(now);
    return Wrap(
      spacing: 4,
      runSpacing: 4,
      children: [
        if (!account.isActive)
          const Tag(label: 'Nieaktywne', colors: AppFeedbackColors.error),
        if (isAppAdmin)
          const Tag(label: 'Administrator', colors: AppFeedbackColors.info),
        if (account.hasPassword)
          const Tag(label: 'Hasło ustawione', colors: AppFeedbackColors.success)
        else
          const Tag(
            label: 'Brak hasła',
            tooltip:
                'Konto nie zaloguje się, dopóki administrator nie '
                'nada hasła tymczasowego (reset hasła).',
          ),
        if (tempExpired)
          const Tag(
            key: ValueKey('temp-password-expired'),
            label: 'Hasło tymczasowe wygasło',
            colors: AppFeedbackColors.error,
            tooltip:
                'Użytkownik nie zaloguje się hasłem tymczasowym. Zresetuj '
                'hasło, aby nadać nowe.',
          )
        else if (pending) ...[
          const Tag(
            label: 'Wymaga zmiany hasła',
            colors: AppFeedbackColors.warning,
            tooltip:
                'Hasło tymczasowe — użytkownik ustawi własne przy '
                'logowaniu.',
          ),
          if (tempExpires != null)
            Tag(
              key: const ValueKey('temp-password-valid-until'),
              label: 'ważne do ${WarsawTime.format(tempExpires)}',
              colors: AppFeedbackColors.warning,
              tooltip: 'Termin ważności hasła tymczasowego.',
            ),
        ],
        if (locked != null && locked.isAfter(now))
          Tag(
            label: 'Zablokowane do ${WarsawTime.format(locked)}',
            colors: AppFeedbackColors.error,
            tooltip:
                'Po nieudanych próbach logowania. Reset hasła zdejmuje '
                'blokadę.',
          ),
      ],
    );
  }
}

/// Asks before an account change; true = confirmed.
Future<bool> confirmAccountAction(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  bool danger = true,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: SizedBox(width: 460, child: Text(message)),
      actions: [
        TextButton(
          key: const ValueKey('confirm-cancel'),
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          key: const ValueKey('confirm-action'),
          style: danger
              ? FilledButton.styleFrom(backgroundColor: AppColors.danger)
              : null,
          onPressed: () => Navigator.pop(context, true),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// "Nowy użytkownik": `POST /users` from inside the dialog (so 409
/// `user.email_taken` is shown at the field). Returns the created account
/// with its temporary password.
Future<UserWithTemporaryPassword?> showCreateUserDialog(BuildContext context) =>
    showFormDialog<UserWithTemporaryPassword>(
      context,
      builder: (context) => const _CreateUserDialog(),
    );

class _CreateUserDialog extends ConsumerStatefulWidget {
  const _CreateUserDialog();

  @override
  ConsumerState<_CreateUserDialog> createState() => _CreateUserDialogState();
}

class _CreateUserDialogState extends ConsumerState<_CreateUserDialog> {
  static final RegExp _emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  final _email = TextEditingController();
  final _name = TextEditingController();
  bool _admin = false;
  bool _validated = false;
  bool _busy = false;
  String? _emailServerError;
  ApiProblem? _error;

  @override
  void dispose() {
    _email.dispose();
    _name.dispose();
    super.dispose();
  }

  bool get _dirty => _email.text.isNotEmpty || _name.text.isNotEmpty || _admin;

  String? get _emailError {
    if (_emailServerError != null) return _emailServerError;
    if (!_validated) return null;
    final email = _email.text.trim();
    if (email.isEmpty) return 'Podaj adres e-mail (login użytkownika).';
    if (email.length > 254 || !_emailPattern.hasMatch(email)) {
      return 'Podaj poprawny adres e-mail.';
    }
    return null;
  }

  String? get _nameError {
    if (!_validated) return null;
    final name = _name.text.trim();
    if (name.isEmpty) return 'Podaj imię i nazwisko.';
    if (name.length > 200) return 'Najwyżej 200 znaków.';
    return null;
  }

  Future<void> _submit() async {
    setState(() {
      _validated = true;
      _emailServerError = null;
      _error = null;
    });
    if (_emailError != null || _nameError != null) return;
    setState(() => _busy = true);
    try {
      final created = await ref
          .read(adminApiProvider)
          .createUser(
            email: _email.text.trim(),
            displayName: _name.text.trim(),
            isAppAdmin: _admin,
          );
      if (mounted) Navigator.pop(context, created);
    } on Object catch (error) {
      if (!mounted) return;
      final problem = ApiProblem.from(error);
      setState(() {
        if (problem.code == 'user.email_taken') {
          _emailServerError = problem.message;
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
    final error = _error;
    return GuardedDialog(
      dirty: _dirty && !_busy,
      child: AlertDialog(
        title: const Text('Nowy użytkownik'),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (error != null) ...[
                  ErrorPanel(error: error),
                  const SizedBox(height: 12),
                ],
                TextField(
                  key: const ValueKey('user-email'),
                  controller: _email,
                  enabled: !_busy,
                  autofocus: true,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  onChanged: (_) => setState(() => _emailServerError = null),
                  decoration: InputDecoration(
                    labelText: 'E-mail (login)',
                    errorText: _emailError,
                    helperText: 'Adresu nie można później zmienić.',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  key: const ValueKey('user-name'),
                  controller: _name,
                  enabled: !_busy,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    labelText: 'Imię i nazwisko',
                    errorText: _nameError,
                  ),
                ),
                const SizedBox(height: 8),
                CheckboxListTile(
                  key: const ValueKey('user-admin'),
                  value: _admin,
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  title: const Text('Administrator aplikacji'),
                  subtitle: const Text(
                    'Spółki, słowniki, użytkownicy i role. Nie daje ról w '
                    'spółkach (rozdział obowiązków).',
                  ),
                  onChanged: _busy
                      ? null
                      : (value) => setState(() => _admin = value ?? false),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Hasło tymczasowe wygeneruje serwer i pokaże je tylko raz. '
                  'Użytkownik zmieni je przy pierwszym logowaniu.',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: _busy ? null : () => Navigator.maybePop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('user-create-submit'),
            onPressed: _busy ? null : _submit,
            child: Text(_busy ? 'Tworzenie…' : 'Utwórz konto'),
          ),
        ],
      ),
    );
  }
}

/// The temporary password, shown ONCE (ADR 0018 §5). It lives only in this
/// dialog: never stored, logged or kept in any provider.
Future<void> showTemporaryPasswordDialog(
  BuildContext context, {
  required String userName,
  required String email,
  required String temporaryPassword,
  required bool reset,
  DateTime? expiresAt,
}) => showDialog<void>(
  context: context,
  barrierDismissible: false,
  builder: (context) => _TemporaryPasswordDialog(
    userName: userName,
    email: email,
    temporaryPassword: temporaryPassword,
    reset: reset,
    expiresAt: expiresAt,
  ),
);

class _TemporaryPasswordDialog extends StatefulWidget {
  const _TemporaryPasswordDialog({
    required this.userName,
    required this.email,
    required this.temporaryPassword,
    required this.reset,
    this.expiresAt,
  });

  final String userName;
  final String email;
  final String temporaryPassword;
  final bool reset;

  /// `temp_password_expires_at` of the answer (ADR 0020 §9).
  final DateTime? expiresAt;

  @override
  State<_TemporaryPasswordDialog> createState() =>
      _TemporaryPasswordDialogState();
}

class _TemporaryPasswordDialogState extends State<_TemporaryPasswordDialog> {
  bool _copied = false;

  Future<void> _copy() async {
    await Clipboard.setData(ClipboardData(text: widget.temporaryPassword));
    if (mounted) setState(() => _copied = true);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(
        widget.reset ? 'Nowe hasło tymczasowe' : 'Konto zostało utworzone',
      ),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const MessageBanner(
                key: ValueKey('temporary-password-warning'),
                kind: BannerKind.warning,
                title: 'Hasło jest wyświetlane tylko raz',
                message:
                    'Skopiuj je teraz i przekaż użytkownikowi bezpiecznym '
                    'kanałem (nie w tej samej wiadomości co login). Po '
                    'zamknięciu okna nie da się go ponownie wyświetlić — '
                    'pozostanie tylko kolejny reset hasła.',
              ),
              const SizedBox(height: 12),
              Text('${widget.userName} · ${widget.email}'),
              const SizedBox(height: 8),
              DecoratedBox(
                decoration: BoxDecoration(
                  color: AppColors.surfaceMuted,
                  borderRadius: AppRadii.mediumAll,
                  border: Border.all(color: AppColors.border),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: SelectableText(
                          widget.temporaryPassword,
                          key: const ValueKey('temporary-password'),
                          style: AppFonts.monoStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        key: const ValueKey('temporary-password-copy'),
                        onPressed: _copy,
                        icon: Icon(
                          _copied ? Icons.check : Icons.copy_outlined,
                          size: 18,
                        ),
                        label: Text(_copied ? 'Skopiowano' : 'Kopiuj'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                temporaryPasswordValidity(widget.expiresAt),
                key: const ValueKey('temporary-password-validity'),
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Text(
                widget.reset
                    ? 'Poprzednie hasło przestało działać, wszystkie sesje '
                          'użytkownika zostały zakończone, a blokada konta '
                          'zdjęta. Przy logowaniu użytkownik musi ustawić '
                          'własne hasło.'
                    : 'Przy pierwszym logowaniu użytkownik musi ustawić '
                          'własne hasło. Role w spółkach nadasz na karcie '
                          'użytkownika.',
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        FilledButton(
          key: const ValueKey('temporary-password-close'),
          onPressed: () => Navigator.pop(context),
          child: const Text('Zamknij'),
        ),
      ],
    );
  }
}

/// Edit of the display name; returns the new name (trimmed).
Future<String?> showEditNameDialog(
  BuildContext context, {
  required String current,
}) => showFormDialog<String>(
  context,
  builder: (context) => _EditNameDialog(current: current),
);

class _EditNameDialog extends StatefulWidget {
  const _EditNameDialog({required this.current});

  final String current;

  @override
  State<_EditNameDialog> createState() => _EditNameDialogState();
}

class _EditNameDialogState extends State<_EditNameDialog> {
  late final _name = TextEditingController(text: widget.current);

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  String? get _error {
    final name = _name.text.trim();
    if (name.isEmpty) return 'Podaj imię i nazwisko.';
    if (name.length > 200) return 'Najwyżej 200 znaków.';
    return null;
  }

  bool get _dirty => _name.text.trim() != widget.current;

  void _save() {
    if (_error != null || !_dirty) return;
    Navigator.pop(context, _name.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    return GuardedDialog(
      dirty: _dirty,
      child: AlertDialog(
        title: const Text('Zmień nazwę użytkownika'),
        content: SizedBox(
          width: 420,
          child: TextField(
            key: const ValueKey('user-name-edit'),
            controller: _name,
            autofocus: true,
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _save(),
            decoration: InputDecoration(
              labelText: 'Imię i nazwisko',
              errorText: _error,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.maybePop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            key: const ValueKey('user-name-save'),
            onPressed: _error != null || !_dirty ? null : _save,
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
  }
}

/// Validity sentence of the temporary password dialog: the deadline from the
/// API (Europe/Warsaw) or, for an answer without it, the default 7 days
/// (`TEMP_PASSWORD_TTL_HOURS`, ADR 0018 §12 p. 4).
String temporaryPasswordValidity(DateTime? expiresAt) => expiresAt == null
    ? 'Hasło tymczasowe jest ważne 7 dni — po tym czasie konieczny będzie '
          'ponowny reset hasła.'
    : 'Hasło tymczasowe jest ważne do ${WarsawTime.format(expiresAt)} '
          '(Europe/Warsaw) — po tym terminie konieczny będzie ponowny reset '
          'hasła.';
