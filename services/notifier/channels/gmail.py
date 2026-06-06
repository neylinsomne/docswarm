"""Canal Gmail.

►► PEGA AQUÍ el código del repo de Gmail ◄◄
Implementa el envío real dentro de ``send`` (API de Gmail o SMTP). Lee
credenciales del entorno. Sin credenciales opera en modo "dry-run".
"""

from __future__ import annotations

import os
from typing import Optional

from services.notifier.channels.base import SendResult


class GmailChannel:
    name = "GMAIL"

    def __init__(self) -> None:
        self.user = os.environ.get("GMAIL_USER", "")
        self.password = os.environ.get("GMAIL_APP_PASSWORD", "")

    def send(self, *, destino: Optional[str], asunto: Optional[str],
             mensaje: Optional[str], metadata: dict) -> SendResult:
        if not self.user or not self.password or not destino:
            return SendResult(ok=True, referencia_externa="dryrun-gmail",
                              meta={"dry_run": True, "destino": destino})
        # ──────────────────────────────────────────────────────────────────
        # TODO: reemplazar por el envío real (SMTP o API de Gmail del otro repo).
        # Ejemplo SMTP (pseudocódigo):
        #   import smtplib; from email.mime.text import MIMEText
        #   msg = MIMEText(mensaje or ""); msg["Subject"]=asunto or ""
        #   msg["From"]=self.user; msg["To"]=destino
        #   with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        #       s.login(self.user, self.password); s.send_message(msg)
        #   return SendResult(ok=True, referencia_externa="smtp-sent")
        # ──────────────────────────────────────────────────────────────────
        return SendResult(ok=False, error="Gmail no implementado todavía")
