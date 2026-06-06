"""Endpoints de contratos."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from pydantic import BaseModel

from app.domain.contracts import schemas, service
from app.domain.contracts.pdf import render_contrato_pdf, render_documento_pdf
from app.domain.generation import schemas as gschemas
from app.domain.generation import service as gservice
from app.security.deps import Principal, get_current_principal, require_admin

router = APIRouter(prefix="/contratos", tags=["contratos"])


@router.post("", status_code=201)
def crear_contrato(data: schemas.ContratoCreate,
                   _admin: Principal = Depends(require_admin)):
    """Crea un contrato Bayern↔proveedor, opcionalmente con cláusulas/precios del
    catálogo maestro (el empleado busca y pone cláusulas). Solo Bayern."""
    return {"id": service.crear_contrato(data)}


@router.post("/generar", tags=["acp"])
def generar_contrato(req: gschemas.GenerarContratoRequest,
                     _admin: Principal = Depends(require_admin)):
    """Entrada ACP: genera el documento del contrato con el swarm a partir de un
    prompt (+ cláusulas/precios elegidos + contexto). Solo Bayern."""
    return gservice.generar_contrato(req)


@router.post("/chat", tags=["acp"])
def chat_contrato(req: gschemas.ChatContratoRequest,
                  _admin: Principal = Depends(require_admin)):
    """Chatbot ACP con decisiones: pregunta lo que falta o genera el documento.

    LLM con fallback (Ollama → Gemini → Stub). Solo Bayern."""
    return gservice.chat_contrato(req)


class DocumentoPdfRequest(BaseModel):
    titulo: str = "Documento"
    markdown: str
    proveedor: str = ""


@router.post("/documento/pdf", tags=["acp"])
def documento_pdf(req: DocumentoPdfRequest, _admin: Principal = Depends(require_admin)):
    """Convierte un documento generado por la IA (markdown) a PDF (con firmas)."""
    pdf = render_documento_pdf(req.titulo, req.markdown, proveedor=req.proveedor)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="documento-generado.pdf"'})


@router.get("")
def listar_contratos(estado: Optional[str] = Query(None),
                     limit: int = Query(50, le=200), offset: int = Query(0, ge=0),
                     _p: Principal = Depends(get_current_principal)):
    """Lista contratos visibles para el tenant (RLS aísla a cada proveedor)."""
    return service.listar_contratos(estado, limit, offset)


@router.get("/{contrato_id}")
def obtener_contrato(contrato_id: int, _p: Principal = Depends(get_current_principal)):
    c = service.obtener_contrato(contrato_id)
    if not c:
        raise HTTPException(404, "contrato no encontrado")
    return c


@router.get("/{contrato_id}/pdf")
def contrato_pdf(contrato_id: int, _p: Principal = Depends(get_current_principal)):
    """Genera y devuelve el PDF del contrato (cabecera + cláusulas). RLS aplica."""
    c = service.obtener_contrato(contrato_id)
    if not c:
        raise HTTPException(404, "contrato no encontrado")
    pdf = render_contrato_pdf(
        c, proveedor=c.get("proveedor_nombre") or "",
        comprador=c.get("comprador_nombre") or "Bayern S.A.")
    nombre = (c.get("numero") or f"contrato-{contrato_id}").replace("/", "-")
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}.pdf"'})


@router.patch("/{contrato_id}")
def actualizar_contrato(contrato_id: int, data: schemas.ContratoUpdate,
                        _admin: Principal = Depends(require_admin)):
    """Edita un contrato (solo Bayern)."""
    if not service.actualizar_contrato(contrato_id, data):
        raise HTTPException(404, "contrato no encontrado o sin cambios")
    return {"ok": True}


@router.post("/{contrato_id}/clausulas", status_code=201)
def agregar_clausula(contrato_id: int, cl: schemas.ClausulaCreate,
                     _admin: Principal = Depends(require_admin)):
    """Agrega una cláusula a un contrato (manual o desde un ítem maestro)."""
    cid = service.agregar_clausula(contrato_id, cl)
    if cid is None:
        raise HTTPException(404, "contrato no encontrado")
    return {"id": cid}


@router.patch("/clausulas/{clausula_id}")
def actualizar_clausula(clausula_id: int, data: schemas.ClausulaUpdate,
                        _admin: Principal = Depends(require_admin)):
    if not service.actualizar_clausula(clausula_id, data):
        raise HTTPException(404, "cláusula no encontrada o sin cambios")
    return {"ok": True}


@router.delete("/clausulas/{clausula_id}")
def eliminar_clausula(clausula_id: int, _admin: Principal = Depends(require_admin)):
    if not service.eliminar_clausula(clausula_id):
        raise HTTPException(404, "cláusula no encontrada")
    return {"ok": True}


@router.post("/{contrato_id}/firma")
def firmar_contrato(contrato_id: int, data: schemas.FirmaContrato,
                    principal: Principal = Depends(get_current_principal)):
    """El proveedor firma su contrato vigente."""
    if not service.firmar_contrato(contrato_id, data.firmado, principal.usuario_id):
        raise HTTPException(404, "contrato no encontrado")
    return {"ok": True, "firmado": data.firmado}
