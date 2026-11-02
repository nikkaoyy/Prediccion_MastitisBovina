"""Paridad entre model.json y scikit-learn, con tolerancia cero."""

import ast
import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier

from src.data.curation import load_curated_dataset
from src.data.dataValidation import DataValidator
from src.data.featureEngineer import FeaturePipelineBuilder
from src.export import tree_eval
from src.export.export_tree import build_model_json, find_discrepancies, serialize
from src.export.tree_eval import predict, transform
from src.paths import MODELS_DIR

MODEL_JSON = MODELS_DIR / "model.json"
PIPELINE = MODELS_DIR / "mastitis_decision_tree_A_pipeline.pkl"


@pytest.fixture(scope="module")
def model():
    return json.loads(MODEL_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pipeline():
    return joblib.load(PIPELINE)


@pytest.fixture(scope="module")
def X():
    validator = DataValidator("A")
    clean, _ = validator.validate_and_clean(load_curated_dataset())
    return clean.loc[:, list(validator.feature_columns)]


def _leaf_reached_by(model, record):
    vector = transform(model, record)
    nodes = model["tree"]["nodes"]
    node = nodes[0]
    while "class" not in node:
        value = tree_eval._to_float32(vector[node["feature"]])
        node = nodes[node["left"] if value <= node["threshold"] else node["right"]]
    return node


def test_paridad_en_las_209_filas(model, pipeline, X):
    assert len(X) == 209
    assert find_discrepancies(model, pipeline, X) == []


def test_paridad_detecta_una_sola_clase_cambiada(model, pipeline, X):
    broken = copy.deepcopy(model)
    record = X.iloc[0].to_dict()
    leaf = _leaf_reached_by(broken, record)
    leaf["class"] = 1 - leaf["class"]
    assert len(find_discrepancies(broken, pipeline, X.iloc[[0]])) == 1


def test_paridad_detecta_una_probabilidad_movida_en_el_cuarto_decimal(model, pipeline, X):
    broken = copy.deepcopy(model)
    leaf = _leaf_reached_by(broken, X.iloc[0].to_dict())
    leaf["probabilities"][1] += 1e-3
    assert len(find_discrepancies(broken, pipeline, X.iloc[[0]])) == 1


def test_paridad_detecta_una_mediana_alterada(model, pipeline, X):
    # Un cambio de imputación solo se ve si la fila usa ese valor.
    broken = copy.deepcopy(model)
    for feature in broken["preprocessing"]["numeric"]:
        if feature["name"] == "ph_leche":
            feature["median"] = 6.0  # cruza el corte del árbol
    sample = X.iloc[[0]].copy()
    sample["ph_leche"] = np.nan
    assert len(find_discrepancies(broken, pipeline, sample)) == 1


def test_transformacion_igual_a_scikit_learn(model, pipeline, X):
    expected = pipeline.named_steps["preprocessor"].transform(X)
    actual = np.array([transform(model, r) for r in X.to_dict(orient="records")])
    assert np.array_equal(actual, expected)


def test_paridad_con_faltantes_y_raza_desconocida(model, pipeline, X):
    sample = X.iloc[:12].copy().reset_index(drop=True)
    sample.loc[0:2, "raza"] = np.nan
    sample.loc[3:5, "raza"] = "Raza_Nueva"
    sample.loc[6:7, "ph_leche"] = np.nan
    sample.loc[8:9, "conductividad_leche_ms_cm"] = np.nan
    sample.loc[10:11, ["temperatura", "humedad"]] = np.nan
    assert find_discrepancies(model, pipeline, sample) == []


def test_paridad_en_arbol_profundo_con_etiquetas_barajadas(X):
    # Prueba mecánica del intérprete, no de desempeño: el árbol final tiene
    # pocos nodos y por sí solo ejercita poco el recorrido.
    labels = np.random.default_rng(0).integers(0, 2, size=len(X))
    deep = FeaturePipelineBuilder("A").build_pipeline(
        DecisionTreeClassifier(random_state=0, class_weight="balanced")
    )
    deep.fit(X, labels)
    assert deep.named_steps["classifier"].tree_.node_count > 100

    exported = build_model_json(deep, "A", {})
    roundtrip = json.loads(serialize(exported))
    assert find_discrepancies(roundtrip, deep, X) == []


def test_compara_en_float32_como_scikit_learn():
    # float32(0.1) = 0.10000000149...: queda por encima de este umbral aunque
    # el double 0.1 esté por debajo. scikit-learn va a la derecha.
    model = {
        "preprocessing": {
            "numeric": [{"name": "x", "median": 0.0, "mean": 0.0, "scale": 1.0}],
            "categorical": [],
        },
        "tree": {
            "nodes": [
                {"feature": 0, "threshold": 0.1000000005, "left": 1, "right": 2},
                {"class": 0, "probabilities": [1.0, 0.0]},
                {"class": 1, "probabilities": [0.0, 1.0]},
            ]
        },
    }
    assert predict(model, {"x": 0.1}) == (1, 1.0)


def test_json_versionado_corresponde_al_pkl_actual(model, pipeline):
    rebuilt = build_model_json(pipeline, model["feature_set"], model["provenance"])
    assert rebuilt == model


def test_json_es_autocontenido_y_pesa_kilobytes(model):
    assert MODEL_JSON.stat().st_size < 10 * 1024
    assert model["provenance"]["datos"] == "reales"
    assert model["provenance"]["rows"] == 209
    assert model["tree"]["classes"] == [0, 1]
    assert len(model["transformed_features"]) == 16

    for node in model["tree"]["nodes"]:
        assert ("class" in node) != ("threshold" in node)


def test_interprete_solo_usa_libreria_estandar():
    source = Path(tree_eval.__file__).read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    assert imported <= {"__future__", "math", "struct", "typing"}
