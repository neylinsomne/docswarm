// Tipos de dominio de DocSwarm. Las respuestas del backend son dicts (FastAPI),
// así que los campos son permisivos; lo crítico para la UI está documentado en
// docs/FRONTEND_PROMPT.md.

export type TipoEmpresa = "COMPRADOR" | "PROVEEDOR";

export type EstadoContrato =
  | "BORRADOR"
  | "VIGENTE"
  | "SUSPENDIDO"
  | "VENCIDO"
  | "TERMINADO";

export type TipoClausula =
  | "PRECIO"
  | "ENTREGA"
  | "CALIDAD"
  | "PAGO"
  | "PENALIZACION"
  | "CONFIDENCIALIDAD"
  | "GENERAL";

export type TipoObjetoCambio = "CLAUSULA" | "PRECIO";
export type AccionCambio = "CREACION" | "ACTUALIZACION" | "DEROGACION";

export type EstadoPropagacion =
  | "PENDIENTE"
  | "NOTIFICADO"
  | "APLICADO"
  | "RECHAZADO";

export type CanalNotif = "WHATSAPP" | "GMAIL" | "SISTEMA";
export type EstadoNotif =
  | "PENDIENTE"
  | "ENVIADO"
  | "ENTREGADO"
  | "LEIDO"
  | "FALLIDO";

export const ESTADOS_CONTRATO: EstadoContrato[] = [
  "BORRADOR",
  "VIGENTE",
  "SUSPENDIDO",
  "VENCIDO",
  "TERMINADO",
];

export const TIPOS_CLAUSULA: TipoClausula[] = [
  "PRECIO",
  "ENTREGA",
  "CALIDAD",
  "PAGO",
  "PENALIZACION",
  "CONFIDENCIALIDAD",
  "GENERAL",
];

export interface Session {
  access_token: string;
  token_type: string;
  empresa_id: number;
  tipo_empresa: TipoEmpresa;
  rol: string;
}

export interface Caracteristica {
  clave: string;
  valor: string;
  valor_num?: number | null;
}

export interface Empresa {
  id: number;
  nombre: string;
  nit?: string | null;
  tipo?: TipoEmpresa;
  tipo_empresa?: TipoEmpresa;
  sector?: string | null;
  nicho?: string | null;
  pais?: string | null;
  ciudad?: string | null;
  activo?: boolean;
  metadata?: Record<string, unknown>;
  caracteristicas?: Caracteristica[];
  creado_en?: string;
}

export interface Clausula {
  id: number;
  contrato_id?: number;
  tipo: TipoClausula | string;
  titulo?: string | null;
  contenido: string;
  orden?: number;
  clausula_maestra_id?: number | null;
  precio_maestro_id?: number | null;
  valor?: number | null;
}

export interface Contrato {
  id: number;
  numero?: string | null;
  titulo: string;
  objeto?: string | null;
  sector?: string | null;
  estado: EstadoContrato | string;
  valor?: number | null;
  moneda?: string;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  empresa_proveedor_id?: number;
  empresa_compradora_id?: number;
  proveedor_nombre?: string | null;
  comprador_nombre?: string | null;
  firmado_proveedor?: boolean;
  fecha_firma?: string | null;
  metadata?: Record<string, unknown>;
  clausulas?: Clausula[];
  creado_en?: string;
}

export interface ClausulaMaestra {
  id: number;
  codigo: string;
  tipo: TipoClausula | string;
  titulo: string;
  contenido_actual: string;
  sector?: string | null;
  nicho?: string | null;
  version?: number;
  vigente?: boolean;
  metadata?: Record<string, unknown>;
}

export interface PrecioMaestro {
  id: number;
  codigo: string;
  producto: string;
  precio: number;
  categoria?: string | null;
  moneda?: string;
  unidad?: string | null;
  sector?: string | null;
  nicho?: string | null;
  version?: number;
  vigente?: boolean;
}

export interface Cambio {
  id: number;
  objeto_codigo?: string;
  objeto_titulo?: string;
  tipo_objeto: TipoObjetoCambio | string;
  accion?: AccionCambio | string;
  descripcion?: string | null;
  docs_afectados?: number;
  docs_firmados?: number;
  docs_pendientes?: number;
  creado_en?: string;
}

export interface CambioAfectado {
  id: number;
  afectado_id?: number;
  cambio_id?: number;
  contrato_id?: number;
  contrato_titulo?: string;
  contrato_numero?: string;
  proveedor_nombre?: string;
  empresa_proveedor_id?: number;
  estado_propagacion: EstadoPropagacion | string;
  firmado_proveedor?: boolean;
  fecha_firma?: string | null;
  notificado_at?: string | null;
  observaciones?: string | null;
}

export interface Notificacion {
  id: number;
  canal: CanalNotif | string;
  asunto?: string | null;
  mensaje?: string | null;
  destino?: string | null;
  estado: EstadoNotif | string;
  leida?: boolean;
  leida_at?: string | null;
  enviado_at?: string | null;
  entregado_at?: string | null;
  creado_en?: string;
}

export interface Firma {
  id: number;
  tipo?: string;
  estado?: string;
  contrato_id?: number;
  afectado_id?: number;
  firmado_at?: string | null;
  creado_en?: string;
}

export interface BusquedaContenido {
  contrato_id: number;
  contrato_titulo?: string;
  fragmento?: string;
  texto?: string;
  similarity?: number;
  score?: number;
}

export interface GenerarContratoResponse {
  titulo: string;
  markdown?: string;
  html?: string;
  secciones?: ({ titulo: string; contenido: string } | string)[];
  warnings?: string[];
  motor?: string | null;
}

export interface ChatMensaje {
  rol: "user" | "assistant" | string;
  contenido: string;
}

export interface ChatContratoResponse {
  accion: "preguntar" | "generar" | string;
  respuesta: string;
  documento?: GenerarContratoResponse | null;
  motor?: string | null;
}

export interface CambioResultado {
  cambio_id: number;
  docs_afectados: number;
  notificaciones: number;
}
