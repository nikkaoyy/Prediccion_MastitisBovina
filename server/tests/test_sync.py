import copy
import hashlib

from server.tests.conftest import confirmacion, medicion, uid, vaca


def statuses(response, kind):
    return [r["status"] for r in response.json()["results"][kind]]


def test_health_needs_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_auth_required(client, device_a):
    assert client.post("/v1/sync/push", json={}).status_code == 401
    assert client.post("/v1/sync/push", json={}, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/v1/sync/pull").status_code == 401
    assert client.get("/v1/model/manifest").status_code == 401
    assert client.post("/v1/sync/push", json={}, headers=device_a["headers"]).status_code == 200


def test_push_full_chain_in_one_batch_and_idempotent_replay(client, device_a):
    v = vaca()
    m = medicion(v["id"])
    c = confirmacion(m["id"])
    payload = {"vacas": [v], "mediciones": [m], "confirmaciones": [c]}

    first = client.post("/v1/sync/push", json=payload, headers=device_a["headers"])
    assert first.status_code == 200
    assert statuses(first, "vacas") == ["accepted"]
    assert statuses(first, "mediciones") == ["accepted"]
    assert statuses(first, "confirmaciones") == ["accepted"]

    # Reintento tras un corte de red: no duplica nada.
    second = client.post("/v1/sync/push", json=payload, headers=device_a["headers"])
    assert statuses(second, "vacas") == ["duplicate"]
    assert statuses(second, "mediciones") == ["duplicate"]
    assert statuses(second, "confirmaciones") == ["duplicate"]

    pulled = client.get("/v1/sync/pull", headers=device_a["headers"]).json()
    assert len(pulled["vacas"]) == len(pulled["mediciones"]) == len(pulled["confirmaciones"]) == 1


def test_partial_batch_reports_each_item(client, device_a):
    v = vaca()
    good = medicion(v["id"])
    out_of_range = medicion(v["id"], ph_leche=11.0)
    bad_schema = medicion(v["id"], nivel_riesgo="extremo")
    naive_date = medicion(v["id"], fecha_medicion="2026-01-01T10:00:00")
    future = medicion(v["id"], fecha_medicion="2999-01-01T10:00:00+00:00")
    extra_field = {**medicion(v["id"]), "conductividad": 5.5}

    r = client.post(
        "/v1/sync/push",
        json={"vacas": [v], "mediciones": [good, out_of_range, bad_schema, naive_date, future, extra_field]},
        headers=device_a["headers"],
    )
    assert statuses(r, "mediciones") == ["accepted"] + ["rejected"] * 5
    reasons = [x.get("reason", "") for x in r.json()["results"]["mediciones"]]
    assert "ph_leche" in reasons[1]
    assert "futuro" in reasons[4]

    pulled = client.get("/v1/sync/pull", headers=device_a["headers"]).json()
    assert len(pulled["mediciones"]) == 1  # solo la válida quedó guardada


def test_missing_dependency_is_retry_then_accepted_later(client, device_a):
    v = vaca()
    m = medicion(v["id"])
    c = confirmacion(m["id"])

    r1 = client.post("/v1/sync/push", json={"mediciones": [m], "confirmaciones": [c]}, headers=device_a["headers"])
    assert statuses(r1, "mediciones") == ["retry"]
    assert statuses(r1, "confirmaciones") == ["retry"]

    r2 = client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [m], "confirmaciones": [c]}, headers=device_a["headers"])
    assert statuses(r2, "mediciones") == ["accepted"]
    assert statuses(r2, "confirmaciones") == ["accepted"]


def test_conflicting_resend_is_rejected_not_overwritten(client, device_a):
    v = vaca()
    m = medicion(v["id"], ph_leche=6.9)
    client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [m]}, headers=device_a["headers"])

    altered = copy.deepcopy(m)
    altered["ph_leche"] = 6.2
    r = client.post("/v1/sync/push", json={"mediciones": [altered]}, headers=device_a["headers"])
    assert statuses(r, "mediciones") == ["rejected"]
    assert "conflicto" in r.json()["results"]["mediciones"][0]["reason"]

    stored = client.get("/v1/sync/pull", headers=device_a["headers"]).json()["mediciones"][0]
    assert stored["ph_leche"] == 6.9

    renamed = {**v, "nombre": "Otro"}
    r = client.post("/v1/sync/push", json={"vacas": [renamed]}, headers=device_a["headers"])
    assert statuses(r, "vacas") == ["rejected"]


def test_duplicate_tag_in_same_farm_rejected(client, device_a):
    r = client.post(
        "/v1/sync/push",
        json={"vacas": [vaca("X-1"), vaca("X-1")]},
        headers=device_a["headers"],
    )
    assert statuses(r, "vacas") == ["accepted", "rejected"]


def test_farms_are_isolated(client, device_a, device_b):
    v = vaca()
    m = medicion(v["id"])
    client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [m]}, headers=device_a["headers"])

    # B no puede apropiarse de ids de A ni escribir sobre su vaca.
    r = client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [medicion(v["id"])]}, headers=device_b["headers"])
    assert statuses(r, "vacas") == ["rejected"]
    assert statuses(r, "mediciones") == ["rejected"]  # la vaca es de otra finca

    r = client.post("/v1/sync/push", json={"mediciones": [m]}, headers=device_b["headers"])
    assert statuses(r, "mediciones") == ["rejected"]

    pulled_b = client.get("/v1/sync/pull", headers=device_b["headers"]).json()
    assert pulled_b["vacas"] == [] and pulled_b["mediciones"] == []


def test_confirmation_grade_must_match_result(client, device_a):
    v = vaca()
    m = medicion(v["id"])
    client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [m]}, headers=device_a["headers"])
    bad = confirmacion(m["id"], positivo=True, grado="N")
    r = client.post("/v1/sync/push", json={"confirmaciones": [bad]}, headers=device_a["headers"])
    assert statuses(r, "confirmaciones") == ["rejected"]


def test_pull_paginates_with_cursors(client, device_a):
    vacas = [vaca(f"V-{i}") for i in range(5)]
    client.post("/v1/sync/push", json={"vacas": vacas}, headers=device_a["headers"])

    seen, cursor = [], 0
    while True:
        page = client.get(
            f"/v1/sync/pull?cursor_vacas={cursor}&limit=2", headers=device_a["headers"]
        ).json()
        seen += [v["id"] for v in page["vacas"]]
        cursor = page["cursors"]["vacas"]
        if not page["has_more"]:
            break
    assert seen == [v["id"] for v in vacas]


def test_oversized_batch_rejected(client, device_a):
    many = [vaca(f"V-{i}") for i in range(501)]
    r = client.post("/v1/sync/push", json={"vacas": many}, headers=device_a["headers"])
    assert r.status_code == 422


def test_model_distribution_with_matching_hash(client, device_a):
    manifest = client.get("/v1/model/manifest", headers=device_a["headers"]).json()
    r = client.get("/v1/model/lite", headers=device_a["headers"])
    assert r.status_code == 200
    assert hashlib.sha256(r.content).hexdigest() == manifest["files"]["model_lite.json"]
    assert r.headers["x-model-sha256"] == manifest["files"]["model_lite.json"]
    assert r.json()["model_version"] == manifest["model_version"]


def test_optional_inputs_may_be_missing_but_ph_may_not(client, device_a):
    v = vaca()
    ok = medicion(v["id"], volumen_de_leche=None, humedad=None, temperatura=None)
    no_ph = medicion(v["id"])
    del no_ph["ph_leche"]
    r = client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [ok, no_ph]}, headers=device_a["headers"])
    assert statuses(r, "mediciones") == ["accepted", "rejected"]
    # el reenvío sigue siendo idempotente con campos nulos
    r = client.post("/v1/sync/push", json={"mediciones": [ok]}, headers=device_a["headers"])
    assert statuses(r, "mediciones") == ["duplicate"]
    stored = client.get("/v1/sync/pull", headers=device_a["headers"]).json()["mediciones"][0]
    assert stored["humedad"] is None and stored["ph_leche"] == 6.9


def test_extreme_dates_are_rejected_not_500(client, device_a):
    v = vaca()
    old = medicion(v["id"], fecha_medicion="2019-12-31T23:00:00+00:00")
    overflow = medicion(v["id"], fecha_medicion="0001-01-01T00:00:00+05:00")
    r = client.post("/v1/sync/push", json={"vacas": [v], "mediciones": [old, overflow]}, headers=device_a["headers"])
    assert r.status_code == 200
    assert statuses(r, "mediciones") == ["rejected", "rejected"]


def test_concurrent_insert_race_returns_duplicate_instead_of_500(client, device_a, monkeypatch):
    """Simula que otra sesión inserta el mismo id entre la consulta y el insert."""
    from sqlalchemy import select
    from server.app.db import Medicion
    from server.app.routers import sync as sync_module

    v = vaca()
    m = medicion(v["id"])
    client.post("/v1/sync/push", json={"vacas": [v]}, headers=device_a["headers"])

    from sqlalchemy.orm import Session
    original = Session.scalar
    state = {"hide": True}

    def scalar(self, stmt, *a, **k):
        # La primera búsqueda del id de la medición "no la ve" (carrera simulada).
        if state["hide"] and "mediciones" in str(stmt) and "mediciones.id" in str(stmt):
            state["hide"] = False
            return None
        return original(self, stmt, *a, **k)

    first = client.post("/v1/sync/push", json={"mediciones": [m]}, headers=device_a["headers"])
    assert statuses(first, "mediciones") == ["accepted"]
    monkeypatch.setattr(Session, "scalar", scalar)
    second = client.post("/v1/sync/push", json={"mediciones": [m]}, headers=device_a["headers"])
    assert second.status_code == 200
    assert statuses(second, "mediciones") == ["duplicate"]
