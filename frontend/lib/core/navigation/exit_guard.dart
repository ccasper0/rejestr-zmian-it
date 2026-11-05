import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'leave_warning_stub.dart'
    if (dart.library.js_interop) 'leave_warning_web.dart'
    as platform;

/// Lets a screen with unsaved work veto in-app navigation away from it
/// (go_router `onExit` of the route calls [allowExit]).
class ExitGuard {
  Future<bool> Function()? current;

  Future<bool> allowExit() async {
    final guard = current;
    return guard == null ? true : await guard();
  }
}

final exitGuardProvider = Provider<ExitGuard>((ref) => ExitGuard());

/// Browser `beforeunload` warning (reload, closing the tab, external link)
/// while [shouldWarn] returns true; null removes it.
void setLeaveWarning(bool Function()? shouldWarn) =>
    platform.setLeaveWarning(shouldWarn);
