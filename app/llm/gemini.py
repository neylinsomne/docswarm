"""GeminiLLM — LLMPort sobre la API de Google Gemini (REST, sin SDK).

Usa solo urllib (igual que OllamaLLM) para no añadir dependencias. Requiere
``GEMINI_API_KEY``. Modelo por defecto: ``gemini-2.0-flash`` (rápido y barato).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLM:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash",
                 timeout: float = 60.0) -> None:
        if not api_key:
            raise ValueError("GeminiLLM requiere GEMINI_API_KEY")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, prompt: str, **options) -> str:
        model = options.get("model") or self.model
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": float(options.get("temperature", 0.4)),
            },
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        if "max_tokens" in options:
            body["generationConfig"]["maxOutputTokens"] = int(options["max_tokens"])

        url = f"{_BASE}/{model}:generateContent?key={self.api_key}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini no accesible ({exc})") from exc

        try:
            parts = payload["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Respuesta inesperada de Gemini: {payload}") from exc
