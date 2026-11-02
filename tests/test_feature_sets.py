import pytest

from src.data.dataValidation import (
    FEATURE_SETS,
    DataValidationError,
    DataValidator,
    resolve_feature_set,
)
from src.data.featureEngineer import FeaturePipelineBuilder


def test_set_b_excludes_conductivity_and_constants():
    b = FEATURE_SETS["B"]
    assert "conductividad_leche_ms_cm" not in b
    assert "frecuencia_de_ordeno" not in b
    assert "estado_de_vacunacion" not in b
    assert "ph_leche" in b
    assert set(b) < set(FEATURE_SETS["A"])


def test_unknown_feature_set_rejected():
    with pytest.raises(ValueError):
        resolve_feature_set("Z")


def test_validator_b_does_not_need_set_a_only_columns(raw_data):
    reduced = raw_data.drop(
        columns=["conductividad_leche_ms_cm", "frecuencia_de_ordeno", "estado_de_vacunacion"]
    )
    clean, report = DataValidator("B").validate_and_clean(reduced)
    assert len(clean) == len(raw_data)
    assert "conductividad_leche_ms_cm" not in report.missing_by_column


def test_validator_a_still_requires_conductivity(raw_data):
    with pytest.raises(DataValidationError, match="conductividad"):
        DataValidator("A").validate_and_clean(
            raw_data.drop(columns=["conductividad_leche_ms_cm"])
        )


def test_validator_b_requires_ph(raw_data):
    with pytest.raises(DataValidationError, match="ph_leche"):
        DataValidator("B").validate_and_clean(raw_data.drop(columns=["ph_leche"]))


def test_validator_b_range_check_on_ph(raw_data):
    bad = raw_data.copy()
    bad.loc[0, "ph_leche"] = 12.0
    with pytest.raises(DataValidationError, match="ph_leche"):
        DataValidator("B").validate_and_clean(bad)


def test_dataset_has_normalized_farms_and_breeds(raw_data):
    clean, report = DataValidator("A").validate_and_clean(raw_data)
    assert report.unique_farms == 6
    assert set(clean["raza"].unique()) == {
        "Holstein", "Normando", "Jersey", "Pardo_Suizo", "Cruzado"
    }


def test_feature_contract_per_set():
    b = FeaturePipelineBuilder("B")
    b.assert_feature_contract(FEATURE_SETS["B"])
    with pytest.raises(ValueError, match="Faltan"):
        FeaturePipelineBuilder("A").assert_feature_contract(FEATURE_SETS["B"])
    with pytest.raises(ValueError, match="agrupamiento"):
        b.assert_feature_contract([*FEATURE_SETS["B"], "finca"])


def test_blank_breed_is_imputed_instead_of_breaking_fit(raw_data):
    from sklearn.linear_model import LogisticRegression

    data = raw_data.copy()
    data.loc[0:2, "raza"] = ""
    validator = DataValidator("B")
    clean, _ = validator.validate_and_clean(data)
    X = clean.loc[:, list(validator.feature_columns)]
    pipe = FeaturePipelineBuilder("B").build_pipeline(LogisticRegression(max_iter=500))
    pipe.fit(X, clean["mastitis"].astype(int))  # no debe lanzar
    assert pipe.predict_proba(X.head(3)).shape == (3, 2)
