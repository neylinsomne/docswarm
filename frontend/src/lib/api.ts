// Cliente tipado del Core API de DocSwarm.
// Base URL relativa (/api) → en dev la redirige Vite proxy; en prod nginx la
// reenvía a http://api:8000. Así el navegador habla con un único origen (sin CORS).

import type {
  Cambio,
  CambioAfectado,
  CambioResultado,
  Caracteristica,
  ChatContratoResponse,
  Clausula,
  ClausulaMaestra,
  Contrato,
  Empresa,
  Firma,
  GenerarContratoResponse,
  Notificacion,
  PrecioMaestro,
  Session,
} from "./types";

const TOKEN_KEY = "docswarm.token";
const SESSION_KEY = "docswarm.session";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function getSession(): Session | null {
  const raw = localStorage.getItem(SESSION_KEY);
  return raw ? (JSON.parse(raw) as Session) : null;
}
export function saveSession(s: Session) {
  localStorage.setItem(TOKEN_KEY, s.access_token);
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
}
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(SESSION_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// Evento global para que el AuthProvider reaccione ante un 401.
function emitUnauthorized() {
  window.dispatchEvent(new CustomEvent("docswarm:unauthorized"));
}

function extractDetail(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const d = (body as { detail?: unknown }).detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((e) =>
        e && typeof e === "object" && "msg" in e
          ? `${(e as { loc?: unknown[] }).loc?.slice(1).join(".") ?? ""}: ${(e as { msg: string }).msg}`
          : String(e),
      )
      .join(" · ");
  }
  return undefined;
}

interface RequestOpts {
  method?: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  form?: URLSearchParams; // application/x-www-form-urlencoded (login)
  multipart?: FormData; // subida de documentos
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOpts["query"]): string {
  const url = new URL(path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  return url.pathname + url.search;
}

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = opts.form.toString();
  } else if (opts.multipart) {
    body = opts.multipart; // el navegador fija el boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(buildUrl(path, opts.query), {
    method: opts.method ?? "GET",
    headers,
    body,
    signal: opts.signal,
  });

  if (res.status === 401) {
    emitUnauthorized();
    throw new ApiError(401, "Sesión expirada. Inicia sesión de nuevo.");
  }

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const payload = res.status === 204 ? null : isJson ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    const msg =
      extractDetail(payload) ||
      (typeof payload === "string" && payload) ||
      `Error ${res.status}`;
    throw new ApiError(res.status, msg, payload);
  }
  return payload as T;
}

// Descarga binaria (PDF) con auth → object-URL para <iframe>/descarga.
async function blobUrl(
  path: string,
  opts: { method?: string; json?: unknown } = {},
): Promise<string> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  const res = await fetch(buildUrl(path), { method: opts.method ?? "GET", headers, body });
  if (res.status === 401) {
    emitUnauthorized();
    throw new ApiError(401, "Sesión expirada.");
  }
  if (!res.ok) throw new ApiError(res.status, "No se pudo generar el PDF.");
  return URL.createObjectURL(await res.blob());
}

// ---------------------------------------------------------------------------
// Helpers de listas: el backend puede devolver [] o {items: [...]}.
// ---------------------------------------------------------------------------
function asList<T>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    for (const key of ["items", "data", "results", "rows"]) {
      if (Array.isArray(o[key])) return o[key] as T[];
    }
  }
  return [];
}

// ===========================================================================
// API
// ===========================================================================
export const api = {
  // ---- Auth ----
  async login(email: string, password: string): Promise<Session> {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const s = await request<Session>("/api/v1/auth/login", { method: "POST", form });
    saveSession(s);
    return s;
  },
  crearUsuario(payload: {
    empresa_id: number;
    email: string;
    password: string;
    nombre?: string;
    rol?: string;
  }) {
    return request("/api/v1/auth/usuarios", { method: "POST", body: payload });
  },

  // ---- Empresas / Proveedores ----
  async listarEmpresas(q: {
    nombre?: string;
    sector?: string;
    nicho?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<Empresa[]> {
    return asList<Empresa>(await request("/api/v1/empresas", { query: q }));
  },
  async buscarEmpresasFacetado(filtro: {
    nombre?: string;
    sector?: string;
    nicho?: string;
    caracteristicas?: Record<string, string>;
    limit?: number;
    offset?: number;
  }): Promise<Empresa[]> {
    return asList<Empresa>(
      await request("/api/v1/empresas/buscar", { method: "POST", body: filtro }),
    );
  },
  crearEmpresa(payload: {
    nombre: string;
    nit?: string;
    tipo?: string;
    sector?: string;
    nicho?: string;
    pais?: string;
    ciudad?: string;
    metadata?: Record<string, unknown>;
    caracteristicas?: Caracteristica[];
  }) {
    return request<Empresa>("/api/v1/empresas", { method: "POST", body: payload });
  },
  obtenerEmpresa(id: number) {
    return request<Empresa>(`/api/v1/empresas/${id}`);
  },
  actualizarEmpresa(
    id: number,
    payload: Partial<{
      nombre: string;
      sector: string;
      nicho: string;
      ciudad: string;
      metadata: Record<string, unknown>;
      activo: boolean;
    }>,
  ) {
    return request<Empresa>(`/api/v1/empresas/${id}`, { method: "PATCH", body: payload });
  },

  // ---- Catálogo maestro ----
  async catalogoClausulas(q: { q?: string; tipo?: string; sector?: string; limit?: number } = {}) {
    return asList<ClausulaMaestra>(await request("/api/v1/catalogo/clausulas", { query: q }));
  },
  crearClausulaMaestra(payload: {
    codigo: string;
    tipo: string;
    titulo: string;
    contenido_actual: string;
    sector?: string;
    nicho?: string;
    metadata?: Record<string, unknown>;
  }) {
    return request<ClausulaMaestra>("/api/v1/catalogo/clausulas", { method: "POST", body: payload });
  },
  async catalogoPrecios(q: { q?: string; categoria?: string; limit?: number } = {}) {
    return asList<PrecioMaestro>(await request("/api/v1/catalogo/precios", { query: q }));
  },
  crearPrecioMaestro(payload: {
    codigo: string;
    producto: string;
    precio: number;
    categoria?: string;
    moneda?: string;
    unidad?: string;
    sector?: string;
    nicho?: string;
    metadata?: Record<string, unknown>;
  }) {
    return request<PrecioMaestro>("/api/v1/catalogo/precios", { method: "POST", body: payload });
  },

  // ---- Contratos ----
  async listarContratos(q: { estado?: string; limit?: number; offset?: number } = {}) {
    return asList<Contrato>(await request("/api/v1/contratos", { query: q }));
  },
  obtenerContrato(id: number) {
    return request<Contrato>(`/api/v1/contratos/${id}`);
  },
  crearContrato(payload: {
    empresa_proveedor_id: number;
    empresa_compradora_id: number;
    titulo: string;
    numero?: string;
    objeto?: string;
    sector?: string;
    valor?: number;
    moneda?: string;
    fecha_inicio?: string;
    fecha_fin?: string;
    metadata?: Record<string, unknown>;
    clausulas?: {
      tipo: string;
      contenido: string;
      titulo?: string;
      orden?: number;
      valor?: number;
    }[];
    clausulas_maestras_ids?: number[];
    precios_maestros_ids?: number[];
  }) {
    return request<Contrato>("/api/v1/contratos", { method: "POST", body: payload });
  },
  generarContrato(payload: {
    prompt: string;
    empresa_proveedor_id?: number;
    contrato_id?: number;
    objeto?: string;
    titulo?: string;
    clausulas_maestras_ids?: number[];
    precios_maestros_ids?: number[];
    use_ollama?: boolean;
    proveedor_llm?: string; // auto | ollama | gemini | stub
  }) {
    return request<GenerarContratoResponse>("/api/v1/contratos/generar", {
      method: "POST",
      body: payload,
    });
  },
  // Chatbot ACP con decisiones (pregunta vs genera).
  chatContrato(payload: {
    mensajes: { rol: string; contenido: string }[];
    empresa_proveedor_id?: number;
    objeto?: string;
    titulo?: string;
    clausulas_maestras_ids?: number[];
    precios_maestros_ids?: number[];
    proveedor_llm?: string;
  }) {
    return request<ChatContratoResponse>("/api/v1/contratos/chat", {
      method: "POST",
      body: payload,
    });
  },
  // PDF del contrato como object-URL (fetch con auth → blob).
  async contratoPdfUrl(id: number): Promise<string> {
    return blobUrl(`/api/v1/contratos/${id}/pdf`);
  },
  // PDF de un documento generado por la IA (markdown → PDF con firmas).
  async documentoPdfUrl(payload: { titulo: string; markdown: string; proveedor?: string }): Promise<string> {
    return blobUrl("/api/v1/contratos/documento/pdf", { method: "POST", json: payload });
  },
  actualizarContrato(
    id: number,
    payload: Partial<{
      titulo: string;
      objeto: string;
      sector: string;
      estado: string;
      valor: number;
      moneda: string;
      fecha_inicio: string;
      fecha_fin: string;
      metadata: Record<string, unknown>;
    }>,
  ) {
    return request<Contrato>(`/api/v1/contratos/${id}`, { method: "PATCH", body: payload });
  },
  agregarClausula(
    contratoId: number,
    payload: {
      tipo: string;
      contenido: string;
      titulo?: string;
      orden?: number;
      clausula_maestra_id?: number;
      precio_maestro_id?: number;
      valor?: number;
    },
  ) {
    return request<Clausula>(`/api/v1/contratos/${contratoId}/clausulas`, {
      method: "POST",
      body: payload,
    });
  },
  actualizarClausula(
    clausulaId: number,
    payload: Partial<{ tipo: string; titulo: string; contenido: string; orden: number; valor: number }>,
  ) {
    return request<Clausula>(`/api/v1/contratos/clausulas/${clausulaId}`, {
      method: "PATCH",
      body: payload,
    });
  },
  eliminarClausula(clausulaId: number) {
    return request<void>(`/api/v1/contratos/clausulas/${clausulaId}`, { method: "DELETE" });
  },
  firmarContrato(contratoId: number, firmado = true) {
    return request(`/api/v1/contratos/${contratoId}/firma`, {
      method: "POST",
      body: { firmado },
    });
  },

  // ---- Cambios (log central) ----
  async listarCambios(q: { limit?: number; offset?: number } = {}) {
    return asList<Cambio>(await request("/api/v1/cambios", { query: q }));
  },
  cambiarClausula(payload: { clausula_maestra_id: number; nuevo_contenido: string; descripcion?: string }) {
    return request<CambioResultado>("/api/v1/cambios/clausula", { method: "POST", body: payload });
  },
  cambiarPrecio(payload: { precio_maestro_id: number; nuevo_precio: number; descripcion?: string }) {
    return request<CambioResultado>("/api/v1/cambios/precio", { method: "POST", body: payload });
  },
  async detalleAfectados(cambioId: number) {
    return asList<CambioAfectado>(await request(`/api/v1/cambios/${cambioId}/afectados`));
  },
  firmarAfectado(afectadoId: number, observaciones?: string) {
    return request(`/api/v1/cambios/afectados/${afectadoId}/firma`, {
      method: "POST",
      body: { observaciones: observaciones ?? null },
    });
  },

  // ---- Firma electrónica in-page ----
  async listarFirmas(q: { limit?: number; offset?: number } = {}) {
    return asList<Firma>(await request("/api/v1/firmas", { query: q }));
  },
  firmaAfectadoInPage(afectadoId: number, evidencia?: Record<string, unknown>) {
    return request(`/api/v1/firmas/afectado/${afectadoId}`, {
      method: "POST",
      body: { evidencia: evidencia ?? null },
    });
  },
  firmaContratoInPage(contratoId: number, evidencia?: Record<string, unknown>) {
    return request(`/api/v1/firmas/contrato/${contratoId}`, {
      method: "POST",
      body: { evidencia: evidencia ?? null },
    });
  },

  // ---- Notificaciones ----
  async listarNotificaciones(q: { canal?: string; no_leidas?: boolean; limit?: number; offset?: number } = {}) {
    return asList<Notificacion>(await request("/api/v1/notificaciones", { query: q }));
  },
  async conteoNoLeidas(): Promise<number> {
    const r = await request<{ no_leidas?: number; conteo?: number; total?: number; count?: number } | number>(
      "/api/v1/notificaciones/no_leidas/conteo",
    );
    if (typeof r === "number") return r;
    return r?.no_leidas ?? r?.conteo ?? r?.total ?? r?.count ?? 0;
  },
  marcarLeida(notifId: number) {
    return request(`/api/v1/notificaciones/${notifId}/leida`, { method: "POST" });
  },

  // ---- Documentos ----
  subirDocumento(file: File, opts: { contrato_id?: number; titulo?: string } = {}) {
    const fd = new FormData();
    fd.set("archivo", file);
    if (opts.contrato_id != null) fd.set("contrato_id", String(opts.contrato_id));
    if (opts.titulo) fd.set("titulo", opts.titulo);
    return request("/api/v1/documentos", { method: "POST", multipart: fd });
  },

  // ---- Búsqueda ----
  async buscarContenido(q: string, top_k = 10) {
    return asList(await request("/api/v1/buscar/contenido", { query: { q, top_k } }));
  },
  async buscarContratos(q: string, limit = 20) {
    return asList<Contrato>(await request("/api/v1/buscar/contratos", { query: { q, limit } }));
  },
  async buscarEmpresas(q: string, top_k = 20) {
    return asList<Empresa>(await request("/api/v1/buscar/empresas", { query: { q, top_k } }));
  },

  // ---- Salud ----
  health() {
    return request("/health");
  },
};
