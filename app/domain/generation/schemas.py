from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerarContratoRequest(BaseModel):
    """Entrada del ACP: el empleado de Bayern genera el documento con un prompt.

    Puede partir de cero (prompt + datos) o tomar como base cláusulas/precios del
    catálogo maestro ('buscar y poner cláusulas'). Si `use_ollama=False` usa el
    LLM stub determinista (sin modelo) — útil para el MVP/offline.
    """
    prompt: str
    empresa_proveedor_id: Optional[int] = None
    contrato_id: Optional[int] = None              # contexto opcional
    objeto: Optional[str] = None
    titulo: str = "Contrato generado"
    clausulas_maestras_ids: list[int] = Field(default_factory=list)
    precios_maestros_ids: list[int] = Field(default_factory=list)
    plan: Optional[dict[str, Any]] = None          # plan override (avanzado)
    use_ollama: bool = False                        # back-compat
    proveedor_llm: Optional[str] = None            # auto|ollama|gemini|stub

    def prefer(self) -> str:
        if self.proveedor_llm:
            return self.proveedor_llm
        return "ollama" if self.use_ollama else "auto"


class DocumentoGenerado(BaseModel):
    titulo: str
    markdown: str
    html: str
    secciones: list[str]
    warnings: list[str]
    motor: Optional[str] = None                     # proveedor LLM realmente usado


class ChatMensaje(BaseModel):
    rol: str                                        # "user" | "assistant"
    contenido: str


class ChatContratoRequest(BaseModel):
    """Entrada del chatbot ACP: conversación + contexto opcional."""
    mensajes: list[ChatMensaje]
    empresa_proveedor_id: Optional[int] = None
    objeto: Optional[str] = None
    titulo: str = "Contrato"
    clausulas_maestras_ids: list[int] = Field(default_factory=list)
    precios_maestros_ids: list[int] = Field(default_factory=list)
    proveedor_llm: Optional[str] = None            # auto|ollama|gemini|stub


class ChatContratoResponse(BaseModel):
    """Decisión del chatbot: preguntar más, o generar el documento."""
    accion: str                                     # "preguntar" | "generar"
    respuesta: str                                  # texto para mostrar en el chat
    documento: Optional[DocumentoGenerado] = None   # presente si accion == generar
    motor: Optional[str] = None
