import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from server.app.monitoring import categorical_psi, numeric_psi, psi, psi_level
from server.tests.conftest import confirmacion, medicion, vaca

BASELINE = json.loads((Path(__file__).resolve().parents[2] / "models" / "drift_baseline.json").read_text())
ADMIN = {"Authorization": "Bearer admin-secret"}


def test_psi_basics():
    assert psi([0.5, 0.5], [0.5, 0.5]) == 0.0
    assert psi_level(psi([0.5, 0.5], [0.9, 0.1])) == "alto"
    assert psi_level(0.05) == "estable" and psi_level(0.15) == "moderado"


def test_numeric_psi_detects_shift_in_ph():
    spec = BASELINE["numeric"]["ph_leche"]
    rng = np.random.default_rng(0)
    # La línea base es bimodal (sanas ~6.6 / enfermas ~6.9): remuestrear el pH real.
    training_ph = pd.read_csv(
        Path(__file__).resolve().parents[2] / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"
    )["ph_leche"].to_numpy()
    same = rng.choice(training_ph, size=400, replace=True)
    shifted = rng.normal(7.1, 0.1, 400)
    assert psi_level(numeric_psi(spec, same)) == "estable"
    assert psi_level(numeric_psi(spec, shifted)) == "alto"


def test_categorical_psi_new_breed_raises_drift():
    base = BASELINE["categorical"]["raza"]
    similar = [b for b, share in base.items() for _ in range(round(share * 200))]
    assert categorical_psi(base, similar) < 0.10
    assert categorical_psi(base, ["Gyr"] * 100) > 0.25


def test_monitoring_requires_admin(client, device_a):
    assert client.get("/v1/monitoring/drift").status_code == 403
    assert client.get("/v1/monitoring/drift", headers=device_a["headers"]).status_code == 403
    assert client.get("/v1/monitoring/drift", headers=ADMIN).status_code == 200


def test_monitoring_reports_insufficient_data(client):
    body = client.get("/v1/monitoring/drift", headers=ADMIN).json()
    assert body["drift"]["status"] == "datos_insuficientes"
    assert body["recall_observado"]["status"] == "datos_insuficientes"
    assert body["revisar_reentrenamiento"]["recomendado"] is False


def test_monitoring_flags_drift_and_low_recall(client, device_a):
    random.seed(1)
    v = vaca()
    meds, confs = [], []
    for i in range(40):
        m = medicion(
            v["id"], ph_leche=round(random.uniform(7.0, 7.18), 2),  # muy por encima de la línea base
            nivel_riesgo="bajo" if i % 2 else "alto", probabilidad=0.1 if i % 2 else 0.9,
            raza="Holstein",
        )
        meds.append(m)
        confs.append(confirmacion(m["id"], positivo=True, grado="2", ciego_al_ph=True))
    r = client.post("/v1/sync/push", json={"vacas": [v], "mediciones": meds, "confirmaciones": confs}, headers=device_a["headers"])
    assert all(x["status"] == "accepted" for x in r.json()["results"]["mediciones"])

    body = client.get("/v1/monitoring/drift", headers=ADMIN).json()
    assert body["drift"]["variables"]["ph_leche"]["nivel"] == "alto"
    assert body["recall_observado"]["status"] == "evaluado"
    assert body["recall_observado"]["recall_alto"] == 0.5
    assert body["revisar_reentrenamiento"]["recomendado"] is True
    assert len(body["revisar_reentrenamiento"]["motivos"]) == 2


def test_recall_ignores_non_blind_confirmations(client, device_a):
    v = vaca()
    meds = [medicion(v["id"], nivel_riesgo="alto") for _ in range(25)]
    confs = [confirmacion(m["id"], positivo=True, grado="2", ciego_al_ph=False) for m in meds]
    client.post("/v1/sync/push", json={"vacas": [v], "mediciones": meds, "confirmaciones": confs}, headers=device_a["headers"])
    body = client.get("/v1/monitoring/drift", headers=ADMIN).json()
    assert body["recall_observado"]["confirmed_total"] == 25
    assert body["recall_observado"]["confirmed_blind_positive"] == 0
    assert body["recall_observado"]["status"] == "datos_insuficientes"


def test_missing_baseline_is_503_not_500(settings, tmp_path):
    import shutil
    from fastapi.testclient import TestClient
    from server.app.config import Settings
    from server.app.main import create_app
    models = tmp_path / "m"
    shutil.copytree(settings.models_dir, models)
    (models / "drift_baseline.json").unlink()
    app = create_app(Settings(settings.database_url, models, "admin-secret"))
    with TestClient(app) as c:
        assert c.get("/v1/monitoring/drift", headers=ADMIN).status_code == 503
