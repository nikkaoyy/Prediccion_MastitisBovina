"""Exporta el Pipeline del árbol de decisión a ``model.json``.

El JSON es autocontenido: lleva imputación, escalado, one-hot y la estructura
del árbol. Se interpreta con ``src/export/tree_eval.py`` o con su equivalente
en el cliente, sin scikit-learn ni ONNX.

Uso:  python -m src.export.export_tree
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn

from src.data.curation import load_curated_dataset
from src.data.dataValidation import DataValidator
from src.export.tree_eval import predict
from src.paths import DATASET_PATH, MODELS_DIR

SCHEMA_VERSION = 1
CLASS_LABELS = ["sana", "mastitis"]
PROBABILITY_DECIMALS = 4


def _export_nodes(classifier) -> list[dict[str, Any]]:
    tree = classifier.tree_
    classes = [int(label) for label in classifier.classes_]
    nodes: list[dict[str, Any]] = []

    for index in range(tree.node_count):
        left = int(tree.children_left[index])

        if left == -1:
            probabilities = [float(p) for p in tree.value[index][0]]
            # Igual que predict(): ante un empate gana la primera clase.
            winner = probabilities.index(max(probabilities))
            nodes.append({"class": classes[winner], "probabilities": probabilities})
        else:
            nodes.append(
                {
                    "feature": int(tree.feature[index]),
                    "threshold": float(tree.threshold[index]),
                    "left": left,
                    "right": int(tree.children_right[index]),
                }
            )

    return nodes


def build_model_json(pipeline, feature_set: str, provenance: dict[str, Any]) -> dict[str, Any]:
    """Traduce un Pipeline ajustado a un diccionario serializable."""

    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]

    numeric = preprocessor.named_transformers_["numeric"]
    categorical = preprocessor.named_transformers_["categorical"]
    imputer = numeric.named_steps["imputer"]
    scaler = numeric.named_steps["scaler"]
    category_imputer = categorical.named_steps["imputer"]
    onehot = categorical.named_steps["onehot"]

    numeric_names = list(preprocessor.transformers_[0][2])
    categorical_names = list(preprocessor.transformers_[1][2])

    core = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": "decision_tree",
        "feature_set": feature_set,
        "input_features": numeric_names + categorical_names,
        "preprocessing": {
            "numeric": [
                {
                    "name": name,
                    "median": float(imputer.statistics_[i]),
                    "mean": float(scaler.mean_[i]),
                    "scale": float(scaler.scale_[i]),
                }
                for i, name in enumerate(numeric_names)
            ],
            "categorical": [
                {
                    "name": name,
                    "fill_value": str(category_imputer.statistics_[i]),
                    "categories": [str(c) for c in onehot.categories_[i]],
                }
                for i, name in enumerate(categorical_names)
            ],
        },
        "transformed_features": [
            str(name) for name in preprocessor.get_feature_names_out()
        ],
        "tree": {
            "comparison": "float32(value) <= threshold -> left",
            "classes": [int(label) for label in classifier.classes_],
            "class_labels": CLASS_LABELS,
            "nodes": _export_nodes(classifier),
        },
    }

    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    return {
        "model_version": f"mastitis-{feature_set}-dt-{digest[:8]}",
        **core,
        "provenance": provenance,
    }


def _rounded(probability: float) -> float:
    return round(float(probability), PROBABILITY_DECIMALS)


def find_discrepancies(model: dict[str, Any], pipeline, X: pd.DataFrame) -> list[dict[str, Any]]:
    """Filas en las que el JSON y scikit-learn difieren en clase o probabilidad.

    La tolerancia es cero; la probabilidad se compara redondeada a 4 decimales.
    """

    classes = pipeline.predict(X)
    probabilities = pipeline.predict_proba(X)[:, 1]
    discrepancies = []

    for position, record in enumerate(X.to_dict(orient="records")):
        json_class, json_probability = predict(model, record)
        expected_class = int(classes[position])
        expected_probability = _rounded(probabilities[position])

        if (
            json_class != expected_class
            or _rounded(json_probability) != expected_probability
        ):
            discrepancies.append(
                {
                    "position": position,
                    "json": (json_class, _rounded(json_probability)),
                    "sklearn": (expected_class, expected_probability),
                }
            )

    return discrepancies


def serialize(model: dict[str, Any]) -> str:
    """JSON compacto; ``allow_nan=False`` evita literales que un cliente no lee."""

    return (
        json.dumps(model, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    )


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", default="A")
    parser.add_argument("--data", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, default=MODELS_DIR / "model.json")
    args = parser.parse_args(argv)

    feature_set = args.feature_set.upper()
    pipeline_path = MODELS_DIR / f"mastitis_decision_tree_{feature_set}_pipeline.pkl"
    pipeline = joblib.load(pipeline_path)

    validator = DataValidator(feature_set=feature_set)
    clean, quality = validator.validate_and_clean(load_curated_dataset(args.data))
    X = clean.loc[:, list(validator.feature_columns)]

    model = build_model_json(
        pipeline,
        feature_set,
        {
            "datos": "reales",
            "dataset": args.data.name,
            "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
            "rows": quality.row_count,
            "farms": quality.unique_farms,
            "scikit_learn": sklearn.__version__,
            "aviso": (
                "Estimación de riesgo de apoyo a la decisión. No es un diagnóstico "
                "y no sustituye la valoración veterinaria ni el CMT."
            ),
        },
    )

    discrepancies = find_discrepancies(model, pipeline, X)
    if discrepancies:
        raise ValueError(f"Paridad rota en {len(discrepancies)} filas: {discrepancies[:3]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialize(model), encoding="utf-8")

    print(f"Versión: {model['model_version']}")
    print(f"Coincidencias: {len(X)}/{len(X)}")
    print(f"Nodos: {len(model['tree']['nodes'])}")
    print(f"Tamaño: {args.output.stat().st_size / 1024:.2f} KB")
    print(f"Campos: {sorted(model)}")
    print(f"Archivo: {args.output}")

    return model


if __name__ == "__main__":
    main()
