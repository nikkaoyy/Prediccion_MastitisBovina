"""Intérprete de referencia de ``model.json`` (solo librería estándar).

Es la especificación ejecutable para un cliente sin Python. Dos detalles son
necesarios para reproducir scikit-learn exactamente:

* el valor transformado se convierte a float32 antes de compararlo con el
  umbral, que sigue en float64 (``Math.fround`` en JavaScript, ``Float32List``
  en Dart);
* si ``value <= threshold`` se va a ``left``; en caso contrario, a ``right``.
"""

from __future__ import annotations

import math
import struct
from typing import Any, Mapping


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _to_float32(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


def transform(model: Mapping[str, Any], record: Mapping[str, Any]) -> list[float]:
    """Aplica imputación, escalado y one-hot en el orden de ``transformed_features``."""

    vector: list[float] = []

    for feature in model["preprocessing"]["numeric"]:
        value = record.get(feature["name"])
        value = feature["median"] if _is_missing(value) else float(value)
        vector.append((value - feature["mean"]) / feature["scale"])

    for feature in model["preprocessing"]["categorical"]:
        value = record.get(feature["name"])
        value = feature["fill_value"] if _is_missing(value) else value
        # Categoría desconocida: todas las columnas en 0 (handle_unknown="ignore").
        vector.extend(1.0 if value == c else 0.0 for c in feature["categories"])

    return vector


def predict(model: Mapping[str, Any], record: Mapping[str, Any]) -> tuple[int, float]:
    """Devuelve la clase y la probabilidad de mastitis de un registro."""

    vector = transform(model, record)
    nodes = model["tree"]["nodes"]
    node = nodes[0]

    while "class" not in node:
        value = _to_float32(vector[node["feature"]])
        node = nodes[node["left"] if value <= node["threshold"] else node["right"]]

    return node["class"], node["probabilities"][1]
