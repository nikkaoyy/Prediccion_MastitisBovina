"""Modelo de campo y tabla de transparencia."""

import json

import pytest
from sklearn.model_selection import GroupKFold

from src.data.curation import load_curated_dataset
from src.data.dataValidation import FEATURE_SETS, DataValidator
from src.models.compare_variants import (
    ALGORITHMS,
    METRICS,
    TABLE_PATH,
    VARIANTS,
    evaluate_variant,
    render_markdown,
)
from src.models.DecisionTreeTraining import DecisionTreeModelTrainer
from src.paths import REPORTS_DIR


@pytest.fixture(scope="module")
def report():
    path = REPORTS_DIR / "comparacion_variantes.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_campo_tiene_ocho_variables_sin_instrumento():
    campo = FEATURE_SETS["CAMPO"]
    assert len(campo) == 8
    assert not {"ph_leche", "conductividad_leche_ms_cm", "humedad", "temperatura"} & set(campo)
    assert {"frecuencia_de_ordeno", "estado_de_vacunacion"} <= set(campo)
    assert set(campo) < set(FEATURE_SETS["A"])


def test_reporte_cubre_todos_los_modelos_y_pliegues(report):
    assert report["datos"] == "reales"
    assert report["rows"] == 209

    for name in ALGORITHMS:
        for variant in VARIANTS:
            data = report["results"][name][variant]
            assert len(data["folds"]) == 5
            assert set(data["summary"]) == set(METRICS)
            confusion = data["confusion_oof"]
            assert sum(confusion.values()) == 209
            assert sum(data["confusion_small_farm"].values()) == 8


def test_modelo_de_campo_no_ve_ph_ni_conductividad(report):
    for name in ALGORITHMS:
        assert "ph_leche" not in report["results"][name]["CAMPO"]["importance"]
        assert "conductividad_leche_ms_cm" not in report["results"][name]["CAMPO"]["importance"]


def test_variables_constantes_no_aportan_en_ningun_modelo(report):
    for name in ALGORITHMS:
        importance = report["results"][name]["CAMPO"]["importance"]
        assert importance["frecuencia_de_ordeno"]["mean"] == 0
        assert abs(importance["estado_de_vacunacion"]["mean"]) < 1e-3


def test_ninguna_finca_cruza_entrenamiento_y_prueba():
    clean, _ = DataValidator("A").validate_and_clean(load_curated_dataset())
    groups = clean["finca"]
    for train, test in GroupKFold(n_splits=5).split(clean, clean["mastitis"], groups):
        assert not set(groups.iloc[train]) & set(groups.iloc[test])


def test_resultado_es_reproducible(report):
    clean, _ = DataValidator("A").validate_and_clean(load_curated_dataset())
    fresh = evaluate_variant(DecisionTreeModelTrainer, "CAMPO", clean)
    stored = report["results"]["decision_tree"]["CAMPO"]
    assert fresh["summary"] == stored["summary"]
    assert fresh["confusion_oof"] == stored["confusion_oof"]


def test_tabla_versionada_coincide_con_el_reporte(report):
    assert TABLE_PATH.read_text(encoding="utf-8") == render_markdown(report)


def test_tabla_tiene_una_fila_por_modelo_y_declara_los_datos(report):
    text = TABLE_PATH.read_text(encoding="utf-8")
    assert "reales" in text and "209 filas" in text
    summary = text.split("## Modelo completo")[1].split("## Resultados")[0]
    rows = [line for line in summary.splitlines() if line.startswith("| ") and "±" in line]
    assert len(rows) == 6
