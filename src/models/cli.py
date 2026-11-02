"""Punto de entrada común: ``python -m src.models.<modelo>``.

Entrena con GroupKFold por finca sobre el dataset real curado, persiste el
Pipeline y escribe un reporte JSON, siempre bajo ``artifacts/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import sklearn
from sklearn.model_selection import GroupKFold, ParameterGrid

from src.data.curation import load_curated_dataset
from src.data.dataValidation import FEATURE_SETS, DataValidator
from src.paths import ARTIFACTS_DIR, DATASET_PATH, MODELS_SUBDIR, REPORTS_SUBDIR


def _count_fits(combinations: int, inner_splits: list[int], n_splits: int) -> int:
    """Ajustes totales: búsqueda final + búsqueda anidada, cada una con su refit."""

    final_search = combinations * n_splits + 1
    nested_search = sum(combinations * splits + 1 for splits in inner_splits)
    return final_search + nested_search


def run_training(
    trainer_class: type,
    model_name: str,
    argv: list[str] | None = None,
) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=f"Entrena {model_name} por finca.")
    parser.add_argument("--data", type=Path, default=DATASET_PATH)
    parser.add_argument("--artifacts-dir", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument(
        "--feature-set", choices=sorted(FEATURE_SETS), default="A"
    )
    args = parser.parse_args(argv)

    feature_set = args.feature_set
    validator = DataValidator(feature_set=feature_set)
    clean, quality = validator.validate_and_clean(load_curated_dataset(args.data))

    X = clean.loc[:, list(validator.feature_columns)]
    y = clean[DataValidator.TARGET_COLUMN].astype(int)
    groups = clean[DataValidator.GROUP_COLUMN]

    trainer = trainer_class(n_splits=5, random_state=42, feature_set=feature_set)
    trainer.fit(X, y, groups)
    evaluation = trainer.evaluate_grouped_cv(X, y, groups)

    stem = f"mastitis_{model_name}_{feature_set}"
    model_path = trainer.persist_model(
        args.artifacts_dir / MODELS_SUBDIR / f"{stem}_pipeline.pkl"
    )

    splits = list(GroupKFold(n_splits=trainer.n_splits).split(X, y, groups))
    test_farms = [sorted(groups.iloc[test].unique()) for _, test in splits]
    inner_splits = [
        min(trainer.n_splits, int(groups.iloc[train].nunique()))
        for train, _ in splits
    ]
    combinations = len(ParameterGrid(trainer.param_grid))

    folds = [
        {**fold, "test_farms": farms}
        for fold, farms in zip(evaluation.fold_metrics, test_farms)
    ]

    report = {
        "datos": "reales",
        "dataset": args.data.name,
        "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "rows": quality.row_count,
        "farms": quality.unique_farms,
        "model": model_name,
        "feature_set": feature_set,
        "features": list(validator.feature_columns),
        "validation": "GroupKFold(5) por finca, búsqueda anidada",
        "combinations": combinations,
        "fits": _count_fits(combinations, inner_splits, trainer.n_splits),
        "best_params": trainer.best_params_,
        "best_inner_f1": trainer.best_score_,
        "folds": folds,
        "aggregate_oof": evaluation.aggregate_metrics,
        "confusion_matrix_oof": evaluation.confusion_matrix,
        "scikit_learn": sklearn.__version__,
    }

    report_path = args.artifacts_dir / REPORTS_SUBDIR / f"entrenamiento_{stem}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Modelo: {model_name} | conjunto {feature_set} | datos reales: {args.data.name}")
    print(f"Combinaciones: {combinations} | ajustes: {report['fits']}")
    print(f"Mejores parámetros: {trainer.best_params_}")
    for fold in folds:
        print(
            f"Pliegue {fold['fold']} {'+'.join(fold['test_farms'])} "
            f"(n={fold['test_rows']}): F1 {fold['f1']:.4f}"
        )
    print(f"Modelo: {model_path}")
    print(f"Reporte: {report_path}")

    return report
