"""Configuración del servidor (variables de entorno)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_url: str
    models_dir: Path
    admin_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("DATABASE_URL", "sqlite:///./server_data.db"),
            models_dir=Path(os.environ.get("MODELS_DIR", PROJECT_ROOT / "models")),
            admin_token=os.environ.get("ADMIN_TOKEN") or None,
        )
