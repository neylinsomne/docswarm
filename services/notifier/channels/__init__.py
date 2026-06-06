"""Adaptadores de canal. AQUÍ va el código del repo de WhatsApp/Gmail.

Cada canal implementa ``send(destino, asunto, mensaje, metadata) -> SendResult``.
El dispatcher los usa para enviar las notificaciones PENDIENTES.
"""

from services.notifier.channels.base import SendResult, Channel
from services.notifier.channels.whatsapp import WhatsAppChannel
from services.notifier.channels.gmail import GmailChannel

REGISTRY: dict[str, Channel] = {
    "WHATSAPP": WhatsAppChannel(),
    "GMAIL": GmailChannel(),
}

__all__ = ["SendResult", "Channel", "REGISTRY"]
