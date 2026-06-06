from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Caracteristica(BaseModel):
    clave: str
    valor: str
    valor_num: Optional[float] = None


class EmpresaCreate(BaseModel):
    """Formulario de alta de empresa proveedora: la 'metadata' rica para búsqueda."""
    nombre: str
    nit: Optional[str] = None
    tipo: str = "PROVEEDOR"
    sector: Optional[str] = None
    nicho: Optional[str] = None
    pais: str = "CO"
    ciudad: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    caracteristicas: list[Caracteristica] = Field(default_factory=list)


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    sector: Optional[str] = None
    nicho: Optional[str] = None
    ciudad: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    activo: Optional[bool] = None


class EmpresaOut(BaseModel):
    id: int
    tipo: str
    nombre: str
    nit: Optional[str]
    sector: Optional[str]
    nicho: Optional[str]
    pais: Optional[str]
    ciudad: Optional[str]
    metadata: dict[str, Any]
    activo: bool


class EmpresaFiltro(BaseModel):
    """Filtrado facetado por características + metadata + texto por nombre."""
    nombre: Optional[str] = None            # ILIKE/trigram
    sector: Optional[str] = None
    nicho: Optional[str] = None
    caracteristicas: dict[str, str] = Field(default_factory=dict)  # clave→valor exacto
    limit: int = 50
    offset: int = 0
