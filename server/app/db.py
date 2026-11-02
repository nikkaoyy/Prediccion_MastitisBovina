"""Modelo de datos (SQLAlchemy 2.0). SQLite en desarrollo, Postgres en producción."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> datetime:
    """UTC 'naive' (SQLite no conserva zona horaria)."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Finca(Base):
    __tablename__ = "fincas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    finca_id: Mapped[str] = mapped_column(ForeignKey("fincas.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Vaca(Base):
    __tablename__ = "vacas"
    __table_args__ = (UniqueConstraint("finca_id", "arete"),)

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    finca_id: Mapped[str] = mapped_column(ForeignKey("fincas.id"), index=True)
    arete: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str | None] = mapped_column(String(80), nullable=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("dispositivos.id"))
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Medicion(Base):
    __tablename__ = "mediciones"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    vaca_id: Mapped[str] = mapped_column(ForeignKey("vacas.id"), index=True)
    finca_id: Mapped[str] = mapped_column(ForeignKey("fincas.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("dispositivos.id"))
    fecha_medicion: Mapped[datetime] = mapped_column(DateTime, index=True)

    edad: Mapped[int] = mapped_column(Integer)
    raza: Mapped[str] = mapped_column(String(40))
    numero_de_partos: Mapped[int] = mapped_column(Integer)
    volumen_de_leche: Mapped[float | None] = mapped_column(Float, nullable=True)
    etapa_de_lactancia: Mapped[int] = mapped_column(Integer)
    antecedentes_de_mastitis: Mapped[int] = mapped_column(Integer)
    humedad: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperatura: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph_leche: Mapped[float] = mapped_column(Float)

    probabilidad: Mapped[float] = mapped_column(Float)
    nivel_riesgo: Mapped[str] = mapped_column(String(10))
    model_version: Mapped[str] = mapped_column(String(40))
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConfirmacionCmt(Base):
    __tablename__ = "confirmaciones_cmt"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    medicion_id: Mapped[str] = mapped_column(ForeignKey("mediciones.id"), index=True)
    finca_id: Mapped[str] = mapped_column(ForeignKey("fincas.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("dispositivos.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime)
    resultado_positivo: Mapped[bool] = mapped_column(Boolean)
    grado: Mapped[str | None] = mapped_column(String(2), nullable=True)
    evaluador: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ciego_al_ph: Mapped[bool] = mapped_column(Boolean, default=False)
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


def make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool

    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _):  # pragma: no cover - trivial
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
