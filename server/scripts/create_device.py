"""Registra una finca y un dispositivo y muestra su token (se muestra una sola vez).

Uso:  python -m server.scripts.create_device --finca "Finca El Roble" --nombre "Celular Juan"
"""

from __future__ import annotations

import argparse
import uuid

from sqlalchemy import select

from server.app.config import Settings
from server.app.db import Base, Dispositivo, Finca, make_engine, make_session_factory
from server.app.security import hash_token, new_token


def register_device(settings: Settings, finca: str, nombre: str) -> tuple[str, str, str]:
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as session:
        row = session.scalar(select(Finca).where(Finca.nombre == finca))
        if row is None:
            row = Finca(id=str(uuid.uuid4()), nombre=finca)
            session.add(row)
            session.flush()
        token = new_token()
        device = Dispositivo(
            id=str(uuid.uuid4()), nombre=nombre, finca_id=row.id, token_hash=hash_token(token)
        )
        session.add(device)
        session.commit()
        return row.id, device.id, token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finca", required=True)
    parser.add_argument("--nombre", required=True, help="Nombre del dispositivo")
    args = parser.parse_args()

    finca_id, device_id, token = register_device(Settings.from_env(), args.finca, args.nombre)
    print(f"finca_id:  {finca_id}")
    print(f"device_id: {device_id}")
    print(f"token:     {token}")
    print("Guarde el token ahora: no se puede recuperar.")


if __name__ == "__main__":
    main()
