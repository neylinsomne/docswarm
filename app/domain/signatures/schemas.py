from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, model_validator


class IniciarFirma(BaseModel):
    """Inicia el proceso de firma electrónica (por WhatsApp/Gmail/Web)."""
    afectado_id: Optional[int] = None     # documento afectado por un cambio
    contrato_id: Optional[int] = None     # o el contrato directamente
    usuario_id: Optional[int] = None
    notificacion_id: Optional[int] = None
    canal: str = "WHATSAPP"

    @model_validator(mode="after")
    def _al_menos_uno(self):
        if not self.afectado_id and not self.contrato_id:
            raise ValueError("indica afectado_id o contrato_id")
        return self


class EventoFirma(BaseModel):
    """Callback del proceso de firma (lo reporta el microservicio externo)."""
    estado: str                           # EN_PROCESO|FIRMADA|RECHAZADA|EXPIRADA
    evidencia: dict[str, Any] = {}        # OTP, hash, IP, timestamp...
    referencia_externa: Optional[str] = None


class FirmaOut(BaseModel):
    id: int
    empresa_id: int
    contrato_id: Optional[int]
    afectado_id: Optional[int]
    usuario_id: Optional[int]
    canal: str
    estado: str
    token: Optional[str]
    referencia_externa: Optional[str]
    firmado_at: Optional[datetime]
    created_at: datetime
