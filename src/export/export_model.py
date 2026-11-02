"""Entrena el Modelo B final y exporta los artefactos de despliegue.

Salidas en ``models/``:
  * ``model.onnx``           modelo completo (preprocesamiento + clasificador)
  * ``model_lite.json``      parámetros para evaluar en el cliente sin runtime nativo
  * ``manifest.json``        versión y hashes SHA-256 de los artefactos
  * ``model_card.json``      métricas OOF por finca, IC bootstrap y advertencias
  * ``parity_fixtures.json`` entradas/salidas esperadas para pruebas de paridad

Uso:  python -m src.export.export_model
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType, StringTensorType

from src.data.dataValidation import DataValidator
from src.export.lite_eval import predict_probability, risk_level
from src.models.LogisticalRegresion import LogisticRegressionModelTrainer
from src.models.evaluation import (
    cluster_bootstrap_ci,
    leave_one_farm_out,
    select_thresholds,
)

DEFAULT_DATASET = PROJECT_ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "models"
FEATURE_SET = "B"

DISCLAIMER = (
    "Estimación de riesgo de apoyo a la decisión. No es un diagnóstico y no "
    "sustituye la valoración veterinaria ni las pruebas confirmatorias (CMT)."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_dump(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_lite(pipeline, validator: DataValidator, thresholds: dict) -> dict:
    """Extrae del Pipeline ajustado los parámetros del modelo lite."""

    pre = pipeline.named_steps["preprocessor"]
    clf = pipeline.named_steps["classifier"]
    numeric = pre.named_transformers_["numeric"]
    categorical = pre.named_transformers_["categorical"]

    num_names = list(pre.transformers_[0][2])
    cat_names = list(pre.transformers_[1][2])
    imputer, scaler = numeric.named_steps["imputer"], numeric.named_steps["scaler"]
    cat_imputer = categorical.named_steps["imputer"]
    onehot = categorical.named_steps["onehot"]

    ranges = {
        name: list(DataValidator.CLINICAL_RANGES[name])
        for name in num_names
        if name in DataValidator.CLINICAL_RANGES
    }
    for binary in ("etapa_de_lactancia", "antecedentes_de_mastitis"):
        ranges[binary] = [0.0, 1.0]

    core = {
        "feature_set": FEATURE_SET,
        "algorithm": "logistic_regression",
        "numeric": [
            {
                "name": name,
                "median": float(imputer.statistics_[i]),
                "mean": float(scaler.mean_[i]),
                "scale": float(scaler.scale_[i]),
            }
            for i, name in enumerate(num_names)
        ],
        "categorical": [
            {
                "name": name,
                "fill_value": str(cat_imputer.statistics_[i]),
                "categories": [str(c) for c in onehot.categories_[i]],
            }
            for i, name in enumerate(cat_names)
        ],
        "coefficients": [float(c) for c in clf.coef_[0]],
        "intercept": float(clf.intercept_[0]),
        "thresholds": {
            "alto": float(thresholds["alto"]),
            "medio": float(thresholds["medio"]),
        },
        "required_inputs": ["ph_leche"],
        "ranges": ranges,
        "disclaimer": DISCLAIMER,
    }

    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    core["model_version"] = f"mastitis-B-lr-{digest[:8]}"

    return core


def export_onnx(pipeline, validator: DataValidator, path: Path) -> None:
    """Convierte el Pipeline a ONNX con una entrada por variable."""

    categorical = set(DataValidator.CATEGORICAL_COLUMNS)
    initial_types = [
        (
            name,
            StringTensorType([None, 1])
            if name in categorical
            else FloatTensorType([None, 1]),
        )
        for name in validator.feature_columns
    ]

    # skl2onnx no convierte SimpleImputer sobre texto. En el ONNX la raza es
    # obligatoria (la app no permite enviarla vacía); el relleno de raza nula
    # solo existe en model_lite.json y en el pipeline de scikit-learn.
    export_pipeline = copy.deepcopy(pipeline)
    cat_pipeline = export_pipeline.named_steps["preprocessor"].named_transformers_[
        "categorical"
    ]
    cat_pipeline.steps = [s for s in cat_pipeline.steps if s[0] != "imputer"]

    clf = export_pipeline.named_steps["classifier"]
    onnx_model = convert_sklearn(
        export_pipeline,
        initial_types=initial_types,
        options={id(clf): {"zipmap": False}},
        target_opset={"": 17, "ai.onnx.ml": 3},
    )
    path.write_bytes(onnx_model.SerializeToString())


def build_drift_baseline(X: pd.DataFrame, bins: int = 10) -> dict:
    """Distribución de referencia para monitorear data drift (PSI) en servidor."""

    numeric: dict[str, dict] = {}

    for column in X.columns:
        if column in DataValidator.CATEGORICAL_COLUMNS:
            continue

        values = X[column].dropna().to_numpy(dtype=float)
        edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)))

        if len(edges) < 3:  # variable casi binaria: usar los valores distintos
            categories = np.unique(values)
            proportions = [float((values == c).mean()) for c in categories]
            numeric[column] = {"kind": "discrete", "values": categories.tolist(),
                               "proportions": proportions}
            continue

        inner = edges[1:-1]
        counts = np.bincount(np.searchsorted(inner, values, side="right"),
                             minlength=len(edges) - 1)
        numeric[column] = {
            "kind": "continuous",
            "edges": inner.tolist(),
            "proportions": (counts / counts.sum()).tolist(),
        }

    categorical = {
        column: X[column].value_counts(normalize=True).to_dict()
        for column in X.columns
        if column in DataValidator.CATEGORICAL_COLUMNS
    }

    return {"rows": int(len(X)), "numeric": numeric, "categorical": categorical}


def _clean(value):
    if isinstance(value, str):
        return value
    return None if pd.isna(value) else float(value)


def build_fixtures(
    pipeline, X: pd.DataFrame, sklearn_prob: np.ndarray, seed: int = 7
) -> list[dict]:
    """Casos de paridad: todo el dataset + casos límite (faltantes y raza nueva).

    Las probabilidades esperadas salen del Pipeline de scikit-learn.
    """

    cases = [
        {
            "input": {k: _clean(v) for k, v in X.iloc[i].items()},
            "probability": float(sklearn_prob[i]),
        }
        for i in range(len(X))
    ]

    rng = np.random.default_rng(seed)
    edge = X.iloc[rng.choice(len(X), size=12, replace=False)].copy().reset_index(drop=True)
    edge.loc[0:2, "raza"] = np.nan  # raza faltante -> se rellena con la moda
    edge.loc[3:5, "raza"] = "Raza_Nueva"  # categoría desconocida -> todo ceros
    edge.loc[6:7, "volumen_de_leche"] = np.nan
    edge.loc[8:9, ["humedad", "temperatura"]] = np.nan
    edge.loc[10:11, "edad"] = np.nan
    edge_prob = pipeline.predict_proba(edge)[:, 1]
    for i in range(len(edge)):
        cases.append(
            {
                "input": {k: _clean(v) for k, v in edge.iloc[i].items()},
                "probability": float(edge_prob[i]),
                "edge": True,
            }
        )

    return cases


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--mobile-assets",
        type=Path,
        default=PROJECT_ROOT / "mobile" / "assets",
        help="Copia model_lite.json aquí (solo si --output es el directorio por defecto).",
    )
    args = parser.parse_args(argv)

    validator = DataValidator(feature_set=FEATURE_SET)
    clean, quality = validator.validate_and_clean(pd.read_csv(args.data))

    X = clean.loc[:, list(validator.feature_columns)]
    y = clean[DataValidator.TARGET_COLUMN].astype(int)
    groups = clean[DataValidator.GROUP_COLUMN]

    trainer = LogisticRegressionModelTrainer(
        n_splits=5, random_state=42, n_jobs=1, feature_set=FEATURE_SET
    )
    trainer.fit(X, y, groups)
    evaluation = trainer.evaluate_grouped_cv(X, y, groups)
    thresholds = select_thresholds(evaluation.y_true, evaluation.y_probability)

    pipeline = trainer.best_estimator_  # refit sobre todos los datos
    lite = build_lite(pipeline, validator, thresholds)

    args.output.mkdir(parents=True, exist_ok=True)
    onnx_path = args.output / "model.onnx"
    lite_path = args.output / "model_lite.json"
    export_onnx(pipeline, validator, onnx_path)
    _json_dump(lite_path, lite)

    sklearn_prob = pipeline.predict_proba(X)[:, 1]
    fixtures = build_fixtures(pipeline, X, sklearn_prob)
    fixtures_path = args.output / "parity_fixtures.json"
    _json_dump(
        fixtures_path,
        {
            "model_version": lite["model_version"],
            "tolerance": 1e-5,
            "cases": fixtures,
        },
    )

    oof_prob = evaluation.y_probability
    y_arr = evaluation.y_true
    level_counts = {
        "positivos_en_bajo": int(((oof_prob < thresholds["medio"]) & (y_arr == 1)).sum()),
        "sanos_en_bajo": int(((oof_prob < thresholds["medio"]) & (y_arr == 0)).sum()),
        "sanos_en_medio": int(
            ((oof_prob >= thresholds["medio"]) & (oof_prob < thresholds["alto"]) & (y_arr == 0)).sum()
        ),
        "positivos_en_medio": int(
            ((oof_prob >= thresholds["medio"]) & (oof_prob < thresholds["alto"]) & (y_arr == 1)).sum()
        ),
        "sanos_en_alto": int(((oof_prob >= thresholds["alto"]) & (y_arr == 0)).sum()),
        "positivos_en_alto": int(((oof_prob >= thresholds["alto"]) & (y_arr == 1)).sum()),
    }

    lofo = leave_one_farm_out(pipeline, X, y, groups)
    lofo.pop("y_probability")

    # Comparador: regresión logística solo con pH (mismo esquema de validación).
    from src.data.featureEngineer import FeaturePipelineBuilder
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_predict
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    ph_model = Pipeline([("scaler", StandardScaler()),
                         ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000))])
    ph_prob = cross_val_predict(ph_model, X[["ph_leche"]], y, groups=groups,
                                cv=GroupKFold(n_splits=5), method="predict_proba")[:, 1]
    ph_only = cluster_bootstrap_ci(y.to_numpy(), ph_prob, groups, 0.5)
    ph_only = {k: round(v["point"], 4) for k, v in ph_only.items()}

    card = {
        "model_version": lite["model_version"],
        "feature_set": FEATURE_SET,
        "features": list(validator.feature_columns),
        "training_rows": quality.row_count,
        "farms": quality.unique_farms,
        "thresholds_oof": thresholds,
        "oof_counts_by_risk_level": level_counts,
        "grouped_cv_5fold": evaluation.aggregate_metrics,
        "bootstrap_ci_by_farm_at_alert_threshold": cluster_bootstrap_ci(
            evaluation.y_true, evaluation.y_probability, groups, thresholds["alto"]
        ),
        "leave_one_farm_out": lofo,
        "comparador_solo_ph_logistica_groupkfold5_umbral_0.5": ph_only,
        "warnings": [
            "Los umbrales alto/medio se eligieron y se reportan sobre las mismas predicciones "
            "OOF: las métricas a esos umbrales son optimistas. El IC bootstrap fija el umbral y "
            "remuestrea solo 6 fincas, por lo que subestima la incertidumbre.",
            "Una regresión logística solo con pH obtiene un desempeño igual o mejor que el "
            "Modelo B de 9 variables (ver comparador); las variables adicionales no están "
            "justificadas empíricamente con esta muestra.",
            "Datos de 6 fincas, una sola medición por animal: no hay validación externa.",
            "El pH separa casi perfectamente las clases (posible circularidad con la "
            "verdad de referencia CMT); documentar el protocolo antes de afirmar generalización.",
            DISCLAIMER,
        ],
    }
    _json_dump(args.output / "model_card.json", card)

    if args.output == DEFAULT_OUTPUT and args.mobile_assets.parent.is_dir():
        args.mobile_assets.mkdir(exist_ok=True)
        (args.mobile_assets / "model_lite.json").write_bytes(lite_path.read_bytes())

    drift_path = args.output / "drift_baseline.json"
    _json_dump(drift_path, build_drift_baseline(X))

    manifest = {
        "model_version": lite["model_version"],
        "files": {
            "model.onnx": _sha256(onnx_path),
            "model_lite.json": _sha256(lite_path),
            "drift_baseline.json": _sha256(drift_path),
        },
    }
    _json_dump(args.output / "manifest.json", manifest)

    # Autocomprobación rápida de paridad lite vs sklearn.
    worst = max(
        abs(predict_probability(lite, row.to_dict()) - p)
        for (_, row), p in zip(X.iterrows(), sklearn_prob)
    )
    print(f"Versión: {lite['model_version']}")
    print(f"Umbrales: {lite['thresholds']}")
    print(f"Máx. diferencia lite vs sklearn: {worst:.2e}")
    print(f"Recall OOF: {evaluation.aggregate_metrics['recall']:.3f}")

    return manifest


if __name__ == "__main__":
    main()
