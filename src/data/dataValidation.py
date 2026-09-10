"""Validación y normalización de datos para mastitis subclínica bovina."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """Señala que el dataset no cumple el contrato clínico/técnico."""


@dataclass(frozen=True)
class DataQualityReport:
    """Resultado auditable de una validación de calidad de datos."""

    row_count: int
    missing_by_column: dict[str, int]
    coercions_to_missing: dict[str, int]
    unique_farms: int

    def to_dict(self) -> dict[str, Any]:
        """Devuelve un objeto apto para persistirse como JSON."""
        return asdict(self)


class DataValidator:
    """Valida esquema, tipos y rangos clínicamente plausibles del dataset."""

    GROUP_COLUMN = "finca"
    TARGET_COLUMN = "mastitis"

    NUMERIC_COLUMNS = (
        "edad",
        "numero_de_partos",
        "volumen_de_leche",
        "etapa_de_lactancia",
        "frecuencia_de_ordeno",
        "estado_de_vacunacion",
        "antecedentes_de_mastitis",
        "humedad",
        "temperatura",
        TARGET_COLUMN,
    )

    CATEGORICAL_COLUMNS = ("raza",)

    FEATURE_COLUMNS = (
        "edad",
        "raza",
        "numero_de_partos",
        "volumen_de_leche",
        "etapa_de_lactancia",
        "frecuencia_de_ordeno",
        "estado_de_vacunacion",
        "antecedentes_de_mastitis",
        "humedad",
        "temperatura",
    )

    REQUIRED_COLUMNS = (GROUP_COLUMN, *FEATURE_COLUMNS, TARGET_COLUMN)

    CLINICAL_RANGES = {
        "edad": (1.0, 25.0),
        "numero_de_partos": (0.0, 20.0),
        "volumen_de_leche": (0.0, 100.0),
        "humedad": (0.0, 100.0),
        "temperatura": (-20.0, 50.0),
        "estado_de_vacunacion": (0.0, 3.0),
    }

    INTEGER_COLUMNS = (
        "edad",
        "numero_de_partos",
        "etapa_de_lactancia",
        "frecuencia_de_ordeno",
        "estado_de_vacunacion",
        "antecedentes_de_mastitis",
        TARGET_COLUMN,
    )

    ALLOWED_VALUES = {
        "etapa_de_lactancia": {0.0, 1.0},
        "frecuencia_de_ordeno": {2.0},
        "estado_de_vacunacion": {0.0, 1.0, 2.0, 3.0},
        "antecedentes_de_mastitis": {0.0, 1.0},
        TARGET_COLUMN: {0.0, 1.0},
    }

    def validate_and_clean(
        self, data: pd.DataFrame
    ) -> tuple[pd.DataFrame, DataQualityReport]:
        """Normaliza números y comprueba el contrato del dataset."""
        self._validate_schema(data)

        cleaned = data.copy(deep=True)
        coercions_to_missing: dict[str, int] = {}

        for column in self.NUMERIC_COLUMNS:
            parsed = self._to_numeric(cleaned[column])
            coerced = int((cleaned[column].notna() & parsed.isna()).sum())
            coercions_to_missing[column] = coerced

            if coerced:
                raise DataValidationError(
                    f"La columna '{column}' tiene {coerced} valor(es) no numéricos. "
                    "Corrija el origen antes de entrenar."
                )

            cleaned[column] = parsed

        for column in (self.GROUP_COLUMN, *self.CATEGORICAL_COLUMNS):
            cleaned[column] = cleaned[column].astype("string").str.strip()
            cleaned.loc[cleaned[column].eq(""), column] = pd.NA

        self._validate_required_non_null(cleaned)
        self._validate_ranges_and_allowed_values(cleaned)
        self._validate_group_values(cleaned)

        report = DataQualityReport(
            row_count=int(len(cleaned)),
            missing_by_column={
                column: int(cleaned[column].isna().sum())
                for column in self.REQUIRED_COLUMNS
            },
            coercions_to_missing=coercions_to_missing,
            unique_farms=int(cleaned[self.GROUP_COLUMN].nunique(dropna=True)),
        )

        return cleaned, report

    def _validate_schema(self, data: pd.DataFrame) -> None:
        if data.empty:
            raise DataValidationError("El dataset está vacío.")

        missing = sorted(set(self.REQUIRED_COLUMNS) - set(data.columns))

        if missing:
            raise DataValidationError(
                "Faltan columnas requeridas: " + ", ".join(missing)
            )

    @staticmethod
    def _to_numeric(series: pd.Series) -> pd.Series:
        """Convierte números con coma decimal o separadores de miles a float."""

        def normalize(value: Any) -> Any:
            if pd.isna(value) or isinstance(value, (int, float, np.number)):
                return value

            text = str(value).strip().replace(" ", "").replace("\u00a0", "")

            if not text:
                return np.nan

            if "," in text and "." in text:
                if text.rfind(",") > text.rfind("."):
                    return text.replace(".", "").replace(",", ".")
                return text.replace(",", "")

            return text.replace(",", ".")

        return pd.to_numeric(series.map(normalize), errors="coerce")

    def _validate_required_non_null(self, data: pd.DataFrame) -> None:
        non_nullable = (self.GROUP_COLUMN, self.TARGET_COLUMN)
        failures = [column for column in non_nullable if data[column].isna().any()]

        if failures:
            raise DataValidationError(
                "No se admiten nulos en columnas estructurales: "
                + ", ".join(failures)
            )

    def _validate_ranges_and_allowed_values(self, data: pd.DataFrame) -> None:
        violations: list[str] = []

        for column, (minimum, maximum) in self.CLINICAL_RANGES.items():
            invalid = data[column].notna() & ~data[column].between(minimum, maximum)

            if invalid.any():
                violations.append(
                    f"{column}: {int(invalid.sum())} fuera de [{minimum}, {maximum}]"
                )

        for column in self.INTEGER_COLUMNS:
            values = data[column].dropna()
            invalid = ~np.isclose(values, np.round(values))

            if invalid.any():
                violations.append(f"{column}: debe contener valores enteros")

        for column, allowed in self.ALLOWED_VALUES.items():
            invalid = data[column].notna() & ~data[column].isin(allowed)

            if invalid.any():
                expected = ", ".join(str(int(value)) for value in sorted(allowed))
                violations.append(f"{column}: valores permitidos {{{expected}}}")

        if violations:
            raise DataValidationError("; ".join(violations))

    def _validate_group_values(self, data: pd.DataFrame) -> None:
        """Exige finca válida, pero permite nulos de features para imputación."""
        if data[self.GROUP_COLUMN].isna().any():
            raise DataValidationError(
                "No se admiten nulos o textos vacíos en finca."
            )