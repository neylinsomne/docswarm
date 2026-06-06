"""Endpoints de búsqueda: por contenido (vector) y por nombre (trigram)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.domain.search import service
from app.security.deps import Principal, get_current_principal

router = APIRouter(prefix="/buscar", tags=["buscar"])


@router.get("/contenido")
def buscar_contenido(q: str = Query(..., min_length=2), top_k: int = Query(10, le=50),
                     _p: Principal = Depends(get_current_principal)):
    """Búsqueda semántica sobre el contenido de los contratos (pgvector)."""
    return service.buscar_por_contenido(q, top_k)


@router.get("/contratos")
def buscar_contratos(q: str = Query(..., min_length=2), limit: int = Query(20, le=100),
                     _p: Principal = Depends(get_current_principal)):
    """Búsqueda de contratos por nombre/título (trigram)."""
    return service.buscar_contratos_por_nombre(q, limit)


@router.get("/empresas")
def buscar_empresas(q: str = Query(..., min_length=2), top_k: int = Query(10, le=50),
                    _p: Principal = Depends(get_current_principal)):
    """Búsqueda de empresas por similitud de perfil (vector)."""
    return service.buscar_empresas_por_similitud(q, top_k)
