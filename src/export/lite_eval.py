"""Evaluador de referencia del modelo lite (Python puro, sin numpy).

Replica exactamente lo que hace el cliente móvil (Dart) con
``model_lite.json``: imputación, estandarización, one-hot y regresión
logística. Sirve para probar paridad con scikit-learn y ONNX.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def predict_probability(lite: Mapping[str, Any], record: Mapping[str, Any]) -> float:
    """Probabilidad de mastitis para un registro con las variables del modelo."""

    total = float(lite["intercept"])
    coefficients = lite["coefficients"]
    position = 0

    for feature in lite["numeric"]:
        value = record.get(feature["name"])

        if _is_missing(value):
            value = feature["median"]

        scaled = (float(value) - feature["mean"]) / feature["scale"]
        total += coefficients[position] * scaled
        position += 1

    for feature in lite["categorical"]:
        value = record.get(feature["name"])

        if _is_missing(value):
            value = feature["fill_value"]

        for category in feature["categories"]:
            # Categoría desconocida => todas las columnas en 0 (handle_unknown=ignore).
            if value == category:
                total += coefficients[position]

            position += 1

    if position != len(coefficients):
        raise ValueError("El número de coeficientes no coincide con las variables.")

    return 1.0 / (1.0 + math.exp(-total))


def risk_level(lite: Mapping[str, Any], probability: float) -> str:
    """Nivel de riesgo: 'bajo', 'medio' o 'alto'."""

    thresholds = lite["thresholds"]

    if probability >= thresholds["alto"]:
        return "alto"

    if probability >= thresholds["medio"]:
        return "medio"

    return "bajo"
