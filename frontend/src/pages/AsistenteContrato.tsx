import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Badge, Field, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import type { ChatMensaje, GenerarContratoResponse } from "../lib/types";

const MOTORES = [
  { id: "auto", label: "Auto (Gemini→Ollama→stub)" },
  { id: "gemini", label: "Gemini" },
  { id: "ollama", label: "Ollama (local)" },
  { id: "stub", label: "Offline (stub)" },
];

// Página dedicada del chatbot ACP (URL directa: /contratos/asistente).
export function AsistenteContrato() {
  const navigate = useNavigate();
  const toast = useToast();

  const [provQuery, setProvQuery] = useState("");
  const [provNombre, setProvNombre] = useState("");
  const [provId, setProvId] = useState<number | undefined>();
  const [motor, setMotor] = useState("auto");
  const [mensajes, setMensajes] = useState<ChatMensaje[]>([
    { rol: "assistant", contenido: "Hola 👋 Soy el asistente de contratos de Bayern. Dime qué contrato quieres crear (proveedor, objeto, precio, entrega, calidad) y te iré preguntando lo que falte. Cuando tenga lo necesario, genero el documento en PDF." },
  ]);
  const [entrada, setEntrada] = useState("");
  const [generado, setGenerado] = useState<GenerarContratoResponse | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const proveedores = useQuery({ queryKey: ["empresas", "asistente", provQuery], queryFn: () => api.listarEmpresas({ nombre: provQuery, limit: 20 }) });

  const chat = useMutation({
    mutationFn: (msgs: ChatMensaje[]) => api.chatContrato({ mensajes: msgs, empresa_proveedor_id: provId, titulo: "Contrato", proveedor_llm: motor }),
    onSuccess: (r) => {
      setMensajes((m) => [...m, { rol: "assistant", contenido: r.respuesta }]);
      if (r.accion === "generar" && r.documento) { setGenerado(r.documento); setPdfUrl(null); toast.success(`Documento generado${r.motor ? ` (${r.motor})` : ""}.`); }
    },
    onError: (e) => setMensajes((m) => [...m, { rol: "assistant", contenido: `⚠️ ${e instanceof ApiError ? e.message : "Error en el chat."}` }]),
  });

  const enviar = () => {
    const t = entrada.trim();
    if (!t || chat.isPending) return;
    const next = [...mensajes, { rol: "user", contenido: t }];
    setMensajes(next); setEntrada(""); chat.mutate(next);
  };

  const verPdf = async () => {
    if (!generado) return;
    setPdfLoading(true);
    try { setPdfUrl(await api.documentoPdfUrl({ titulo: generado.titulo, markdown: generado.markdown ?? generado.html ?? "", proveedor: provNombre })); }
    catch (e) { toast.error(e instanceof ApiError ? e.message : "No se pudo generar el PDF."); }
    finally { setPdfLoading(false); }
  };

  return (
    <div className="mx-auto max-w-[900px]">
      <PageHeader title="Asistente IA de contratos" subtitle="Chatea para redactar un contrato; el swarm de agentes (con fallback a Gemini) genera el documento en PDF." actions={
        <button className="btn-secondary" onClick={() => navigate("/contratos/nuevo")}><Icon name="tune" className="text-[18px]" /> Asistente con pasos</button>
      } />

      <div className="card mb-stack-relaxed flex flex-wrap items-end gap-3 p-4">
        <Field label="Proveedor (opcional, da contexto)">
          <input className="input" placeholder="Buscar proveedor…" value={provNombre || provQuery} onChange={(e) => { setProvQuery(e.target.value); setProvNombre(""); setProvId(undefined); }} />
          {!provId && provQuery && (
            <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-outline-variant">
              {proveedores.data?.map((p) => (
                <button key={p.id} className="block w-full px-3 py-2 text-left hover:bg-surface-container-high" onClick={() => { setProvId(p.id); setProvNombre(p.nombre); setProvQuery(""); }}>{p.nombre} <span className="font-data-mono text-data-mono text-outline">#{p.id}</span></button>
              ))}
            </div>
          )}
        </Field>
        <Field label="Motor LLM">
          <select className="input max-w-[240px]" value={motor} onChange={(e) => setMotor(e.target.value)}>{MOTORES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}</select>
        </Field>
      </div>

      <div className="card overflow-hidden">
        <div className="flex max-h-[420px] flex-col gap-2 overflow-y-auto p-4">
          {mensajes.map((m, i) => (
            <div key={i} className={`flex ${m.rol === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 font-body-md text-body-md ${m.rol === "user" ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface"}`}>{m.contenido}</div>
            </div>
          ))}
          {chat.isPending && <div className="flex justify-start"><div className="rounded-2xl bg-surface-container-high px-4 py-2"><Spinner /></div></div>}
        </div>
        <div className="flex items-end gap-2 border-t border-outline-variant bg-surface-container-low p-3">
          <textarea className="input min-h-[48px] flex-1" value={entrada} onChange={(e) => setEntrada(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }} placeholder="Ej: Contrato de suministro de soya con AgroSemillas, entrega mensual, pago a 30 días, calidad humedad ≤12%…" />
          <button className="btn-primary" disabled={!entrada.trim() || chat.isPending} onClick={enviar}>{chat.isPending ? <Spinner /> : <><Icon name="send" className="text-[18px]" /> Enviar</>}</button>
        </div>
      </div>

      {generado && (
        <div className="card mt-stack-relaxed p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2"><Icon name="auto_awesome" className="text-[18px] text-primary" /><h3 className="font-title-sm text-title-sm">Documento generado — {generado.titulo}</h3>{generado.motor && <Badge tone="info">{generado.motor}</Badge>}</div>
            <button className="btn-secondary text-body-sm" disabled={pdfLoading} onClick={verPdf}>{pdfLoading ? <Spinner /> : <><Icon name="picture_as_pdf" className="text-[18px]" /> Ver PDF</>}</button>
          </div>
          {pdfUrl ? (
            <iframe title="PDF generado" src={pdfUrl} className="h-[520px] w-full rounded-lg border border-outline-variant bg-surface-container-lowest" />
          ) : (
            <div className="max-h-80 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-lowest p-4 font-body-sm text-body-sm whitespace-pre-wrap">{generado.markdown ?? generado.html ?? JSON.stringify(generado.secciones, null, 2)}</div>
          )}
        </div>
      )}
    </div>
  );
}
