"""Orquestador CRISP-ML(Q) del componente de aprendizaje automático."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.dataValidation import DataValidator
from src.data.dummyDataGenerator import generate_dummy_data
from src.models.DecisionTreeTraining import DecisionTreeModelTrainer
from src.models.RandomForest import RandomForestModelTrainer
from src.models.LogisticalRegresion import LogisticRegressionModelTrainer
from src.models.evaluation import (
    cluster_bootstrap_ci,
    leave_one_farm_out,
    ph_rule_baseline,
    select_thresholds,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
)


def run(
    data_path: str | Path,
    artifacts_dir: str | Path = PROJECT_ROOT / "src/data/artifacts",
    reports_dir: str | Path = PROJECT_ROOT / "demo_reports",
    use_dummy: bool = False,
    feature_set: str = "B",
) -> dict[str, Any]:
    """Ejecuta el flujo CRISP-ML(Q) completo para múltiples modelos."""

    artifacts_dir = Path(artifacts_dir)
    reports_dir = Path(reports_dir)

    if use_dummy:
        print("\n=== Usando Dummy Data ===")
        raw_data = generate_dummy_data(n_samples=200, random_state=42)
    else:
        data_path = Path(data_path)
        if not data_path.is_file():
            raise FileNotFoundError(f"No se encontró el dataset: {data_path}")
        raw_data = pd.read_csv(data_path)

    feature_set = feature_set.upper()
    validator = DataValidator(feature_set=feature_set)
    clean_data, quality_report = validator.validate_and_clean(raw_data)

    X = clean_data.loc[:, list(validator.feature_columns)]
    y = clean_data[DataValidator.TARGET_COLUMN].astype(int)
    groups = clean_data[DataValidator.GROUP_COLUMN]

    trainers = {
        "decision_tree": DecisionTreeModelTrainer(n_splits=5, random_state=42, feature_set=feature_set),
        "random_forest": RandomForestModelTrainer(n_splits=5, random_state=42, feature_set=feature_set),
        "logistic_regression": LogisticRegressionModelTrainer(n_splits=5, random_state=42, feature_set=feature_set),
    }

    results: dict[str, Any] = {
        "feature_set": feature_set,
        "features": list(validator.feature_columns),
        "data_quality": quality_report.to_dict(),
        "baseline_ph_rule": (
            ph_rule_baseline(clean_data) if "ph_leche" in clean_data else None
        ),
        "models": {},
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n=== Calidad de datos ===")
    print(json.dumps(quality_report.to_dict(), ensure_ascii=False, indent=2))

    for model_name, trainer in trainers.items():
        print(f"\n=== Entrenando {model_name} ===")
        
        trainer.fit(X=X, y=y, groups=groups)

        evaluation = trainer.evaluate_grouped_cv(X=X, y=y, groups=groups)

        model_path = trainer.persist_model(
            artifacts_dir / f"mastitis_{model_name}_{feature_set}_pipeline.pkl"
        )

        # Matriz de confusión para todos los modelos
        confusion_matrix_path = reports_dir / f"matriz_confusion_{model_name}_{feature_set}.png"
        
        if hasattr(trainer, 'save_confusion_matrix'):
            trainer.save_confusion_matrix(evaluation, confusion_matrix_path)
            
        # Árbol de decisión diagrama específico
        tree_diagram_path = None
        if model_name == "decision_tree" and hasattr(trainer, 'save_tree_diagram'):
            tree_diagram_path = trainer.save_tree_diagram(
                reports_dir / f"arbol_decision_mastitis_{feature_set}.png"
            )

        print(f"Mejor F1 GroupKFold: {trainer.best_score_:.4f}")
        print(f"Mejores parámetros: {trainer.best_params_}")

        print("=== Evaluación OOF por finca ===")
        for metric, value in evaluation.aggregate_metrics.items():
            print(f"{metric}: {value:.4f}")

        thresholds = select_thresholds(evaluation.y_true, evaluation.y_probability)
        bootstrap = {
            "threshold_0.5": cluster_bootstrap_ci(
                evaluation.y_true, evaluation.y_probability, groups, 0.5
            ),
            "threshold_alto": cluster_bootstrap_ci(
                evaluation.y_true,
                evaluation.y_probability,
                groups,
                thresholds["alto"],
            ),
        }
        lofo = leave_one_farm_out(trainer.best_estimator_, X, y, groups)
        lofo.pop("y_probability")

        model_summary = {
            "thresholds_oof": thresholds,
            "bootstrap_ci_by_farm": bootstrap,
            "leave_one_farm_out": lofo,
            "selection_metric": "f1",
            "best_grouped_cv_f1": trainer.best_score_,
            "best_params": trainer.best_params_,
            "evaluation": evaluation.serializable_summary(),
            "artifacts": {
                "model": str(model_path),
                "confusion_matrix": str(confusion_matrix_path) if hasattr(trainer, 'save_confusion_matrix') else None,
                "tree_diagram": str(tree_diagram_path) if tree_diagram_path else None,
            },
        }
        
        results["models"][model_name] = model_summary

    metrics_path = reports_dir / f"reporte_metricas_{feature_set}.json"
    metrics_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nReporte global guardado en: {metrics_path}")

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena los modelos de mastitis."
    )

    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATASET,
    )

    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=PROJECT_ROOT / "src/data/artifacts",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=PROJECT_ROOT / "demo_reports",
    )

    parser.add_argument(
        "--feature-set",
        choices=["A", "B"],
        default="B",
        help=(
            "A: laboratorio (con conductividad). "
            "B: desplegable en la app (sin conductividad, pH obligatorio)."
        ),
    )

    parser.add_argument(
        "--use-dummy",
        action="store_true",
        help="Utiliza datos sintéticos generados automáticamente para pruebas rápidas."
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run(
        args.data,
        args.artifacts_dir,
        args.reports_dir,
        args.use_dummy,
        args.feature_set,
    )