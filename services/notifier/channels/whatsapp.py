"""Canal WhatsApp.

Dos modos, en este orden de preferencia:

1. **Gateway por QR (Baileys)** — si ``WA_GATEWAY_URL`` está definido, envía el
   mensaje POSTeando a ``{WA_GATEWAY_URL}/send`` (header ``X-API-Key``). Es el
   microservicio ``services/wa-gateway`` (cuenta vinculada por QR). Vía no oficial,
   ideal para demo/pruebas.
2. **Cloud API oficial de Meta** — si hay ``WHATSAPP_TOKEN`` + ``WHATSAPP_PHONE_ID``.

Si no hay ninguno configurado, opera en **dry-run** (simula entrega) para no romper
el MVP. Usa solo la librería estándar (``urllib``) para no añadir dependencias.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

from services.notifier.channels.base import SendResult


class WhatsAppChannel:
    name = "WHATSAPP"

    def __init__(self) -> None:
        # Gateway por QR (preferente)
        self.gateway_url = os.environ.get("WA_GATEWAY_URL", "").rstrip("/")
        self.gateway_key = os.environ.get("WA_GATEWAY_KEY") or os.environ.get("SERVICE_API_KEY", "")
        # Cloud API oficial (alternativa)
        self.token = os.environ.get("WHATSAPP_TOKEN", "")
        self.phone_id = os.environ.get("WHATSAPP_PHONE_ID", "")
        self.timeout = float(os.environ.get("WA_TIMEOUT", "20"))

    # ------------------------------------------------------------------ helpers
    def _post_json(self, url: str, payload: dict, headers: dict) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as e:  # 4xx/5xx con cuerpo
            try:
                body = json.loads(e.read().decode("utf-8") or "{}")
            except Exception:
                body = {"error": str(e)}
            return e.code, body

    # --------------------------------------------------------------------- send
    def send(self, *, destino: Optional[str], asunto: Optional[str],
             mensaje: Optional[str], metadata: dict) -> SendResult:
        texto = mensaje or asunto or ""
        if asunto and mensaje:
            texto = f"*{asunto}*\n{mensaje}"

        # 1) Gateway por QR ----------------------------------------------------
        if self.gateway_url:
            if not destino:
                return SendResult(ok=False, error="WhatsApp: falta 'destino' (número).")
            headers = {}
            if self.gateway_key:
                headers["X-API-Key"] = self.gateway_key
            try:
                status, body = self._post_json(
                    f"{self.gateway_url}/send",
                    {"to": destino, "message": texto},
                    headers,
                )
            except Exception as e:  # red caída, timeout, etc.
                return SendResult(ok=False, error=f"WhatsApp gateway inaccesible: {e}")
            if status == 200 and body.get("ok"):
                return SendResult(ok=True, referencia_externa=body.get("id"),
                                  meta={"via": "wa-gateway", "jid": body.get("jid")})
            return SendResult(ok=False,
                              error=body.get("error") or f"gateway HTTP {status}",
                              meta={"via": "wa-gateway", "status": status})

        # 2) Cloud API oficial de Meta ----------------------------------------
        if self.token and self.phone_id:
            if not destino:
                return SendResult(ok=False, error="WhatsApp: falta 'destino' (número).")
            url = f"https://graph.facebook.com/v20.0/{self.phone_id}/messages"
            payload = {"messaging_product": "whatsapp", "to": destino,
                       "type": "text", "text": {"body": texto}}
            try:
                status, body = self._post_json(
                    url, payload, {"Authorization": f"Bearer {self.token}"})
            except Exception as e:
                return SendResult(ok=False, error=f"WhatsApp Cloud API: {e}")
            if status in (200, 201):
                ref = None
                try:
                    ref = body["messages"][0]["id"]
                except Exception:
                    pass
                return SendResult(ok=True, referencia_externa=ref, meta={"via": "cloud-api"})
            return SendResult(ok=False, error=f"Cloud API HTTP {status}: {body}",
                              meta={"via": "cloud-api"})

        # 3) Dry-run -----------------------------------------------------------
        return SendResult(ok=True, referencia_externa="dryrun-whatsapp",
                          meta={"dry_run": True, "destino": destino})
