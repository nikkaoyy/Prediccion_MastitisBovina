"""Rutas ancladas, grids podados y artefactos persistidos."""

import json
import subprocess
import sys

import joblib
import pytest
from sklearn.model_selection import ParameterGrid

from src.data.curation import load_curated_dataset
from src.data.dataValidation import DataValidator
from src.models.DecisionTreeTraining import DecisionTreeModelTrainer
from src.models.LogisticalRegresion import LogisticRegressionModelTrainer
from src.models.RandomForest import RandomForestModelTrainer
from src.paths import DATASET_PATH, MODELS_DIR, PROJECT_ROOT, REPORTS_DIR

MODELOS = ("decision_tree", "random_forest", "logistic_regression")
MODULOS = {
    "DecisionTreeTraining": "decision_tree",
    "LogisticalRegresion": "logistic_regression",
    "RandomForest": "random_forest",
}


def test_rutas_ancladas_a_la_raiz_del_repo():
    assert (PROJECT_ROOT / "main.py").is_file()
    assert DATASET_PATH.is_file()
    assert MODELS_DIR.is_relative_to(PROJECT_ROOT / "artifacts")
    assert REPORTS_DIR.is_relative_to(PROJECT_ROOT / "artifacts")


def test_grids_en_el_orden_de_decenas():
    sizes = {
        trainer: len(ParameterGrid(trainer.DEFAULT_PARAM_GRID))
        for trainer in (
            DecisionTreeModelTrainer,
            RandomForestModelTrainer,
            LogisticRegressionModelTrainer,
        )
    }
    assert all(size >= 2 for size in sizes.values())
    assert 10 <= sum(sizes.values()) < 100


@pytest.mark.parametrize("modelo", MODELOS)
def test_pkl_existe_carga_y_predice_las_209_filas(modelo):
    pipeline = joblib.load(MODELS_DIR / f"mastitis_{modelo}_A_pipeline.pkl")
    validator = DataValidator("A")
    clean, _ = validator.validate_and_clean(load_curated_dataset())
    X = clean.loc[:, list(validator.feature_columns)]

    assert pipeline.predict_proba(X).shape == (209, 2)


@pytest.mark.parametrize("modelo", MODELOS)
def test_reporte_declara_datos_reales_y_cinco_pliegues_por_finca(modelo):
    report = json.loads(
        (REPORTS_DIR / f"entrenamiento_mastitis_{modelo}_A.json").read_text(encoding="utf-8")
    )
    assert report["datos"] == "reales"
    assert report["rows"] == 209
    assert len(report["folds"]) == 5

    farms = [farm for fold in report["folds"] for farm in fold["test_farms"]]
    assert sorted(farms) == [f"Finca_{n}" for n in range(1, 7)]


@pytest.mark.parametrize("modulo", sorted(MODULOS))
def test_modulo_corre_desde_la_raiz_con_dash_m(modulo, tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", f"src.models.{modulo}", "--artifacts-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "models" / f"mastitis_{MODULOS[modulo]}_A_pipeline.pkl").is_file()


def test_script_no_depende_del_directorio_de_trabajo(tmp_path):
    workdir = tmp_path / "otro_directorio"
    workdir.mkdir()
    output = tmp_path / "salida"

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "src" / "models" / "LogisticalRegresion.py"),
            "--artifacts-dir",
            str(output),
        ],
        cwd=workdir,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert list(workdir.iterdir()) == []
    assert sorted(path.name for path in output.iterdir()) == ["models", "reports"]
