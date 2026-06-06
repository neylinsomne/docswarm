"""Endpoints de autenticación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.domain.auth import schemas, service
from app.security.deps import Principal, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login OAuth2 (username = email). Devuelve un JWT con empresa_id/tipo/rol."""
    token = service.login(form.username, form.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def crear_usuario(data: schemas.RegisterUsuario,
                  _admin: Principal = Depends(require_admin)):
    """Alta de usuario para una empresa (solo Bayern/admin)."""
    return {"id": service.register_usuario(data)}
