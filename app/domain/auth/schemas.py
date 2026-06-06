from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    empresa_id: int
    tipo_empresa: str
    rol: str


class RegisterUsuario(BaseModel):
    """Alta de usuario para una empresa existente (acción de admin de la empresa)."""
    empresa_id: int
    email: EmailStr
    password: str
    nombre: str | None = None
    rol: str = "MIEMBRO"
