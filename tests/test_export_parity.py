import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pandas as pd
import pytest

from src.export import export_model
from src.export.lite_eval import predict_probability, risk_level

ROOT = Path(__file__).resolve().parents[1]


def _onnx_probability(session, record):
    feed = {
        k: np.array([[v]], dtype=object)
        if isinstance(v, str)
        else np.array([[np.nan if v is None else v]], dtype=np.float32)
        for k, v in record.items()
    }
    return float(session.run(None, feed)[1][0][1])


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    out = tmp_path_factory.mktemp("models")
    export_model.main(["--output", str(out)])
    return out


def test_lite_onnx_and_fixtures_agree(exported):
    lite = json.loads((exported / "model_lite.json").read_text(encoding="utf-8"))
    fixtures = json.loads((exported / "parity_fixtures.json").read_text(encoding="utf-8"))
    session = ort.InferenceSession(str(exported / "model.onnx"))

    cases = fixtures["cases"]
    assert len(cases) >= 209 and any(c.get("edge") for c in cases), "faltan casos"
    for case in cases:
        expected = case["probability"]
        assert abs(predict_probability(lite, case["input"]) - expected) < 1e-9
        # En ONNX la raza es obligatoria (el imputador de texto no es convertible).
        if case["input"]["raza"] is None:
            continue
        assert abs(_onnx_probability(session, case["input"]) - expected) < fixtures["tolerance"]


def test_manifest_hashes_match_files(exported):
    manifest = json.loads((exported / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((exported / name).read_bytes()).hexdigest() == digest


def test_export_is_deterministic(exported, tmp_path):
    export_model.main(["--output", str(tmp_path)])
    first = json.loads((exported / "model_lite.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "model_lite.json").read_text(encoding="utf-8"))
    assert first["model_version"] == second["model_version"]


def test_lite_handles_missing_and_unknown_values(exported):
    lite = json.loads((exported / "model_lite.json").read_text(encoding="utf-8"))
    base = {
        "edad": 5, "raza": "Holstein", "numero_de_partos": 3, "volumen_de_leche": 11,
        "etapa_de_lactancia": 1, "antecedentes_de_mastitis": 0, "humedad": 70,
        "temperatura": 12, "ph_leche": 6.6,
    }
    with_nan = dict(base, volumen_de_leche=None, raza=None)
    unknown = dict(base, raza="Raza_Nueva")
    for record in (with_nan, unknown):
        p = predict_probability(lite, record)
        assert 0.0 <= p <= 1.0


def test_risk_levels_are_monotonic(exported):
    lite = json.loads((exported / "model_lite.json").read_text(encoding="utf-8"))
    order = {"bajo": 0, "medio": 1, "alto": 2}
    levels = [order[risk_level(lite, p)] for p in np.linspace(0, 1, 101)]
    assert levels == sorted(levels)
    assert levels[0] == 0 and levels[-1] == 2


def test_committed_artifacts_are_consistent():
    """Los artefactos versionados en models/ deben coincidir con su manifiesto."""

    models = ROOT / "models"
    manifest = json.loads((models / "manifest.json").read_text(encoding="utf-8"))
    lite = json.loads((models / "model_lite.json").read_text(encoding="utf-8"))
    assert manifest["model_version"] == lite["model_version"]
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((models / name).read_bytes()).hexdigest() == digest
