import 'package:flutter/material.dart';

class WazenTheme {
  static const green = Color(0xFF355E3B);
  static const greenDark = Color(0xFF24452A);
  static const beige = Color(0xFFF5F0E6);
  static const sand = Color(0xFFE8DCC7);
  static const gold = Color(0xFFC8A96B);
  static const ink = Color(0xFF1E2721);

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: green,
      brightness: Brightness.light,
      surface: const Color(0xFFFBFAF7),
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(primary: green, secondary: gold),
      scaffoldBackgroundColor: const Color(0xFFFBFAF7),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: green,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(54),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFE8E8E2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: green, width: 1.4),
        ),
      ),
    );
  }
}
