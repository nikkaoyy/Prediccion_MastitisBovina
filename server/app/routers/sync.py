"""Sincronización asíncrona cliente ↔ servidor (push idempotente, pull por cursor)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.app.db import ConfirmacionCmt, Dispositivo, Medicion, Vaca, utcnow
from server.app.schemas import ConfirmacionIn, MedicionIn, PushRequest, VacaIn
from server.app.security import current_device, get_session

router = APIRouter(prefix="/v1/sync", tags=["sync"])

ACCEPTED, DUPLICATE, REJECTED, RETRY = "accepted", "duplicate", "rejected", "retry"
CMT_POSITIVE_GRADES = {"1", "2", "3"}
MIN_DATE = datetime(2020, 1, 1)


def _utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _result(item_id: Any, status: str, reason: str | None = None) -> dict:
    out = {"id": str(item_id) if item_id is not None else None, "status": status}
    if reason:
        out["reason"] = reason
    return out


def _raw_id(raw: dict) -> str | None:
    value = raw.get("id") if isinstance(raw, dict) else None
    return str(value) if value is not None else None


def _reason(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(p) for p in first["loc"])
    return f"{location}: {first['msg']}"


def _same(row: Any, values: dict[str, Any]) -> bool:
    return all(getattr(row, key) == value for key, value in values.items())


def _range_violation(ranges: dict, medicion: MedicionIn) -> str | None:
    for name, (low, high) in ranges.items():
        value = getattr(medicion, name, None)
        if value is not None and not (low <= value <= high):
            return f"{name}: fuera de rango [{low}, {high}]"
    return None


def _process_vacas(items, device, session: Session) -> list[dict]:
    results = []
    for raw in items:
        try:
            vaca = VacaIn.model_validate(raw)
        except ValidationError as error:
            results.append(_result(_raw_id(raw), REJECTED, _reason(error)))
            continue

        values = {"arete": vaca.arete, "nombre": vaca.nombre}
        existing = session.scalar(select(Vaca).where(Vaca.id == str(vaca.id)))

        if existing is not None:
            if existing.finca_id != device.finca_id:
                results.append(_result(vaca.id, REJECTED, "vaca pertenece a otra finca"))
            elif _same(existing, values):
                results.append(_result(vaca.id, DUPLICATE))
            else:
                results.append(_result(vaca.id, REJECTED, "conflicto: la vaca ya existe con otros datos"))
            continue

        try:
            with session.begin_nested():
                session.add(
                    Vaca(id=str(vaca.id), finca_id=device.finca_id, device_id=device.id, **values)
                )
        except IntegrityError:
            # Carrera: otro envío insertó el mismo id (duplicado) o el mismo arete.
            raced = session.scalar(select(Vaca).where(Vaca.id == str(vaca.id)))
            if raced is not None and raced.finca_id == device.finca_id and _same(raced, values):
                results.append(_result(vaca.id, DUPLICATE))
            else:
                results.append(_result(vaca.id, REJECTED, "arete duplicado en la finca"))
            continue
        results.append(_result(vaca.id, ACCEPTED))
    return results


def _process_mediciones(items, device, session: Session, ranges: dict) -> list[dict]:
    results = []
    latest_allowed = utcnow() + timedelta(days=1)

    for raw in items:
        try:
            med = MedicionIn.model_validate(raw)
        except ValidationError as error:
            results.append(_result(_raw_id(raw), REJECTED, _reason(error)))
            continue

        violation = _range_violation(ranges, med)
        fecha = _utc_naive(med.fecha_medicion)
        if violation is None and fecha > latest_allowed:
            violation = "fecha_medicion: en el futuro"
        if violation is None and fecha < MIN_DATE:
            violation = "fecha_medicion: anterior a 2020"
        if violation:
            results.append(_result(med.id, REJECTED, violation))
            continue

        values = med.model_dump(exclude={"id", "vaca_id", "fecha_medicion"})
        values["fecha_medicion"] = fecha

        existing = session.scalar(select(Medicion).where(Medicion.id == str(med.id)))
        if existing is not None:
            if existing.finca_id != device.finca_id:
                results.append(_result(med.id, REJECTED, "medición pertenece a otra finca"))
            elif existing.vaca_id == str(med.vaca_id) and _same(existing, values):
                results.append(_result(med.id, DUPLICATE))
            else:
                results.append(_result(med.id, REJECTED, "conflicto: la medición ya existe con otros datos"))
            continue

        vaca = session.scalar(select(Vaca).where(Vaca.id == str(med.vaca_id)))
        if vaca is None:
            results.append(_result(med.id, RETRY, "vaca desconocida en el servidor"))
            continue
        if vaca.finca_id != device.finca_id:
            results.append(_result(med.id, REJECTED, "vaca pertenece a otra finca"))
            continue

        try:
            with session.begin_nested():
                session.add(
                    Medicion(
                        id=str(med.id), vaca_id=str(med.vaca_id),
                        finca_id=device.finca_id, device_id=device.id, **values,
                    )
                )
        except IntegrityError:  # carrera: otro envío insertó el mismo id
            raced = session.scalar(select(Medicion).where(Medicion.id == str(med.id)))
            same = (raced is not None and raced.finca_id == device.finca_id
                    and raced.vaca_id == str(med.vaca_id) and _same(raced, values))
            results.append(_result(med.id, DUPLICATE) if same
                           else _result(med.id, REJECTED, "conflicto: la medición ya existe con otros datos"))
            continue
        results.append(_result(med.id, ACCEPTED))
    return results


def _process_confirmaciones(items, device, session: Session) -> list[dict]:
    results = []
    for raw in items:
        try:
            conf = ConfirmacionIn.model_validate(raw)
        except ValidationError as error:
            results.append(_result(_raw_id(raw), REJECTED, _reason(error)))
            continue

        if conf.grado is not None and (conf.grado in CMT_POSITIVE_GRADES) != conf.resultado_positivo:
            results.append(_result(conf.id, REJECTED, "grado inconsistente con resultado_positivo"))
            continue

        values = {
            "fecha": _utc_naive(conf.fecha),
            "resultado_positivo": conf.resultado_positivo,
            "grado": conf.grado,
            "evaluador": conf.evaluador,
            "ciego_al_ph": conf.ciego_al_ph,
        }

        existing = session.scalar(select(ConfirmacionCmt).where(ConfirmacionCmt.id == str(conf.id)))
        if existing is not None:
            if existing.finca_id != device.finca_id:
                results.append(_result(conf.id, REJECTED, "confirmación pertenece a otra finca"))
            elif existing.medicion_id == str(conf.medicion_id) and _same(existing, values):
                results.append(_result(conf.id, DUPLICATE))
            else:
                results.append(_result(conf.id, REJECTED, "conflicto: la confirmación ya existe con otros datos"))
            continue

        medicion = session.scalar(select(Medicion).where(Medicion.id == str(conf.medicion_id)))
        if medicion is None:
            results.append(_result(conf.id, RETRY, "medición desconocida en el servidor"))
            continue
        if medicion.finca_id != device.finca_id:
            results.append(_result(conf.id, REJECTED, "medición pertenece a otra finca"))
            continue

        if values["fecha"] < MIN_DATE:
            results.append(_result(conf.id, REJECTED, "fecha: anterior a 2020"))
            continue
        try:
            with session.begin_nested():
                session.add(
                    ConfirmacionCmt(
                        id=str(conf.id), medicion_id=str(conf.medicion_id),
                        finca_id=device.finca_id, device_id=device.id, **values,
                    )
                )
        except IntegrityError:  # carrera: otro envío insertó el mismo id
            raced = session.scalar(select(ConfirmacionCmt).where(ConfirmacionCmt.id == str(conf.id)))
            same = (raced is not None and raced.finca_id == device.finca_id
                    and raced.medicion_id == str(conf.medicion_id) and _same(raced, values))
            results.append(_result(conf.id, DUPLICATE) if same
                           else _result(conf.id, REJECTED, "conflicto: la confirmación ya existe con otros datos"))
            continue
        results.append(_result(conf.id, ACCEPTED))
    return results


@router.post("/push")
def push(
    payload: PushRequest,
    request: Request,
    device: Dispositivo = Depends(current_device),
    session: Session = Depends(get_session),
) -> dict:
    """Recibe un lote. Idempotente: reenviar el mismo lote no duplica registros.

    Estados por ítem: ``accepted``, ``duplicate`` (ya estaba, equivale a éxito),
    ``rejected`` (error permanente; no reintentar) y ``retry`` (falta una
    dependencia que aún no llegó; reintentar en la próxima sincronización).
    """

    ranges = request.app.state.ranges
    vacas = _process_vacas(payload.vacas, device, session)
    session.flush()
    mediciones = _process_mediciones(payload.mediciones, device, session, ranges)
    session.flush()
    confirmaciones = _process_confirmaciones(payload.confirmaciones, device, session)
    session.commit()

    return {
        "results": {"vacas": vacas, "mediciones": mediciones, "confirmaciones": confirmaciones},
        "server_time": datetime.now(timezone.utc).isoformat(),
        "model_version": request.app.state.model_version,
    }


def _iso(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat()


@router.get("/pull")
def pull(
    request: Request,
    cursor_vacas: int = Query(0, ge=0),
    cursor_mediciones: int = Query(0, ge=0),
    cursor_confirmaciones: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    device: Dispositivo = Depends(current_device),
    session: Session = Depends(get_session),
) -> dict:
    """Cambios de la finca del dispositivo posteriores a los cursores dados."""

    def page(model, cursor):
        rows = session.scalars(
            select(model)
            .where(model.finca_id == device.finca_id, model.seq > cursor)
            .order_by(model.seq)
            .limit(limit + 1)
        ).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return rows, (rows[-1].seq if rows else cursor), has_more

    vacas, c_vacas, more_v = page(Vaca, cursor_vacas)
    meds, c_meds, more_m = page(Medicion, cursor_mediciones)
    confs, c_confs, more_c = page(ConfirmacionCmt, cursor_confirmaciones)

    return {
        "vacas": [{"id": v.id, "arete": v.arete, "nombre": v.nombre} for v in vacas],
        "mediciones": [
            {
                "id": m.id, "vaca_id": m.vaca_id, "fecha_medicion": _iso(m.fecha_medicion),
                "edad": m.edad, "raza": m.raza, "numero_de_partos": m.numero_de_partos,
                "volumen_de_leche": m.volumen_de_leche, "etapa_de_lactancia": m.etapa_de_lactancia,
                "antecedentes_de_mastitis": m.antecedentes_de_mastitis, "humedad": m.humedad,
                "temperatura": m.temperatura, "ph_leche": m.ph_leche,
                "probabilidad": m.probabilidad, "nivel_riesgo": m.nivel_riesgo,
                "model_version": m.model_version,
            }
            for m in meds
        ],
        "confirmaciones": [
            {
                "id": c.id, "medicion_id": c.medicion_id, "fecha": _iso(c.fecha),
                "resultado_positivo": c.resultado_positivo, "grado": c.grado,
                "evaluador": c.evaluador, "ciego_al_ph": c.ciego_al_ph,
            }
            for c in confs
        ],
        "cursors": {
            "vacas": c_vacas, "mediciones": c_meds, "confirmaciones": c_confs,
        },
        "has_more": more_v or more_m or more_c,
        "model_version": request.app.state.model_version,
    }
