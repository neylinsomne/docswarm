"""Endpoints de empresas (proveedores) + metadata/características."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.companies import schemas, service
from app.security.deps import Principal, get_current_principal, require_admin

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.post("", status_code=201)
def crear_empresa(data: schemas.EmpresaCreate,
                  _admin: Principal = Depends(require_admin)):
    """Alta de empresa proveedora con su metadata rica (solo Bayern)."""
    return {"id": service.crear_empresa(data)}


@router.get("")
def listar_empresas(
    nombre: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    nicho: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    _p: Principal = Depends(get_current_principal),
):
    """Listado simple por nombre (trigram) / sector / nicho."""
    return service.listar_empresas(schemas.EmpresaFiltro(
        nombre=nombre, sector=sector, nicho=nicho, limit=limit, offset=offset))


@router.post("/buscar")
def buscar_empresas(filtro: schemas.EmpresaFiltro,
                    _p: Principal = Depends(get_current_principal)):
    """Filtrado facetado completo (incluye características clave→valor)."""
    return service.listar_empresas(filtro)


@router.get("/{empresa_id}")
def obtener_empresa(empresa_id: int, _p: Principal = Depends(get_current_principal)):
    emp = service.obtener_empresa(empresa_id)
    if not emp:
        raise HTTPException(404, "empresa no encontrada")
    return emp


@router.patch("/{empresa_id}")
def actualizar_empresa(empresa_id: int, data: schemas.EmpresaUpdate,
                       _p: Principal = Depends(get_current_principal)):
    if not service.actualizar_empresa(empresa_id, data):
        raise HTTPException(404, "empresa no encontrada o sin cambios")
    return {"ok": True}
