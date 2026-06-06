"""API del microservicio `notifier` (puerto propio, ej. 8010).

Todos los endpoints son máquina-a-máquina (header ``X-API-Key``). Los consume el
repo externo de WhatsApp/Gmail, o el propio dispatcher interno.

    uvicorn services.notifier.main:app --host 0.0.0.0 --port 8010
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from app.db import close_pool, get_pool
from app.domain.notifications import schemas as nschemas
from app.domain.notifications import service as notif_service
from app.domain.signatures import schemas as fschemas
from app.domain.signatures import service as firma_service
from app.security.deps import require_service_key
from services.notifier.channels import REGISTRY

app = FastAPI(
    title="docswarm notifier · WhatsApp/Gmail + firma electrónica",
    description="Microservicio de comunicación. Endpoints M2M con X-API-Key.",
    version="0.1.0",
)


@app.on_event("startup")
def _startup() -> None:
    get_pool()


@app.on_event("shutdown")
def _shutdown() -> None:
    close_pool()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "notifier", "canales": list(REGISTRY)}


# --- Cola pull: el sender externo reclama las pendientes -----------------------
@app.get("/pendientes", tags=["notificaciones"],
         dependencies=[Depends(require_service_key)])
def pendientes(canal: Optional[str] = Query(None), limit: int = Query(100, le=500)):
    return notif_service.listar_pendientes(canal, limit)


# --- Callback de entrega ------------------------------------------------------
@app.post("/notificaciones/{notif_id}/estado", tags=["notificaciones"],
          dependencies=[Depends(require_service_key)])
def actualizar_estado(notif_id: int, data: nschemas.EstadoUpdate):
    try:
        ok = notif_service.actualizar_estado(
            notif_id, data.estado, referencia_externa=data.referencia_externa,
            error=data.error)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "notificación no encontrada")
    return {"ok": True}


# --- Firma electrónica --------------------------------------------------------
@app.post("/firmas", tags=["firmas"], status_code=201,
          dependencies=[Depends(require_service_key)])
def iniciar_firma(data: fschemas.IniciarFirma):
    try:
        return firma_service.iniciar_firma(data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/firmas/{firma_id}/evento", tags=["firmas"],
          dependencies=[Depends(require_service_key)])
def evento_firma(firma_id: int, data: fschemas.EventoFirma):
    try:
        ok = firma_service.registrar_evento(firma_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "firma no encontrada")
    return {"ok": True, "estado": data.estado}


# --- Dispatcher interno: envía pendientes por los canales (código pegado) -----
@app.post("/dispatch", tags=["dispatch"],
          dependencies=[Depends(require_service_key)])
def dispatch(canal: Optional[str] = Query(None), limit: int = Query(50, le=200)):
    """Toma pendientes y las envía por el canal correspondiente, marcando estado.

    Útil cuando el envío vive aquí (canales en services/notifier/channels). Si el
    envío lo hace el repo externo, usa /pendientes + /notificaciones/{id}/estado.
    """
    enviados, fallidos = 0, 0
    for n in notif_service.listar_pendientes(canal, limit):
        ch = REGISTRY.get(n["canal"])
        if ch is None:
            notif_service.actualizar_estado(n["id"], "FALLIDO",
                                            error=f"sin canal {n['canal']}")
            fallidos += 1
            continue
        res = ch.send(destino=n["destino"], asunto=n["asunto"],
                      mensaje=n["mensaje"], metadata=n["metadata"])
        if res.ok:
            notif_service.actualizar_estado(
                n["id"], "ENTREGADO", referencia_externa=res.referencia_externa)
            enviados += 1
        else:
            notif_service.actualizar_estado(n["id"], "FALLIDO", error=res.error)
            fallidos += 1
    return {"enviados": enviados, "fallidos": fallidos}
