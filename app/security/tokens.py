"""Emisión y validación de JWT de acceso."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from app.settings import settings


def create_access_token(
    *, usuario_id: int, empresa_id: int, tipo_empresa: str, rol: str,
    expires_minutes: Optional[int] = None,
) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.jwt_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "empresa_id": empresa_id,
        "tipo_empresa": tipo_empresa,   # COMPRADOR (admin) | PROVEEDOR
        "rol": rol,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
