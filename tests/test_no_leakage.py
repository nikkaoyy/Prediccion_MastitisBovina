import numpy as np
import pandas as pd

from src.data.dataValidation import DataValidator
from src.data.featureEngineer import FeaturePipelineBuilder


def test_imputer_and_scaler_use_only_training_rows(raw_data):
    validator = DataValidator("A")
    clean, _ = validator.validate_and_clean(raw_data)
    X = clean.loc[:, list(validator.feature_columns)]
    y = clean["mastitis"].astype(int)

    train = clean["finca"] != "Finca_6"  # Finca 6 no tiene conductividad
    pre = FeaturePipelineBuilder("A").build_preprocessor()
    pre.fit(X[train], y[train])

    numeric = pre.named_transformers_["numeric"]
    names = list(pre.transformers_[0][2])
    idx = names.index("conductividad_leche_ms_cm")
    expected = X.loc[train, "conductividad_leche_ms_cm"].median()

    assert np.isclose(numeric.named_steps["imputer"].statistics_[idx], expected)
    assert np.isclose(
        numeric.named_steps["scaler"].mean_[names.index("ph_leche")],
        X.loc[train, "ph_leche"].mean(),
    )


def test_unknown_breed_does_not_break_inference(raw_data):
    validator = DataValidator("B")
    clean, _ = validator.validate_and_clean(raw_data)
    X = clean.loc[:, list(validator.feature_columns)]
    y = clean["mastitis"].astype(int)

    from sklearn.linear_model import LogisticRegression

    pipe = FeaturePipelineBuilder("B").build_pipeline(LogisticRegression(max_iter=500))
    pipe.fit(X, y)

    sample = X.head(3).copy()
    sample["raza"] = "Raza_Nueva"
    probabilities = pipe.predict_proba(sample)[:, 1]
    assert np.all((probabilities >= 0) & (probabilities <= 1))
