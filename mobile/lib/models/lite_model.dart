import 'dart:convert';
import 'dart:math' as math;

/// Nivel de riesgo estimado. Es apoyo a la decisión, no un diagnóstico.
enum RiskLevel {
  bajo,
  medio,
  alto;

  static RiskLevel parse(String value) => RiskLevel.values.firstWhere(
        (level) => level.name == value,
        orElse: () => throw FormatException('Nivel de riesgo desconocido: $value'),
      );
}

class NumericFeature {
  const NumericFeature({
    required this.name,
    required this.median,
    required this.mean,
    required this.scale,
  });

  final String name;
  final double median;
  final double mean;
  final double scale;
}

class CategoricalFeature {
  const CategoricalFeature({
    required this.name,
    required this.fillValue,
    required this.categories,
  });

  final String name;
  final String fillValue;
  final List<String> categories;
}

class ValueRange {
  const ValueRange(this.low, this.high);
  final double low;
  final double high;
}

/// Modelo lite: regresión logística evaluada localmente sin runtime nativo.
///
/// Replica `src/export/lite_eval.py` y se verifica contra
/// `models/parity_fixtures.json` (ver test/lite_model_test.dart).
class LiteModel {
  const LiteModel({
    required this.version,
    required this.numeric,
    required this.categorical,
    required this.coefficients,
    required this.intercept,
    required this.thresholdAlto,
    required this.thresholdMedio,
    required this.requiredInputs,
    required this.ranges,
    required this.disclaimer,
  });

  final String version;
  final List<NumericFeature> numeric;
  final List<CategoricalFeature> categorical;
  final List<double> coefficients;
  final double intercept;
  final double thresholdAlto;
  final double thresholdMedio;
  final List<String> requiredInputs;
  final Map<String, ValueRange> ranges;
  final String disclaimer;

  /// Lanza [FormatException] ante cualquier JSON que no sea un modelo válido.
  factory LiteModel.fromJsonString(String source) {
    try {
      return LiteModel.fromJson(jsonDecode(source) as Map<String, dynamic>);
    } on FormatException {
      rethrow;
    } on Object catch (e) {
      throw FormatException('Modelo inválido: $e');
    }
  }

  factory LiteModel.fromJson(Map<String, dynamic> json) {
    double num_(Object? v) => (v as num).toDouble();

    final numeric = (json['numeric'] as List)
        .map((e) => e as Map<String, dynamic>)
        .map((e) => NumericFeature(
              name: e['name'] as String,
              median: num_(e['median']),
              mean: num_(e['mean']),
              scale: num_(e['scale']),
            ))
        .toList();

    final categorical = (json['categorical'] as List)
        .map((e) => e as Map<String, dynamic>)
        .map((e) => CategoricalFeature(
              name: e['name'] as String,
              fillValue: e['fill_value'] as String,
              categories: (e['categories'] as List).cast<String>(),
            ))
        .toList();

    final coefficients =
        (json['coefficients'] as List).map(num_).toList(growable: false);
    final expected = numeric.length +
        categorical.fold<int>(0, (sum, f) => sum + f.categories.length);
    if (coefficients.length != expected) {
      throw FormatException(
          'Modelo inválido: ${coefficients.length} coeficientes, se esperaban $expected');
    }

    final thresholds = json['thresholds'] as Map<String, dynamic>;
    final ranges = <String, ValueRange>{
      for (final entry in (json['ranges'] as Map<String, dynamic>).entries)
        entry.key: ValueRange(
          num_((entry.value as List)[0]),
          num_((entry.value as List)[1]),
        ),
    };

    return LiteModel(
      version: json['model_version'] as String,
      numeric: numeric,
      categorical: categorical,
      coefficients: coefficients,
      intercept: num_(json['intercept']),
      thresholdAlto: num_(thresholds['alto']),
      thresholdMedio: num_(thresholds['medio']),
      requiredInputs: (json['required_inputs'] as List).cast<String>(),
      ranges: ranges,
      disclaimer: json['disclaimer'] as String,
    );
  }

  List<String> get breeds => categorical
      .firstWhere((f) => f.name == 'raza',
          orElse: () => const CategoricalFeature(
              name: 'raza', fillValue: '', categories: []))
      .categories;

  /// Puntaje del modelo en [0, 1] (no es una probabilidad calibrada).
  double predict(Map<String, Object?> record) {
    var total = intercept;
    var position = 0;

    for (final feature in numeric) {
      final raw = record[feature.name];
      var value = raw is num ? raw.toDouble() : feature.median;
      if (value.isNaN) value = feature.median;
      total += coefficients[position] * ((value - feature.mean) / feature.scale);
      position++;
    }

    for (final feature in categorical) {
      final raw = record[feature.name];
      final value = raw is String ? raw : feature.fillValue;
      for (final category in feature.categories) {
        // Categoría desconocida => todas las columnas en 0.
        if (value == category) total += coefficients[position];
        position++;
      }
    }

    // Sigmoide numéricamente estable.
    if (total >= 0) return 1.0 / (1.0 + math.exp(-total));
    final e = math.exp(total);
    return e / (1.0 + e);
  }

  RiskLevel levelFor(double score) {
    if (score >= thresholdAlto) return RiskLevel.alto;
    if (score >= thresholdMedio) return RiskLevel.medio;
    return RiskLevel.bajo;
  }

  /// Errores de validación (obligatorios y rangos fisiológicos de calidad de datos).
  List<String> validate(Map<String, Object?> record) {
    final errors = <String>[];
    for (final name in requiredInputs) {
      if (record[name] == null) errors.add('$name es obligatorio');
    }
    ranges.forEach((name, range) {
      final value = record[name];
      if (value is num && !value.isFinite) {
        errors.add('$name no es un número válido');
      } else if (value is num && (value < range.low || value > range.high)) {
        errors.add('$name fuera de rango [${range.low}, ${range.high}]');
      }
    });
    return errors;
  }
}
