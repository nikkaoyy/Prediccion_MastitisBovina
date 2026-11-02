"""Esquemas de entrada de la API de sincronización."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_BATCH_ITEMS = 500


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _check_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} debe incluir zona horaria (ISO 8601)")
    try:
        value.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise ValueError(f"{name} fuera de rango") from None
    return value


class VacaIn(_Strict):
    id: UUID
    arete: str = Field(min_length=1, max_length=40)
    nombre: str | None = Field(default=None, max_length=80)


class MedicionIn(_Strict):
    id: UUID
    vaca_id: UUID
    fecha_medicion: datetime
    edad: int
    raza: str = Field(min_length=1, max_length=40)
    numero_de_partos: int
    volumen_de_leche: float | None = None
    etapa_de_lactancia: Literal[0, 1]
    antecedentes_de_mastitis: Literal[0, 1]
    humedad: float | None = None
    temperatura: float | None = None
    ph_leche: float
    probabilidad: float = Field(ge=0.0, le=1.0)
    nivel_riesgo: Literal["bajo", "medio", "alto"]
    model_version: str = Field(min_length=1, max_length=40)

    @field_validator("fecha_medicion")
    @classmethod
    def _needs_timezone(cls, value: datetime) -> datetime:
        return _check_aware(value, "fecha_medicion")


class ConfirmacionIn(_Strict):
    id: UUID
    medicion_id: UUID
    fecha: datetime
    resultado_positivo: bool
    grado: Literal["N", "T", "1", "2", "3"] | None = None
    evaluador: str | None = Field(default=None, max_length=80)
    ciego_al_ph: bool = False

    @field_validator("fecha")
    @classmethod
    def _needs_timezone(cls, value: datetime) -> datetime:
        return _check_aware(value, "fecha")


class PushRequest(BaseModel):
    """Lote de registros; cada ítem se valida por separado (aceptación parcial)."""

    vacas: list[dict] = Field(default_factory=list)
    mediciones: list[dict] = Field(default_factory=list)
    confirmaciones: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def _batch_size(self) -> "PushRequest":
        total = len(self.vacas) + len(self.mediciones) + len(self.confirmaciones)
        if total > MAX_BATCH_ITEMS:
            raise ValueError(f"El lote supera {MAX_BATCH_ITEMS} registros")
        return self
