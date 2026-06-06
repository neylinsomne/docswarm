"""Endpoints in-page de avisos (notificaciones) y firma electrónica.

Todo aquí funciona DENTRO de la página con el JWT del usuario (RLS por tenant),
sin depender de WhatsApp/Gmail. Los endpoints máquina-a-máquina (cola + callbacks
para el sender externo) viven en el microservicio `notifier`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.domain.notifications import service as notif_service
from app.domain.signatures import service as firma_service
from app.security.deps import Principal, get_current_principal

router = APIRouter(tags=["avisos-firma"])


# --------------------------- Avisos (notificaciones) -------------------------
@router.get("/notificaciones")
def listar_notificaciones(
    limit: int = Query(50, le=200), offset: int = Query(0, ge=0),
    no_leidas: bool = Query(False), canal: Optional[str] = Query(None),
    _p: Principal = Depends(get_current_principal),
):
    """Feed de avisos del tenant. `canal=SISTEMA&no_leidas=true` = bandeja in-page."""
    return notif_service.listar_por_tenant(
        limit, offset, solo_no_leidas=no_leidas, canal=canal)


@router.get("/notificaciones/no_leidas/conteo")
def conteo_no_leidas(canal: Optional[str] = Query("SISTEMA"),
                     _p: Principal = Depends(get_current_principal)):
    """Badge de la campanita (avisos in-page). `canal=` vacío cuenta todos."""
    return {"no_leidas": notif_service.contar_no_leidas(canal or None)}


@router.post("/notificaciones/{notif_id}/leida")
def marcar_leida(notif_id: int, _p: Principal = Depends(get_current_principal)):
    """Marca un aviso como leído dentro de la página."""
    if not notif_service.marcar_leida(notif_id):
        raise HTTPException(404, "aviso no encontrado")
    return {"ok": True}


# --------------------------- Firma electrónica in-page -----------------------
class FirmarAfectado(BaseModel):
    evidencia: dict | None = None


class FirmarContrato(BaseModel):
    evidencia: dict | None = None


@router.get("/firmas")
def listar_firmas(limit: int = Query(50, le=200), offset: int = Query(0, ge=0),
                  _p: Principal = Depends(get_current_principal)):
    """Procesos de firma del tenant."""
    return firma_service.listar_por_tenant(limit, offset)


@router.post("/firmas/afectado/{afectado_id}")
def firmar_afectado(afectado_id: int, data: FirmarAfectado | None = None,
                    principal: Principal = Depends(get_current_principal)):
    """Firma electrónica in-page de la actualización derivada de un cambio."""
    try:
        return firma_service.firmar_en_pagina(
            usuario_id=principal.usuario_id, afectado_id=afectado_id,
            evidencia=(data.evidencia if data else None))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/firmas/contrato/{contrato_id}")
def firmar_contrato(contrato_id: int, data: FirmarContrato | None = None,
                    principal: Principal = Depends(get_current_principal)):
    """Firma electrónica in-page de un contrato."""
    try:
        return firma_service.firmar_en_pagina(
            usuario_id=principal.usuario_id, contrato_id=contrato_id,
            evidencia=(data.evidencia if data else None))
    except ValueError as e:
        raise HTTPException(404, str(e))
