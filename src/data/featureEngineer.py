"""Construcción del preprocesamiento libre de fuga de datos."""

from __future__ import annotations

from typing import Iterable

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.dataValidation import DataValidator, resolve_feature_set


class FeaturePipelineBuilder:
    """Crea el transformador y Pipeline de features para el árbol."""

    def __init__(self, feature_set: str = "A") -> None:
        self.feature_set = feature_set.upper()
        self.feature_columns = resolve_feature_set(self.feature_set)
        self.numeric_features: tuple[str, ...] = tuple(
            feature
            for feature in self.feature_columns
            if feature not in DataValidator.CATEGORICAL_COLUMNS
        )
        self.categorical_features: tuple[str, ...] = tuple(
            feature
            for feature in self.feature_columns
            if feature in DataValidator.CATEGORICAL_COLUMNS
        )

    def build_preprocessor(self) -> ColumnTransformer:
        """Construye un ColumnTransformer con imputación por tipo."""

        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )

        return ColumnTransformer(
            transformers=[
                ("numeric", numeric_pipeline, list(self.numeric_features)),
                (
                    "categorical",
                    categorical_pipeline,
                    list(self.categorical_features),
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=True,
        )

    def build_pipeline(self, classifier: object) -> Pipeline:
        """Encapsula preprocesamiento y clasificador en un único Pipeline."""

        return Pipeline(
            steps=[
                ("preprocessor", self.build_preprocessor()),
                ("classifier", classifier),
            ]
        )

    @staticmethod
    def transformed_feature_names(fitted_pipeline: Pipeline) -> list[str]:
        """Obtiene nombres de variables después de la codificación."""

        preprocessor = fitted_pipeline.named_steps["preprocessor"]
        return list(preprocessor.get_feature_names_out())

    def assert_feature_contract(self, columns: Iterable[str]) -> None:
        """Comprueba que X no incluya objetivo ni identificador de finca."""

        columns = set(columns)

        forbidden = (
            {DataValidator.GROUP_COLUMN, DataValidator.TARGET_COLUMN} & columns
        )

        if forbidden:
            raise ValueError(
                "X no puede contener columnas de agrupamiento/objetivo: "
                + ", ".join(sorted(forbidden))
            )

        missing = set(self.feature_columns) - columns

        if missing:
            raise ValueError(
                "Faltan features requeridas: " + ", ".join(sorted(missing))
            )