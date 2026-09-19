"""Entrenamiento, ajuste y evaluación agrupada del árbol de decisión."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.metrics import make_scorer
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier, plot_tree

from src.data.featureEngineer import FeaturePipelineBuilder

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class EvaluationResult:
    """Predicciones fuera de pliegue y métricas de evaluación agrupada."""

    aggregate_metrics: dict[str, float]
    fold_metrics: list[dict[str, float | int]]
    classification_report: dict[str, Any]
    confusion_matrix: list[list[int]]
    y_true: np.ndarray
    y_pred: np.ndarray
    y_probability: np.ndarray

    def serializable_summary(self) -> dict[str, Any]:
        """Resume métricas sin incluir arrays de predicciones en JSON."""

        return {
            "aggregate_metrics": self.aggregate_metrics,
            "fold_metrics": self.fold_metrics,
            "classification_report": self.classification_report,
            "confusion_matrix": self.confusion_matrix,
        }


class DecisionTreeModelTrainer:
    """Gestiona tuning, GroupKFold y persistencia del modelo."""

    DEFAULT_PARAM_GRID: dict[str, list[Any]] = {
        "classifier__criterion": ["gini"],
        "classifier__max_depth": [5, None],
        "classifier__min_samples_split": [2],
        "classifier__min_samples_leaf": [1],
        "classifier__class_weight": ["balanced"],
    }

    def __init__(
        self,
        n_splits: int = 5,
        random_state: int = 42,
        param_grid: dict[str, list[Any]] | None = None,
        n_jobs: int | None = 1,
    ) -> None:
        self.n_splits = n_splits
        self.random_state = random_state
        self.param_grid = param_grid or self.DEFAULT_PARAM_GRID
        self.n_jobs = n_jobs

        self.feature_builder = FeaturePipelineBuilder()
        self.best_estimator_: Pipeline | None = None
        self.best_params_: dict[str, Any] | None = None
        self.best_score_: float | None = None
        self.tuning_results_: pd.DataFrame | None = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
    ) -> "DecisionTreeModelTrainer":
        """Ajusta hiperparámetros con GroupKFold y entrena el modelo final."""

        self._validate_training_inputs(X, y, groups)

        search = self._build_search(n_splits=self.n_splits)
        search.fit(X, y, groups=groups)

        self.best_estimator_ = search.best_estimator_
        self.best_params_ = dict(search.best_params_)
        self.best_score_ = float(search.best_score_)

        self.tuning_results_ = pd.DataFrame(
            search.cv_results_
        ).sort_values("rank_test_score")

        return self

    def evaluate_grouped_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
    ) -> EvaluationResult:
        """Calcula predicciones OOF con GroupKFold anidado por finca."""

        self._validate_training_inputs(X, y, groups)

        if self.best_params_ is None:
            raise RuntimeError("Ejecute fit() antes de evaluate_grouped_cv().")

        splitter = GroupKFold(n_splits=self.n_splits)

        y_true = y.to_numpy(dtype=int)
        y_pred = np.empty(shape=len(X), dtype=int)
        y_probability = np.full(shape=len(X), fill_value=np.nan, dtype=float)

        fold_metrics: list[dict[str, float | int]] = []

        for fold, (train_idx, test_idx) in enumerate(
            splitter.split(X, y, groups),
            start=1,
        ):
            training_groups = groups.iloc[train_idx]

            inner_splits = min(
                self.n_splits,
                int(training_groups.nunique()),
            )

            inner_search = self._build_search(n_splits=inner_splits)

            inner_search.fit(
                X.iloc[train_idx],
                y.iloc[train_idx],
                groups=training_groups,
            )

            fold_pipeline = inner_search.best_estimator_

            predictions = fold_pipeline.predict(X.iloc[test_idx]).astype(int)
            probabilities = fold_pipeline.predict_proba(X.iloc[test_idx])[:, 1]

            y_pred[test_idx] = predictions
            y_probability[test_idx] = probabilities

            fold_metrics.append(
                {
                    "fold": fold,
                    "test_rows": int(len(test_idx)),
                    "accuracy": float(
                        accuracy_score(y.iloc[test_idx], predictions)
                    ),
                    "balanced_accuracy": float(
                        balanced_accuracy_score(y.iloc[test_idx], predictions)
                    ),
                    "precision": float(
                        precision_score(
                            y.iloc[test_idx],
                            predictions,
                            zero_division=0,
                        )
                    ),
                    "recall": float(
                        recall_score(
                            y.iloc[test_idx],
                            predictions,
                            zero_division=0,
                        )
                    ),
                    "f1": float(
                        f1_score(
                            y.iloc[test_idx],
                            predictions,
                            zero_division=0,
                        )
                    ),
                    "inner_best_f1": float(inner_search.best_score_),
                }
            )

        aggregate = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "balanced_accuracy": float(
                balanced_accuracy_score(y_true, y_pred)
            ),
            "precision": float(
                precision_score(y_true, y_pred, zero_division=0)
            ),
            "recall": float(
                recall_score(y_true, y_pred, zero_division=0)
            ),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }

        if len(np.unique(y_true)) == 2 and not np.isnan(y_probability).any():
            aggregate["roc_auc"] = float(
                roc_auc_score(y_true, y_probability)
            )

        return EvaluationResult(
            aggregate_metrics=aggregate,
            fold_metrics=fold_metrics,
            classification_report=classification_report(
                y_true,
                y_pred,
                labels=[0, 1],
                target_names=["Sana", "Mastitis"],
                output_dict=True,
                zero_division=0,
            ),
            confusion_matrix=confusion_matrix(
                y_true,
                y_pred,
                labels=[0, 1],
            ).tolist(),
            y_true=y_true,
            y_pred=y_pred,
            y_probability=y_probability,
        )

    def persist_model(self, output_path: str | Path) -> Path:
        """Guarda Pipeline final: preprocesamiento y clasificador."""

        if self.best_estimator_ is None:
            raise RuntimeError("No existe un modelo entrenado para persistir.")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.best_estimator_, path)

        return path

    def save_confusion_matrix(
        self,
        evaluation: EvaluationResult,
        output_path: str | Path,
    ) -> Path:
        """Genera matriz de confusión usando predicciones OOF."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        figure, axis = plt.subplots(figsize=(6, 5))

        display = ConfusionMatrixDisplay(
            confusion_matrix=np.asarray(evaluation.confusion_matrix),
            display_labels=["Sana (0)", "Mastitis (1)"],
        )

        display.plot(ax=axis, cmap="Blues", colorbar=False)

        axis.set_title("Matriz de confusión — GroupKFold por finca")

        figure.tight_layout()
        figure.savefig(path, dpi=180, bbox_inches="tight")

        plt.close(figure)

        return path

    def save_tree_diagram(self, output_path: str | Path) -> Path:
        """Exporta el árbol final con los nombres de features transformadas."""

        if self.best_estimator_ is None:
            raise RuntimeError("No existe un modelo entrenado para graficar.")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        classifier = self.best_estimator_.named_steps["classifier"]

        feature_names = self.feature_builder.transformed_feature_names(
            self.best_estimator_
        )

        figure_width = max(
            16,
            min(48, classifier.tree_.max_depth * 4 + 8),
        )

        figure_height = max(
            10,
            min(40, classifier.get_n_leaves() * 0.55 + 4),
        )

        figure, axis = plt.subplots(
            figsize=(figure_width, figure_height)
        )

        plot_tree(
            classifier,
            feature_names=feature_names,
            class_names=["Sana", "Mastitis"],
            filled=True,
            rounded=True,
            impurity=False,
            proportion=True,
            ax=axis,
        )

        axis.set_title("Árbol de decisión final para mastitis subclínica")

        figure.tight_layout()
        figure.savefig(path, dpi=180, bbox_inches="tight")

        plt.close(figure)

        return path

    def _build_base_pipeline(self) -> Pipeline:
        classifier = DecisionTreeClassifier(random_state=self.random_state)
        return self.feature_builder.build_pipeline(classifier)

    def _build_search(self, n_splits: int) -> GridSearchCV:
        """Crea búsqueda que conserva grupos y Pipeline en cada ajuste."""

        return GridSearchCV(
            estimator=self._build_base_pipeline(),
            param_grid=self.param_grid,
            scoring=make_scorer(f1_score, zero_division=0),
            cv=GroupKFold(n_splits=n_splits),
            n_jobs=self.n_jobs,
            refit=True,
            return_train_score=True,
            error_score="raise",
        )

    def _validate_training_inputs(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
    ) -> None:
        self.feature_builder.assert_feature_contract(X.columns)

        if len(X) != len(y) or len(X) != len(groups):
            raise ValueError(
                "X, y y groups deben tener la misma cantidad de filas."
            )

        if groups.isna().any():
            raise ValueError("groups contiene fincas nulas.")

        if groups.nunique() < self.n_splits:
            raise ValueError(
                f"GroupKFold({self.n_splits}) requiere al menos "
                f"{self.n_splits} fincas; se recibieron {groups.nunique()}."
            )

        labels = set(pd.Series(y).dropna().astype(int).unique())

        if labels != {0, 1}:
            raise ValueError(
                "y debe contener exactamente las clases binarias 0 y 1."
            )