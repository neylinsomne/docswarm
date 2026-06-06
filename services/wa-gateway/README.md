# wa-gateway · WhatsApp por QR (Baileys)

Microservicio Node que vincula una cuenta de WhatsApp como **dispositivo enlazado**
(igual que WhatsApp Web) y permite al `notifier` enviar mensajes de texto.

> ⚠️ Vincular por QR es la vía **no oficial** de WhatsApp (contra sus ToS). Sirve para
> demos/pruebas; el número puede ser **baneado**. Para producción, usa la **Cloud API**
> oficial (sin QR, con templates aprobados).

## Endpoints
| Método | Ruta | Uso |
|---|---|---|
| GET | `/qr` | Página web con el QR para escanear (o estado si ya vinculado) |
| GET | `/status` | `{ connected, me, hasQr }` |
| GET | `/health` | salud |
| POST | `/send` | `{ to, message }` · header `X-API-Key` · envía un texto |

## Vincular
1. `docker compose up -d wa-gateway`
2. Abre **http://localhost:3010/qr**
3. En tu teléfono: WhatsApp → ⋮ → **Dispositivos vinculados** → **Vincular un dispositivo** → escanea.
4. La sesión queda guardada en el volumen `wa_auth` (no hay que re-escanear).

## Probar envío
```bash
curl -X POST http://localhost:3010/send \
  -H "X-API-Key: $SERVICE_API_KEY" -H "Content-Type: application/json" \
  -d '{"to":"+57 300 123 4567","message":"Hola desde DocSwarm 👋"}'
```

El número se normaliza a JID; si llega sin código de país y tiene ≤10 dígitos, se le
antepone `WA_DEFAULT_COUNTRY_CODE` (por defecto `57`, Colombia).

## Variables
- `PORT` (3000 interno), `AUTH_DIR` (`/data/auth`)
- `WA_GATEWAY_KEY` / `SERVICE_API_KEY` — protege `/send`
- `WA_DEFAULT_COUNTRY_CODE` — prefijo país para números locales (default `57`)

## Resetear sesión
Borra el volumen de auth para forzar un QR nuevo:
```bash
docker compose down wa-gateway && docker volume rm docswarm_wa_auth
```
