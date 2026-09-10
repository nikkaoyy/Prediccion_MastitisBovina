"""Generador de datos sintéticos (dummy data) para pruebas."""

import numpy as np
import pandas as pd
from src.data.dataValidation import DataValidator

def generate_dummy_data(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Genera datos sintéticos basados en los rangos clínicos definidos."""
    np.random.seed(random_state)
    
    ranges = DataValidator.CLINICAL_RANGES
    
    data = {
        "finca": [f"Finca_{np.random.randint(1, 6)}" for _ in range(n_samples)],
        "edad": np.random.randint(int(ranges["edad"][0]), int(ranges["edad"][1]) + 1, n_samples),
        "raza": np.random.choice(["Normando", "Holstein", "Jersey"], n_samples),
        "numero_de_partos": np.random.randint(int(ranges["numero_de_partos"][0]), int(ranges["numero_de_partos"][1]) + 1, n_samples),
        "volumen_de_leche": np.round(np.random.uniform(ranges["volumen_de_leche"][0], ranges["volumen_de_leche"][1] / 2, n_samples), 1),
        "etapa_de_lactancia": np.random.randint(0, 2, n_samples),
        "frecuencia_de_ordeno": np.full(n_samples, 2),
        "estado_de_vacunacion": np.random.randint(0, 2, n_samples),
        "antecedentes_de_mastitis": np.random.randint(0, 2, n_samples),
        "humedad": np.round(np.random.uniform(60.0, 90.0, n_samples), 1),
        "temperatura": np.round(np.random.uniform(10.0, 30.0, n_samples), 1),
        "ph_leche": np.round(np.random.uniform(ranges["ph_leche"][0], ranges["ph_leche"][1], n_samples), 2),
        "conductividad_leche_ms_cm": np.round(np.random.uniform(ranges["conductividad_leche_ms_cm"][0], ranges["conductividad_leche_ms_cm"][1], n_samples), 2),
    }
    
    df = pd.DataFrame(data)
    
    # Simular la correlación anómala mencionada por el usuario (volumen alto -> mastitis) 
    # y otras relaciones plausibles para que los modelos puedan aprender algo
    mastitis_prob = (
        (df["edad"] > 8).astype(float) * 0.2 +
        (df["antecedentes_de_mastitis"] == 1).astype(float) * 0.3 + 
        (df["volumen_de_leche"] > 25).astype(float) * 0.3 +
        (df["estado_de_vacunacion"] == 0).astype(float) * 0.1
    )
    mastitis_prob = np.clip(mastitis_prob + np.random.uniform(0, 0.4, n_samples), 0, 1)
    
    df["mastitis"] = (mastitis_prob > 0.5).astype(int)
    
    return df

if __name__ == "__main__":
    df = generate_dummy_data(10)
    print("Dummy data generada (10 muestras):")
    print(df)
