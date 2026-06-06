from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class ClausulaCreate(BaseModel):
    tipo: str                               # PRECIO|ENTREGA|CALIDAD|...
    contenido: str
    titulo: Optional[str] = None
    orden: int = 0
    clausula_maestra_id: Optional[int] = None
    precio_maestro_id: Optional[int] = None
    valor: Optional[float] = None


class ContratoCreate(BaseModel):
    empresa_proveedor_id: int
    empresa_compradora_id: int
    titulo: str
    numero: Optional[str] = None
    objeto: Optional[str] = None
    sector: Optional[str] = None
    valor: Optional[float] = None
    moneda: str = "COP"
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    clausulas: list[ClausulaCreate] = Field(default_factory=list)
    # Materializar cláusulas/precios desde el catálogo maestro (el empleado de
    # Bayern "busca y pone" cláusulas): se copia el contenido vigente del maestro.
    clausulas_maestras_ids: list[int] = Field(default_factory=list)
    precios_maestros_ids: list[int] = Field(default_factory=list)


class ContratoUpdate(BaseModel):
    titulo: Optional[str] = None
    objeto: Optional[str] = None
    sector: Optional[str] = None
    estado: Optional[str] = None
    valor: Optional[float] = None
    moneda: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    metadata: Optional[dict[str, Any]] = None


class ClausulaUpdate(BaseModel):
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    contenido: Optional[str] = None
    orden: Optional[int] = None
    valor: Optional[float] = None


class ContratoOut(BaseModel):
    id: int
    empresa_proveedor_id: int
    empresa_compradora_id: int
    numero: Optional[str]
    titulo: str
    estado: str
    valor: Optional[float]
    moneda: Optional[str]
    firmado_proveedor: bool
    sector: Optional[str]


class FirmaContrato(BaseModel):
    firmado: bool = True
