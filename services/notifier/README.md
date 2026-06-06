# `services/notifier/` — Microservicio de comunicación (WhatsApp/Gmail + firma)

Servicio **independiente** (imagen y puerto propios, por defecto **8010**) para
aislar fallos: si se cae, el core API y la BD siguen funcionando y las
notificaciones quedan `PENDIENTE` hasta que vuelva. Comparte la lógica de BD con
el core vía `app.domain.notifications` / `app.domain.signatures` (sin duplicar SQL).

```
services/notifier/
├── main.py              API M2M (X-API-Key): cola + callbacks + dispatcher
├── channels/
│   ├── base.py          contrato Channel.send() → SendResult
│   ├── whatsapp.py      ►► PEGA AQUÍ el código de WhatsApp ◄◄ (dry-run sin credenciales)
│   └── gmail.py         ►► PEGA AQUÍ el código de Gmail ◄◄
└── Dockerfile           imagen liviana (solo extra [backend])
```

## Autenticación
Todos los endpoints son **máquina-a-máquina** con header `X-API-Key:
$SERVICE_API_KEY`. Corren en contexto admin (ven/actualizan todos los tenants).

## Endpoints (contrato de integración)

| Método | Ruta | Para qué |
|---|---|---|
| GET  | `/pendientes?canal=&limit=` | Cola pull: notificaciones por enviar |
| POST | `/notificaciones/{id}/estado` | Callback de entrega: `ENVIADO\|ENTREGADO\|LEIDO\|FALLIDO` (al ENTREGADO/LEIDO marca el doc afectado `NOTIFICADO`) |
| POST | `/firmas` | Inicia firma electrónica → devuelve `firma_id` + `token` |
| POST | `/firmas/{id}/evento` | Callback de firma: `FIRMADA` marca `firmado_proveedor=TRUE` |
| POST | `/dispatch?canal=&limit=` | Envía pendientes por los canales locales (si pegaste el código aquí) |
| GET  | `/health` | Liveness |

## Dos formas de integrar tu repo de WhatsApp/Gmail

**(a) El otro repo envía (pull + callbacks).** Tu repo hace `GET /pendientes`,
envía por su cuenta y reporta con `POST /notificaciones/{id}/estado`. La firma se
inicia con `POST /firmas` y se confirma con `POST /firmas/{id}/evento`.

**(b) El envío vive aquí.** Pega el código en `channels/whatsapp.py` /
`gmail.py` y llama `POST /dispatch` (o un cron) — el dispatcher toma las
pendientes, las envía y actualiza el estado.

## Ejemplo (curl)

```bash
KEY=$SERVICE_API_KEY
# 1) ver pendientes
curl localhost:8010/pendientes -H "X-API-Key: $KEY"
# 2) reportar entrega (→ documento afectado NOTIFICADO)
curl -X POST localhost:8010/notificaciones/1/estado -H "X-API-Key: $KEY" \
     -H "Content-Type: application/json" -d '{"estado":"ENTREGADO","referencia_externa":"wa-123"}'
# 3) iniciar firma del documento afectado
curl -X POST localhost:8010/firmas -H "X-API-Key: $KEY" \
     -H "Content-Type: application/json" -d '{"afectado_id":4,"canal":"WHATSAPP","usuario_id":2}'
# 4) confirmar firma (→ firmado_proveedor=TRUE)
curl -X POST localhost:8010/firmas/1/evento -H "X-API-Key: $KEY" \
     -H "Content-Type: application/json" -d '{"estado":"FIRMADA","evidencia":{"otp":"123456"}}'
```

Sin credenciales de canal (`WHATSAPP_TOKEN`/`GMAIL_USER` vacíos) los adaptadores
operan en **dry-run** (simulan entrega) para poder probar todo el flujo del MVP.
