"""Contrato común de los canales de comunicación."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class SendResult:
    ok: bool
    referencia_externa: Optional[str] = None   # id del mensaje en el proveedor
    error: Optional[str] = None
    meta: dict = field(default_factory=dict)


class Channel(Protocol):
    name: str

    def send(self, *, destino: Optional[str], asunto: Optional[str],
             mensaje: Optional[str], metadata: dict) -> SendResult:
        """Envía el mensaje por el canal. Devuelve SendResult (nunca lanza)."""
        ...
