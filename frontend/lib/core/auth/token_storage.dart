import 'token_storage_stub.dart'
    if (dart.library.js_interop) 'token_storage_web.dart'
    as platform;

/// Where the access token survives a page reload (ADR 0014 §1).
///
/// Web: `sessionStorage` — per browser tab, cleared when the tab closes,
/// never shared with other tabs or persisted to disk like `localStorage`.
/// Tests and non-web platforms: memory only.
abstract interface class TokenStorage {
  String? read();
  void write(String value);
  void clear();
}

class MemoryTokenStorage implements TokenStorage {
  MemoryTokenStorage([this._value]);

  String? _value;

  @override
  String? read() => _value;

  @override
  void write(String value) => _value = value;

  @override
  void clear() => _value = null;
}

TokenStorage createTokenStorage() => platform.createPlatformTokenStorage();
