import 'package:web/web.dart' as web;

import 'token_storage.dart';

const _key = 'rejestr.auth';

class _SessionStorageTokenStorage implements TokenStorage {
  @override
  String? read() {
    try {
      return web.window.sessionStorage.getItem(_key);
    } on Object {
      return null; // storage disabled (privacy mode) — memory-only session
    }
  }

  @override
  void write(String value) {
    try {
      web.window.sessionStorage.setItem(_key, value);
    } on Object {
      // Storage unavailable: the session lasts until the page is reloaded.
    }
  }

  @override
  void clear() {
    try {
      web.window.sessionStorage.removeItem(_key);
    } on Object {
      // nothing stored
    }
  }
}

TokenStorage createPlatformTokenStorage() => _SessionStorageTokenStorage();
