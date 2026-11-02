"""Monitoreo del modelo: data drift (PSI) y Recall observado con CMT.

Esqueleto operativo del protocolo de la fase de monitoreo de CRISP-ML(Q).
Solo informa: NO dispara reentrenamiento automático.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.app.db import ConfirmacionCmt, Medicion
from server.app.security import get_session, require_admin

PSI_MODERATE, PSI_MAJOR = 0.10, 0.25
EPS = 1e-4
RECALL_GOAL = 0.80
MIN_POSITIVES_FOR_RECALL = 20

router = APIRouter(prefix="/v1/monitoring", tags=["monitoring"], dependencies=[Depends(require_admin)])


def psi(expected: list[float], actual: list[float]) -> float:
    """Population Stability Index entre dos distribuciones discretas."""

    e = np.clip(np.asarray(expected, dtype=float), EPS, None)
    a = np.clip(np.asarray(actual, dtype=float), EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def psi_level(value: float) -> str:
    if value >= PSI_MAJOR:
        return "alto"
    if value >= PSI_MODERATE:
        return "moderado"
    return "estable"


def numeric_psi(baseline: dict, values: np.ndarray) -> float:
    if baseline["kind"] == "discrete":
        cats = baseline["values"]
        actual = [float(np.isclose(values, c).mean()) for c in cats]
        actual.append(max(0.0, 1.0 - sum(actual)))  # valores nunca vistos
        return psi(baseline["proportions"] + [0.0], actual)

    edges = np.asarray(baseline["edges"], dtype=float)
    counts = np.bincount(np.searchsorted(edges, values, side="right"), minlength=len(edges) + 1)
    return psi(baseline["proportions"], (counts / counts.sum()).tolist())


def categorical_psi(baseline: dict[str, float], values: list[str]) -> float:
    cats = sorted(set(baseline) | set(values))
    expected = [baseline.get(c, 0.0) for c in cats]
    actual = [values.count(c) / len(values) for c in cats]
    return psi(expected, actual)


def drift_report(
    mediciones: list[Medicion],
    confirmaciones: list[tuple[ConfirmacionCmt, Medicion]],
    baseline: dict[str, Any],
    min_rows: int = 30,
) -> dict[str, Any]:
    report: dict[str, Any] = {"rows_analyzed": len(mediciones), "min_rows": min_rows}

    if len(mediciones) < min_rows:
        report["drift"] = {"status": "datos_insuficientes"}
    else:
        variables: dict[str, Any] = {}
        for name, spec in baseline["numeric"].items():
            observed = [getattr(m, name) for m in mediciones if getattr(m, name) is not None]
            if len(observed) < min_rows:
                variables[name] = {"psi": None, "nivel": "datos_insuficientes"}
                continue
            value = numeric_psi(spec, np.array(observed, dtype=float))
            variables[name] = {"psi": round(value, 4), "nivel": psi_level(value)}
        for name, spec in baseline["categorical"].items():
            value = categorical_psi(spec, [getattr(m, name) for m in mediciones])
            variables[name] = {"psi": round(value, 4), "nivel": psi_level(value)}

        scored = [v["psi"] for v in variables.values() if v["psi"] is not None]
        worst = max(scored)
        report["drift"] = {"status": "evaluado", "max_psi": worst, "nivel": psi_level(worst), "variables": variables}

    # Solo cuentan las confirmaciones ciegas al pH (protocolo §2): las demás
    # pueden estar contaminadas por conocer el pH o la estimación.
    blind = [(c, m) for c, m in confirmaciones if c.ciego_al_ph]
    positives = [(c, m) for c, m in blind if c.resultado_positivo]
    caught = [pair for pair in positives if pair[1].nivel_riesgo in ("medio", "alto")]
    caught_alto = [pair for pair in positives if pair[1].nivel_riesgo == "alto"]
    recall_block: dict[str, Any] = {
        "confirmed_total": len(confirmaciones),
        "confirmed_blind_to_ph": sum(1 for c, _ in confirmaciones if c.ciego_al_ph),
        "confirmed_blind_positive": len(positives),
        "nota_sesgo": "Si la app recomienda CMT sobre todo en riesgo medio/alto, el Recall observado "
                      "tiene sesgo de verificación; el protocolo pide CMT a todas las vacas.",
    }
    if len(positives) < MIN_POSITIVES_FOR_RECALL:
        recall_block["status"] = "datos_insuficientes"
        recall_block["needed_positives"] = MIN_POSITIVES_FOR_RECALL
    else:
        recall_block["status"] = "evaluado"
        recall_block["recall_alto"] = round(len(caught_alto) / len(positives), 4)
        recall_block["recall_medio_o_alto"] = round(len(caught) / len(positives), 4)
        recall_block["meta"] = RECALL_GOAL
    report["recall_observado"] = recall_block

    reasons = []
    if report["drift"].get("nivel") == "alto":
        reasons.append("PSI >= 0.25 en alguna variable")
    if recall_block["status"] == "evaluado" and recall_block["recall_alto"] < RECALL_GOAL:
        reasons.append(f"Recall observado < {RECALL_GOAL}")
    report["revisar_reentrenamiento"] = {"recomendado": bool(reasons), "motivos": reasons}
    report["nota"] = "Informativo: el reentrenamiento requiere decisión humana y datos confirmados."
    return report


@router.get("/drift")
def drift(
    request: Request,
    window: int = Query(500, ge=1, le=5000),
    min_rows: int = Query(30, ge=1),
    session: Session = Depends(get_session),
) -> dict:
    baseline_path: Path = request.app.state.settings.models_dir / "drift_baseline.json"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(503, "Línea base de drift no disponible en el servidor.") from None

    mediciones = list(
        session.scalars(select(Medicion).order_by(Medicion.seq.desc()).limit(window)).all()
    )
    pairs = list(
        session.execute(
            select(ConfirmacionCmt, Medicion).join(Medicion, Medicion.id == ConfirmacionCmt.medicion_id)
        ).all()
    )
    return drift_report(mediciones, [(c, m) for c, m in pairs], baseline, min_rows)
