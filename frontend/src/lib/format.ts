// Helpers de formato y mapeo de estados → estilos de badge (sistema semáforo).

export function formatMoney(value?: number | null, moneda = "COP"): string {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: moneda || "COP",
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value} ${moneda}`;
  }
}

export function formatNumber(value?: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("es-CO").format(value);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "2-digit" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleString("es-CO", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export type BadgeTone = "ok" | "warn" | "danger" | "info" | "neutral";

const TONE_CLASS: Record<BadgeTone, string> = {
  ok: "bg-ok-bg text-ok-fg",
  warn: "bg-warn-bg text-warn-fg",
  danger: "bg-danger-bg text-danger-fg",
  info: "bg-info-bg text-info-fg",
  neutral: "bg-neutral-bg text-neutral-fg",
};

export function toneClass(tone: BadgeTone): string {
  return TONE_CLASS[tone];
}

// Mapeo de cada enum del dominio a un tono semáforo.
export function estadoContratoTone(estado?: string): BadgeTone {
  switch (estado) {
    case "VIGENTE":
      return "ok";
    case "BORRADOR":
      return "neutral";
    case "SUSPENDIDO":
      return "warn";
    case "VENCIDO":
    case "TERMINADO":
      return "danger";
    default:
      return "neutral";
  }
}

export function estadoPropagacionTone(estado?: string): BadgeTone {
  switch (estado) {
    case "APLICADO":
      return "ok";
    case "NOTIFICADO":
      return "info";
    case "PENDIENTE":
      return "warn";
    case "RECHAZADO":
      return "danger";
    default:
      return "neutral";
  }
}

export function estadoNotifTone(estado?: string): BadgeTone {
  switch (estado) {
    case "ENTREGADO":
    case "LEIDO":
      return "ok";
    case "ENVIADO":
      return "info";
    case "PENDIENTE":
      return "warn";
    case "FALLIDO":
      return "danger";
    default:
      return "neutral";
  }
}

export function canalIcon(canal?: string): string {
  switch (canal) {
    case "WHATSAPP":
      return "chat";
    case "GMAIL":
      return "mail";
    case "SISTEMA":
      return "notifications";
    default:
      return "notifications";
  }
}

export function tipoClausulaTone(tipo?: string): BadgeTone {
  switch (tipo) {
    case "PRECIO":
    case "PAGO":
      return "info";
    case "PENALIZACION":
      return "danger";
    case "CONFIDENCIALIDAD":
      return "warn";
    default:
      return "neutral";
  }
}

export function boolTone(v?: boolean): BadgeTone {
  return v ? "ok" : "warn";
}
