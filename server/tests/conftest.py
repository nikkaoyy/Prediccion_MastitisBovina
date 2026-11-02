import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app.config import Settings
from server.app.main import create_app
from server.scripts.create_device import register_device

MODELS = Path(__file__).resolve().parents[2] / "models"


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        models_dir=MODELS,
        admin_token="admin-secret",
    )


@pytest.fixture()
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture()
def device_a(settings):
    _, device_id, token = register_device(settings, "Finca A", "Celular A")
    return {"id": device_id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture()
def device_b(settings):
    _, device_id, token = register_device(settings, "Finca B", "Celular B")
    return {"id": device_id, "headers": {"Authorization": f"Bearer {token}"}}


def uid() -> str:
    return str(uuid.uuid4())


def vaca(arete="A-001", nombre="Lola", id=None):
    return {"id": id or uid(), "arete": arete, "nombre": nombre}


def medicion(vaca_id, id=None, **over):
    base = {
        "id": id or uid(),
        "vaca_id": vaca_id,
        "fecha_medicion": datetime.now(timezone.utc).isoformat(),
        "edad": 5, "raza": "Holstein", "numero_de_partos": 3,
        "volumen_de_leche": 11.0, "etapa_de_lactancia": 1,
        "antecedentes_de_mastitis": 0, "humedad": 70.0, "temperatura": 12.0,
        "ph_leche": 6.9, "probabilidad": 0.8, "nivel_riesgo": "alto",
        "model_version": "mastitis-B-lr-test",
    }
    base.update(over)
    return base


def confirmacion(medicion_id, positivo=True, grado="2", id=None, **over):
    base = {
        "id": id or uid(), "medicion_id": medicion_id,
        "fecha": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "resultado_positivo": positivo, "grado": grado, "evaluador": "Vet", "ciego_al_ph": True,
    }
    base.update(over)
    return base
