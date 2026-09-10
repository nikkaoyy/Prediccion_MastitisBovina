"""Construcción del preprocesamiento libre de fuga de datos."""

from __future__ import annotations

from typing import Iterable

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.dataValidation import DataValidator


class FeaturePipelineBuilder:
    """Crea el transformador y Pipeline de features para el árbol."""

    numeric_features: tuple[str, ...] = tuple(
        feature
        for feature in DataValidator.FEATURE_COLUMNS
        if feature not in DataValidator.CATEGORICAL_COLUMNS
    )

    categorical_features: tuple[str, ...] = DataValidator.CATEGORICAL_COLUMNS

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

    @staticmethod
    def assert_feature_contract(columns: Iterable[str]) -> None:
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

        missing = set(DataValidator.FEATURE_COLUMNS) - columns

        if missing:
            raise ValueError(
                "Faltan features requeridas: " + ", ".join(sorted(missing))
            )