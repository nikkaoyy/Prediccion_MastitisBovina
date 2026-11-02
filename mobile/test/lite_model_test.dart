import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/models/lite_model.dart';

import 'helpers.dart';

void main() {
  final model = loadModel();

  test('paridad con scikit-learn sobre los casos exportados (models/parity_fixtures.json)', () {
    final fixtures = jsonDecode(readModelsFile('parity_fixtures.json')) as Map<String, dynamic>;
    expect(fixtures['model_version'], model.version);
    final cases = fixtures['cases'] as List;
    expect(cases, isNotEmpty);

    var worst = 0.0;
    for (final c in cases) {
      final input = Map<String, Object?>.from((c as Map)['input'] as Map);
      final expected = (c['probability'] as num).toDouble();
      final diff = (model.predict(input) - expected).abs();
      if (diff > worst) worst = diff;
    }
    expect(worst, lessThan(1e-9));
  });

  test('el asset empaquetado es idéntico a models/model_lite.json', () {
    final asset = File('assets/model_lite.json').readAsStringSync();
    expect(asset, readModelsFile('model_lite.json'),
        reason: 'Ejecute: python -m src.export.export_model para regenerar y copiar el asset');
  });

  Map<String, Object?> base() => {
        'edad': 5, 'raza': 'Holstein', 'numero_de_partos': 3, 'volumen_de_leche': 11.0,
        'etapa_de_lactancia': 1, 'antecedentes_de_mastitis': 0, 'humedad': 70.0,
        'temperatura': 12.0, 'ph_leche': 6.6,
      };

  test('valores faltantes se imputan y la raza desconocida no rompe la predicción', () {
    final withMissing = base()
      ..['volumen_de_leche'] = null
      ..['humedad'] = null
      ..['raza'] = null;
    final unknown = base()..['raza'] = 'Raza_Nueva';
    for (final record in [withMissing, unknown]) {
      final p = model.predict(record);
      expect(p, inInclusiveRange(0.0, 1.0));
    }
  });

  test('a mayor pH, mayor puntaje (relación biológica esperada)', () {
    final low = model.predict(base()..['ph_leche'] = 6.4);
    final high = model.predict(base()..['ph_leche'] = 7.0);
    expect(high, greaterThan(low));
    expect(model.levelFor(low), RiskLevel.bajo);
    expect(model.levelFor(high), RiskLevel.alto);
  });

  test('los niveles de riesgo son monótonos en el puntaje', () {
    var last = 0;
    for (var i = 0; i <= 100; i++) {
      final level = model.levelFor(i / 100).index;
      expect(level, greaterThanOrEqualTo(last));
      last = level;
    }
  });

  test('validate exige pH y respeta rangos', () {
    expect(model.validate(base()..['ph_leche'] = null), isNotEmpty);
    expect(model.validate(base()..['ph_leche'] = 12.0), isNotEmpty);
    expect(model.validate(base()), isEmpty);
  });

  test('NaN e infinito no son mediciones válidas', () {
    expect(model.validate(base()..['ph_leche'] = double.nan), isNotEmpty);
    expect(model.validate(base()..['ph_leche'] = double.infinity), isNotEmpty);
    expect(model.validate(base()..['volumen_de_leche'] = double.nan), isNotEmpty);
  });

  test('un modelo con coeficientes de más se rechaza', () {
    final json = jsonDecode(readModelsFile('model_lite.json')) as Map<String, dynamic>;
    (json['coefficients'] as List).add(0.1);
    expect(() => LiteModel.fromJson(json), throwsFormatException);
  });
}
