/// Build-time configuration passed via `--dart-define`.
abstract final class AppConfig {
  /// Default API origin used when `API_URL` is not defined at all.
  static const String defaultApiOrigin = 'http://localhost:8000';

  /// Whether `--dart-define=API_URL=...` was passed (even with empty value).
  static const bool _hasApiUrl = bool.hasEnvironment('API_URL');
  static const String _apiUrl = String.fromEnvironment('API_URL');

  /// API origin **without** the `/api` prefix (CLAUDE.md, section 14):
  ///
  /// * not defined → [defaultApiOrigin] (`http://localhost:8000`),
  /// * `--dart-define=API_URL=http://localhost:8000` → that origin,
  /// * `--dart-define=API_URL=` (empty) → same origin as the web app
  ///   (nginx proxies `/api/`), i.e. relative URLs.
  static String get apiOrigin =>
      resolveApiOrigin(hasValue: _hasApiUrl, value: _apiUrl);

  /// Base URL for API v1 requests, e.g. `http://localhost:8000/api/v1`, or
  /// `/api/v1` for the same origin. Request paths are relative to it
  /// (`/health` → `$API_URL/api/v1/health`).
  static String get apiBaseUrl => apiBaseUrlFor(apiOrigin);

  static String resolveApiOrigin({
    required bool hasValue,
    required String value,
  }) {
    if (!hasValue) return defaultApiOrigin;
    // Empty value is meaningful: same origin. Do not replace it.
    return _stripTrailingSlashes(value.trim());
  }

  static const String _authMode = String.fromEnvironment('AUTH_MODE');

  /// Login method (`--dart-define=AUTH_MODE=dev|local`, ADR 0014 §1,
  /// ADR 0018 §1).
  ///
  /// Not defined (or any other value) → [AuthModeSetting.auto]: the app asks
  /// the API — `GET /auth/dev/users` exists only when the backend runs with
  /// `AUTH_MODE=dev` (404 otherwise: local accounts, e-mail + password), so
  /// the backend stays the single source of truth and a production API can
  /// never be logged into via dev.
  static AuthModeSetting get authMode => parseAuthMode(_authMode);

  static AuthModeSetting parseAuthMode(String value) =>
      switch (value.trim().toLowerCase()) {
        'dev' => AuthModeSetting.dev,
        'local' => AuthModeSetting.local,
        _ => AuthModeSetting.auto,
      };

  static String apiBaseUrlFor(String origin) =>
      '${_stripTrailingSlashes(origin)}/api/v1';

  static String _stripTrailingSlashes(String url) {
    var result = url;
    while (result.endsWith('/')) {
      result = result.substring(0, result.length - 1);
    }
    return result;
  }
}

/// Configured login method; `auto` detects it from the API.
enum AuthModeSetting { auto, dev, local }
