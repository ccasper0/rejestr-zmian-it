import 'dart:js_interop';

import 'package:web/web.dart' as web;

bool Function()? _shouldWarn;
bool _installed = false;

void setLeaveWarning(bool Function()? shouldWarn) {
  _shouldWarn = shouldWarn;
  if (_installed) return;
  _installed = true;
  web.window.addEventListener(
    'beforeunload',
    ((web.BeforeUnloadEvent event) {
      if (_shouldWarn?.call() ?? false) {
        event.preventDefault();
        event.returnValue = '';
      }
    }).toJS,
  );
}
