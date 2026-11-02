import numpy as np
import pandas as pd

from src.models.evaluation import (
    cluster_bootstrap_ci,
    ph_rule_baseline,
    select_thresholds,
)


def _toy():
    rng = np.random.default_rng(0)
    groups = np.repeat(["f1", "f2", "f3", "f4", "f5"], 40)
    y = rng.integers(0, 2, size=len(groups))
    prob = np.clip(y * 0.6 + rng.normal(0.2, 0.2, size=len(y)), 0, 1)
    return y, prob, groups


def test_bootstrap_is_deterministic_and_brackets_point():
    y, prob, groups = _toy()
    a = cluster_bootstrap_ci(y, prob, groups, n_boot=300, random_state=1)
    b = cluster_bootstrap_ci(y, prob, groups, n_boot=300, random_state=1)
    assert a == b
    recall = a["recall"]
    assert recall["ci_low"] <= recall["point"] <= recall["ci_high"] + 1e-9


def test_bootstrap_resamples_whole_farms():
    # Con un solo clúster todos los remuestreos son idénticos: IC degenerado.
    y = np.array([0, 1, 0, 1, 1, 0])
    prob = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3])
    groups = np.array(["a"] * 6)
    ci = cluster_bootstrap_ci(y, prob, groups, n_boot=50)
    assert ci["recall"]["ci_low"] == ci["recall"]["ci_high"]


def test_thresholds_meet_recall_targets_and_are_ordered():
    y, prob, _ = _toy()
    t = select_thresholds(y, prob, target_recall=0.9, low_risk_recall=0.97)
    assert t["medio"] <= t["alto"]
    positives = y.sum()
    recall_alto = ((prob >= t["alto"]) & (y == 1)).sum() / positives
    recall_medio = ((prob >= t["medio"]) & (y == 1)).sum() / positives
    assert recall_alto >= 0.9
    assert recall_medio >= 0.97


def test_ph_baseline_on_separable_data():
    df = pd.DataFrame({"ph_leche": [6.5, 6.6, 6.8, 7.0], "mastitis": [0, 0, 1, 1]})
    result = ph_rule_baseline(df, cutoff=6.7)
    assert result["accuracy"] == 1.0 and result["recall"] == 1.0


def test_threshold_is_an_actual_probability_value():
    y = np.array([0, 0, 1, 1, 1, 1])
    prob = np.array([0.1, 0.2, 0.5174194, 0.5791, 0.8, 0.9])
    t = select_thresholds(y, prob, target_recall=0.75, low_risk_recall=0.75)
    assert t["alto"] in prob  # sin redondeos que muevan el punto de corte
    assert t["alto"] == 0.5791
