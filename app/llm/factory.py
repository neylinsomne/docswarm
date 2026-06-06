"""Selección de LLM con fallback, según configuración y preferencia.

prefer:
  · "stub"   → solo StubLLM (offline determinista).
  · "ollama" → Ollama, luego Gemini (si hay key), luego Stub.
  · "gemini" → Gemini (si hay key), luego Ollama, luego Stub.
  · "auto"   → si hay GEMINI_API_KEY: Gemini → Ollama → Stub (rápido y fiable);
               si no: Ollama → Stub.
"""

from __future__ import annotations

from app.settings import settings
from app.llm.fallback import FallbackLLM
from app.llm.gemini import GeminiLLM
from docswarm.adapters.ollama_llm import OllamaLLM
from docswarm.adapters.stub_llm import StubLLM

VALID = {"auto", "ollama", "gemini", "stub"}


def _ollama() -> OllamaLLM:
    return OllamaLLM(model=settings.ollama_model, host=settings.ollama_host,
                     timeout=settings.llm_timeout)


def _gemini():
    if not settings.gemini_api_key:
        return None
    return GeminiLLM(settings.gemini_api_key, model=settings.gemini_model,
                     timeout=settings.llm_timeout)


def build_llm(prefer: str = "auto"):
    prefer = (prefer or "auto").lower()
    if prefer not in VALID:
        prefer = "auto"
    if prefer == "stub":
        return StubLLM()

    gem = _gemini()
    chain = []
    labels = []

    def add(p, label):
        if p is not None:
            chain.append(p); labels.append(label)

    if prefer == "gemini":
        add(gem, "gemini"); add(_ollama(), "ollama")
    elif prefer == "ollama":
        add(_ollama(), "ollama"); add(gem, "gemini")
    else:  # auto
        if gem is not None:
            add(gem, "gemini"); add(_ollama(), "ollama")
        else:
            add(_ollama(), "ollama")

    chain.append(StubLLM()); labels.append("stub")
    return FallbackLLM(chain, labels)
