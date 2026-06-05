"""Adapters — ready-made implementations of the ports.

  - ``OllamaLLM`` : LLMPort backed by a local Ollama server (stdlib HTTP).
  - ``StubLLM``   : deterministic offline LLMPort that reads the contract hints
                    embedded in the prompt and emits matching content. Lets the
                    full swarm run (and tests pass) with no model installed.
"""

from __future__ import annotations

from docswarm.adapters.ollama_llm import OllamaLLM
from docswarm.adapters.stub_llm import StubLLM

__all__ = ["OllamaLLM", "StubLLM"]
