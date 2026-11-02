"""Distribución del modelo lite a los clientes."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from server.app.security import current_device

router = APIRouter(prefix="/v1/model", tags=["model"], dependencies=[Depends(current_device)])


def _manifest(request: Request) -> dict:
    path = request.app.state.settings.models_dir / "manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(503, "Modelo no disponible en el servidor.") from None


@router.get("/manifest")
def manifest(request: Request) -> dict:
    return _manifest(request)


@router.get("/lite")
def lite(request: Request) -> Response:
    """Entrega model_lite.json verificando su hash contra el manifiesto."""

    expected = _manifest(request)["files"]["model_lite.json"]
    body = (request.app.state.settings.models_dir / "model_lite.json").read_bytes()

    if hashlib.sha256(body).hexdigest() != expected:
        raise HTTPException(500, "El modelo en disco no coincide con el manifiesto.")

    return Response(
        content=body,
        media_type="application/json",
        headers={"ETag": f'"{expected}"', "X-Model-Sha256": expected},
    )
