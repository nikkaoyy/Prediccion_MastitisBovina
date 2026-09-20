"""Generador de datos sintéticos (dummy data) para pruebas.

Genera datos que respetan las correlaciones biológicas observadas en el
dataset real (datos_entrenamiento_mastitis-v3.csv, 208 registros, 6 fincas).

Distribuciones clave calibradas desde los datos reales:
  - Conductividad: Sana ~4.5 mS/cm, Mastitis ~7.2 mS/cm  (r = +0.917)
  - pH leche:      Sana ~6.55,      Mastitis ~6.95         (r = +0.851)
  - Volumen leche: Sana ~12.28 L,   Mastitis ~9.76 L       (r = -0.385)
"""

import numpy as np
import pandas as pd
from src.data.dataValidation import DataValidator


def generate_dummy_data(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Genera datos sintéticos calibrados con las distribuciones reales.

    La variable ``mastitis`` se determina PRIMERO, y luego los biomarcadores
    (conductividad, pH, volumen) se generan condicionados a ella, replicando
    las correlaciones clínicas observadas en campo.
    """
    rng = np.random.default_rng(random_state)

    ranges = DataValidator.CLINICAL_RANGES

    # ── 1. Variables independientes (no correlacionadas con mastitis) ────
    data = {
        "finca": [f"Finca_{rng.integers(1, 7)}" for _ in range(n_samples)],
        "edad": rng.integers(
            int(ranges["edad"][0]), int(ranges["edad"][1]) + 1, n_samples
        ),
        "raza": rng.choice(["Normando", "Holstein", "Jersey"], n_samples),
        "numero_de_partos": rng.integers(
            int(ranges["numero_de_partos"][0]),
            int(ranges["numero_de_partos"][1]) + 1,
            n_samples,
        ),
        "etapa_de_lactancia": rng.integers(0, 2, n_samples),
        "frecuencia_de_ordeno": np.full(n_samples, 2),
        "estado_de_vacunacion": rng.integers(0, 2, n_samples),
        "antecedentes_de_mastitis": rng.integers(0, 2, n_samples),
        "humedad": np.round(rng.uniform(60.0, 90.0, n_samples), 1),
        "temperatura": np.round(rng.uniform(10.0, 30.0, n_samples), 1),
    }

    df = pd.DataFrame(data)

    # ── 2. Determinar mastitis PRIMERO (≈53% positivo, como el real) ────
    # Factores de riesgo con pesos calibrados al dataset real.
    mastitis_logit = (
        (df["edad"] > 6).astype(float) * 0.15
        + (df["antecedentes_de_mastitis"] == 1).astype(float) * 0.35
        + (df["estado_de_vacunacion"] == 0).astype(float) * 0.10
        + (df["numero_de_partos"] > 4).astype(float) * 0.10
        + rng.uniform(0, 0.45, n_samples)
    )
    df["mastitis"] = (mastitis_logit > 0.50).astype(int)

    # ── 3. Biomarcadores CONDICIONADOS a mastitis (correlaciones reales) ─
    # Conductividad: Sana ≈ N(4.5, 0.6), Mastitis ≈ N(7.2, 0.8)
    df["conductividad_leche_ms_cm"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(4.5, 0.6, n_samples), 2),
        np.round(rng.normal(7.2, 0.8, n_samples), 2),
    )
    # Clamp al rango clínico válido [2.0, 15.0]
    df["conductividad_leche_ms_cm"] = df["conductividad_leche_ms_cm"].clip(
        ranges["conductividad_leche_ms_cm"][0],
        ranges["conductividad_leche_ms_cm"][1],
    )

    # pH leche: Sana ≈ N(6.55, 0.08), Mastitis ≈ N(6.95, 0.10)
    df["ph_leche"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(6.55, 0.08, n_samples), 2),
        np.round(rng.normal(6.95, 0.10, n_samples), 2),
    )
    df["ph_leche"] = df["ph_leche"].clip(
        ranges["ph_leche"][0], ranges["ph_leche"][1]
    )

    # Volumen de leche: Sana ≈ N(12.3, 2.5), Mastitis ≈ N(9.8, 2.0)
    # La mastitis REDUCE la producción (correlación negativa confirmada).
    df["volumen_de_leche"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(12.3, 2.5, n_samples), 1),
        np.round(rng.normal(9.8, 2.0, n_samples), 1),
    )
    df["volumen_de_leche"] = df["volumen_de_leche"].clip(0.5, None)

    # ── 4. Reordenar columnas para coincidir con el esquema del CSV real ─
    column_order = [
        "finca",
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
        "ph_leche",
        "conductividad_leche_ms_cm",
        "mastitis",
    ]

    return df[column_order]


if __name__ == "__main__":
    df = generate_dummy_data(500, random_state=123)
    print(f"Dummy data generada: {len(df)} muestras")
    print(f"Balance: {df['mastitis'].value_counts().to_dict()}")
    print(f"\nCorrelaciones con mastitis:")
    numeric_cols = df.select_dtypes(include="number").columns
    print(df[numeric_cols].corr()["mastitis"].sort_values(ascending=False))
    print(f"\nPrimeras 5 filas:")
    print(df.head())
