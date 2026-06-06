// =============================================================================
// DocSwarm · WhatsApp Gateway (Baileys, vinculación por QR)
// -----------------------------------------------------------------------------
// Vincula una cuenta de WhatsApp como "dispositivo enlazado" (igual que WhatsApp
// Web) escaneando un QR, y expone una mini API HTTP para que el notifier de
// Python envíe mensajes:
//
//   GET  /qr      → página web con el QR para escanear (o estado si ya vinculado)
//   GET  /status  → JSON { connected, me, hasQr }
//   GET  /health  → JSON { status }
//   POST /send    → { to, message }  (header X-API-Key)  envía un texto
//
// La sesión se persiste en AUTH_DIR (volumen) para no re-escanear en cada arranque.
//
// ⚠️ Vincular por QR usa la vía NO oficial de WhatsApp (contra sus ToS): sirve para
//    demos/pruebas; el número puede ser baneado. Para producción usa la Cloud API.
// =============================================================================

import express from "express";
import pino from "pino";
import qrcode from "qrcode";
import { Boom } from "@hapi/boom";
import {
  makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  DisconnectReason,
} from "@whiskeysockets/baileys";

const PORT = parseInt(process.env.PORT || "3000", 10);
const AUTH_DIR = process.env.AUTH_DIR || "/data/auth";
const API_KEY = process.env.WA_GATEWAY_KEY || process.env.SERVICE_API_KEY || "";
const DEFAULT_CC = (process.env.WA_DEFAULT_COUNTRY_CODE || "57").replace(/\D/g, ""); // Colombia por defecto

const log = pino({ level: process.env.LOG_LEVEL || "info" });

// --- Estado en memoria del gateway -------------------------------------------
let sock = null;
let currentQR = null; // string del último QR sin escanear
let connected = false;
let me = null; // { id, name }
let starting = false;

// --- Normaliza un número a JID de WhatsApp -----------------------------------
// Acepta "+57 300 123 4567", "573001234567", "3001234567" → "573001234567@s.whatsapp.net"
function toJid(raw) {
  if (!raw) return null;
  if (typeof raw === "string" && raw.includes("@")) return raw; // ya es JID
  let digits = String(raw).replace(/\D/g, "");
  if (!digits) return null;
  // Si parece un número local (10 dígitos, sin código de país), antepone DEFAULT_CC.
  if (digits.length <= 10 && DEFAULT_CC) digits = DEFAULT_CC + digits;
  return `${digits}@s.whatsapp.net`;
}

// --- Arranque/relanzamiento del socket Baileys -------------------------------
async function startSock() {
  if (starting) return;
  starting = true;
  try {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();
    log.info({ version }, "Iniciando socket Baileys");

    sock = makeWASocket({
      version,
      auth: state,
      printQRInTerminal: false,
      logger: pino({ level: "silent" }),
      browser: ["DocSwarm Notifier", "Chrome", "1.0.0"],
      markOnlineOnConnect: false,
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", (update) => {
      const { connection, lastDisconnect, qr } = update;
      if (qr) {
        currentQR = qr;
        connected = false;
        log.info("Nuevo QR disponible — abre /qr para escanear.");
      }
      if (connection === "open") {
        connected = true;
        currentQR = null;
        me = sock?.user ? { id: sock.user.id, name: sock.user.name } : null;
        log.info({ me }, "✅ WhatsApp vinculado y conectado.");
      }
      if (connection === "close") {
        connected = false;
        const statusCode = new Boom(lastDisconnect?.error)?.output?.statusCode;
        const loggedOut = statusCode === DisconnectReason.loggedOut;
        log.warn({ statusCode, loggedOut }, "Conexión cerrada.");
        starting = false;
        if (loggedOut) {
          // Sesión inválida: limpia credenciales para forzar nuevo QR.
          me = null;
          log.warn("Sesión cerrada por WhatsApp. Re-escanea el QR (borra el volumen si persiste).");
          startSock();
        } else {
          // Reconexión transitoria.
          setTimeout(startSock, 2500);
        }
      }
    });
  } catch (err) {
    log.error({ err }, "Fallo al iniciar el socket");
    starting = false;
    setTimeout(startSock, 5000);
  }
}

// --- HTTP API ----------------------------------------------------------------
const app = express();
app.use(express.json({ limit: "256kb" }));

function requireKey(req, res, next) {
  if (!API_KEY) return next(); // sin key configurada → abierto (solo uso local/dev)
  const key = req.get("X-API-Key") || req.query.key;
  if (key !== API_KEY) return res.status(401).json({ ok: false, error: "X-API-Key inválida" });
  next();
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "wa-gateway", connected });
});

app.get("/status", (_req, res) => {
  res.json({ connected, me, hasQr: Boolean(currentQR) });
});

// Página web con el QR (o estado de vinculación).
app.get("/qr", async (_req, res) => {
  res.set("Content-Type", "text/html; charset=utf-8");
  if (connected) {
    return res.send(page(`
      <div class="ok">✅ WhatsApp vinculado</div>
      <p class="muted">${me ? me.name || "" : ""}<br><code>${me ? me.id : ""}</code></p>
      <p class="muted">El gateway está listo para enviar mensajes.</p>
    `, false));
  }
  if (!currentQR) {
    return res.send(page(`
      <div class="wait">⏳ Generando QR…</div>
      <p class="muted">Espera unos segundos y recarga. Si tarda, revisa los logs del contenedor.</p>
    `, true));
  }
  try {
    const dataUrl = await qrcode.toDataURL(currentQR, { margin: 1, width: 320 });
    return res.send(page(`
      <div class="title">Vincula tu WhatsApp empresarial</div>
      <img src="${dataUrl}" alt="QR de WhatsApp" />
      <ol class="steps">
        <li>Abre <b>WhatsApp</b> en tu teléfono.</li>
        <li>Menú ⋮ → <b>Dispositivos vinculados</b>.</li>
        <li><b>Vincular un dispositivo</b> y escanea este código.</li>
      </ol>
      <p class="muted">Esta página se recarga sola cada 20 s.</p>
    `, true));
  } catch (err) {
    return res.status(500).send(page(`<div class="err">Error generando QR: ${String(err)}</div>`, true));
  }
});

// Envío de un mensaje de texto.
app.post("/send", requireKey, async (req, res) => {
  const { to, message } = req.body || {};
  if (!to || !message) return res.status(400).json({ ok: false, error: "Faltan 'to' o 'message'." });
  if (!connected || !sock) return res.status(503).json({ ok: false, error: "WhatsApp no está vinculado. Abre /qr." });

  const jid = toJid(to);
  if (!jid) return res.status(400).json({ ok: false, error: `Número inválido: ${to}` });

  try {
    // Verifica que el número exista en WhatsApp antes de enviar.
    const [check] = await sock.onWhatsApp(jid).catch(() => [null]);
    if (check && check.exists === false) {
      return res.status(422).json({ ok: false, error: `El número ${to} no está en WhatsApp.` });
    }
    const sent = await sock.sendMessage(jid, { text: String(message) });
    return res.json({ ok: true, id: sent?.key?.id || null, jid });
  } catch (err) {
    log.error({ err }, "Fallo al enviar");
    return res.status(500).json({ ok: false, error: String(err?.message || err) });
  }
});

function page(inner, autoRefresh) {
  return `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
${autoRefresh ? '<meta http-equiv="refresh" content="20">' : ""}
<title>DocSwarm · WhatsApp Gateway</title>
<style>
  body{font-family:Inter,system-ui,sans-serif;background:#f9f9ff;color:#151c27;margin:0;
       min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#fff;border:1px solid #bdc9c8;border-radius:12px;padding:28px;max-width:420px;
        text-align:center;box-shadow:0 10px 15px -3px rgba(0,0,0,.08)}
  h1{font-size:22px;margin:0 0 4px;color:#006565}
  .sub{color:#3e4949;font-size:13px;margin:0 0 20px}
  .title{font-weight:600;font-size:16px;margin-bottom:14px}
  img{border:1px solid #e2e8f8;border-radius:8px}
  .ok{font-size:20px;color:#137333;font-weight:700}
  .wait{font-size:18px;color:#F57F17;font-weight:600}
  .err{color:#ba1a1a}
  .steps{text-align:left;font-size:13px;color:#3e4949;margin:16px auto 0;max-width:300px;line-height:1.6}
  .muted{color:#6e7979;font-size:12px;margin-top:14px}
  code{font-family:"JetBrains Mono",monospace;font-size:11px}
</style></head>
<body><div class="card">
  <h1>DocSwarm · WhatsApp</h1>
  <p class="sub">Gateway de notificaciones (Baileys)</p>
  ${inner}
</div></body></html>`;
}

app.listen(PORT, "0.0.0.0", () => {
  log.info(`wa-gateway escuchando en :${PORT} · QR en /qr`);
  startSock();
});
