import 'dart:convert';

import 'package:dio/dio.dart';

/// An API or network error converted for the UI.
///
/// The API returns RFC 9457 `application/problem+json` with a stable English
/// `code` and a Polish `detail` (CLAUDE.md §8, §11.8). The UI shows a Polish
/// [message] (mapped from `code`; otherwise `detail`; otherwise a text based
/// on the HTTP status) and, when it adds information, the server's [detail].
class ApiProblem implements Exception {
  const ApiProblem({
    required this.message,
    this.status,
    this.code,
    this.detail,
    this.requestId,
    this.retryAfter,
    this.body = const {},
  });

  /// Converts anything thrown by an API call.
  factory ApiProblem.from(Object error) {
    if (error is ApiProblem) return error;
    if (error is! DioException) {
      return const ApiProblem(message: 'Wystąpił nieoczekiwany błąd.');
    }
    final transport = _transportMessage(error.type);
    if (transport != null) return ApiProblem(message: transport);

    final status = error.response?.statusCode;
    final body = _problemBody(error.response?.data);
    final code = body['code'] is String ? body['code'] as String : null;
    final detail = body['detail'] is String ? body['detail'] as String : null;
    final requestId = body['request_id'] is String
        ? body['request_id'] as String
        : error.response?.headers.value('x-request-id');
    final retryAfter = parseRetryAfter(
      error.response?.headers.value('retry-after'),
    );
    final mapped = code == null
        ? null
        : _codeMessage(code, body, retryAfter: retryAfter);
    final message = mapped ?? detail ?? _statusMessage(status);
    return ApiProblem(
      message: message,
      status: status,
      code: code,
      detail: detail != null && detail != message ? detail : null,
      requestId: requestId,
      retryAfter: retryAfter,
      body: body,
    );
  }

  /// Polish, user-facing message.
  final String message;

  /// Additional server explanation (`detail`) when it differs from [message].
  final String? detail;
  final int? status;
  final String? code;
  final String? requestId;

  /// `Retry-After` of a 429 (null when absent — e.g. hidden by CORS).
  final Duration? retryAfter;

  /// Full problem body (extension members: `checks`, `fields`, ...).
  final Map<String, dynamic> body;

  bool get isVersionConflict => code == 'change.version_conflict';
  bool get isNotReady => code == 'change.not_ready';
  bool get isUnauthorized => status == 401;

  /// Too many requests: nginx (`request.rate_limited`) or failed logins
  /// from the network (`auth.too_many_attempts`).
  bool get isRateLimited => status == 429;

  /// `current_version` of a 409 `change.version_conflict`.
  int? get currentVersion {
    final value = body['current_version'];
    return value is int ? value : null;
  }

  /// Raw `checks` of 422 `change.not_ready` / `change.invalid_edit`.
  List<Map<String, dynamic>> get checks => [
    for (final item in (body['checks'] as List<Object?>? ?? const []))
      if (item is Map) Map<String, dynamic>.from(item),
  ];

  /// Single field (`field`) of a `*.invalid_data` problem.
  String? get field => body['field'] is String ? body['field'] as String : null;

  /// Field names (`fields`) the error refers to.
  List<String> get fields => [
    for (final item in (body['fields'] as List<Object?>? ?? const []))
      if (item is String) item,
  ];

  /// Message and detail in one string (snackbars).
  String get fullMessage => detail == null ? message : '$message $detail';

  @override
  String toString() => 'ApiProblem($status, $code): $fullMessage';
}

/// Problem body from a JSON map, or from bytes / text when the request asked
/// for a binary response (attachment download) and the API answered with
/// problem+json.
Map<String, dynamic> _problemBody(Object? data) {
  Object? decoded = data;
  try {
    if (data is List<int>) decoded = jsonDecode(utf8.decode(data));
    if (data is String && data.trimLeft().startsWith('{')) {
      decoded = jsonDecode(data);
    }
  } on FormatException {
    return <String, dynamic>{};
  }
  return decoded is Map
      ? Map<String, dynamic>.from(decoded)
      : <String, dynamic>{};
}

/// `Retry-After` in seconds (the API and nginx send seconds, ADR 0019 §1).
Duration? parseRetryAfter(String? value) {
  final seconds = int.tryParse(value?.trim() ?? '');
  return seconds == null || seconds < 0 ? null : Duration(seconds: seconds);
}

/// "30 s", "2 min" (rounded up) — waiting time in messages.
String formatWait(Duration wait) {
  final seconds = wait.inMilliseconds <= 0
      ? 0
      : (wait.inMilliseconds / 1000).ceil();
  if (seconds < 60) return '$seconds s';
  return '${(seconds / 60).ceil()} min';
}

String _retryHint(Duration? retryAfter) => retryAfter == null
    ? 'Odczekaj chwilę i spróbuj ponownie.'
    : 'Spróbuj ponownie za ${formatWait(retryAfter)}.';

/// Polish labels of attachment types (`allowed_types`, `detected_type`),
/// mirroring `backend/app/services/file_types.py` (`LABELS`).
const Map<String, String> fileTypeLabels = {
  'application/pdf': 'PDF',
  'image/png': 'PNG',
  'image/jpeg': 'JPEG',
  'image/gif': 'GIF',
  'image/webp': 'WebP',
  'image/bmp': 'BMP',
  'image/tiff': 'TIFF',
  'application/zip': 'ZIP',
  'application/gzip': 'GZIP',
  'application/x-7z-compressed': '7z',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      'DOCX',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation':
      'PPTX',
  'application/vnd.oasis.opendocument.text': 'ODT',
  'application/vnd.oasis.opendocument.spreadsheet': 'ODS',
  'application/vnd.oasis.opendocument.presentation': 'ODP',
  'application/vnd.ms-outlook': 'MSG (Outlook)',
  'application/x-ole-storage': 'dokument Office 97-2003',
  'application/x-msdownload': 'program Windows',
  'application/x-executable': 'program Linux',
  'text/plain': 'tekst (TXT, LOG)',
  'text/csv': 'CSV',
  'application/json': 'JSON',
  'application/xml': 'XML',
  'message/rfc822': 'EML (e-mail)',
  'text/html': 'HTML',
  'image/svg+xml': 'SVG',
  'application/octet-stream': 'nieznany',
};

String fileTypeLabel(String type) => fileTypeLabels[type] ?? type;

/// Polish message of [code]; some codes carry numbers in extension members.
String? _codeMessage(
  String code,
  Map<String, dynamic> body, {
  Duration? retryAfter,
}) {
  switch (code) {
    case 'request.rate_limited':
      return 'Przekroczono limit żądań. ${_retryHint(retryAfter)}';
    case 'auth.too_many_attempts':
      return 'Zbyt wiele nieudanych prób logowania z tej sieci. '
          '${_retryHint(retryAfter)}';
    case 'attachment.type_not_allowed':
      final detected = body['detected_type'];
      final allowed = {
        for (final t in (body['allowed_types'] as List<Object?>? ?? const []))
          if (t is String) fileTypeLabel(t),
      }.toList()..sort();
      final what = detected is String
          ? 'Niedozwolony typ pliku (${fileTypeLabel(detected)}).'
          : 'Niedozwolony typ pliku.';
      return allowed.isEmpty
          ? what
          : '$what Dozwolone typy załączników: ${allowed.join(', ')}.';
    case 'attachment.too_large':
      final max = body['max_bytes'];
      if (max is int && max > 0) {
        return 'Plik jest zbyt duży (maksymalnie ${_megabytes(max)}).';
      }
      return 'Plik jest zbyt duży.';
  }
  if (code == 'report.too_large') {
    final count = body['change_count'];
    final max = body['max_changes'];
    if (count is int && max is int) {
      return 'Raport obejmowałby $count zmian (maksymalnie $max). Zawęź '
          'okres lub filtry.';
    }
  }
  return problemCodeMessages[code];
}

String _megabytes(int bytes) {
  final mb = bytes / (1024 * 1024);
  final text = mb == mb.roundToDouble()
      ? mb.toStringAsFixed(0)
      : mb.toStringAsFixed(1).replaceAll('.', ',');
  return '$text MB';
}

/// Polish message for any error thrown by an API call.
String describeApiError(Object error) => ApiProblem.from(error).message;

String? _transportMessage(DioExceptionType type) => switch (type) {
  DioExceptionType.connectionTimeout ||
  DioExceptionType.sendTimeout ||
  DioExceptionType.receiveTimeout ||
  DioExceptionType.transformTimeout =>
    'Przekroczono czas oczekiwania na odpowiedź serwera.',
  DioExceptionType.connectionError => 'Brak połączenia z serwerem.',
  DioExceptionType.cancel => 'Żądanie zostało anulowane.',
  DioExceptionType.badCertificate => 'Nieprawidłowy certyfikat serwera.',
  DioExceptionType.badResponse || DioExceptionType.unknown => null,
};

String _statusMessage(int? status) => switch (status) {
  400 || 422 => 'Przesłane dane są nieprawidłowe.',
  401 => 'Sesja wygasła. Zaloguj się ponownie.',
  403 => 'Brak uprawnień do wykonania tej operacji.',
  404 => 'Nie znaleziono zasobu.',
  409 => 'Dane zostały w międzyczasie zmienione przez innego użytkownika.',
  413 => 'Przesłany plik jest zbyt duży.',
  428 => 'Brak wersji danych — odśwież widok i spróbuj ponownie.',
  429 => 'Zbyt wiele żądań. Spróbuj ponownie za chwilę.',
  final int s when s >= 500 => 'Błąd serwera. Spróbuj ponownie.',
  _ => 'Wystąpił nieoczekiwany błąd.',
};

/// Polish messages of API problem codes (English codes: backend, §11.8).
///
/// Codes not listed here use the server's Polish `detail`.
const Map<String, String> problemCodeMessages = {
  // changes — state machine (ADR 0012 §8)
  'change.invalid_transition':
      'Ta operacja nie jest dozwolona w bieżącym stanie zmiany.',
  'change.forbidden_actor': 'Nie możesz wykonać tej operacji na tej zmianie.',
  'change.four_eyes_violation':
      'Zasada czterech oczu: nie możesz zatwierdzić zmiany, której jesteś '
      'zgłaszającym lub wykonawcą.',
  'change.verifier_is_assignee':
      'Wykonawca nie może zweryfikować własnej zmiany, gdy w spółce jest inna '
      'osoba uprawniona do weryfikacji.',
  'change.approval_missing':
      'Zmiana awaryjna musi zostać zatwierdzona po fakcie przed weryfikacją.',
  'change.comment_required': 'Ta operacja wymaga komentarza.',
  'change.comment_too_long': 'Komentarz jest zbyt długi (maks. 4000 znaków).',
  'change.not_ready':
      'Zmiana nie spełnia warunków — popraw pozycje oznaczone w kontroli.',
  'change.ci_owner_consent_missing':
      'Brakuje zgody właściciela obiektu (CI) na tę zmianę.',
  'change.frozen':
      'Zmiana jest zamrożona i nie może być edytowana. Korekta wymaga nowej '
      'zmiany.',
  'change.field_not_editable': 'Tego pola nie można zmienić w tym statusie.',
  'change.invalid_edit': 'Nowa wartość nie spełnia reguł zmiany.',
  // changes — API (ADR 0013 §7)
  'change.version_conflict':
      'Zmiana została w międzyczasie zapisana przez innego użytkownika.',
  'change.version_required':
      'Brak wersji zmiany — odśwież kartę i spróbuj ponownie.',
  'change.version_mismatch': 'Niespójna wersja zmiany w żądaniu.',
  'change.invalid_if_match': 'Niespójna wersja zmiany w żądaniu.',
  'change.not_found': 'Nie znaleziono zmiany.',
  'change.unknown_action': 'Nieznana operacja na zmianie.',
  'change.ci_not_found': 'Wybrany obiekt (CI) nie istnieje w tej spółce.',
  'change.user_not_found': 'Wybrana osoba nie jest członkiem tej spółki.',
  'change.invalid_window':
      'Początek okna serwisowego musi być wcześniejszy niż jego koniec.',
  'change.invalid_period':
      'Początek okresu musi być wcześniejszy niż jego koniec.',
  'change.invalid_filter': 'Nieprawidłowy filtr rejestru.',
  // companies
  'company.not_found': 'Nie znaleziono spółki lub nie masz do niej dostępu.',
  'company.archived':
      'Spółka jest zarchiwizowana — zmiany i obiekty są tylko do odczytu.',
  'company.name_taken': 'Spółka o tej nazwie już istnieje.',
  'company.prefix_taken': 'Ten prefiks jest już używany przez inną spółkę.',
  'company.prefix_immutable':
      'Prefiksu spółki nie można zmienić po jej utworzeniu.',
  'company.already_archived': 'Spółka jest już zarchiwizowana.',
  // company categories (ADR 0011 §4)
  'company_category.approver_not_eligible':
      'Zatwierdzający dla kategorii musi być aktywnym użytkownikiem z rolą '
      'zatwierdzającego w tej spółce.',
  'company_category.duplicate': 'Kategoria występuje na liście więcej niż raz.',
  'company_category.category_not_found': 'Nie znaleziono kategorii.',
  'company_category.not_top_level':
      'Spółce przypisuje się tylko kategorie główne (podkategorie są dostępne '
      'razem z nimi).',
  'company_category.category_inactive':
      'Nie można udostępnić nieaktywnej kategorii.',
  // memberships and users
  'membership.user_inactive':
      'Nie można nadać roli nieaktywnemu użytkownikowi (odebrać można).',
  'user.not_found': 'Nie znaleziono użytkownika.',
  'user.email_taken': 'Użytkownik o tym adresie e-mail już istnieje.',
  'user.self_password_reset':
      'Nie możesz zresetować własnego hasła — zmień je w menu konta (podając '
      'obecne hasło).',
  'user.cannot_modify_self':
      'Nie możesz dezaktywować swojego konta ani odebrać sobie uprawnień '
      'administratora.',
  'user.last_admin':
      'To ostatni aktywny administrator aplikacji — nie można go '
      'dezaktywować ani odebrać mu uprawnień.',
  // dictionaries (ADR 0011 §2)
  'category.not_found': 'Nie znaleziono kategorii.',
  'category.code_taken': 'Kategoria o tym kodzie już istnieje.',
  'category.code_immutable': 'Kodu kategorii nie można zmienić.',
  'category.parent_immutable':
      'Nie można przenieść podkategorii do innej kategorii.',
  'category.depth_exceeded':
      'Podkategoria nie może mieć własnych podkategorii (dozwolone są dwa '
      'poziomy).',
  'category.parent_inactive':
      'Nie można dodać podkategorii do nieaktywnej kategorii.',
  'category.parent_not_found': 'Nie znaleziono kategorii nadrzędnej.',
  'ci_type.not_found': 'Nie znaleziono typu obiektu.',
  'ci_type.code_taken': 'Typ obiektu o tym kodzie już istnieje.',
  'ci_type.code_immutable': 'Kodu typu obiektu nie można zmienić.',
  // audit
  'audit.invalid_period':
      'Początek okresu musi być wcześniejszy niż jego koniec.',
  // auth (ADR 0018)
  'auth.invalid_token': 'Sesja wygasła. Zaloguj się ponownie.',
  'auth.session_expired':
      'Sesja wygasła lub została zakończona. Zaloguj się ponownie.',
  'auth.invalid_refresh_token':
      'Sesja wygasła lub została zakończona. Zaloguj się ponownie.',
  'auth.unauthenticated': 'Wymagane jest zalogowanie.',
  'auth.forbidden': 'Brak uprawnień do wykonania tej operacji.',
  'auth.user_inactive':
      'Twoje konto jest nieaktywne. Skontaktuj się z administratorem.',
  'auth.dev_user_not_found': 'Nie znaleziono użytkownika testowego.',
  'auth.invalid_credentials':
      'Nieprawidłowy e-mail lub hasło albo konto jest zablokowane/nieaktywne.',
  'auth.password_change_required':
      'Przed dalszą pracą musisz zmienić hasło tymczasowe.',
  'auth.invalid_current_password': 'Obecne hasło jest nieprawidłowe.',
  'auth.password_too_short': 'Hasło musi mieć co najmniej 12 znaków.',
  'auth.password_too_long': 'Hasło może mieć najwyżej 128 znaków.',
  'auth.password_too_simple':
      'Hasło jest zbyt proste (powtórzony znak albo prosty ciąg z '
      'klawiatury). Użyj np. kilku niepowiązanych słów.',
  'auth.password_contains_identity':
      'Hasło nie może zawierać adresu e-mail ani imienia i nazwiska.',
  'auth.password_too_common':
      'To hasło jest zbyt popularne (znajduje się na liście często używanych '
      'haseł).',
  'auth.password_reused': 'Nowe hasło musi się różnić od obecnego.',
  'auth.account_locked':
      'Konto jest czasowo zablokowane po nieudanych próbach. Spróbuj później '
      'albo poproś administratora o reset hasła.',
  'auth.temporary_password_expired':
      'Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie '
      'hasła.',
  'auth.password_not_set':
      'To konto nie ma hasła. Poproś administratora o reset hasła.',
  // attachments (413/415 with numbers and types: _codeMessage)
  'attachment.empty': 'Plik jest pusty.',
  'attachment.not_found': 'Nie znaleziono załącznika.',
  'attachment.file_missing':
      'Plik załącznika jest niedostępny w magazynie. Skontaktuj się z '
      'administratorem.',
  // CI
  'ci.identifier_taken': 'Obiekt o tym identyfikatorze już istnieje w spółce.',
  'ci.invalid_data': 'Nieprawidłowe dane obiektu (CI).',
  'ci.not_found': 'Nie znaleziono obiektu (CI).',
  'ci.type_not_found': 'Nie znaleziono typu obiektu.',
  'ci.type_inactive': 'Typ obiektu jest nieaktywny.',
  'ci.owner_not_member': 'Właściciel obiektu musi być członkiem spółki.',
  'ci.owner_locked_by_change':
      'Nie można zmienić właściciela obiektu, którego dotyczy zmiana '
      'oczekująca na zgodę.',
  // report exports (ADR 0017 §10)
  'report.not_found': 'Nie znaleziono raportu lub nie masz do niego dostępu.',
  'report.period_required': 'Podaj okres raportu (początek i koniec).',
  'report.invalid_period':
      'Początek okresu musi być wcześniejszy niż jego koniec.',
  'report.invalid_kind':
      'Ten rodzaj raportu nie jest dostępny dla wybranego zakresu.',
  'report.change_required': 'Wskaż zmianę, której kartę chcesz wygenerować.',
  'report.too_large':
      'Raport obejmowałby zbyt wiele zmian. Zawęź okres lub filtry.',
  'report.not_ready':
      'Raport jest jeszcze generowany. Spróbuj ponownie za chwilę.',
  'report.failed':
      'Generowanie raportu nie powiodło się — wygeneruj raport ponownie.',
  'report.queue_unavailable':
      'Kolejka generowania raportów jest chwilowo niedostępna. Spróbuj '
      'ponownie za chwilę lub zawęź raport.',
  'report.file_missing':
      'Plik raportu jest niedostępny w magazynie. Wygeneruj raport ponownie.',
  'report.file_corrupted':
      'Plik raportu został zmieniony w magazynie i nie zostanie wydany. '
      'Skontaktuj się z administratorem.',
  // generic
  'request.validation_error': 'Przesłane dane są nieprawidłowe.',
  'server.internal_error': 'Błąd serwera. Spróbuj ponownie.',
  'http.not_found': 'Nie znaleziono zasobu.',
  'http.too_many_requests': 'Zbyt wiele żądań. Spróbuj ponownie za chwilę.',
  'http.payload_too_large': 'Przesłane dane są zbyt duże.',
  // nginx (ADR 0019 §8)
  'api.unavailable':
      'Serwer aplikacji jest chwilowo niedostępny. Spróbuj ponownie za '
      'chwilę.',
};
