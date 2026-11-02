"""Rutas del proyecto, ancladas a la ubicación de este archivo.

Ninguna ruta depende del directorio de trabajo desde el que se ejecute.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_SUBDIR = "models"
REPORTS_SUBDIR = "reports"
MODELS_DIR = ARTIFACTS_DIR / MODELS_SUBDIR
REPORTS_DIR = ARTIFACTS_DIR / REPORTS_SUBDIR
