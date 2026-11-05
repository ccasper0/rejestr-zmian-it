/// Inline validation of the admin forms. It only repeats the backend rules
/// for UX (CLAUDE.md §15); the API decides (`*.invalid_data`, 409, 422).
library;

/// Company prefix: 2–8 upper-case letters A–Z (`app/domain/companies.py`).
final RegExp companyPrefixRule = RegExp(r'^[A-Z]{2,8}$');

/// Category code: `ACC`, `ACC-PRIV` (`app/domain/dictionaries.py`).
final RegExp categoryCodeRule = RegExp(r'^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$');

/// CI type code: `server`, `network_device`, 2–32 characters.
final RegExp ciTypeCodeRule = RegExp(r'^[a-z][a-z0-9_]{1,31}$');

const int nameMaxLength = 200;
const int ciIdentifierMaxLength = 100;
const int ciDescriptionMaxLength = 4000;

String? validateCompanyName(String value) {
  final clean = value.trim();
  if (clean.isEmpty) return 'Podaj nazwę spółki.';
  if (clean.length > nameMaxLength) {
    return 'Nazwa może mieć najwyżej $nameMaxLength znaków.';
  }
  return null;
}

String? validatePrefix(String value) {
  if (value.isEmpty) return 'Podaj prefiks.';
  if (!companyPrefixRule.hasMatch(value)) {
    return 'Od 2 do 8 wielkich liter A–Z (bez polskich znaków i cyfr).';
  }
  return null;
}

/// Example change number of a company (§4.1): `CHG-ALFA-2026-0001`.
String exampleChangeNumber(String prefix, int year) =>
    'CHG-${prefix.isEmpty ? '…' : prefix}-$year-0001';

/// NIP as the backend normalizes it: separators and a `PL` prefix dropped.
String normalizeNip(String raw) {
  var value = raw.trim().toUpperCase().replaceAll(RegExp(r'[\s-]'), '');
  if (value.startsWith('PL')) value = value.substring(2);
  return value;
}

/// Polish NIP: optional; otherwise 10 digits with a valid checksum.
String? validateNip(String raw) {
  if (raw.trim().isEmpty) return null;
  final value = normalizeNip(raw);
  if (!RegExp(r'^\d{10}$').hasMatch(value)) {
    return 'NIP musi składać się z 10 cyfr.';
  }
  const weights = [6, 5, 7, 2, 3, 4, 5, 6, 7];
  final digits = value.codeUnits.map((c) => c - 48).toList();
  var sum = 0;
  for (var i = 0; i < weights.length; i++) {
    sum += weights[i] * digits[i];
  }
  final checksum = sum % 11;
  if (checksum == 10 || checksum != digits[9]) {
    return 'NIP ma nieprawidłową sumę kontrolną.';
  }
  return null;
}

String? validateCategoryCode(String value) {
  if (value.isEmpty) return 'Podaj kod.';
  if (value.length < 2 ||
      value.length > 32 ||
      !categoryCodeRule.hasMatch(value)) {
    return 'Od 2 do 32 znaków: wielkie litery A–Z i cyfry, grupy łączone '
        'myślnikiem (np. NET, NET-VLAN).';
  }
  return null;
}

String? validateCiTypeCode(String value) {
  if (value.isEmpty) return 'Podaj kod.';
  if (!ciTypeCodeRule.hasMatch(value)) {
    return 'Od 2 do 32 znaków: małe litery a–z, cyfry i podkreślenie, '
        'zaczyna się literą (np. network_device).';
  }
  return null;
}

String? validateName(String value, {int max = nameMaxLength}) {
  final clean = value.trim();
  if (clean.isEmpty) return 'Podaj nazwę.';
  if (clean.length > max) return 'Najwyżej $max znaków.';
  return null;
}
