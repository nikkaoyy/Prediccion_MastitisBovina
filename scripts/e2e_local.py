"""Prueba E2E local: servidor FastAPI real + cliente Dart real (sin dispositivo).

1. Crea una base SQLite temporal y registra un dispositivo.
2. Levanta uvicorn en un puerto libre.
3. Ejecuta `flutter test test/e2e` (offline → online → reenvío → segundo teléfono).
4. Verifica en la base que cada registro existe exactamente una vez.

Uso:  .venv/bin/python scripts/e2e_local.py
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from server.app.config import Settings  # noqa: E402
from server.scripts.create_device import register_device  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_flutter() -> str:
    for candidate in (os.environ.get("FLUTTER_BIN"), shutil.which("flutter"),
                      str(Path.home() / "development/flutter/bin/flutter")):
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("No se encontró Flutter (defina FLUTTER_BIN).")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="e2e_mastitis_"))
    db_url = f"sqlite:///{tmp / 'e2e.db'}"
    settings = Settings(database_url=db_url, models_dir=ROOT / "models", admin_token=None)
    _, _, token = register_device(settings, "Finca E2E", "Celular E2E")

    port = free_port()
    env = {**os.environ, "DATABASE_URL": db_url, "MODELS_DIR": str(ROOT / "models")}
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=1).read()
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise SystemExit("El servidor no arrancó.")

        out = tmp / "ids.json"
        flutter_env = {**os.environ, "E2E_SERVER_URL": base, "E2E_TOKEN": token, "E2E_OUT": str(out),
                       "PATH": f"{Path(find_flutter()).parent}:{os.environ['PATH']}",
                       "ANDROID_HOME": os.environ.get("ANDROID_HOME", str(Path.home() / "Android/Sdk"))}
        result = subprocess.run([find_flutter(), "test", "test/e2e/sync_e2e_test.dart"],
                                cwd=ROOT / "mobile", env=flutter_env)
        if result.returncode != 0:
            print("FALLÓ la prueba Dart E2E")
            return result.returncode

        expected = set(json.loads(out.read_text())["ids"])
        engine = create_engine(db_url)
        with engine.connect() as conn:
            counts = {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                      for t in ("vacas", "mediciones", "confirmaciones_cmt")}
            stored = set()
            for t in ("vacas", "mediciones", "confirmaciones_cmt"):
                stored |= {r[0] for r in conn.execute(text(f"SELECT id FROM {t}"))}
            distinct = conn.execute(text("SELECT COUNT(DISTINCT id) FROM mediciones")).scalar()

        print("Filas en el servidor:", counts)
        ok = counts == {"vacas": 3, "mediciones": 6, "confirmaciones_cmt": 3} and stored == expected \
            and distinct == counts["mediciones"]
        print("E2E OK: exactamente una vez cada registro" if ok else "E2E FALLÓ: la base no coincide")
        return 0 if ok else 1
    finally:
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
