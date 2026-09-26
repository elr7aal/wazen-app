import 'package:flutter/material.dart';

class WazenTheme {
  static const green = Color(0xFF2E8B74);
  static const greenDark = Color(0xFF123F3A);
  static const beige = Color(0xFFF4FAF7);
  static const sand = Color(0xFFE8D8B5);
  static const gold = Color(0xFFC7A75A);
  static const coral = Color(0xFFEF765E);
  static const ink = Color(0xFF18312E);
  static const muted = Color(0xFF64736F);
  static const border = Color(0xFFDDE8E4);
  static const surface = Color(0xFFFFFFFF);
  static const mint = Color(0xFFE7F4EF);

  static ThemeData light() {
    const scheme = ColorScheme.light(
      primary: greenDark,
      onPrimary: Colors.white,
      primaryContainer: mint,
      onPrimaryContainer: greenDark,
      secondary: green,
      onSecondary: Colors.white,
      secondaryContainer: Color(0xFFDDF2EA),
      onSecondaryContainer: greenDark,
      tertiary: coral,
      onTertiary: Colors.white,
      error: Color(0xFFB94438),
      onError: Colors.white,
      surface: surface,
      onSurface: ink,
      outline: border,
      outlineVariant: Color(0xFFEAF1EE),
      shadow: Color(0x14123F3A),
    );
    final base = ThemeData(useMaterial3: true, colorScheme: scheme);
    return base.copyWith(
      scaffoldBackgroundColor: beige,
      textTheme: base.textTheme.copyWith(
        headlineLarge: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, height: 1.18, color: ink),
        headlineMedium: const TextStyle(fontSize: 27, fontWeight: FontWeight.w900, height: 1.2, color: ink),
        titleLarge: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800, color: ink),
        titleMedium: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: ink),
        bodyLarge: const TextStyle(fontSize: 16, height: 1.5, color: ink),
        bodyMedium: const TextStyle(fontSize: 14, height: 1.45, color: ink),
        bodySmall: const TextStyle(fontSize: 12, height: 1.4, color: muted),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: ink,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: ink),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24), side: const BorderSide(color: border)),
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: greenDark,
          foregroundColor: Colors.white,
          disabledBackgroundColor: const Color(0xFFB9C8C4),
          minimumSize: const Size.fromHeight(56),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: greenDark,
          minimumSize: const Size.fromHeight(54),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          side: const BorderSide(color: Color(0xFFB8CEC7)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: greenDark,
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 17, vertical: 17),
        labelStyle: const TextStyle(color: muted),
        floatingLabelStyle: const TextStyle(color: greenDark, fontWeight: FontWeight.w700),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: border)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: border)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: green, width: 1.6)),
        errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: const BorderSide(color: coral)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        elevation: 0,
        backgroundColor: surface,
        indicatorColor: mint,
        labelTextStyle: WidgetStateProperty.resolveWith((states) => TextStyle(
          fontSize: 11,
          fontWeight: states.contains(WidgetState.selected) ? FontWeight.w800 : FontWeight.w600,
          color: states.contains(WidgetState.selected) ? greenDark : muted,
        )),
        iconTheme: WidgetStateProperty.resolveWith((states) => IconThemeData(color: states.contains(WidgetState.selected) ? greenDark : muted)),
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: mint,
        side: BorderSide.none,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        labelStyle: const TextStyle(color: greenDark, fontWeight: FontWeight.w600),
      ),
      dividerTheme: const DividerThemeData(color: border, thickness: 1),
      dialogTheme: DialogThemeData(backgroundColor: surface, surfaceTintColor: Colors.transparent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26))),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: greenDark,
        contentTextStyle: const TextStyle(color: Colors.white),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: green, linearTrackColor: mint),
    );
  }
}
