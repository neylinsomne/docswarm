import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, Field, LoadingState, Modal, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { formatMoney, tipoClausulaTone } from "../lib/format";
import { TIPOS_CLAUSULA } from "../lib/types";

export function Catalogo() {
  const [tab, setTab] = useState<"clausulas" | "precios">("clausulas");
  return (
    <>
      <PageHeader title="Catálogo maestro" subtitle="Cláusulas y precios maestros versionados de Bayern." />
      <div className="mb-stack-relaxed flex gap-1 rounded-lg bg-surface-container p-1 w-fit">
        <button onClick={() => setTab("clausulas")} className={`rounded-lg px-4 py-1.5 text-body-sm font-semibold ${tab === "clausulas" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Cláusulas</button>
        <button onClick={() => setTab("precios")} className={`rounded-lg px-4 py-1.5 text-body-sm font-semibold ${tab === "precios" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Precios</button>
      </div>
      {tab === "clausulas" ? <TablaClausulas /> : <TablaPrecios />}
    </>
  );
}

function TablaClausulas() {
  const toast = useToast(); const qc = useQueryClient();
  const [q, setQ] = useState(""); const [tipo, setTipo] = useState(""); const [creating, setCreating] = useState(false);
  const lista = useQuery({ queryKey: ["cat-clausulas", q, tipo], queryFn: () => api.catalogoClausulas({ q, tipo: tipo || undefined, limit: 100 }) });

  const [form, setForm] = useState({ codigo: "", tipo: "GENERAL", titulo: "", contenido_actual: "", sector: "", nicho: "" });
  const mut = useMutation({
    mutationFn: () => api.crearClausulaMaestra(form),
    onSuccess: () => { toast.success("Cláusula maestra creada."); setCreating(false); qc.invalidateQueries({ queryKey: ["cat-clausulas"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });

  return (
    <>
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]"><Field label="Buscar"><input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="texto…" /></Field></div>
        <Field label="Tipo"><select className="input" value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="">Todos</option>{TIPOS_CLAUSULA.map((t) => <option key={t}>{t}</option>)}</select></Field>
        <button className="btn-primary" onClick={() => setCreating(true)}><Icon name="add" className="text-[18px]" /> Crear</button>
      </div>
      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : !lista.data?.length ? <EmptyState icon="inventory_2" title="Sin cláusulas" /> : (
          <table className="w-full border-collapse text-left">
            <thead><tr className="border-b border-outline-variant bg-surface-bright"><th className="th w-[120px]">Código</th><th className="th w-[120px]">Tipo</th><th className="th">Título</th><th className="th w-[100px]">Versión</th><th className="th w-[100px]">Vigente</th></tr></thead>
            <tbody className="font-body-md text-body-md">
              {lista.data.map((c) => (
                <tr key={c.id} className="h-[48px] border-b border-outline-variant hover:bg-surface-container-highest">
                  <td className="td font-data-mono text-data-mono text-secondary">{c.codigo}</td>
                  <td className="td"><Badge tone={tipoClausulaTone(c.tipo)}>{c.tipo}</Badge></td>
                  <td className="td font-semibold">{c.titulo}</td>
                  <td className="td font-data-mono text-data-mono">v{c.version ?? 1}</td>
                  <td className="td"><Badge tone={c.vigente === false ? "danger" : "ok"}>{c.vigente === false ? "No" : "Sí"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {creating && (
        <Modal open onClose={() => setCreating(false)} title="Crear cláusula maestra" size="lg"
          footer={<><button className="btn-ghost" onClick={() => setCreating(false)}>Cancelar</button><button className="btn-primary" disabled={!form.codigo || !form.titulo || !form.contenido_actual || mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Crear"}</button></>}>
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Código" required><input className="input" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></Field>
              <Field label="Tipo" required><select className="input" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>{TIPOS_CLAUSULA.map((t) => <option key={t}>{t}</option>)}</select></Field>
              <Field label="Sector"><input className="input" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} /></Field>
              <Field label="Nicho"><input className="input" value={form.nicho} onChange={(e) => setForm({ ...form, nicho: e.target.value })} /></Field>
            </div>
            <Field label="Título" required><input className="input" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} /></Field>
            <Field label="Contenido actual" required><textarea className="input min-h-[120px]" value={form.contenido_actual} onChange={(e) => setForm({ ...form, contenido_actual: e.target.value })} /></Field>
          </div>
        </Modal>
      )}
    </>
  );
}

function TablaPrecios() {
  const toast = useToast(); const qc = useQueryClient();
  const [q, setQ] = useState(""); const [categoria, setCategoria] = useState(""); const [creating, setCreating] = useState(false);
  const lista = useQuery({ queryKey: ["cat-precios", q, categoria], queryFn: () => api.catalogoPrecios({ q, categoria: categoria || undefined, limit: 100 }) });

  const [form, setForm] = useState({ codigo: "", producto: "", precio: "", categoria: "", moneda: "COP", unidad: "", sector: "", nicho: "" });
  const mut = useMutation({
    mutationFn: () => api.crearPrecioMaestro({ ...form, precio: Number(form.precio) }),
    onSuccess: () => { toast.success("Precio maestro creado."); setCreating(false); qc.invalidateQueries({ queryKey: ["cat-precios"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });

  return (
    <>
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]"><Field label="Buscar"><input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="producto…" /></Field></div>
        <Field label="Categoría"><input className="input" value={categoria} onChange={(e) => setCategoria(e.target.value)} /></Field>
        <button className="btn-primary" onClick={() => setCreating(true)}><Icon name="add" className="text-[18px]" /> Crear</button>
      </div>
      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : !lista.data?.length ? <EmptyState icon="payments" title="Sin precios" /> : (
          <table className="w-full border-collapse text-left">
            <thead><tr className="border-b border-outline-variant bg-surface-bright"><th className="th w-[120px]">Código</th><th className="th">Producto</th><th className="th">Categoría</th><th className="th w-[160px]">Precio</th><th className="th w-[90px]">Versión</th><th className="th w-[90px]">Vigente</th></tr></thead>
            <tbody className="font-body-md text-body-md">
              {lista.data.map((p) => (
                <tr key={p.id} className="h-[48px] border-b border-outline-variant hover:bg-surface-container-highest">
                  <td className="td font-data-mono text-data-mono text-secondary">{p.codigo}</td>
                  <td className="td font-semibold">{p.producto}</td>
                  <td className="td">{p.categoria ?? "—"}{p.unidad ? ` / ${p.unidad}` : ""}</td>
                  <td className="td font-data-mono text-data-mono text-primary">{formatMoney(p.precio, p.moneda)}</td>
                  <td className="td font-data-mono text-data-mono">v{p.version ?? 1}</td>
                  <td className="td"><Badge tone={p.vigente === false ? "danger" : "ok"}>{p.vigente === false ? "No" : "Sí"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {creating && (
        <Modal open onClose={() => setCreating(false)} title="Crear precio maestro" size="lg"
          footer={<><button className="btn-ghost" onClick={() => setCreating(false)}>Cancelar</button><button className="btn-primary" disabled={!form.codigo || !form.producto || !form.precio || mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Crear"}</button></>}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Código" required><input className="input" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></Field>
            <Field label="Producto" required><input className="input" value={form.producto} onChange={(e) => setForm({ ...form, producto: e.target.value })} /></Field>
            <Field label="Precio" required><input className="input" type="number" value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} /></Field>
            <Field label="Moneda"><input className="input" value={form.moneda} onChange={(e) => setForm({ ...form, moneda: e.target.value })} /></Field>
            <Field label="Categoría"><input className="input" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} /></Field>
            <Field label="Unidad"><input className="input" value={form.unidad} onChange={(e) => setForm({ ...form, unidad: e.target.value })} /></Field>
            <Field label="Sector"><input className="input" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} /></Field>
            <Field label="Nicho"><input className="input" value={form.nicho} onChange={(e) => setForm({ ...form, nicho: e.target.value })} /></Field>
          </div>
        </Modal>
      )}
    </>
  );
}
