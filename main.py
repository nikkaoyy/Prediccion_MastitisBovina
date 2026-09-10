"""Orquestador CRISP-ML(Q) del componente de árbol de decisión."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.dataValidation import DataValidator
from src.models.DecisionTreeTraining import DecisionTreeModelTrainer


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
)


def run(
    data_path: str | Path,
    artifacts_dir: str | Path = "src/data/artifacts",
    reports_dir: str | Path = "demo_reports",
) -> dict[str, Any]:
    """Ejecuta el flujo CRISP-ML(Q) completo."""

    data_path = Path(data_path)
    artifacts_dir = Path(artifacts_dir)
    reports_dir = Path(reports_dir)

    if not data_path.is_file():
        raise FileNotFoundError(
            f"No se encontró el dataset: {data_path}"
        )

    raw_data = pd.read_csv(data_path)

    validator = DataValidator()
    clean_data, quality_report = validator.validate_and_clean(raw_data)

    X = clean_data.loc[:, DataValidator.FEATURE_COLUMNS]
    y = clean_data[DataValidator.TARGET_COLUMN].astype(int)
    groups = clean_data[DataValidator.GROUP_COLUMN]

    trainer = DecisionTreeModelTrainer(
        n_splits=5,
        random_state=42,
    )

    trainer.fit(X=X, y=y, groups=groups)

    evaluation = trainer.evaluate_grouped_cv(
        X=X,
        y=y,
        groups=groups,
    )

    model_path = trainer.persist_model(
        artifacts_dir / "mastitis_decision_tree_pipeline.pkl"
    )

    confusion_matrix_path = trainer.save_confusion_matrix(
        evaluation,
        reports_dir / "matriz_confusion_groupkfold.png",
    )

    tree_diagram_path = trainer.save_tree_diagram(
        reports_dir / "arbol_decision_mastitis.png"
    )

    summary: dict[str, Any] = {
        "data_quality": quality_report.to_dict(),
        "selection_metric": "f1",
        "best_grouped_cv_f1": trainer.best_score_,
        "best_params": trainer.best_params_,
        "evaluation_protocol": (
            "Validación cruzada agrupada anidada: "
            "GroupKFold(n_splits=5) externo por finca y "
            "GroupKFold(n_splits=4) interno para tuning."
        ),
        "evaluation": evaluation.serializable_summary(),
        "artifacts": {
            "model": str(model_path),
            "confusion_matrix": str(confusion_matrix_path),
            "tree_diagram": str(tree_diagram_path),
        },
    }

    reports_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = reports_dir / "reporte_metricas_groupkfold.json"

    metrics_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== Calidad de datos ===")
    print(json.dumps(quality_report.to_dict(), ensure_ascii=False, indent=2))

    print("\n=== Tuning agrupado ===")
    print(f"Mejor F1 GroupKFold: {trainer.best_score_:.4f}")
    print(f"Mejores parámetros: {trainer.best_params_}")

    print("\n=== Evaluación OOF por finca ===")

    for metric, value in evaluation.aggregate_metrics.items():
        print(f"{metric}: {value:.4f}")

    print(f"Modelo persistido: {model_path}")
    print(f"Reporte de métricas: {metrics_path}")

    return summary


def parse_args() -> argparse.Namespace:
    """Define CLI para usar otro CSV sin modificar código."""

    parser = argparse.ArgumentParser(
        description="Entrena el modelo de mastitis."
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATASET,
    )

    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("src/data/artifacts"),
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("demo_reports"),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run(
        args.data,
        args.artifacts_dir,
        args.reports_dir,
    )