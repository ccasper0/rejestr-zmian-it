import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/session.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import 'router.dart' show signOutToLogin;

/// `/`: sends the user to their first company (from `GET /me`).
class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    final target = me.value == null ? null : homeLocation(me.value!);
    if (target != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) context.go(target);
      });
    }

    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: switch (me) {
              AsyncError(:final error) => Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ErrorPanel(
                    error: error,
                    onRetry: () => ref.invalidate(meProvider),
                  ),
                  const SizedBox(height: 12),
                  const _SignOutButton(),
                ],
              ),
              AsyncData() when target == null => const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  MessageBanner(
                    kind: BannerKind.warning,
                    title: 'Brak dostępu do spółek',
                    message:
                        'Twoje konto nie ma jeszcze roli w żadnej spółce. '
                        'Poproś administratora aplikacji o nadanie dostępu.',
                  ),
                  SizedBox(height: 12),
                  _SignOutButton(),
                ],
              ),
              _ => const LoadingPanel(label: 'Wczytywanie profilu…'),
            },
          ),
        ),
      ),
      backgroundColor: AppColors.background,
    );
  }
}

/// First company register; admins without memberships go to administration.
String? homeLocation(Me me) {
  if (me.memberships.isNotEmpty) {
    return '/c/${me.memberships.first.companyPrefix}/changes';
  }
  if (me.isAppAdmin) return '/admin/companies';
  return null;
}

class _SignOutButton extends ConsumerWidget {
  const _SignOutButton();

  @override
  Widget build(BuildContext context, WidgetRef ref) => OutlinedButton.icon(
    onPressed: () => signOutToLogin(context, ref),
    icon: const Icon(Icons.logout),
    label: const Text('Wyloguj'),
  );
}
