# Implementación — Modelo B y exportación

Parte de [[Implementación 2026-11-01 — Índice]].

## Qué se hizo
- `DataValidator` y `FeaturePipelineBuilder` aceptan `feature_set` **A** o **B** (`FEATURE_SETS` en `src/data/dataValidation.py`).
  - **A:** 12 variables con conductividad (laboratorio).
  - **B:** 9 variables sin conductividad, con pH obligatorio (desplegable).
- Los entrenadores reciben `feature_set`; `main.py --feature-set` (por defecto B) genera reportes separados.
- `src/models/evaluation.py`: bootstrap por finca (remuestrea fincas, no animales), umbrales sobre OOF, leave-one-farm-out, regla de pH como línea base.
- `src/export/export_model.py`: entrena B final y exporta ONNX, `model_lite.json`, manifiesto con SHA-256, tarjeta del modelo, casos de paridad y baseline de drift.

## Cifras (versión `mastitis-B-lr-d4ae0119`)
| Métrica (OOF, GroupKFold 5) | Valor |
|---|---|
| Accuracy | 0,971 |
| Precisión | 0,982 |
| Recall | 0,964 |
| F1 | 0,973 |
| ROC-AUC | 0,981 |

- Umbral alto 0,579 → Recall 0,955 (IC 0,906–0,993).
- Umbral medio 0,415.
- Positivos por nivel: 107 alto · 2 medio · **3 bajo**. Sanos: 1 alto · 4 medio · 92 bajo.

## Hallazgos que el artículo debe discutir
- [[Implementación — Hallazgos de la revisión]]: un modelo **solo con pH** obtiene 1,00 en las mismas métricas.
- Los umbrales son optimistas (se eligen sobre las mismas predicciones que se reportan).
- Sanos ≤ pH 6,72 y enfermos ≥ pH 6,75: separación casi perfecta, posible circularidad.

## Paridad
- Lite (Dart/Python) vs scikit-learn: ≤ 2e-16.
- ONNX vs scikit-learn: ≤ 1,8e-6.
- 209 casos del dataset + 12 casos límite (raza faltante, raza nueva, volumen/humedad/temperatura/edad faltantes).

## Archivos
- `models/`: model.onnx, model_lite.json, manifest.json, model_card.json, parity_fixtures.json, drift_baseline.json
- `mobile/assets/model_lite.json` (copia para la app)
- `docs/cambios_articulo.md`: correcciones propuestas al artículo.
