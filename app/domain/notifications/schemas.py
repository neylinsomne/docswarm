from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class NotificacionPendiente(BaseModel):
    """Lo que el microservicio externo necesita para enviar el mensaje."""
    id: int
    canal: str
    tipo: str
    empresa_id: int
    usuario_id: Optional[int]
    afectado_id: Optional[int]
    contrato_id: Optional[int]
    destino: Optional[str]
    asunto: Optional[str]
    mensaje: Optional[str]
    metadata: dict[str, Any]


class EstadoUpdate(BaseModel):
    """Callback de entrega que reporta el microservicio externo."""
    estado: str                          # ENVIADO|ENTREGADO|LEIDO|FALLIDO
    referencia_externa: Optional[str] = None
    error: Optional[str] = None


class NotificacionOut(BaseModel):
    id: int
    canal: str
    tipo: str
    empresa_id: int
    usuario_id: Optional[int]
    afectado_id: Optional[int]
    contrato_id: Optional[int]
    destino: Optional[str]
    asunto: Optional[str]
    mensaje: Optional[str]
    estado: str
    referencia_externa: Optional[str]
    enviado_at: Optional[datetime]
    entregado_at: Optional[datetime]
    leido_at: Optional[datetime]
    created_at: datetime
