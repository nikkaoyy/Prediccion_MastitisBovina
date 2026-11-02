import 'package:flutter/material.dart';

import '../models/lite_model.dart';

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: const Color(0xFF1B5E20), brightness: Brightness.light);
  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    visualDensity: VisualDensity.standard,
    textTheme: const TextTheme(
      bodyLarge: TextStyle(fontSize: 18),
      bodyMedium: TextStyle(fontSize: 17),
      titleMedium: TextStyle(fontSize: 19, fontWeight: FontWeight.w600),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(56),
        textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        textStyle: const TextStyle(fontSize: 17),
      ),
    ),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 16),
    ),
  );
}

/// El nivel se comunica con texto + icono + color (nunca solo color).
class RiskStyle {
  const RiskStyle(this.label, this.icon, this.background, this.foreground);
  final String label;
  final IconData icon;
  final Color background;
  final Color foreground;

  static RiskStyle of(RiskLevel level) => switch (level) {
        RiskLevel.bajo => const RiskStyle(
            'Riesgo bajo', Icons.check_circle, Color(0xFFE8F5E9), Color(0xFF1B5E20)),
        RiskLevel.medio => const RiskStyle(
            'Riesgo medio', Icons.warning_amber_rounded, Color(0xFFFFF3CD), Color(0xFF7A5200)),
        RiskLevel.alto => const RiskStyle(
            'Riesgo alto', Icons.error, Color(0xFFFDE7E7), Color(0xFFB00020)),
      };
}

String recommendationFor(RiskLevel level) => switch (level) {
      RiskLevel.bajo =>
        'Mantenga la rutina de ordeño e higiene. Un resultado bajo no descarta mastitis: '
            'si ve grumos en la leche, calor, hinchazón o dolor en la ubre, haga la prueba CMT '
            'y consulte al veterinario.',
      RiskLevel.medio =>
        'Haga la prueba CMT a este animal, ordéñelo al final y vigile la ubre en los próximos días. '
            'Consulte al veterinario si aparecen signos.',
      RiskLevel.alto =>
        'Ordeñe a este animal al final o sepárelo, confirme con la prueba CMT y consulte al '
            'veterinario antes de decidir cualquier tratamiento.',
    };

const decisionSupportNotice =
    'Estimación de apoyo a la decisión. No es un diagnóstico y no sustituye la valoración '
    'veterinaria ni la prueba confirmatoria (CMT).';

String formatDateTime(DateTime value) {
  final v = value.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(v.day)}/${two(v.month)}/${v.year} ${two(v.hour)}:${two(v.minute)}';
}
