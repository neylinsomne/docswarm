"""Dependencias de FastAPI: usuario autenticado + propagación de tenant a RLS.

``get_current_principal`` decodifica el JWT y fija el ContextVar de tenant:
  · COMPRADOR (Bayern) → tenant None (admin: ve todo).
  · PROVEEDOR          → tenant = su empresa_id (RLS lo aísla).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.db import set_request_empresa
from app.security.tokens import decode_token
from app.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def require_service_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Auth máquina-a-máquina para el microservicio notifier / repo WhatsApp+Gmail.

    Corre en contexto admin (tenant None = ve/actualiza todos los tenants).
    """
    if x_api_key != settings.service_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="X-API-Key inválida")
    set_request_empresa(None)


@dataclass
class Principal:
    usuario_id: int
    empresa_id: int
    tipo_empresa: str       # COMPRADOR | PROVEEDOR
    rol: str

    @property
    def is_admin(self) -> bool:
        return self.tipo_empresa == "COMPRADOR"

    @property
    def tenant(self) -> Optional[int]:
        """Tenant efectivo para RLS (None = admin ve todo)."""
        return None if self.is_admin else self.empresa_id


def get_current_principal(token: str = Depends(oauth2_scheme)) -> Principal:
    try:
        payload = decode_token(token)
        principal = Principal(
            usuario_id=int(payload["sub"]),
            empresa_id=int(payload["empresa_id"]),
            tipo_empresa=payload["tipo_empresa"],
            rol=payload.get("rol", "MIEMBRO"),
        )
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Propaga el tenant a RLS para toda la request.
    set_request_empresa(principal.tenant)
    return principal


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Solo Bayern (COMPRADOR) puede tocar el catálogo maestro y registrar cambios."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la empresa compradora (Bayern) puede realizar esta acción",
        )
    return principal
