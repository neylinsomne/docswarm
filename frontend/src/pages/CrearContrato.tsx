import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, Field, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { formatMoney } from "../lib/format";
import { TIPOS_CLAUSULA, type ChatMensaje, type GenerarContratoResponse } from "../lib/types";

const MOTORES = [
  { id: "auto", label: "Auto (Gemini→Ollama→stub)" },
  { id: "gemini", label: "Gemini" },
  { id: "ollama", label: "Ollama (local)" },
  { id: "stub", label: "Offline (stub)" },
];

interface Datos {
  empresa_proveedor_id?: number;
  titulo: string;
  numero: string;
  objeto: string;
  sector: string;
  valor: string;
  moneda: string;
  fecha_inicio: string;
  fecha_fin: string;
}
interface ClausulaManual { tipo: string; titulo: string; contenido: string; valor?: string }

const STEPS = ["Datos", "Asistente IA / Cláusulas", "Confirmar"];

export function CrearContrato() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [datos, setDatos] = useState<Datos>({ titulo: "", numero: "", objeto: "", sector: "", valor: "", moneda: "COP", fecha_inicio: "", fecha_fin: "" });
  const [provQuery, setProvQuery] = useState("");
  const [provNombre, setProvNombre] = useState("");
  const [clausulasMaestrasIds, setClausulasMaestrasIds] = useState<number[]>([]);
  const [preciosMaestrosIds, setPreciosMaestrosIds] = useState<number[]>([]);
  const [manuales, setManuales] = useState<ClausulaManual[]>([]);
  const [generado, setGenerado] = useState<GenerarContratoResponse | null>(null);

  const proveedores = useQuery({ queryKey: ["empresas", "wizard", provQuery], queryFn: () => api.listarEmpresas({ nombre: provQuery, limit: 20 }) });

  const crear = useMutation({
    mutationFn: () =>
      api.crearContrato({
        empresa_proveedor_id: datos.empresa_proveedor_id!,
        empresa_compradora_id: session!.empresa_id,
        titulo: datos.titulo,
        numero: datos.numero || undefined,
        objeto: datos.objeto || undefined,
        sector: datos.sector || undefined,
        valor: datos.valor ? Number(datos.valor) : undefined,
        moneda: datos.moneda,
        fecha_inicio: datos.fecha_inicio || undefined,
        fecha_fin: datos.fecha_fin || undefined,
        clausulas: manuales.map((m, i) => ({ tipo: m.tipo, contenido: m.contenido, titulo: m.titulo || undefined, orden: i, valor: m.valor ? Number(m.valor) : undefined })),
        clausulas_maestras_ids: clausulasMaestrasIds,
        precios_maestros_ids: preciosMaestrosIds,
      }),
    onSuccess: (c) => { toast.success("Contrato creado."); navigate(`/contratos/${c.id}`); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "No se pudo crear."),
  });

  const canNext = step === 0 ? !!datos.empresa_proveedor_id && !!datos.titulo : true;

  return (
    <div className="mx-auto max-w-[760px]">
      <button onClick={() => navigate("/contratos")} className="mb-3 flex items-center gap-1 font-body-sm text-body-sm text-primary"><Icon name="arrow_back" className="text-[18px]" /> Contratos</button>
      <PageHeader title="Nuevo contrato" subtitle="Paso 1 datos · Paso 2 chatbot IA que redacta el contrato · Paso 3 confirmar." />

      <div className="mb-stack-relaxed flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className="flex flex-1 items-center gap-2">
            <div className={`flex h-7 w-7 items-center justify-center rounded-full text-body-sm font-bold ${i <= step ? "bg-primary text-on-primary" : "bg-surface-container-high text-secondary"}`}>{i + 1}</div>
            <span className={`font-body-sm text-body-sm ${i === step ? "font-semibold text-on-surface" : "text-secondary"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="h-px flex-1 bg-outline-variant" />}
          </div>
        ))}
      </div>

      <div className="card p-5">
        {step === 0 && (
          <div className="flex flex-col gap-3">
            <Field label="Proveedor" required>
              <input className="input" placeholder="Buscar proveedor…" value={provNombre || provQuery} onChange={(e) => { setProvQuery(e.target.value); setProvNombre(""); setDatos({ ...datos, empresa_proveedor_id: undefined }); }} />
              {!datos.empresa_proveedor_id && provQuery && (
                <div className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-outline-variant">
                  {proveedores.data?.map((p) => (
                    <button key={p.id} className="block w-full px-3 py-2 text-left hover:bg-surface-container-high" onClick={() => { setDatos({ ...datos, empresa_proveedor_id: p.id }); setProvNombre(p.nombre); setProvQuery(""); }}>
                      {p.nombre} <span className="font-data-mono text-data-mono text-outline">#{p.id}</span>
                    </button>
                  ))}
                </div>
              )}
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Título" required><input className="input" value={datos.titulo} onChange={(e) => setDatos({ ...datos, titulo: e.target.value })} /></Field>
              <Field label="Número"><input className="input" value={datos.numero} onChange={(e) => setDatos({ ...datos, numero: e.target.value })} /></Field>
              <Field label="Objeto"><input className="input" value={datos.objeto} onChange={(e) => setDatos({ ...datos, objeto: e.target.value })} /></Field>
              <Field label="Sector"><input className="input" value={datos.sector} onChange={(e) => setDatos({ ...datos, sector: e.target.value })} /></Field>
              <Field label="Valor"><input className="input" type="number" value={datos.valor} onChange={(e) => setDatos({ ...datos, valor: e.target.value })} /></Field>
              <Field label="Moneda"><input className="input" value={datos.moneda} onChange={(e) => setDatos({ ...datos, moneda: e.target.value })} /></Field>
              <Field label="Fecha inicio"><input className="input" type="date" value={datos.fecha_inicio} onChange={(e) => setDatos({ ...datos, fecha_inicio: e.target.value })} /></Field>
              <Field label="Fecha fin"><input className="input" type="date" value={datos.fecha_fin} onChange={(e) => setDatos({ ...datos, fecha_fin: e.target.value })} /></Field>
            </div>
          </div>
        )}

        {step === 1 && (
          <PasoClausulas
            clausulasMaestrasIds={clausulasMaestrasIds} setClausulasMaestrasIds={setClausulasMaestrasIds}
            preciosMaestrosIds={preciosMaestrosIds} setPreciosMaestrosIds={setPreciosMaestrosIds}
            manuales={manuales} setManuales={setManuales}
            datos={datos} generado={generado} setGenerado={setGenerado}
          />
        )}

        {step === 2 && (
          <div className="flex flex-col gap-3">
            <h3 className="font-title-sm text-title-sm">Resumen</h3>
            <dl className="grid grid-cols-2 gap-2 text-body-md">
              <Sum label="Proveedor" value={provNombre || `#${datos.empresa_proveedor_id}`} />
              <Sum label="Título" value={datos.titulo} />
              <Sum label="Valor" value={formatMoney(datos.valor ? Number(datos.valor) : null, datos.moneda)} />
              <Sum label="Objeto" value={datos.objeto || "—"} />
            </dl>
            <div className="flex flex-wrap gap-2">
              <Badge tone="info">{clausulasMaestrasIds.length} cláusulas maestras</Badge>
              <Badge tone="info">{preciosMaestrosIds.length} precios maestros</Badge>
              <Badge tone="neutral">{manuales.length} cláusulas manuales</Badge>
            </div>
            {generado?.markdown && (
              <div>
                <p className="label">Documento generado (ACP)</p>
                <div className="max-h-64 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-low p-4 font-body-sm text-body-sm whitespace-pre-wrap">{generado.markdown}</div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-stack-relaxed flex justify-between">
        <button className="btn-ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}><Icon name="arrow_back" className="text-[18px]" /> Atrás</button>
        {step < 2 ? (
          <button className="btn-primary" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>Siguiente <Icon name="arrow_forward" className="text-[18px]" /></button>
        ) : (
          <button className="btn-primary" disabled={crear.isPending} onClick={() => crear.mutate()}>{crear.isPending ? <Spinner /> : <><Icon name="check" className="text-[18px]" /> Crear contrato</>}</button>
        )}
      </div>
    </div>
  );
}

function Sum({ label, value }: { label: string; value: string }) {
  return <div><dt className="font-label-caps text-label-caps uppercase text-secondary">{label}</dt><dd className="text-on-surface">{value}</dd></div>;
}

function PasoClausulas(props: {
  clausulasMaestrasIds: number[]; setClausulasMaestrasIds: (v: number[]) => void;
  preciosMaestrosIds: number[]; setPreciosMaestrosIds: (v: number[]) => void;
  manuales: ClausulaManual[]; setManuales: (v: ClausulaManual[]) => void;
  datos: Datos; generado: GenerarContratoResponse | null; setGenerado: (g: GenerarContratoResponse | null) => void;
}) {
  const { clausulasMaestrasIds, setClausulasMaestrasIds, preciosMaestrosIds, setPreciosMaestrosIds, manuales, setManuales, datos, generado, setGenerado } = props;
  const toast = useToast();
  const [tab, setTab] = useState<"catalogo" | "acp">("acp");
  const [qCl, setQCl] = useState("");
  const [qPr, setQPr] = useState("");
  const [motor, setMotor] = useState("auto");
  const [mensajes, setMensajes] = useState<ChatMensaje[]>([
    { rol: "assistant", contenido: "Hola, soy el asistente de contratos. Cuéntame qué contrato quieres crear (proveedor, objeto, precio, entrega, calidad) y te iré preguntando lo que falte. Cuando tenga lo necesario, generaré el documento." },
  ]);
  const [entrada, setEntrada] = useState("");

  const clausulas = useQuery({ queryKey: ["cat-clausulas", qCl], queryFn: () => api.catalogoClausulas({ q: qCl, limit: 30 }) });
  const precios = useQuery({ queryKey: ["cat-precios", qPr], queryFn: () => api.catalogoPrecios({ q: qPr, limit: 30 }) });

  const chat = useMutation({
    mutationFn: (msgs: ChatMensaje[]) => api.chatContrato({
      mensajes: msgs, empresa_proveedor_id: datos.empresa_proveedor_id,
      objeto: datos.objeto || undefined, titulo: datos.titulo || "Contrato",
      clausulas_maestras_ids: clausulasMaestrasIds, precios_maestros_ids: preciosMaestrosIds,
      proveedor_llm: motor,
    }),
    onSuccess: (r) => {
      setMensajes((m) => [...m, { rol: "assistant", contenido: r.respuesta }]);
      if (r.accion === "generar" && r.documento) {
        setGenerado(r.documento);
        setPdfUrl(null);
        toast.success(`Documento generado${r.motor ? ` (${r.motor})` : ""}.`);
      }
    },
    onError: (e) => {
      const msg = e instanceof ApiError ? e.message : "Error en el chat.";
      setMensajes((m) => [...m, { rol: "assistant", contenido: `⚠️ ${msg}` }]);
    },
  });

  const enviar = () => {
    const texto = entrada.trim();
    if (!texto || chat.isPending) return;
    const next = [...mensajes, { rol: "user", contenido: texto }];
    setMensajes(next);
    setEntrada("");
    chat.mutate(next);
  };

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const verPdfGenerado = async () => {
    if (!generado) return;
    setPdfLoading(true);
    try {
      const url = await api.documentoPdfUrl({
        titulo: generado.titulo,
        markdown: generado.markdown ?? generado.html ?? "",
      });
      setPdfUrl(url);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "No se pudo generar el PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  const toggle = (arr: number[], set: (v: number[]) => void, id: number) => set(arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id]);

  return (
    <div>
      <div className="mb-4 flex gap-1 rounded-lg bg-surface-container p-1">
        <button onClick={() => setTab("catalogo")} className={`flex-1 rounded-lg px-3 py-1.5 text-body-sm font-semibold ${tab === "catalogo" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Buscar del catálogo</button>
        <button onClick={() => setTab("acp")} className={`flex-1 rounded-lg px-3 py-1.5 text-body-sm font-semibold ${tab === "acp" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Generar con prompt (ACP)</button>
      </div>

      {tab === "catalogo" ? (
        <div className="flex flex-col gap-4">
          <div>
            <div className="mb-2 flex items-center justify-between"><p className="label !mb-0">Cláusulas maestras</p><span className="font-body-sm text-body-sm text-primary">{clausulasMaestrasIds.length} sel.</span></div>
            <input className="input mb-2" placeholder="Buscar cláusula…" value={qCl} onChange={(e) => setQCl(e.target.value)} />
            <div className="max-h-40 overflow-y-auto rounded-lg border border-outline-variant">
              {clausulas.data?.map((cl) => (
                <label key={cl.id} className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-surface-container-high">
                  <input type="checkbox" checked={clausulasMaestrasIds.includes(cl.id)} onChange={() => toggle(clausulasMaestrasIds, setClausulasMaestrasIds, cl.id)} />
                  <Badge tone="neutral">{cl.tipo}</Badge> <span className="flex-1">{cl.titulo}</span> <span className="font-data-mono text-data-mono text-outline">{cl.codigo}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between"><p className="label !mb-0">Precios maestros</p><span className="font-body-sm text-body-sm text-primary">{preciosMaestrosIds.length} sel.</span></div>
            <input className="input mb-2" placeholder="Buscar precio…" value={qPr} onChange={(e) => setQPr(e.target.value)} />
            <div className="max-h-40 overflow-y-auto rounded-lg border border-outline-variant">
              {precios.data?.map((pr) => (
                <label key={pr.id} className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-surface-container-high">
                  <input type="checkbox" checked={preciosMaestrosIds.includes(pr.id)} onChange={() => toggle(preciosMaestrosIds, setPreciosMaestrosIds, pr.id)} />
                  <span className="flex-1">{pr.producto}</span> <span className="font-data-mono text-data-mono text-primary">{formatMoney(pr.precio, pr.moneda)}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="border-t border-outline-variant pt-3">
            <div className="mb-2 flex items-center justify-between"><p className="label !mb-0">Cláusulas manuales</p>
              <button className="btn-secondary text-body-sm" onClick={() => setManuales([...manuales, { tipo: "GENERAL", titulo: "", contenido: "" }])}><Icon name="add" className="text-[16px]" /> Añadir</button></div>
            {manuales.map((m, i) => (
              <div key={i} className="mb-2 rounded-lg border border-outline-variant p-2">
                <div className="mb-2 flex gap-2">
                  <select className="input" value={m.tipo} onChange={(e) => setManuales(manuales.map((x, j) => j === i ? { ...x, tipo: e.target.value } : x))}>{TIPOS_CLAUSULA.map((t) => <option key={t}>{t}</option>)}</select>
                  <input className="input" placeholder="Título" value={m.titulo} onChange={(e) => setManuales(manuales.map((x, j) => j === i ? { ...x, titulo: e.target.value } : x))} />
                  <button className="btn-ghost px-2" onClick={() => setManuales(manuales.filter((_, j) => j !== i))}><Icon name="delete" /></button>
                </div>
                <textarea className="input min-h-[60px]" placeholder="Contenido" value={m.contenido} onChange={(e) => setManuales(manuales.map((x, j) => j === i ? { ...x, contenido: e.target.value } : x))} />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-2">
            <p className="font-body-sm text-body-sm text-secondary">Asistente de contratos (decide qué preguntar y cuándo generar). Las cláusulas/precios marcados en el tab catálogo se usan como base.</p>
            <select className="input max-w-[220px]" value={motor} onChange={(e) => setMotor(e.target.value)} title="Motor LLM">
              {MOTORES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
            </select>
          </div>

          <div className="flex max-h-80 flex-col gap-2 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-low p-3">
            {mensajes.map((m, i) => (
              <div key={i} className={`flex ${m.rol === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-3 py-2 font-body-sm text-body-sm ${m.rol === "user" ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface"}`}>{m.contenido}</div>
              </div>
            ))}
            {chat.isPending && <div className="flex justify-start"><div className="rounded-2xl bg-surface-container-high px-3 py-2"><Spinner /></div></div>}
          </div>

          <div className="flex items-end gap-2">
            <textarea
              className="input min-h-[48px] flex-1"
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }}
              placeholder="Ej: Contrato de suministro de soya con AgroSemillas, entrega mensual, pago a 30 días…"
            />
            <button className="btn-primary" disabled={!entrada.trim() || chat.isPending} onClick={enviar}>
              {chat.isPending ? <Spinner /> : <><Icon name="send" className="text-[18px]" /> Enviar</>}
            </button>
          </div>

          {generado && (
            <div className="rounded-lg border border-primary/40 bg-primary/5 p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon name="auto_awesome" className="text-[18px] text-primary" />
                  <p className="label !mb-0">Documento generado — {generado.titulo}</p>
                  {generado.motor && <Badge tone="info">{generado.motor}</Badge>}
                </div>
                <button className="btn-secondary text-body-sm" disabled={pdfLoading} onClick={verPdfGenerado}>
                  {pdfLoading ? <Spinner /> : <><Icon name="picture_as_pdf" className="text-[18px]" /> Ver PDF</>}
                </button>
              </div>
              {!!generado.warnings?.length && <div className="mb-2 flex flex-wrap gap-1">{generado.warnings.map((w, i) => <Badge key={i} tone="warn">{w}</Badge>)}</div>}
              {pdfUrl ? (
                <iframe title="PDF generado" src={pdfUrl} className="h-[460px] w-full rounded-lg border border-outline-variant bg-surface-container-lowest" />
              ) : (
                <div className="max-h-72 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-lowest p-4 font-body-sm text-body-sm whitespace-pre-wrap">{generado.markdown ?? generado.html ?? JSON.stringify(generado.secciones, null, 2)}</div>
              )}
              <p className="mt-2 font-body-sm text-body-sm text-secondary">Continúa al paso <b>Confirmar</b> para crear el contrato con estos datos.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
