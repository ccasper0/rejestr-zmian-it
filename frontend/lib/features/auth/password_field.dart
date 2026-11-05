import 'package:flutter/material.dart';

/// Password input with a show/hide toggle (≥ 44 px target).
class PasswordField extends StatefulWidget {
  const PasswordField({
    required this.controller,
    required this.label,
    this.fieldKey,
    this.errorText,
    this.helperText,
    this.autofillHints,
    this.focusNode,
    this.textInputAction = TextInputAction.done,
    this.onSubmitted,
    this.onChanged,
    this.enabled = true,
    this.autofocus = false,
    super.key,
  });

  final TextEditingController controller;
  final String label;

  /// Key of the inner [TextField] (tests enter text there); the toggle gets
  /// `<fieldKey>-toggle`.
  final String? fieldKey;
  final String? errorText;
  final String? helperText;
  final Iterable<String>? autofillHints;
  final FocusNode? focusNode;
  final TextInputAction textInputAction;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;
  final bool enabled;
  final bool autofocus;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    final key = widget.fieldKey;
    return TextField(
      key: key == null ? null : ValueKey(key),
      controller: widget.controller,
      focusNode: widget.focusNode,
      obscureText: _obscure,
      enableSuggestions: false,
      autocorrect: false,
      enabled: widget.enabled,
      autofocus: widget.autofocus,
      autofillHints: widget.autofillHints,
      textInputAction: widget.textInputAction,
      onSubmitted: widget.onSubmitted,
      onChanged: widget.onChanged,
      decoration: InputDecoration(
        labelText: widget.label,
        errorText: widget.errorText,
        helperText: widget.helperText,
        helperMaxLines: 3,
        errorMaxLines: 4,
        suffixIcon: IconButton(
          key: key == null ? null : ValueKey('$key-toggle'),
          tooltip: _obscure ? 'Pokaż hasło' : 'Ukryj hasło',
          onPressed: () => setState(() => _obscure = !_obscure),
          icon: Icon(
            _obscure
                ? Icons.visibility_outlined
                : Icons.visibility_off_outlined,
          ),
        ),
      ),
    );
  }
}
