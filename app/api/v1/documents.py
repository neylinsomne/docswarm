"""Endpoints de documentos: subida + ingest version-aware (encola el procesado)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.ingest import ingest_document
from app.orchestration.worker import enqueue
from app.security.deps import Principal, get_current_principal

router = APIRouter(prefix="/documentos", tags=["documentos"])


@router.post("", status_code=201)
async def subir_documento(
    archivo: UploadFile = File(...),
    contrato_id: Optional[int] = Form(None),
    titulo: Optional[str] = Form(None),
    principal: Principal = Depends(get_current_principal),
):
    """Sube un documento (PDF/DOCX/XLSX) y lo persiste version-aware.

    El tenant es el de la sesión (un proveedor sube a su propio espacio; Bayern
    puede subir global). El parse/chunk/embed se hace en el worker (cola).
    """
    content = await archivo.read()
    res = ingest_document(
        content=content, filename=archivo.filename, source="upload",
        tenant_id=principal.tenant, contrato_id=contrato_id, titulo=titulo,
    )
    if not res["unchanged"]:
        enqueue("ingest_doc", {"raw_document_id": res["raw_document_id"]},
                dedup_key=f"ingest:{res['raw_document_id']}")
    return res
