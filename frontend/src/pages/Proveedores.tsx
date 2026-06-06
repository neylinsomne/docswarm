import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Badge, Drawer, EmptyState, Field, LoadingState, Modal, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import type { Caracteristica, Empresa } from "../lib/types";

export function Proveedores() {
  const toast = useToast();
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [sector, setSector] = useState("");
  const [nicho, setNicho] = useState("");
  const [caracKey, setCaracKey] = useState("");
  const [caracVal, setCaracVal] = useState("");
  const [creating, setCreating] = useState(false);
  const [detalleId, setDetalleId] = useState<number | null>(null);

  const useFacets = Boolean(caracKey && caracVal);
  const lista = useQuery({
    queryKey: ["empresas", { nombre, sector, nicho, caracKey, caracVal }],
    queryFn: () =>
      useFacets
        ? api.buscarEmpresasFacetado({ nombre, sector, nicho, caracteristicas: { [caracKey]: caracVal }, limit: 100 })
        : api.listarEmpresas({ nombre, sector, nicho, limit: 100 }),
  });

  return (
    <>
      <PageHeader
        title="Proveedores"
        subtitle="Directorio de empresas proveedoras con filtros por perfil."
        actions={<button className="btn-primary" onClick={() => setCreating(true)}><Icon name="add" className="text-[18px]" /> Crear proveedor</button>}
      />

      <div className="card mb-stack-relaxed p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-5">
          <Field label="Nombre"><input className="input" value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Buscar…" /></Field>
          <Field label="Sector"><input className="input" value={sector} onChange={(e) => setSector(e.target.value)} placeholder="agro, logística…" /></Field>
          <Field label="Nicho"><input className="input" value={nicho} onChange={(e) => setNicho(e.target.value)} /></Field>
          <Field label="Característica (clave)"><input className="input" value={caracKey} onChange={(e) => setCaracKey(e.target.value)} placeholder="certificacion" /></Field>
          <Field label="Característica (valor)"><input className="input" value={caracVal} onChange={(e) => setCaracVal(e.target.value)} placeholder="ISO9001" /></Field>
        </div>
        {useFacets && <p className="mt-2 font-body-sm text-body-sm text-primary">Búsqueda facetada activa: {caracKey}={caracVal}</p>}
      </div>

      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : lista.isError ? (
          <EmptyState icon="error" title="No se pudo cargar" hint={(lista.error as Error).message} />
        ) : !lista.data?.length ? (
          <EmptyState icon="business" title="Sin proveedores" hint="Ajusta los filtros o crea uno nuevo." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] border-collapse text-left">
              <thead><tr className="border-b border-outline-variant bg-surface-bright">
                <th className="th">Nombre</th><th className="th w-[140px]">NIT</th><th className="th">Sector / Nicho</th><th className="th">Ciudad</th><th className="th w-[100px]">Estado</th><th className="th w-[60px]"></th>
              </tr></thead>
              <tbody className="font-body-md text-body-md text-on-surface">
                {lista.data.map((e) => (
                  <tr key={e.id} onClick={() => setDetalleId(e.id)} className="h-[48px] cursor-pointer border-b border-outline-variant hover:bg-surface-container-highest">
                    <td className="td font-semibold">{e.nombre}</td>
                    <td className="td font-data-mono text-data-mono text-secondary">{e.nit ?? "—"}</td>
                    <td className="td">{e.sector ?? "—"}{e.nicho ? ` · ${e.nicho}` : ""}</td>
                    <td className="td">{e.ciudad ?? "—"}</td>
                    <td className="td"><Badge tone={e.activo === false ? "danger" : "ok"}>{e.activo === false ? "Inactivo" : "Activo"}</Badge></td>
                    <td className="td text-right"><Icon name="chevron_right" className="text-outline" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {creating && <CrearProveedorModal onClose={() => setCreating(false)} onCreated={() => { setCreating(false); qc.invalidateQueries({ queryKey: ["empresas"] }); toast.success("Proveedor creado."); }} />}
      {detalleId != null && <DetalleProveedor id={detalleId} onClose={() => setDetalleId(null)} />}
    </>
  );
}

function CrearProveedorModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const toast = useToast();
  const [form, setForm] = useState({ nombre: "", nit: "", sector: "", nicho: "", ciudad: "", pais: "CO" });
  const [metaRows, setMetaRows] = useState<{ k: string; v: string }[]>([{ k: "", v: "" }]);
  const [caracs, setCaracs] = useState<Caracteristica[]>([{ clave: "", valor: "" }]);

  const mut = useMutation({
    mutationFn: () => {
      const metadata: Record<string, unknown> = {};
      metaRows.forEach((r) => r.k && (metadata[r.k] = r.v));
      const caracteristicas = caracs.filter((c) => c.clave && c.valor);
      return api.crearEmpresa({ ...form, tipo: "PROVEEDOR", metadata, caracteristicas });
    },
    onSuccess: onCreated,
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error al crear."),
  });

  return (
    <Modal open onClose={onClose} title="Crear proveedor" size="lg"
      footer={<><button className="btn-ghost" onClick={onClose}>Cancelar</button><button className="btn-primary" disabled={!form.nombre || mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Crear"}</button></>}>
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Nombre" required><input className="input" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></Field>
          <Field label="NIT"><input className="input" value={form.nit} onChange={(e) => setForm({ ...form, nit: e.target.value })} /></Field>
          <Field label="Sector"><input className="input" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} /></Field>
          <Field label="Nicho"><input className="input" value={form.nicho} onChange={(e) => setForm({ ...form, nicho: e.target.value })} /></Field>
          <Field label="Ciudad"><input className="input" value={form.ciudad} onChange={(e) => setForm({ ...form, ciudad: e.target.value })} /></Field>
          <Field label="País"><input className="input" value={form.pais} onChange={(e) => setForm({ ...form, pais: e.target.value })} /></Field>
        </div>

        <KeyValueEditor title="Metadata (JSON libre)" rows={metaRows} setRows={setMetaRows} />

        <div>
          <p className="label">Características (clave → valor) — para filtrado facetado</p>
          {caracs.map((c, i) => (
            <div key={i} className="mb-2 flex gap-2">
              <input className="input" placeholder="clave (certificacion)" value={c.clave} onChange={(e) => setCaracs(caracs.map((x, j) => j === i ? { ...x, clave: e.target.value } : x))} />
              <input className="input" placeholder="valor (ISO9001)" value={c.valor} onChange={(e) => setCaracs(caracs.map((x, j) => j === i ? { ...x, valor: e.target.value } : x))} />
              <button className="btn-ghost px-2" onClick={() => setCaracs(caracs.filter((_, j) => j !== i))}><Icon name="delete" /></button>
            </div>
          ))}
          <button className="btn-secondary text-body-sm" onClick={() => setCaracs([...caracs, { clave: "", valor: "" }])}><Icon name="add" className="text-[16px]" /> Añadir</button>
        </div>
      </div>
    </Modal>
  );
}

function KeyValueEditor({ title, rows, setRows }: { title: string; rows: { k: string; v: string }[]; setRows: (r: { k: string; v: string }[]) => void }) {
  return (
    <div>
      <p className="label">{title}</p>
      {rows.map((r, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input className="input" placeholder="clave" value={r.k} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, k: e.target.value } : x))} />
          <input className="input" placeholder="valor" value={r.v} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, v: e.target.value } : x))} />
          <button className="btn-ghost px-2" onClick={() => setRows(rows.filter((_, j) => j !== i))}><Icon name="delete" /></button>
        </div>
      ))}
      <button className="btn-secondary text-body-sm" onClick={() => setRows([...rows, { k: "", v: "" }])}><Icon name="add" className="text-[16px]" /> Añadir</button>
    </div>
  );
}

function DetalleProveedor({ id, onClose }: { id: number; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [edit, setEdit] = useState(false);
  const [draft, setDraft] = useState<{ nombre?: string; sector?: string; nicho?: string; ciudad?: string; activo?: boolean }>({});
  const det = useQuery({ queryKey: ["empresa", id], queryFn: () => api.obtenerEmpresa(id) });

  const mut = useMutation({
    mutationFn: () => api.actualizarEmpresa(id, draft),
    onSuccess: () => { toast.success("Proveedor actualizado."); setEdit(false); qc.invalidateQueries({ queryKey: ["empresa", id] }); qc.invalidateQueries({ queryKey: ["empresas"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });

  const e = det.data;
  return (
    <Drawer open onClose={onClose} title={e?.nombre ?? "Proveedor"}
      footer={edit ? (
        <><button className="btn-ghost" onClick={() => setEdit(false)}>Cancelar</button><button className="btn-primary" disabled={mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Guardar"}</button></>
      ) : (
        <button className="btn-secondary" onClick={() => { setEdit(true); setDraft({ nombre: e?.nombre, sector: e?.sector ?? undefined, nicho: e?.nicho ?? undefined, ciudad: e?.ciudad ?? undefined, activo: e?.activo }); }}><Icon name="edit" className="text-[18px]" /> Editar</button>
      )}>
      {det.isLoading ? <LoadingState /> : !e ? <EmptyState icon="error" title="No encontrado" /> : edit ? (
        <div className="flex flex-col gap-3">
          <Field label="Nombre"><input className="input" value={draft.nombre ?? ""} onChange={(ev) => setDraft({ ...draft, nombre: ev.target.value })} /></Field>
          <Field label="Sector"><input className="input" value={draft.sector ?? ""} onChange={(ev) => setDraft({ ...draft, sector: ev.target.value })} /></Field>
          <Field label="Nicho"><input className="input" value={draft.nicho ?? ""} onChange={(ev) => setDraft({ ...draft, nicho: ev.target.value })} /></Field>
          <Field label="Ciudad"><input className="input" value={draft.ciudad ?? ""} onChange={(ev) => setDraft({ ...draft, ciudad: ev.target.value })} /></Field>
          <label className="flex items-center gap-2"><input type="checkbox" checked={draft.activo !== false} onChange={(ev) => setDraft({ ...draft, activo: ev.target.checked })} /> Activo</label>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-2 gap-3 text-body-md">
            <Info label="NIT" value={e.nit} mono /><Info label="Tipo" value={e.tipo ?? e.tipo_empresa} />
            <Info label="Sector" value={e.sector} /><Info label="Nicho" value={e.nicho} />
            <Info label="Ciudad" value={e.ciudad} /><Info label="País" value={e.pais} />
          </dl>
          {!!e.caracteristicas?.length && (
            <div>
              <p className="label">Características</p>
              <div className="flex flex-wrap gap-2">{e.caracteristicas.map((c, i) => <Badge key={i} tone="info">{c.clave}: {c.valor}</Badge>)}</div>
            </div>
          )}
          {e.metadata && Object.keys(e.metadata).length > 0 && (
            <div>
              <p className="label">Metadata</p>
              <pre className="overflow-x-auto rounded-lg bg-surface-container p-3 font-data-mono text-data-mono text-on-surface">{JSON.stringify(e.metadata, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}

function Info({ label, value, mono }: { label: string; value?: unknown; mono?: boolean }) {
  return (
    <div>
      <dt className="font-label-caps text-label-caps uppercase text-secondary">{label}</dt>
      <dd className={`text-on-surface ${mono ? "font-data-mono text-data-mono" : "font-body-md text-body-md"}`}>{value != null && value !== "" ? String(value) : "—"}</dd>
    </div>
  );
}
