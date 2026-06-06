import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, Drawer, EmptyState, Field, LoadingState, Modal, ProgressBar, Spinner } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { estadoPropagacionTone, formatDate, formatDateTime } from "../lib/format";

export function Cambios() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [registrar, setRegistrar] = useState(false);
  const detalleId = params.get("id") ? Number(params.get("id")) : null;
  const setDetalleId = (id: number | null) => { if (id) setParams({ id: String(id) }); else setParams({}); };

  const lista = useQuery({ queryKey: ["cambios"], queryFn: () => api.listarCambios({ limit: 100 }) });

  return (
    <>
      <PageHeader
        title="Cambios"
        subtitle={isAdmin ? "Log de cambios de cláusulas/precios y documentos afectados." : "Actualizaciones que afectan a tus contratos."}
        actions={isAdmin && <button className="btn-primary" onClick={() => setRegistrar(true)}><Icon name="add" className="text-[18px]" /> Registrar cambio</button>}
      />

      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : !lista.data?.length ? (
          <EmptyState icon="sync_alt" title="Sin cambios" hint={isAdmin ? "Registra un cambio de cláusula o precio." : "No hay actualizaciones para ti."} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] border-collapse text-left">
              <thead><tr className="border-b border-outline-variant bg-surface-bright">
                <th className="th w-[120px]">Fecha</th><th className="th">Objeto</th><th className="th w-[110px]">Tipo</th><th className="th w-[220px]">Firmados / Afectados</th><th className="th w-[110px]">Pendientes</th><th className="th w-[50px]"></th>
              </tr></thead>
              <tbody className="font-body-md text-body-md text-on-surface">
                {lista.data.map((c) => (
                  <tr key={c.id} onClick={() => setDetalleId(c.id)} className="h-[48px] cursor-pointer border-b border-outline-variant hover:bg-surface-container-highest">
                    <td className="td font-data-mono text-data-mono text-secondary">{formatDate(c.creado_en)}</td>
                    <td className="td"><span className="font-semibold">{c.objeto_titulo ?? `Cambio #${c.id}`}</span>{c.objeto_codigo && <span className="ml-2 font-data-mono text-data-mono text-outline">{c.objeto_codigo}</span>}</td>
                    <td className="td"><Badge tone={c.tipo_objeto === "PRECIO" ? "info" : "neutral"}>{c.tipo_objeto}</Badge></td>
                    <td className="td"><ProgressBar value={c.docs_firmados ?? 0} total={c.docs_afectados ?? 0} /></td>
                    <td className="td"><Badge tone={(c.docs_pendientes ?? 0) > 0 ? "warn" : "ok"}>{c.docs_pendientes ?? 0}</Badge></td>
                    <td className="td text-right"><Icon name="chevron_right" className="text-outline" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {registrar && <RegistrarCambio onClose={() => setRegistrar(false)} onDone={(r) => { setRegistrar(false); qc.invalidateQueries({ queryKey: ["cambios"] }); toast.success(`${r.docs_afectados} contratos afectados · ${r.notificaciones} notificaciones.`); }} />}
      {detalleId != null && <DetalleAfectados cambioId={detalleId} onClose={() => setDetalleId(null)} />}
    </>
  );
}

function RegistrarCambio({ onClose, onDone }: { onClose: () => void; onDone: (r: { docs_afectados: number; notificaciones: number }) => void }) {
  const toast = useToast();
  const [tab, setTab] = useState<"clausula" | "precio">("clausula");
  const [qCl, setQCl] = useState(""); const [qPr, setQPr] = useState("");
  const [clausulaId, setClausulaId] = useState<number | null>(null);
  const [precioId, setPrecioId] = useState<number | null>(null);
  const [nuevoContenido, setNuevoContenido] = useState("");
  const [nuevoPrecio, setNuevoPrecio] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const clausulas = useQuery({ queryKey: ["cat-clausulas", qCl], queryFn: () => api.catalogoClausulas({ q: qCl, limit: 30 }) });
  const precios = useQuery({ queryKey: ["cat-precios", qPr], queryFn: () => api.catalogoPrecios({ q: qPr, limit: 30 }) });

  const mut = useMutation({
    mutationFn: () => tab === "clausula"
      ? api.cambiarClausula({ clausula_maestra_id: clausulaId!, nuevo_contenido: nuevoContenido, descripcion: descripcion || undefined })
      : api.cambiarPrecio({ precio_maestro_id: precioId!, nuevo_precio: Number(nuevoPrecio), descripcion: descripcion || undefined }),
    onSuccess: (r) => onDone(r),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error al registrar cambio."),
  });

  const valid = tab === "clausula" ? clausulaId && nuevoContenido : precioId && nuevoPrecio;

  return (
    <Modal open onClose={onClose} title="Registrar cambio maestro" size="lg"
      footer={<><button className="btn-ghost" onClick={onClose}>Cancelar</button><button className="btn-primary" disabled={!valid || mut.isPending} onClick={() => mut.mutate()}>{mut.isPending ? <Spinner /> : "Registrar y notificar"}</button></>}>
      <div className="mb-4 flex gap-1 rounded-lg bg-surface-container p-1">
        <button onClick={() => setTab("clausula")} className={`flex-1 rounded-lg px-3 py-1.5 text-body-sm font-semibold ${tab === "clausula" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Cláusula</button>
        <button onClick={() => setTab("precio")} className={`flex-1 rounded-lg px-3 py-1.5 text-body-sm font-semibold ${tab === "precio" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>Precio</button>
      </div>
      {tab === "clausula" ? (
        <div className="flex flex-col gap-3">
          <Field label="Cláusula maestra" required>
            <input className="input mb-2" placeholder="Buscar…" value={qCl} onChange={(e) => setQCl(e.target.value)} />
            <div className="max-h-40 overflow-y-auto rounded-lg border border-outline-variant">
              {clausulas.data?.map((cl) => (
                <button key={cl.id} onClick={() => setClausulaId(cl.id)} className={`block w-full px-3 py-2 text-left hover:bg-surface-container-high ${clausulaId === cl.id ? "bg-primary-container/20" : ""}`}>
                  {clausulaId === cl.id && <Icon name="check" className="mr-1 text-[16px] text-primary" />}<Badge tone="neutral">{cl.tipo}</Badge> {cl.titulo} <span className="font-data-mono text-data-mono text-outline">{cl.codigo}</span>
                </button>
              ))}
            </div>
          </Field>
          <Field label="Nuevo contenido" required><textarea className="input min-h-[100px]" value={nuevoContenido} onChange={(e) => setNuevoContenido(e.target.value)} /></Field>
          <Field label="Descripción del cambio"><input className="input" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} /></Field>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <Field label="Precio maestro" required>
            <input className="input mb-2" placeholder="Buscar…" value={qPr} onChange={(e) => setQPr(e.target.value)} />
            <div className="max-h-40 overflow-y-auto rounded-lg border border-outline-variant">
              {precios.data?.map((pr) => (
                <button key={pr.id} onClick={() => setPrecioId(pr.id)} className={`block w-full px-3 py-2 text-left hover:bg-surface-container-high ${precioId === pr.id ? "bg-primary-container/20" : ""}`}>
                  {precioId === pr.id && <Icon name="check" className="mr-1 text-[16px] text-primary" />}{pr.producto} <span className="font-data-mono text-data-mono text-outline">{pr.codigo}</span>
                </button>
              ))}
            </div>
          </Field>
          <Field label="Nuevo precio" required><input className="input" type="number" value={nuevoPrecio} onChange={(e) => setNuevoPrecio(e.target.value)} /></Field>
          <Field label="Descripción del cambio"><input className="input" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} /></Field>
        </div>
      )}
    </Modal>
  );
}

function DetalleAfectados({ cambioId, onClose }: { cambioId: number; onClose: () => void }) {
  const { isProveedor } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const afectados = useQuery({ queryKey: ["afectados", cambioId], queryFn: () => api.detalleAfectados(cambioId) });

  const firmar = useMutation({
    mutationFn: (afectadoId: number) => api.firmaAfectadoInPage(afectadoId),
    onSuccess: () => { toast.success("Actualización firmada."); qc.invalidateQueries({ queryKey: ["afectados", cambioId] }); qc.invalidateQueries({ queryKey: ["cambios"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "No se pudo firmar."),
  });

  return (
    <Drawer open onClose={onClose} title={`Cambio #${cambioId} · documentos afectados`}>
      {afectados.isLoading ? <LoadingState /> : !afectados.data?.length ? <EmptyState icon="inbox" title="Sin documentos afectados" /> : (
        <ul className="flex flex-col gap-3">
          {afectados.data.map((a) => {
            const aid = a.afectado_id ?? a.id;
            return (
              <li key={aid} className="card p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div>
                    <p className="font-title-sm text-title-sm text-on-surface">{a.contrato_titulo ?? `Contrato #${a.contrato_id}`}</p>
                    <p className="font-body-sm text-body-sm text-secondary">{a.proveedor_nombre ?? ""} {a.contrato_numero ? `· ${a.contrato_numero}` : ""}</p>
                  </div>
                  <Badge tone={estadoPropagacionTone(a.estado_propagacion)}>{a.estado_propagacion}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-body-sm">
                  <Badge tone={a.firmado_proveedor ? "ok" : "warn"}>{a.firmado_proveedor ? "Firmado" : "Sin firmar"}</Badge>
                  {a.fecha_firma && <span className="font-data-mono text-data-mono text-secondary">{formatDateTime(a.fecha_firma)}</span>}
                  {a.notificado_at && <span className="text-outline">Notificado {formatDate(a.notificado_at)}</span>}
                </div>
                {isProveedor && !a.firmado_proveedor && (
                  <button className="btn-primary mt-3 text-body-sm" disabled={firmar.isPending} onClick={() => firmar.mutate(aid)}>
                    {firmar.isPending ? <Spinner /> : <><Icon name="draw" className="text-[16px]" /> Firmar actualización</>}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Drawer>
  );
}
