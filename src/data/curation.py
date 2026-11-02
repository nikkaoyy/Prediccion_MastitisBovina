"""Curación de etiquetas del dataset de mastitis.

Solo unifica la escritura de ``finca`` y ``raza``. No toca valores numéricos ni
imputa: la conductividad faltante de Finca 6 se resuelve dentro del Pipeline,
con la mediana del pliegue de entrenamiento. Decisiones en
``docs/CURACION_DATOS.md``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.data.dataValidation import DataValidationError
from src.paths import DATASET_PATH

FINCAS_ADMITIDAS = tuple(f"Finca_{n}" for n in range(1, 7))

RAZAS_ADMITIDAS = ("Holstein", "Normando", "Jersey", "Pardo_Suizo", "Cruzado")

# Clave normalizada (sin tildes, minúsculas, con "_") -> nombre canónico.
# Solo se agregan variantes de escritura de una misma raza: nunca se reasigna
# un animal a una raza distinta de la registrada.
_RAZA_CANONICA = {
    **{raza.lower(): raza for raza in RAZAS_ADMITIDAS},
    "hounstein": "Holstein",
    "normanda": "Normando",
}

_PATRON_FINCA = re.compile(r"finca_(\d+)")


def _clave(valor: str) -> str:
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"[\s_]+", "_", sin_tildes.strip().casefold())


def _finca_canonica(valor: str) -> str:
    coincidencia = _PATRON_FINCA.fullmatch(_clave(valor))

    if coincidencia is None:
        raise DataValidationError(f"Finca no reconocida: {valor!r}")

    return f"Finca_{int(coincidencia.group(1))}"


def _raza_canonica(valor: str) -> str:
    try:
        return _RAZA_CANONICA[_clave(valor)]
    except KeyError:
        raise DataValidationError(
            f"Raza no reconocida: {valor!r}. Admitidas: {RAZAS_ADMITIDAS}. "
            "Si es una raza nueva, agréguela a RAZAS_ADMITIDAS."
        ) from None


def curate(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Devuelve una copia curada y las filas cambiadas por columna.

    Los vacíos se conservan: los resuelve el Pipeline. Una etiqueta
    desconocida lanza ``DataValidationError`` en vez de pasar en silencio.
    """

    curated = data.copy(deep=True)
    changed: dict[str, int] = {}

    for column, canonical in (("finca", _finca_canonica), ("raza", _raza_canonica)):
        original = curated[column]
        present = original.notna()
        repaired = original[present].astype(str).map(canonical)
        changed[column] = int((repaired != original[present]).sum())
        curated.loc[present, column] = repaired

    return curated, changed


def assert_curated(data: pd.DataFrame) -> None:
    """Falla si reaparece una finca o raza fuera de las admitidas."""

    fincas = set(data["finca"].dropna())
    razas = set(data["raza"].dropna())

    extra_fincas = sorted(fincas - set(FINCAS_ADMITIDAS))
    extra_razas = sorted(razas - set(RAZAS_ADMITIDAS))

    if extra_fincas or extra_razas:
        raise DataValidationError(
            f"Etiquetas sin curar. Fincas: {extra_fincas}. Razas: {extra_razas}."
        )


def load_curated_dataset(path: str | Path = DATASET_PATH) -> pd.DataFrame:
    """Lee el CSV, unifica etiquetas y verifica el resultado."""

    curated, _ = curate(pd.read_csv(path))
    assert_curated(curated)
    return curated
