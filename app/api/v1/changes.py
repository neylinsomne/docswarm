"""Endpoints de la feature central: log de cambios + documentos afectados + firma."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.changes import schemas, service
from app.security.deps import Principal, get_current_principal, require_admin

router = APIRouter(prefix="/cambios", tags=["cambios"])


@router.post("/clausula", status_code=201)
def cambiar_clausula(req: schemas.CambioClausulaRequest,
                     admin: Principal = Depends(require_admin)):
    """Bayern cambia una cláusula maestra y propaga a los contratos afectados."""
    try:
        return service.registrar_cambio_clausula(req, admin.usuario_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/precio", status_code=201)
def cambiar_precio(req: schemas.CambioPrecioRequest,
                   admin: Principal = Depends(require_admin)):
    """Bayern cambia un precio maestro y propaga a los contratos afectados."""
    try:
        return service.registrar_cambio_precio(req, admin.usuario_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("")
def listar_cambios(limit: int = Query(50, le=200), offset: int = Query(0, ge=0),
                   _p: Principal = Depends(get_current_principal)):
    """Tablero: cada cambio con docs_afectados / docs_firmados / docs_pendientes."""
    return service.listar_cambios(limit, offset)


@router.get("/{cambio_id}/afectados")
def detalle_afectados(cambio_id: int, _p: Principal = Depends(get_current_principal)):
    """Drill-down: contratos/documentos afectados + booleano de firma por proveedor."""
    return service.detalle_cambio(cambio_id)


@router.post("/afectados/{afectado_id}/firma")
def firmar_afectado(afectado_id: int, data: schemas.FirmaAfectado,
                    principal: Principal = Depends(get_current_principal)):
    """El proveedor firma la actualización derivada de un cambio (booleano → TRUE)."""
    ok = service.firmar_documento_afectado(
        afectado_id, principal.usuario_id, data.observaciones)
    if not ok:
        raise HTTPException(404, "afectado no encontrado o ya firmado")
    return {"ok": True, "firmado": True}
