from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class CambioClausulaRequest(BaseModel):
    clausula_maestra_id: int
    nuevo_contenido: str
    descripcion: Optional[str] = None


class CambioPrecioRequest(BaseModel):
    precio_maestro_id: int
    nuevo_precio: float
    descripcion: Optional[str] = None


class CambioResumen(BaseModel):
    cambio_id: int
    tipo_objeto: str
    accion: str
    descripcion: Optional[str]
    objeto_codigo: Optional[str]
    objeto_titulo: Optional[str]
    version_anterior: Optional[int]
    version_nueva: Optional[int]
    created_at: datetime
    docs_afectados: int
    docs_firmados: int
    docs_pendientes: int


class DocumentoAfectado(BaseModel):
    afectado_id: int
    contrato_id: int
    contrato_numero: Optional[str]
    contrato_titulo: Optional[str]
    empresa_proveedor_id: int
    empresa_proveedor: str
    estado_propagacion: str
    firmado_proveedor: bool
    fecha_firma: Optional[datetime]
    notificado_at: Optional[datetime]
    raw_document_id: Optional[int]


class FirmaAfectado(BaseModel):
    observaciones: Optional[str] = None
