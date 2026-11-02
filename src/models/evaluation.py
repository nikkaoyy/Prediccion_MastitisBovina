"""Utilidades de evaluación: bootstrap por finca, umbrales y baselines."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    balanced_accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut


def _metric_dict(
    y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray
) -> dict[str, float]:
    """Calcula métricas puntuales; AUC es NaN si falta una clase."""

    metrics = {
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }

    if len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = float("nan")

    return metrics


def cluster_bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    groups: pd.Series | np.ndarray,
    threshold: float = 0.5,
    n_boot: int = 2000,
    confidence: float = 0.95,
    random_state: int = 42,
) -> dict[str, dict[str, float]]:
    """IC bootstrap remuestreando fincas completas (unidad de agrupamiento).

    Remuestrear animales sueltos subestimaría la incertidumbre porque los
    animales de una misma finca no son independientes.
    """

    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    groups = np.asarray(groups)

    unique_groups = np.unique(groups)
    index_by_group = {g: np.flatnonzero(groups == g) for g in unique_groups}
    rng = np.random.default_rng(random_state)

    samples: dict[str, list[float]] = {}

    for _ in range(n_boot):
        chosen = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([index_by_group[g] for g in chosen])

        if len(np.unique(y_true[idx])) < 2:
            continue  # remuestreo degenerado: sin ambas clases no hay AUC

        metrics = _metric_dict(
            y_true[idx], (y_prob[idx] >= threshold).astype(int), y_prob[idx]
        )

        for name, value in metrics.items():
            samples.setdefault(name, []).append(value)

    alpha = (1.0 - confidence) / 2.0
    point = _metric_dict(
        y_true, (y_prob >= threshold).astype(int), y_prob
    )

    return {
        name: {
            "point": point[name],
            "ci_low": float(np.quantile(values, alpha)),
            "ci_high": float(np.quantile(values, 1.0 - alpha)),
            "n_valid_resamples": len(values),
        }
        for name, values in samples.items()
    }


def select_thresholds(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    target_recall: float = 0.95,
    low_risk_recall: float = 0.97,
) -> dict[str, float]:
    """Elige umbrales sobre probabilidades fuera de pliegue (OOF).

    * ``alto``: mayor umbral cuyo Recall OOF alcanza ``target_recall``
      (maximiza la precisión sujeto a la restricción de sensibilidad).
    * ``medio``: mayor umbral cuyo Recall OOF alcanza ``low_risk_recall``;
      por debajo de él el riesgo se considera bajo.

    Advertencia: los umbrales se eligen y se reportan sobre las mismas
    predicciones OOF, por lo que cumplen la meta por construcción (optimismo).
    La confirmación requiere datos nuevos.
    """

    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    candidates = np.unique(y_prob)  # valores reales, sin redondear
    positives = max(int(y_true.sum()), 1)

    def highest_threshold_for(recall_target: float) -> float:
        best = float(candidates.min())

        for threshold in candidates:
            recall = float(((y_prob >= threshold) & (y_true == 1)).sum()) / positives

            if recall >= recall_target:
                best = max(best, float(threshold))

        return best

    alto = highest_threshold_for(target_recall)
    medio = min(highest_threshold_for(low_risk_recall), alto)

    return {
        "alto": alto,
        "medio": medio,
        "target_recall_alto": target_recall,
        "target_recall_medio": low_risk_recall,
    }


def ph_rule_baseline(
    data: pd.DataFrame, cutoff: float = 6.7
) -> dict[str, float]:
    """Regla trivial 'pH > corte' para dimensionar la separabilidad."""

    y_true = data["mastitis"].to_numpy(dtype=int)
    score = data["ph_leche"].to_numpy(dtype=float)
    y_pred = (score > cutoff).astype(int)

    return {
        "cutoff": cutoff,
        "accuracy": float((y_pred == y_true).mean()),
        **_metric_dict(y_true, y_pred, score),
    }


def leave_one_farm_out(
    estimator: Any,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Validación dejando una finca fuera por turno (con estimador fijo)."""

    y_true = y.to_numpy(dtype=int)
    y_prob = np.full(len(X), np.nan, dtype=float)
    per_farm: dict[str, dict[str, float | int]] = {}

    for train_idx, test_idx in LeaveOneGroupOut().split(X, y, groups):
        model = clone(estimator)
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        y_prob[test_idx] = model.predict_proba(X.iloc[test_idx])[:, 1]

        farm = str(groups.iloc[test_idx].iloc[0])
        pred = (y_prob[test_idx] >= threshold).astype(int)
        positives = int(y_true[test_idx].sum())

        per_farm[farm] = {
            "rows": int(len(test_idx)),
            "positives": positives,
            "recall": (
                float(recall_score(y_true[test_idx], pred, zero_division=0))
                if positives
                else float("nan")
            ),
            "accuracy": float((pred == y_true[test_idx]).mean()),
        }

    pooled = _metric_dict(y_true, (y_prob >= threshold).astype(int), y_prob)

    return {"pooled": pooled, "per_farm": per_farm, "y_probability": y_prob}
