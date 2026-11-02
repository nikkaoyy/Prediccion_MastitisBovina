"""Rutas del proyecto, ancladas a la ubicación de este archivo.

Ninguna ruta depende del directorio de trabajo desde el que se ejecute.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
