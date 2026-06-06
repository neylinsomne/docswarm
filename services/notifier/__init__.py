"""Microservicio `notifier` — comunicación WhatsApp/Gmail + firma electrónica.

Servicio independiente (imagen y puerto propios) para aislar fallos: si se cae,
el core API y la BD siguen funcionando; las notificaciones quedan PENDIENTES
hasta que el notifier vuelva. Comparte la lógica de BD con el core vía
`app.domain.notifications` / `app.domain.signatures` (sin duplicar SQL).

Responsabilidades:
  · Exponer los endpoints máquina-a-máquina (X-API-Key) que consume el repo
    externo de WhatsApp/Gmail: cola de pendientes + callbacks de entrega/firma.
  · Despachar (opcional) las notificaciones pendientes a los canales reales.
"""

__version__ = "0.1.0"
