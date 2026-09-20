"""Generador de datos sintéticos (dummy data) para pruebas.

Genera datos que respetan las correlaciones biológicas observadas en el
dataset real (datos_entrenamiento_mastitis-v3.csv, 208 registros, 6 fincas).

Distribuciones clave calibradas desde los datos reales:
  - Conductividad: Sana ~4.66 ± 0.24,  Mastitis ~6.27 ± 0.42
  - pH leche:      Sana ~6.60 ± 0.07,  Mastitis ~6.91 ± 0.11
  - Volumen leche: Sana ~12.28 ± 2.64, Mastitis ~9.76 ± 3.32
  - Edad:          3–12 años   (media 5.5)
  - Partos:        1–10        (media 2.8)
  - Razas:         Holstein 61%, Normando 28%, Jersey 6%, Pardo_Suizo 3%, Cruzado 2%
"""

import sys
from pathlib import Path

# Agregar la raíz del proyecto a sys.path para que los imports absolutos funcionen
# sin importar cómo se ejecute el script (python archivo.py o python -m ...)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
    # Probabilidades de raza basadas en datos reales
    razas = ["Holstein", "Normando", "Jersey", "Pardo_Suizo", "Cruzado"]
    p_razas = [0.61, 0.28, 0.06, 0.03, 0.02]
    
    data = {
        "finca": [f"Finca_{rng.integers(1, 7)}" for _ in range(n_samples)],
        # Edad real: mean=5.5, min=3, max=12
        "edad": np.clip(np.round(rng.normal(5.5, 1.6, n_samples)), 3, 12).astype(int),
        "raza": rng.choice(razas, n_samples, p=p_razas),
        # Partos reales: mean=2.8, min=1, max=10
        "numero_de_partos": np.clip(np.round(rng.normal(2.8, 1.6, n_samples)), 1, 10).astype(int),
        "etapa_de_lactancia": rng.integers(0, 2, n_samples),
        "frecuencia_de_ordeno": np.full(n_samples, 2),
        "estado_de_vacunacion": rng.integers(0, 2, n_samples),
        "antecedentes_de_mastitis": rng.integers(0, 2, n_samples),
        "humedad": np.round(rng.uniform(60.0, 90.0, n_samples), 1),
        "temperatura": np.round(rng.uniform(10.0, 30.0, n_samples), 1),
    }

    df = pd.DataFrame(data)

    # ── 2. Determinar mastitis PRIMERO (≈53% positivo, como el real) ────
    mastitis_logit = (
        (df["edad"] > 6).astype(float) * 0.15
        + (df["antecedentes_de_mastitis"] == 1).astype(float) * 0.35
        + (df["estado_de_vacunacion"] == 0).astype(float) * 0.10
        + (df["numero_de_partos"] > 4).astype(float) * 0.10
        + rng.uniform(0, 0.45, n_samples)
    )
    df["mastitis"] = (mastitis_logit > 0.45).astype(int)

    # ── 3. Biomarcadores CONDICIONADOS a mastitis (correlaciones reales) ─
    # Conductividad: Sana ~4.66 ± 0.24,  Mastitis ~6.27 ± 0.42
    df["conductividad_leche_ms_cm"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(4.66, 0.24, n_samples), 2),
        np.round(rng.normal(6.27, 0.42, n_samples), 2),
    )
    # Clamp al rango clínico válido [2.0, 15.0]
    df["conductividad_leche_ms_cm"] = df["conductividad_leche_ms_cm"].clip(
        ranges["conductividad_leche_ms_cm"][0],
        ranges["conductividad_leche_ms_cm"][1],
    )

    # pH leche: Sana ~6.60 ± 0.07,  Mastitis ~6.91 ± 0.11
    df["ph_leche"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(6.60, 0.07, n_samples), 2),
        np.round(rng.normal(6.91, 0.11, n_samples), 2),
    )
    df["ph_leche"] = df["ph_leche"].clip(
        ranges["ph_leche"][0], ranges["ph_leche"][1]
    )

    # Volumen de leche: Sana ~12.28 ± 2.64, Mastitis ~9.76 ± 3.32
    df["volumen_de_leche"] = np.where(
        df["mastitis"] == 0,
        np.round(rng.normal(12.28, 2.64, n_samples), 1),
        np.round(rng.normal(9.76, 3.32, n_samples), 1),
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
