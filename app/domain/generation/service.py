"""Generación de documentos de contrato con el swarm de agentes (ACP).

Toma el prompt del empleado de Bayern (+ cláusulas/precios elegidos del catálogo
+ contexto del contrato/empresa) y lo convierte en `facts` compartidos que los
agentes deben respetar; luego ejecuta el `SwarmRunner` de docswarm sobre un plan
de secciones de contrato. Devuelve el documento compuesto (markdown/html).
"""

from __future__ import annotations

from typing import Any, Optional

from psycopg.rows import dict_row

from app.db import db_conn
from app.domain.generation import schemas
from app.orchestration import generar_documento

# Plan por defecto de un contrato: una sección por agente de dominio, con alcance
# disjunto vía must_cover/must_not_cover (anti-solape del engine).
DEFAULT_CONTRACT_PLAN: dict[str, Any] = {
    "title": "Contrato",
    "sections": [
        {"id": "objeto", "agent": "general", "order": 1,
         "title": "Objeto del contrato",
         "must_cover": ["objeto del contrato", "alcance del suministro"]},
        {"id": "condiciones_comerciales", "agent": "comercial", "order": 2,
         "title": "Condiciones comerciales",
         "must_cover": ["precio", "forma de pago", "plazo de entrega"],
         "must_not_cover": ["cláusulas legales"]},
        {"id": "especificaciones_tecnicas", "agent": "tecnico", "order": 3,
         "title": "Especificaciones técnicas",
         "must_cover": ["estándar de calidad", "logística de entrega"]},
        {"id": "clausulas_legales", "agent": "legal", "order": 4,
         "title": "Cláusulas legales",
         "must_cover": ["confidencialidad", "penalizaciones", "terminación"]},
    ],
}


def _cargar_facts(req: schemas.GenerarContratoRequest) -> dict:
    """Construye los hechos compartidos (verdad única que los agentes respetan)."""
    facts: dict[str, Any] = {"instruccion_usuario": req.prompt, "titulo": req.titulo}
    if req.objeto:
        facts["objeto"] = req.objeto

    with db_conn(empresa_id=None) as conn:
        conn.row_factory = dict_row
        if req.empresa_proveedor_id:
            emp = conn.execute(
                "SELECT nombre, sector, nicho FROM empresas WHERE id = %s",
                (req.empresa_proveedor_id,),
            ).fetchone()
            if emp:
                facts["empresa_proveedor"] = emp["nombre"]
                facts["sector"] = emp.get("sector")
                facts["nicho"] = emp.get("nicho")
        if req.contrato_id:
            c = conn.execute(
                "SELECT numero, titulo, objeto FROM contratos WHERE id = %s",
                (req.contrato_id,),
            ).fetchone()
            if c:
                facts["contrato"] = c["numero"] or c["titulo"]
                facts.setdefault("objeto", c.get("objeto"))
        if req.clausulas_maestras_ids:
            facts["clausulas_base"] = conn.execute(
                """
                SELECT codigo, titulo, contenido_actual AS contenido
                FROM clausulas_maestras WHERE id = ANY(%s)
                """,
                (req.clausulas_maestras_ids,),
            ).fetchall()
        if req.precios_maestros_ids:
            facts["precios_base"] = conn.execute(
                """
                SELECT codigo, producto, precio::float8 AS precio, moneda, unidad
                FROM precios_maestros WHERE id = ANY(%s)
                """,
                (req.precios_maestros_ids,),
            ).fetchall()
    return facts


def generar_contrato(req: schemas.GenerarContratoRequest) -> schemas.DocumentoGenerado:
    plan = req.plan or DEFAULT_CONTRACT_PLAN
    plan = {**plan, "title": req.titulo}
    facts = _cargar_facts(req)
    result = generar_documento(
        plan, facts, prefer=req.prefer(),
        empresa_id=req.empresa_proveedor_id, contrato_id=req.contrato_id,
    )
    motor = None
    try:
        motor = getattr(result, "_motor", None)
    except Exception:  # noqa: BLE001
        motor = None
    return schemas.DocumentoGenerado(
        titulo=req.titulo,
        markdown=result.markdown,
        html=result.html,
        secciones=[s.section_id for s in result.sections],
        warnings=result.warnings,
        motor=motor,
    )


# ---------------------------------------------------------------------------
# Chatbot ACP con decisiones (preguntar vs generar)
# ---------------------------------------------------------------------------
_CHAT_SYSTEM = (
    "Eres un asistente que ayuda a un empleado de Bayern a redactar un contrato de "
    "suministro con sus proveedores. Tu trabajo es DECIDIR si ya tienes suficiente "
    "información para generar el contrato o si falta algo.\n"
    "Datos mínimos: proveedor, objeto del suministro, precio/condición comercial, "
    "plazo de entrega y al menos una cláusula de calidad.\n"
    "REGLAS DE RESPUESTA (obligatorio):\n"
    "- Si falta información, responde una sola pregunta clara y empieza con la "
    "etiqueta [PREGUNTA].\n"
    "- Si ya tienes lo suficiente, responde con la etiqueta [GENERAR] seguida de un "
    "resumen de una línea de lo que vas a generar.\n"
    "Responde en español, breve."
)


def _conversacion_texto(mensajes: list[schemas.ChatMensaje]) -> str:
    out = []
    for m in mensajes:
        quien = "Usuario" if m.rol == "user" else "Asistente"
        out.append(f"{quien}: {m.contenido}")
    return "\n".join(out)


def chat_contrato(req: schemas.ChatContratoRequest) -> schemas.ChatContratoResponse:
    """Un turno del chatbot: decide preguntar o generar el documento."""
    from app.llm import build_llm

    prefer = req.proveedor_llm or "auto"
    llm = build_llm(prefer)
    conv = _conversacion_texto(req.mensajes)
    decision = llm.complete(_CHAT_SYSTEM, conv, temperature=0.3, max_tokens=400)
    motor = getattr(llm, "last_used", None)

    up = decision.upper()
    quiere_generar = "[GENERAR]" in up
    # Heurística de respaldo: si el stub/keyword no marca, generar tras varios turnos.
    turnos_usuario = sum(1 for m in req.mensajes if m.rol == "user")
    if "[GENERAR]" not in up and "[PREGUNTA]" not in up and turnos_usuario >= 3:
        quiere_generar = True

    if not quiere_generar:
        pregunta = decision.replace("[PREGUNTA]", "").strip() or \
            "¿Puedes darme más detalles del contrato (proveedor, objeto, precio, entrega)?"
        return schemas.ChatContratoResponse(
            accion="preguntar", respuesta=pregunta, motor=motor)

    # Generar: usar toda la conversación como prompt + contexto.
    resumen = decision.replace("[GENERAR]", "").strip() or "Generando el contrato…"
    gen_req = schemas.GenerarContratoRequest(
        prompt=conv, empresa_proveedor_id=req.empresa_proveedor_id,
        objeto=req.objeto, titulo=req.titulo,
        clausulas_maestras_ids=req.clausulas_maestras_ids,
        precios_maestros_ids=req.precios_maestros_ids,
        proveedor_llm=prefer,
    )
    doc = generar_contrato(gen_req)
    return schemas.ChatContratoResponse(
        accion="generar", respuesta=resumen, documento=doc, motor=motor)
