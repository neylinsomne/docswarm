"""LLMPort — the only way the engine talks to a language model."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMPort(Protocol):
    """A minimal text-completion port.

    Implementations: ``docswarm.adapters.OllamaLLM`` (local Ollama),
    ``docswarm.adapters.StubLLM`` (deterministic, offline, for tests/demos).
    Bring your own (OpenAI, Anthropic, vLLM...) by implementing ``complete``.
    """

    def complete(self, system: str, prompt: str, **options) -> str:
        """Return the model completion for ``system`` + ``prompt``.

        ``options`` may carry ``temperature``, ``max_tokens``, ``model`` etc.;
        implementations should ignore unknown keys. Must return a string (never
        ``None``); on failure, raise.
        """
        ...
