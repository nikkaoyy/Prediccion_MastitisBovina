"""Ejecución puntual para entrenar y persistir el Pipeline final."""

from __future__ import annotations

import argparse
from pathlib import Path

from main import run


PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
)

DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "src/data/artifacts"


def parse_args() -> argparse.Namespace:
    """Obtiene parámetros de ejecución."""

    parser = argparse.ArgumentParser(
        description=(
            "Entrena y persiste un DecisionTree para mastitis subclínica."
        )
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATASET,
        help="Ruta al CSV de entrenamiento.",
    )

    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directorio de salida del Pipeline serializado.",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=PROJECT_ROOT / "demo_reports",
        help="Directorio de matrices, diagrama y reporte JSON.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()

    run(
        data_path=arguments.data,
        artifacts_dir=arguments.artifacts_dir,
        reports_dir=arguments.reports_dir,
    )