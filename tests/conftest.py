from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "raw" / "datos_entrenamiento_mastitis-v3.csv"


@pytest.fixture(scope="session")
def raw_data() -> pd.DataFrame:
    return pd.read_csv(DATASET)
