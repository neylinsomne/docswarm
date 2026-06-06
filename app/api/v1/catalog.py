"""Endpoints del catálogo maestro (cláusulas/precios de Bayern)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domain.catalog import schemas, service
from app.security.deps import Principal, get_current_principal, require_admin

router = APIRouter(prefix="/catalogo", tags=["catalogo"])


@router.get("/clausulas")
def buscar_clausulas(q: Optional[str] = Query(None), tipo: Optional[str] = Query(None),
                     sector: Optional[str] = Query(None), limit: int = Query(50, le=200),
                     _p: Principal = Depends(get_current_principal)):
    """Buscar cláusulas maestras (para armar el contrato eligiéndolas)."""
    return service.buscar_clausulas(q, tipo, sector, limit=limit)


@router.get("/precios")
def buscar_precios(q: Optional[str] = Query(None), categoria: Optional[str] = Query(None),
                   limit: int = Query(50, le=200),
                   _p: Principal = Depends(get_current_principal)):
    """Buscar precios maestros."""
    return service.buscar_precios(q, categoria, limit=limit)


@router.post("/clausulas", status_code=201)
def crear_clausula(data: schemas.ClausulaMaestraCreate,
                   _admin: Principal = Depends(require_admin)):
    """Crear una cláusula maestra (solo Bayern)."""
    return {"id": service.crear_clausula(data)}


@router.post("/precios", status_code=201)
def crear_precio(data: schemas.PrecioMaestroCreate,
                 _admin: Principal = Depends(require_admin)):
    """Crear un precio maestro (solo Bayern)."""
    return {"id": service.crear_precio(data)}
