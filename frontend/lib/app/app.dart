import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/service_notice.dart';
import '../core/theme.dart';
import 'router.dart';

/// Root messenger: app-wide notices (rate limit, API unavailable) appear
/// whatever page is shown.
final rootScaffoldMessengerKeyProvider =
    Provider<GlobalKey<ScaffoldMessengerState>>(
      (ref) => GlobalKey<ScaffoldMessengerState>(),
    );

class RejestrApp extends ConsumerWidget {
  const RejestrApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final messengerKey = ref.watch(rootScaffoldMessengerKeyProvider);
    ref.listen(serviceNoticeProvider, (previous, next) {
      if (next == null) return;
      messengerKey.currentState
        ?..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            key: ValueKey('service-notice-${next.code}'),
            content: Text(next.message),
            duration: const Duration(seconds: 8),
            showCloseIcon: true,
          ),
        );
    });
    return MaterialApp.router(
      title: 'Rejestr zmian IT',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      scaffoldMessengerKey: messengerKey,
      locale: const Locale('pl', 'PL'),
      supportedLocales: const [Locale('pl', 'PL')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      routerConfig: ref.watch(routerProvider),
    );
  }
}
