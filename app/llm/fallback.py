"""FallbackLLM — encadena varios LLMPort; usa el primero que responda.

Si el primario (p.ej. Ollama local) lanza o se cuelga, prueba el siguiente
(p.ej. Gemini) y, en último caso, el StubLLM determinista. Así la generación
nunca falla en duro.
"""

from __future__ import annotations

from typing import List

from docswarm.ports.llm import LLMPort


class FallbackLLM:
    def __init__(self, providers: List[LLMPort], labels: List[str] | None = None) -> None:
        self.providers = [p for p in providers if p is not None]
        self.labels = labels or [type(p).__name__ for p in self.providers]
        if not self.providers:
            raise ValueError("FallbackLLM requiere al menos un proveedor")
        self.last_used: str | None = None

    def complete(self, system: str, prompt: str, **options) -> str:
        errors = []
        for prov, label in zip(self.providers, self.labels):
            try:
                out = prov.complete(system, prompt, **options)
                if out:
                    self.last_used = label
                    return out
            except Exception as exc:  # noqa: BLE001 — probar el siguiente proveedor
                errors.append(f"{label}: {exc}")
        raise RuntimeError("Todos los proveedores LLM fallaron → " + " | ".join(errors))
