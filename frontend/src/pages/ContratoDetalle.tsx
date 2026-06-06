import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, Field, LoadingState, Modal, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { estadoContratoTone, formatDate, formatMoney, tipoClausulaTone } from "../lib/format";
import { TIPOS_CLAUSULA, type Clausula } from "../lib/types";

export function ContratoDetalle() {
  const { id } = useParams();
  const cid = Number(id);
  const { isAdmin, isProveedor } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [addClausula, setAddClausula] = useState(false);

  const det = useQuery({ queryKey: ["contrato", cid], queryFn: () => api.obtenerContrato(cid), enabled: !!cid });
  const c = det.data;

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const verPdf = async () => {
    setPdfLoading(true);
    try {
      const url = await api.contratoPdfUrl(cid);
      setPdfUrl(url);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "No se pudo generar el PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  const firmar = useMutation({
    mutationFn: () => api.firmaContratoInPage(cid),
    onSuccess: () => { toast.success("Contrato firmado."); qc.invalidateQueries({ queryKey: ["contrato", cid] }); qc.invalidateQueries({ queryKey: ["contratos"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "No se pudo firmar."),
  });

  const delClausula = useMutation({
    mutationFn: (clid: number) => api.eliminarClausula(clid),
    onSuccess: () => { toast.success("Cláusula eliminada."); qc.invalidateQueries({ queryKey: ["contrato", cid] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });

  if (det.isLoading) return <LoadingState />;
  if (!c) return <EmptyState icon="error" title="Contrato no encontrado" />;

  return (
    <>
      <button onClick={() => navigate(-1)} className="mb-3 flex items-center gap-1 font-body-sm text-body-sm text-primary hover:text-surface-tint"><Icon name="arrow_back" className="text-[18px]" /> Volver</button>
      <PageHeader
        title={c.titulo}
        subtitle={`${c.numero ?? `#${c.id}`} · ${c.proveedor_nombre ?? "Proveedor"}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={estadoContratoTone(c.estado)}>{c.estado}</Badge>
            <button className="btn-secondary text-body-sm" disabled={pdfLoading} onClick={verPdf}>
              {pdfLoading ? <Spinner /> : <><Icon name="picture_as_pdf" className="text-[18px]" /> Ver PDF</>}
            </button>
            {isProveedor && !c.firmado_proveedor && (
              <button className="btn-primary" disabled={firmar.isPending} onClick={() => firmar.mutate()}>{firmar.isPending ? <Spinner /> : <><Icon name="draw" className="text-[18px]" /> Firmar contrato</>}</button>
            )}
            {c.firmado_proveedor && <Badge tone="ok">Firmado {formatDate(c.fecha_firma)}</Badge>}
          </div>
        }
      />

      <div className="mb-stack-relaxed grid grid-cols-2 gap-3 md:grid-cols-4">
        <Cell label="Valor" value={formatMoney(c.valor, c.moneda)} mono />
        <Cell label="Objeto" value={c.objeto} />
        <Cell label="Inicio" value={formatDate(c.fecha_inicio)} mono />
        <Cell label="Fin" value={formatDate(c.fecha_fin)} mono />
      </div>

      {pdfUrl && (
        <div className="card mb-stack-relaxed overflow-hidden">
          <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-low p-3">
            <h3 className="font-title-sm text-title-sm text-on-surface flex items-center gap-2"><Icon name="picture_as_pdf" className="text-[18px] text-primary" /> Documento PDF</h3>
            <div className="flex items-center gap-2">
              <a className="btn-ghost text-body-sm" href={pdfUrl} download={`${c.numero ?? `contrato-${c.id}`}.pdf`}><Icon name="download" className="text-[16px]" /> Descargar</a>
              <a className="btn-ghost text-body-sm" href={pdfUrl} target="_blank" rel="noreferrer"><Icon name="open_in_new" className="text-[16px]" /> Abrir</a>
              <button className="btn-ghost px-2" onClick={() => setPdfUrl(null)}><Icon name="close" /></button>
            </div>
          </div>
          <iframe title="PDF del contrato" src={pdfUrl} className="h-[560px] w-full bg-surface-container-low" />
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-low p-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">Cláusulas ({c.clausulas?.length ?? 0})</h3>
          {isAdmin && <button className="btn-secondary text-body-sm" onClick={() => setAddClausula(true)}><Icon name="add" className="text-[16px]" /> Agregar cláusula</button>}
        </div>
        {!c.clausulas?.length ? (
          <EmptyState icon="gavel" title="Sin cláusulas" />
        ) : (
          <ul className="divide-y divide-outline-variant">
            {[...c.clausulas].sort((a, b) => (a.orden ?? 0) - (b.orden ?? 0)).map((cl) => (
              <li key={cl.id} className="px-5 py-4">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-data-mono text-data-mono text-outline">#{cl.orden ?? 0}</span>
                    <Badge tone={tipoClausulaTone(cl.tipo)}>{cl.tipo}</Badge>
                    <span className="font-title-sm text-title-sm text-on-surface">{cl.titulo ?? "Cláusula"}</span>
                    {cl.clausula_maestra_id && <span title="Vinculada a catálogo maestro"><Icon name="link" className="text-[16px] text-primary" /></span>}
                  </div>
                  {isAdmin && (
                    <button className="text-outline hover:text-error" onClick={() => confirm("¿Eliminar cláusula?") && delClausula.mutate(cl.id)}><Icon name="delete" className="text-[18px]" /></button>
                  )}
                </div>
                <p className="whitespace-pre-wrap font-body-md text-body-md text-on-surface-variant">{cl.contenido}</p>
                {cl.valor != null && <p className="mt-1 font-data-mono text-data-mono text-primary">{formatMoney(cl.valor, c.moneda)}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {addClausula && <AddClausulaModal contratoId={cid} onClose={() => setAddClausula(false)} onDone={() => { setAddClausula(false); qc.invalidateQueries({ queryKey: ["contrato", cid] }); toast.success("Cláusula agregada."); }} />}
    </>
  );
}

function Cell({ label, value, mono }: { label: string; value?: unknown; mono?: boolean }) {
  return (
    <div className="card p-3">
      <p className="font-label-caps text-label-caps uppercase text-secondary">{label}</p>
      <p className={`text-on-surface ${mono ? "font-data-mono text-data-mono" : "font-body-md text-body-md"}`}>{value != null && value !== "" ? String(value) : "—"}</p>
    </div>
  );
}

function AddClausulaModal({ contratoId, onClose, onDone }: { contratoId: number; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [form, setForm] = useState<Partial<Clausula>>({ tipo: "GENERAL", titulo: "", contenido: "", orden: 0 });
  const mut = useMutation({
    mutationFn: () => api.agregarClausula(contratoId, { tipo: form.tipo as string, contenido: form.contenido as string, titulo: form.titulo ?? undefined, orden: form.orden ?? 0, valor: form.valor ?? undefined }),
    onSuccess: onDone,
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });
  return (
    <Modal open onClose={onClose} title="Agregar cláusula"
      footer={<><button className="btn-ghost" onClick={onClose}>Cancelar</button><button className="btn-primary" disabled={!form.contenido || mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Agregar"}</button></>}>
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tipo"><select className="input" value={form.tipo as string} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{TIPOS_CLAUSULA.map((t) => <option key={t}>{t}</option>)}</select></Field>
          <Field label="Orden"><input className="input" type="number" value={form.orden ?? 0} onChange={(e) => setForm({ ...form, orden: Number(e.target.value) })} /></Field>
        </div>
        <Field label="Título"><input className="input" value={form.titulo ?? ""} onChange={(e) => setForm({ ...form, titulo: e.target.value })} /></Field>
        <Field label="Contenido" required><textarea className="input min-h-[120px]" value={form.contenido ?? ""} onChange={(e) => setForm({ ...form, contenido: e.target.value })} /></Field>
        <Field label="Valor (opcional)"><input className="input" type="number" value={form.valor ?? ""} onChange={(e) => setForm({ ...form, valor: e.target.value ? Number(e.target.value) : undefined })} /></Field>
      </div>
    </Modal>
  );
}
