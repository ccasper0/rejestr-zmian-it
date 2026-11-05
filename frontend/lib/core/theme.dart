import 'package:flutter/material.dart';

import 'change_status.dart';

/// Visual design tokens (CLAUDE.md, section 10).
///
/// Widgets must take colours, radii and font families from here — never
/// hardcode them.
abstract final class AppColors {
  static const Color background = Color(0xFFF4F5F7);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color border = Color(0xFFDDE1E6);
  static const Color text = Color(0xFF161A1F);
  static const Color textSecondary = Color(0xFF5A6270);
  static const Color accent = Color(0xFF1D4ED8);
  static const Color onAccent = Color(0xFFFFFFFF);

  /// Error/destructive text (same as the "rejected" status text).
  static const Color danger = Color(0xFF8A1C1C);

  /// Emergency change type highlight (red border).
  static const Color emergencyBorder = Color(0xFFB91C1C);

  // Navigation side panel (dark).
  static const Color sidebar = Color(0xFF161A1F);
  static const Color sidebarText = Color(0xFFE6E8EB);
  static const Color sidebarTextMuted = Color(0xFF9AA3AF);
  static const Color sidebarActive = Color(0xFF2A313A);
  static const Color sidebarHover = Color(0xFF20262D);
  static const Color sidebarDivider = Color(0xFF2E353E);
  static const Color sidebarActiveIndicator = Color(0xFF6B8EF5);

  // Connection indicator dots (decorative, text label carries meaning).
  static const Color indicatorOk = Color(0xFF22C55E);
  static const Color indicatorError = Color(0xFFEF4444);
  static const Color indicatorPending = Color(0xFF9AA3AF);

  /// Audit diff: old value (struck through) and new value (§10.2).
  static const Color diffRemoved = Color(0xFF8A1C1C);
  static const Color diffRemovedBackground = Color(0xFFFBE1E1);
  static const Color diffAdded = Color(0xFF14532D);
  static const Color diffAddedBackground = Color(0xFFDDF3E4);

  /// Light fill for nested boxes (diffs, read-only fields).
  static const Color surfaceMuted = Color(0xFFF8F9FA);

  /// Scrim behind modal progress overlays.
  static const Color scrim = Color(0x66161A1F);
}

/// Feedback palettes (banners, badges, readiness checks) — reuse the status
/// pairs of §10, whose text/background contrast is >= 4.5:1.
abstract final class AppFeedbackColors {
  static const StatusColors success = AppStatusColors.verified;
  static const StatusColors warning = AppStatusColors.pendingApproval;
  static const StatusColors error = AppStatusColors.negative;
  static const StatusColors info = AppStatusColors.approved;
  static const StatusColors neutral = AppStatusColors.draft;
}

/// Background / foreground colour pair of a status pill.
@immutable
class StatusColors {
  const StatusColors({required this.background, required this.foreground});

  final Color background;
  final Color foreground;
}

abstract final class AppStatusColors {
  static const StatusColors draft = StatusColors(
    background: Color(0xFFECEEF1),
    foreground: Color(0xFF3D4450),
  );
  static const StatusColors pendingApproval = StatusColors(
    background: Color(0xFFFDF0D5),
    foreground: Color(0xFF7A4B00),
  );
  static const StatusColors approved = StatusColors(
    background: Color(0xFFDCE7FD),
    foreground: Color(0xFF1E3A8A),
  );
  static const StatusColors implemented = StatusColors(
    background: Color(0xFFE2F0FB),
    foreground: Color(0xFF0B4A6F),
  );
  static const StatusColors verified = StatusColors(
    background: Color(0xFFDDF3E4),
    foreground: Color(0xFF14532D),
  );

  /// Shared by `rejected` and `rolled_back`.
  static const StatusColors negative = StatusColors(
    background: Color(0xFFFBE1E1),
    foreground: Color(0xFF8A1C1C),
  );

  static StatusColors of(ChangeStatus status) => switch (status) {
    ChangeStatus.draft => draft,
    ChangeStatus.pendingApproval => pendingApproval,
    ChangeStatus.approved => approved,
    ChangeStatus.implemented => implemented,
    ChangeStatus.verified => verified,
    ChangeStatus.rejected || ChangeStatus.rolledBack => negative,
    // Not specified in section 10 — neutral palette (same as draft).
    ChangeStatus.cancelled => draft,
  };
}

abstract final class AppRadii {
  static const double small = 8;
  static const double medium = 10;
  static const BorderRadius smallAll = BorderRadius.all(Radius.circular(small));
  static const BorderRadius mediumAll = BorderRadius.all(
    Radius.circular(medium),
  );
}

abstract final class AppSizes {
  /// Minimum touch target (WCAG / section 10).
  static const double minTouchTarget = 44;
  static const double sidebarWidth = 232;

  /// Below this width the side panel collapses into a drawer.
  static const double wideLayoutBreakpoint = 900;
}

abstract final class AppFonts {
  static const String sans = 'IBMPlexSans';
  static const String mono = 'IBMPlexMono';

  /// Style for identifiers, dates, hashes and abbreviations.
  static TextStyle monoStyle({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
  }) => TextStyle(
    fontFamily: mono,
    fontSize: fontSize,
    fontWeight: fontWeight,
    color: color,
  );
}

abstract final class AppTheme {
  static ThemeData light() {
    final colorScheme =
        ColorScheme.fromSeed(
          seedColor: AppColors.accent,
          brightness: Brightness.light,
        ).copyWith(
          primary: AppColors.accent,
          onPrimary: AppColors.onAccent,
          surface: AppColors.surface,
          onSurface: AppColors.text,
          onSurfaceVariant: AppColors.textSecondary,
          outline: AppColors.border,
          outlineVariant: AppColors.border,
          error: AppColors.danger,
        );

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: AppFonts.sans,
      scaffoldBackgroundColor: AppColors.background,
      materialTapTargetSize: MaterialTapTargetSize.padded,
    );

    const minButtonSize = Size(
      AppSizes.minTouchTarget,
      AppSizes.minTouchTarget,
    );
    const buttonShape = RoundedRectangleBorder(borderRadius: AppRadii.smallAll);

    return base.copyWith(
      textTheme: base.textTheme.apply(
        bodyColor: AppColors.text,
        displayColor: AppColors.text,
        fontFamily: AppFonts.sans,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 1,
        space: 1,
      ),
      cardTheme: const CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadii.mediumAll,
          side: BorderSide(color: AppColors.border),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.sidebar,
        foregroundColor: AppColors.sidebarText,
        elevation: 0,
        centerTitle: false,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: minButtonSize,
          shape: buttonShape,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: minButtonSize,
          shape: buttonShape,
          side: const BorderSide(color: AppColors.border),
          foregroundColor: AppColors.text,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: minButtonSize,
          shape: buttonShape,
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(minimumSize: minButtonSize),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppColors.accent, width: 2),
        ),
      ),
      drawerTheme: const DrawerThemeData(
        backgroundColor: AppColors.sidebar,
        width: AppSizes.sidebarWidth + 48,
      ),
    );
  }
}
