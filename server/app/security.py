"""Autenticación por token de dispositivo (Bearer) y token de administrador."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.app.db import Dispositivo


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def get_session(request: Request):
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def current_device(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Dispositivo:
    token = _bearer(authorization)
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token de dispositivo inválido o ausente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized

    device = session.scalar(
        select(Dispositivo).where(Dispositivo.token_hash == hash_token(token))
    )
    if device is None or not device.activo:
        raise unauthorized
    return device


def require_admin(
    request: Request, authorization: str | None = Header(default=None)
) -> None:
    expected = request.app.state.settings.admin_token
    if not expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administración deshabilitada.")

    token = _bearer(authorization) or ""
    if not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de administrador inválido.")
