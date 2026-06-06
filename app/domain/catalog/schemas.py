from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ClausulaMaestraCreate(BaseModel):
    codigo: str
    tipo: str                               # ENTREGA|CALIDAD|PAGO|...
    titulo: str
    contenido_actual: str
    sector: Optional[str] = None
    nicho: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrecioMaestroCreate(BaseModel):
    codigo: str
    producto: str
    precio: float
    categoria: Optional[str] = None
    moneda: str = "COP"
    unidad: Optional[str] = None
    sector: Optional[str] = None
    nicho: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClausulaMaestraOut(BaseModel):
    id: int
    codigo: str
    tipo: str
    titulo: str
    contenido_actual: str
    version: int
    sector: Optional[str]
    nicho: Optional[str]
    vigente: bool


class PrecioMaestroOut(BaseModel):
    id: int
    codigo: str
    producto: str
    categoria: Optional[str]
    precio: float
    moneda: str
    unidad: Optional[str]
    version: int
    vigente: bool
