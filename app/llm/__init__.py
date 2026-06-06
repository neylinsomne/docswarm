"""Proveedores de LLM y selección con fallback.

`build_llm(prefer)` arma una cadena de fallback para que la generación nunca se
quede colgada: si Ollama (local) no responde, cae a Gemini (si hay API key) y, en
último caso, al StubLLM determinista (offline). Implementa el puerto LLMPort del
engine docswarm.
"""

from app.llm.factory import build_llm
from app.llm.gemini import GeminiLLM
from app.llm.fallback import FallbackLLM

__all__ = ["build_llm", "GeminiLLM", "FallbackLLM"]
