"""Candados del dataset curado: leen el CSV tal como está en disco."""

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold

from src.data.curation import (
    FINCAS_ADMITIDAS,
    RAZAS_ADMITIDAS,
    assert_curated,
    curate,
    load_curated_dataset,
)
from src.data.dataValidation import DataValidationError, DataValidator
from src.data.featureEngineer import FeaturePipelineBuilder


def test_csv_conserva_las_209_filas_y_seis_fincas(raw_data):
    assert raw_data.shape == (209, 14)
    assert sorted(raw_data["finca"].unique()) == sorted(FINCAS_ADMITIDAS)


def test_csv_no_tiene_finca_6_en_minuscula(raw_data):
    assert not raw_data["finca"].eq("finca_6").any()
    assert raw_data["finca"].eq("Finca_6").sum() == 8


def test_csv_solo_tiene_razas_admitidas(raw_data):
    assert set(raw_data["raza"]) == set(RAZAS_ADMITIDAS)


def test_csv_ya_curado_no_cambia(raw_data):
    curated, changed = curate(raw_data)
    assert changed == {"finca": 0, "raza": 0}
    pd.testing.assert_frame_equal(curated, raw_data)
    assert_curated(raw_data)


def test_los_unicos_nulos_son_conductividad_de_finca_6(raw_data):
    nulls = raw_data.isna().sum()
    assert nulls[nulls > 0].to_dict() == {"conductividad_leche_ms_cm": 8}
    missing = raw_data[raw_data["conductividad_leche_ms_cm"].isna()]
    assert set(missing["finca"]) == {"Finca_6"}


@pytest.mark.parametrize(
    ("column", "bad_value"),
    [("finca", "finca_6"), ("finca", "Finca_7"), ("raza", "Hounstein"), ("raza", "Brahman")],
)
def test_assert_curated_detecta_una_sola_etiqueta_mala(raw_data, column, bad_value):
    bad = raw_data.copy()
    bad.loc[0, column] = bad_value
    with pytest.raises(DataValidationError):
        assert_curated(bad)


def test_curate_repara_los_defectos_historicos_y_los_cuenta(raw_data):
    # Los defectos del commit 4a7765d: 6 filas de finca y 7 de raza.
    dirty = raw_data.copy()
    dirty.loc[0:5, "finca"] = "finca_6"
    dirty.loc[0:3, "raza"] = "Hounstein"
    dirty.loc[4:6, "raza"] = "Normanda"

    curated, changed = curate(dirty)

    assert changed == {"finca": 6, "raza": 7}
    assert_curated(curated)
    assert curated["raza"].iloc[:4].eq("Holstein").all()
    assert curated["raza"].iloc[4:7].eq("Normando").all()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("holstein", "Holstein"), (" NORMANDO ", "Normando"), ("Pardo Suizo", "Pardo_Suizo"),
     ("Jérsey", "Jersey"), ("cruzado", "Cruzado")],
)
def test_curate_unifica_mayusculas_tildes_y_separadores(raw_data, value, expected):
    dirty = raw_data.copy()
    dirty.loc[0, "raza"] = value
    curated, _ = curate(dirty)
    assert curated.loc[0, "raza"] == expected


def test_curate_rechaza_raza_desconocida_en_vez_de_reasignarla(raw_data):
    dirty = raw_data.copy()
    dirty.loc[0, "raza"] = "Brahman"
    with pytest.raises(DataValidationError, match="Brahman"):
        curate(dirty)


def test_curate_conserva_los_vacios(raw_data):
    dirty = raw_data.copy()
    dirty.loc[0, "raza"] = np.nan
    curated, _ = curate(dirty)
    assert pd.isna(curated.loc[0, "raza"])


def test_cero_nulos_al_modelo_e_imputacion_solo_con_entrenamiento():
    validator = DataValidator("A")
    clean, _ = validator.validate_and_clean(load_curated_dataset())
    X = clean.loc[:, list(validator.feature_columns)]
    y = clean["mastitis"].astype(int)
    groups = clean["finca"]
    conductivity = "conductividad_leche_ms_cm"

    for train, test in GroupKFold(n_splits=5).split(X, y, groups):
        pre = FeaturePipelineBuilder("A").build_preprocessor().fit(X.iloc[train])

        assert not np.isnan(pre.transform(X.iloc[train])).any()
        assert not np.isnan(pre.transform(X.iloc[test])).any()

        names = list(pre.transformers_[0][2])
        imputer = pre.named_transformers_["numeric"].named_steps["imputer"]
        assert imputer.statistics_[names.index(conductivity)] == pytest.approx(
            X[conductivity].iloc[train].median()
        )
