"""Compara el modelo completo (A) con el modelo de campo (CAMPO).

Misma validación para ambos: GroupKFold(5) por finca, búsqueda anidada y
preprocesamiento dentro del Pipeline. Las métricas y la importancia por
permutación se calculan solo sobre la finca de prueba de cada pliegue.

Uso:  python -m src.models.compare_variants
Salidas: artifacts/reports/comparacion_variantes.json y
docs/TABLA_TRANSPARENCIA_METRICAS.md, que se genera a partir de ese JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupKFold

from src.data.curation import load_curated_dataset
from src.data.dataValidation import DataValidator
from src.models.DecisionTreeTraining import DecisionTreeModelTrainer
from src.models.LogisticalRegresion import LogisticRegressionModelTrainer
from src.models.RandomForest import RandomForestModelTrainer
from src.paths import DATASET_PATH, PROJECT_ROOT, REPORTS_DIR

N_SPLITS = 5
RANDOM_STATE = 42
PERMUTATION_REPEATS = 20

VARIANTS = {"A": "Completo", "CAMPO": "Campo"}
ALGORITHMS = {
    "decision_tree": ("Árbol de decisión", DecisionTreeModelTrainer),
    "random_forest": ("Random Forest", RandomForestModelTrainer),
    "logistic_regression": ("Regresión logística", LogisticRegressionModelTrainer),
}
TABLE_PATH = PROJECT_ROOT / "docs" / "TABLA_TRANSPARENCIA_METRICAS.md"
SMALL_FARM = "Finca_6"
UNCHANGED_BELOW = 0.005  # |ΔPR-AUC| menor a esto se lee como "sin cambio"

METRICS = ("f1", "precision", "recall", "pr_auc")
METRIC_LABELS = {
    "f1": "F1",
    "precision": "Precision",
    "recall": "Recall",
    "pr_auc": "PR-AUC",
}


def _fold_metrics(y: np.ndarray, pred: np.ndarray, prob: np.ndarray) -> dict[str, float]:
    return {
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y, prob)),
    }


def _confusion(y: np.ndarray, pred: np.ndarray) -> dict[str, int]:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def evaluate_variant(
    trainer_class: type,
    feature_set: str,
    clean: pd.DataFrame,
) -> dict[str, Any]:
    """Validación anidada por finca de un algoritmo con un conjunto de variables."""

    validator = DataValidator(feature_set=feature_set)
    X = clean.loc[:, list(validator.feature_columns)]
    y = clean[DataValidator.TARGET_COLUMN].astype(int)
    groups = clean[DataValidator.GROUP_COLUMN]

    trainer = trainer_class(
        n_splits=N_SPLITS, random_state=RANDOM_STATE, feature_set=feature_set
    )

    folds: list[dict[str, Any]] = []
    importance_by_fold: list[dict[str, float]] = []
    prediction_by_row = np.zeros(len(X), dtype=int)

    splitter = GroupKFold(n_splits=N_SPLITS)
    for fold, (train, test) in enumerate(splitter.split(X, y, groups), start=1):
        inner_splits = min(N_SPLITS, int(groups.iloc[train].nunique()))
        search = trainer._build_search(n_splits=inner_splits)
        search.fit(X.iloc[train], y.iloc[train], groups=groups.iloc[train])

        pipeline = search.best_estimator_
        y_test = y.iloc[test].to_numpy()
        pred = pipeline.predict(X.iloc[test]).astype(int)
        prob = pipeline.predict_proba(X.iloc[test])[:, 1]
        prediction_by_row[test] = pred

        folds.append(
            {
                "fold": fold,
                "test_farms": sorted(groups.iloc[test].unique()),
                "test_rows": int(len(test)),
                "prevalence": float(y_test.mean()),
                "best_params": {
                    key.removeprefix("classifier__"): value
                    for key, value in search.best_params_.items()
                },
                **_fold_metrics(y_test, pred, prob),
            }
        )

        permuted = permutation_importance(
            pipeline,
            X.iloc[test],
            y_test,
            scoring="average_precision",
            n_repeats=PERMUTATION_REPEATS,
            random_state=RANDOM_STATE,
        )
        importance_by_fold.append(dict(zip(X.columns, permuted.importances_mean)))

    summary = {
        metric: {
            "mean": float(np.mean([fold[metric] for fold in folds])),
            "sd": float(np.std([fold[metric] for fold in folds], ddof=1)),
        }
        for metric in METRICS
    }

    importance = pd.DataFrame(importance_by_fold)
    small_farm = groups.eq(SMALL_FARM).to_numpy()

    return {
        "summary": summary,
        "folds": folds,
        "importance": {
            column: {
                "mean": float(importance[column].mean()),
                "sd": float(importance[column].std(ddof=1)),
            }
            for column in importance.columns
        },
        "confusion_oof": _confusion(y.to_numpy(), prediction_by_row),
        "confusion_small_farm": _confusion(
            y.to_numpy()[small_farm], prediction_by_row[small_farm]
        ),
    }


def run_comparison(data_path: Path = DATASET_PATH) -> dict[str, Any]:
    clean, quality = DataValidator("A").validate_and_clean(load_curated_dataset(data_path))

    results = {
        name: {
            variant: evaluate_variant(trainer_class, variant, clean)
            for variant in VARIANTS
        }
        for name, (_, trainer_class) in ALGORITHMS.items()
    }

    return {
        "datos": "reales",
        "dataset": data_path.name,
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "rows": quality.row_count,
        "farms": quality.unique_farms,
        "separation": {
            column: {
                "max_sanas": float(clean.loc[clean["mastitis"] == 0, column].max()),
                "min_mastitis": float(clean.loc[clean["mastitis"] == 1, column].min()),
            }
            for column in ("ph_leche", "conductividad_leche_ms_cm")
        },
        "validation": "GroupKFold(5) por finca, búsqueda anidada optimizando F1",
        "importance_method": (
            f"Permutación sobre la finca de prueba, ΔPR-AUC, {PERMUTATION_REPEATS} repeticiones"
        ),
        "scikit_learn": sklearn.__version__,
        "results": results,
    }


def _num(value: float, decimals: int = 3) -> str:
    text = f"{round(value, decimals) + 0.0:.{decimals}f}"
    return text.replace(".", ",")


def _render_summary(results: dict[str, Any]) -> list[str]:
    labels = [METRIC_LABELS[metric] for metric in METRICS]
    lines = [
        "| Modelo | Variables | " + " | ".join(labels) + " |",
        "|---|---|" + "---|" * len(METRICS),
    ]

    for name, (label, _) in ALGORITHMS.items():
        for variant, variant_label in VARIANTS.items():
            summary = results[name][variant]["summary"]
            cells = [
                f"{_num(summary[m]['mean'])} ± {_num(summary[m]['sd'])}" for m in METRICS
            ]
            n_features = len(results[name][variant]["importance"])
            lines.append(
                f"| {label} | {variant_label} ({n_features}) | " + " | ".join(cells) + " |"
            )

    return lines


def _render_folds(results: dict[str, Any]) -> list[str]:
    lines = [
        "| Modelo | Variables | Métrica | P1 | P2 | P3 | P4 | P5 | Promedio | DE |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for name, (label, _) in ALGORITHMS.items():
        for variant, variant_label in VARIANTS.items():
            data = results[name][variant]
            for metric in METRICS:
                values = [_num(fold[metric]) for fold in data["folds"]]
                lines.append(
                    f"| {label} | {variant_label} | {METRIC_LABELS[metric]} | "
                    + " | ".join(values)
                    + f" | {_num(data['summary'][metric]['mean'])}"
                    + f" | {_num(data['summary'][metric]['sd'])} |"
                )

    return lines


def _reading(full: float, field: float | None) -> str:
    if field is None:
        return "Perdió (excluida)"
    if abs(field - full) < UNCHANGED_BELOW:
        return "Sin cambio"
    return "Ganó" if field > full else "Perdió"


def _render_importance(data: dict[str, Any]) -> list[str]:
    full = data["A"]["importance"]
    field = data["CAMPO"]["importance"]

    def sort_key(column: str) -> tuple[float, float, str]:
        field_value = field[column]["mean"] if column in field else float("-inf")
        return (-field_value, -full[column]["mean"], column)

    lines = [
        "| Variable | Completo | Campo | Lectura |",
        "|---|---|---|---|",
    ]

    for column in sorted(full, key=sort_key):
        full_value = full[column]["mean"]
        field_value = field[column]["mean"] if column in field else None
        field_text = "—" if field_value is None else _num(field_value)
        lines.append(
            f"| `{column}` | {_num(full_value)} | {field_text} | "
            f"{_reading(full_value, field_value)} |"
        )

    return lines


def _render_small_farm(results: dict[str, Any]) -> list[str]:
    lines = [
        "| Modelo | Variables | VP | FP | VN | FN |",
        "|---|---|---|---|---|---|",
    ]

    for name, (label, _) in ALGORITHMS.items():
        for variant, variant_label in VARIANTS.items():
            c = results[name][variant]["confusion_small_farm"]
            lines.append(
                f"| {label} | {variant_label} | {c['tp']} | {c['fp']} | {c['tn']} | {c['fn']} |"
            )

    return lines


def render_markdown(report: dict[str, Any]) -> str:
    """Genera la tabla lista para pegar; todas las cifras salen del reporte."""

    results = report["results"]
    folds = results["decision_tree"]["A"]["folds"]
    ph = report["separation"]["ph_leche"]
    conductivity = report["separation"]["conductividad_leche_ms_cm"]
    mean_prevalence = float(np.mean([fold["prevalence"] for fold in folds]))

    fold_legend = [
        f"- **P{fold['fold']}:** {' + '.join(fold['test_farms'])} "
        f"(n = {fold['test_rows']}, prevalencia {_num(fold['prevalence'] * 100, 1)} %)"
        for fold in folds
    ]

    importance_sections: list[str] = []
    for name, (label, _) in ALGORITHMS.items():
        importance_sections += [f"### {label}", "", *_render_importance(results[name]), ""]

    lines = [
        "# Tabla de transparencia de métricas",
        "",
        "Generado por `python -m src.models.compare_variants`. No editar a mano.",
        "",
        f"**Datos:** reales, `{report['dataset']}`, {report['rows']} filas, "
        f"{report['farms']} fincas (SHA-256 `{report['dataset_sha256'][:12]}`). "
        "Ninguna cifra sale de datos sintéticos.",
        "",
        f"**Validación:** {report['validation']}. El preprocesamiento se ajusta dentro de "
        "cada pliegue de entrenamiento. Umbral de clasificación 0,5. El promedio y la "
        "desviación estándar (DE, muestral, n = 5) son entre pliegues.",
        "",
        "**Variables.** Completo (12): las 12 predictoras del conjunto A, con pH y "
        "conductividad. Campo (8): `edad`, `raza`, `numero_de_partos`, `volumen_de_leche`, "
        "`etapa_de_lactancia`, `frecuencia_de_ordeno`, `estado_de_vacunacion` y "
        "`antecedentes_de_mastitis`.",
        "",
        "## Modelo completo frente a modelo de campo",
        "",
        *_render_summary(results),
        "",
        f"Referencia para PR-AUC: un clasificador sin información obtiene aproximadamente "
        f"la prevalencia, {_num(mean_prevalence)} en promedio entre pliegues.",
        "",
        "## Resultados por pliegue",
        "",
        *fold_legend,
        "",
        *_render_folds(results),
        "",
        "## Importancia de variables",
        "",
        f"{report['importance_method']}, promediada entre pliegues y por variable original "
        f"(`raza` se permuta completa). \"Ganó\" o \"Perdió\" compara campo con completo; "
        f"una diferencia menor que {_num(UNCHANGED_BELOW)} se lee como \"Sin cambio\". "
        "Con variables correlacionadas, como pH y conductividad o edad y partos, la "
        "permutación reparte la importancia entre ellas y puede subestimar cada una.",
        "",
        *importance_sections,
        "## Filas de Finca 6 (n = 8, 1 positiva)",
        "",
        "Predicciones fuera de pliegue. Su conductividad se imputa con la mediana de "
        "entrenamiento, que cae en el rango de mastitis (`docs/CURACION_DATOS.md`).",
        "",
        *_render_small_farm(results),
        "",
        "## Cómo leer esta tabla",
        "",
        f"- **Separación total por pH en esta muestra.** Máximo en sanas {_num(ph['max_sanas'], 2)}, "
        f"mínimo con mastitis {_num(ph['min_mastitis'], 2)}. Con conductividad: "
        f"{_num(conductivity['max_sanas'], 2)} y {_num(conductivity['min_mastitis'], 2)}. "
        "Las métricas del modelo completo reflejan esa separación y no demuestran "
        "generalización: puede ser un efecto biológico o una circularidad con la verdad "
        "de referencia.",
        "- **Dos variables de campo no aportan.** `frecuencia_de_ordeno` es constante y "
        "`estado_de_vacunacion` vale 1 en una sola fila de 209. Se entrenó con las ocho; "
        "retirarlas es decisión de los autores.",
        "- **`signos sanitarios`.** No existe esa columna. Se tomó `antecedentes_de_mastitis`, "
        "la única predictora restante del animal que no requiere instrumento. Debe confirmarse.",
        "- **Solo 6 fincas.** P5 agrupa dos fincas y la DE se calcula sobre 5 pliegues. "
        "No hay validación externa.",
        "",
    ]

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATASET_PATH)
    parser.add_argument(
        "--output", type=Path, default=REPORTS_DIR / "comparacion_variantes.json"
    )
    parser.add_argument("--table", type=Path, default=TABLE_PATH)
    args = parser.parse_args(argv)

    report = run_comparison(args.data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.table.write_text(render_markdown(report), encoding="utf-8")

    print(f"Reporte: {args.output}")
    print(f"Tabla: {args.table}")
    return report


if __name__ == "__main__":
    main()
