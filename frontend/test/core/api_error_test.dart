import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/core/api_error.dart';

DioException problem(int status, Map<String, Object?> body) {
  final options = RequestOptions(path: '/x');
  return DioException(
    requestOptions: options,
    type: DioExceptionType.badResponse,
    response: Response(requestOptions: options, statusCode: status, data: body),
  );
}

void main() {
  test('known code is mapped to Polish; server detail kept as details', () {
    final p = ApiProblem.from(
      problem(403, {
        'code': 'change.four_eyes_violation',
        'detail': 'Zatwierdzający jest wykonawcą tej zmiany.',
        'request_id': 'req-1',
      }),
    );
    expect(p.message, startsWith('Zasada czterech oczu'));
    expect(p.detail, 'Zatwierdzający jest wykonawcą tej zmiany.');
    expect(p.requestId, 'req-1');
  });

  test('unknown code falls back to the Polish detail of the API', () {
    final p = ApiProblem.from(
      problem(422, {'code': 'ci.something_new', 'detail': 'Opis po polsku.'}),
    );
    expect(p.message, 'Opis po polsku.');
    expect(p.detail, isNull);
  });

  test('no body: message from the HTTP status', () {
    expect(ApiProblem.from(problem(404, {})).message, 'Nie znaleziono zasobu.');
    expect(
      ApiProblem.from(problem(503, {})).message,
      startsWith('Błąd serwera'),
    );
  });

  test('version conflict exposes current_version', () {
    final p = ApiProblem.from(
      problem(409, {
        'code': 'change.version_conflict',
        'detail': 'Nieaktualna wersja.',
        'current_version': 7,
      }),
    );
    expect(p.isVersionConflict, isTrue);
    expect(p.currentVersion, 7);
    expect(p.message, contains('innego użytkownika'));
  });

  test('not_ready exposes the readiness checks', () {
    final p = ApiProblem.from(
      problem(422, {
        'code': 'change.not_ready',
        'detail': 'Zmiana nie jest gotowa.',
        'checks': [
          {
            'code': 'ci.required',
            'ok': false,
            'level': 'error',
            'message_pl': 'Wskazano co najmniej jeden obiekt.',
            'field': 'ci_ids',
          },
        ],
      }),
    );
    expect(p.isNotReady, isTrue);
    expect(p.checks.single['code'], 'ci.required');
  });

  test('problem+json in a bytes response (attachment download) is decoded', () {
    final options = RequestOptions(path: '/x');
    final bytes = utf8.encode(
      jsonEncode({
        'code': 'attachment.file_missing',
        'detail': 'Plik załącznika jest niedostępny.',
      }),
    );
    final p = ApiProblem.from(
      DioException(
        requestOptions: options,
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options,
          statusCode: 500,
          data: bytes,
        ),
      ),
    );
    expect(p.code, 'attachment.file_missing');
    expect(p.message, startsWith('Plik załącznika jest niedostępny'));
  });

  test('network errors are described in Polish', () {
    final error = DioException(
      requestOptions: RequestOptions(path: '/x'),
      type: DioExceptionType.connectionError,
    );
    expect(describeApiError(error), 'Brak połączenia z serwerem.');
    expect(describeApiError(StateError('x')), 'Wystąpił nieoczekiwany błąd.');
  });

  test('report codes (ADR 0017 §10) have Polish messages', () {
    for (final code in [
      'report.not_found',
      'report.period_required',
      'report.invalid_period',
      'report.invalid_kind',
      'report.change_required',
      'report.too_large',
      'report.not_ready',
      'report.failed',
      'report.queue_unavailable',
      'report.file_missing',
      'report.file_corrupted',
      'change.invalid_filter',
      'change.not_found',
      'company.not_found',
      'auth.forbidden',
    ]) {
      expect(problemCodeMessages[code], isNotEmpty, reason: code);
    }
  });

  test('report.too_large: numbers from the problem body', () {
    final p = ApiProblem.from(
      problem(422, {
        'code': 'report.too_large',
        'detail':
            'Raport obejmowałby 6120 zmian (maksymalnie 5000). Zawęź '
            'okres lub filtry.',
        'change_count': 6120,
        'max_changes': 5000,
      }),
    );
    expect(
      p.message,
      'Raport obejmowałby 6120 zmian (maksymalnie 5000). Zawęź okres lub '
      'filtry.',
    );
    expect(p.detail, isNull);
    final bare = ApiProblem.from(problem(422, {'code': 'report.too_large'}));
    expect(bare.message, problemCodeMessages['report.too_large']);
  });

  test('Retry-After: seconds parsed, waiting time in Polish units', () {
    expect(parseRetryAfter('30'), const Duration(seconds: 30));
    expect(parseRetryAfter(' 0 '), Duration.zero);
    expect(parseRetryAfter('-1'), isNull);
    expect(parseRetryAfter('Wed, 21 Oct 2026 07:28:00 GMT'), isNull);
    expect(parseRetryAfter(null), isNull);
    expect(formatWait(const Duration(milliseconds: 1500)), '2 s');
    expect(formatWait(const Duration(seconds: 59)), '59 s');
    expect(formatWait(const Duration(seconds: 61)), '2 min');
  });

  test('415 without extension members: generic Polish message', () {
    final p = ApiProblem.from(
      problem(415, {'code': 'attachment.type_not_allowed'}),
    );
    expect(p.message, 'Niedozwolony typ pliku.');
    expect(fileTypeLabel('application/x-unknown'), 'application/x-unknown');
  });
}
