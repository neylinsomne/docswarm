"""OllamaLLM — an LLMPort backed by a local Ollama server.

Uses only the standard library (urllib) so the engine stays dependency-free.
Default endpoint is http://localhost:11434. Start a model first, e.g.:

    ollama pull qwen3:8b
    ollama serve            # usually already running

Qwen3 supports a ``/no_think`` directive to skip its reasoning trace; we prepend
it to the system prompt by default (toggle with ``no_think=False``).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_QWEN_NO_THINK = "/no_think\n"


class OllamaLLM:
    def __init__(self, model: str = "qwen3:8b", *,
                 host: str = "", no_think: bool = True,
                 timeout: float = 120.0) -> None:
        self.model = model
        self.host = (host or os.environ.get("OLLAMA_HOST")
                     or "http://localhost:11434").rstrip("/")
        self.no_think = no_think
        self.timeout = timeout

    def complete(self, system: str, prompt: str, **options) -> str:
        model = options.get("model") or self.model
        sys_prompt = system or ""
        if self.no_think and "qwen" in model.lower():
            sys_prompt = _QWEN_NO_THINK + sys_prompt
        body = {
            "model": model,
            "prompt": prompt,
            "system": sys_prompt,
            "stream": False,
            "options": {"temperature": float(options.get("temperature", 0.4))},
        }
        if "max_tokens" in options:
            body["options"]["num_predict"] = int(options["max_tokens"])

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama not reachable at {self.host} ({exc}). "
                "Is `ollama serve` running and the model pulled?") from exc
        return (payload.get("response") or "").strip()
