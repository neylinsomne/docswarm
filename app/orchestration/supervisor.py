"""Supervisor del swarm: arma el ``SwarmRunner`` de docswarm con los puertos.

Caso de uso de dominio: generar documentos a partir de contratos/cambios (p.ej.
una propuesta de adenda, un resumen de contrato, una notificación de cambio).
Aquí se cablea el engine; el catálogo de secciones y los prompts son la parte
de dominio. Cada ejecución se persiste en `acp_runs`.
"""

from __future__ import annotations

from typing import Optional

from app.settings import settings
from app.retrieval import PgVectorRetrieval
from app.orchestration.store import AcpRunsStore
from app.llm import build_llm
from docswarm.agents.base import LLMAgent
from docswarm.agents.judge import JudgeAgent
from docswarm.config.schema import plan_from_dict
from docswarm.runner import SwarmRunner, SwarmResult


# Catálogo de agentes de dominio (cada uno escribe un tipo de sección).
def _build_agents() -> dict:
    return {
        "legal": LLMAgent(
            "legal",
            "Eres un abogado experto en contratación B2B agroindustrial. "
            "Redactas cláusulas y consideraciones legales precisas. No inventes datos."),
        "comercial": LLMAgent(
            "comercial",
            "Eres un analista comercial. Redactas condiciones comerciales, precios "
            "y términos de suministro con claridad."),
        "tecnico": LLMAgent(
            "tecnico",
            "Eres un especialista técnico agro. Describes especificaciones de "
            "producto, calidad y logística de entrega."),
        "general": LLMAgent(
            "general",
            "Eres un redactor técnico preciso. Escribes solo la sección pedida."),
    }


def build_runner(*, prefer: str = "auto", empresa_id: Optional[int] = None,
                 contrato_id: Optional[int] = None) -> SwarmRunner:
    return SwarmRunner(
        llm=build_llm(prefer),
        agents=_build_agents(),
        judge=JudgeAgent(),
        retrieval=PgVectorRetrieval(),
        store=AcpRunsStore(empresa_id=empresa_id, contrato_id=contrato_id),
    )


def generar_documento(plan: dict, facts: Optional[dict] = None, *,
                      prefer: str = "auto", empresa_id: Optional[int] = None,
                      contrato_id: Optional[int] = None) -> SwarmResult:
    """Ejecuta el swarm sobre un plan (dict) y devuelve el documento compuesto.

    `prefer` ∈ auto|ollama|gemini|stub (con fallback automático).
    """
    runner = build_runner(prefer=prefer, empresa_id=empresa_id,
                          contrato_id=contrato_id)
    return runner.run(plan_from_dict(plan), facts or {})
