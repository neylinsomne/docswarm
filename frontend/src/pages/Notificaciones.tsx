import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, LoadingState } from "../components/ui";
import { Icon } from "../components/Icon";
import { useToast } from "../components/Toast";
import { canalIcon, estadoNotifTone, formatDateTime } from "../lib/format";

export function Notificaciones() {
  const toast = useToast();
  const qc = useQueryClient();
  const [soloNoLeidas, setSoloNoLeidas] = useState(false);
  const [canal, setCanal] = useState("");

  const lista = useQuery({
    queryKey: ["notificaciones", { soloNoLeidas, canal }],
    queryFn: () => api.listarNotificaciones({ no_leidas: soloNoLeidas || undefined, canal: canal || undefined, limit: 100 }),
  });

  const marcar = useMutation({
    mutationFn: (id: number) => api.marcarLeida(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notificaciones"] }); qc.invalidateQueries({ queryKey: ["notif-conteo"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Error."),
  });

  return (
    <>
      <PageHeader title="Notificaciones" subtitle="Avisos por WhatsApp, Gmail y sistema (solo lectura del envío)." />
      <div className="card mb-stack-relaxed flex flex-wrap items-center gap-3 p-3">
        <label className="flex items-center gap-2 font-body-sm text-body-sm"><input type="checkbox" checked={soloNoLeidas} onChange={(e) => setSoloNoLeidas(e.target.checked)} /> Solo no leídas</label>
        <div className="flex gap-1">
          {["", "SISTEMA", "WHATSAPP", "GMAIL"].map((c) => (
            <button key={c} onClick={() => setCanal(c)} className={`rounded-full px-3 py-1 text-body-sm ${canal === c ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant"}`}>{c || "Todos"}</button>
          ))}
        </div>
      </div>

      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : !lista.data?.length ? <EmptyState icon="notifications_off" title="Sin notificaciones" /> : (
          <ul className="divide-y divide-outline-variant">
            {lista.data.map((n) => (
              <li key={n.id} className={`flex items-start gap-3 px-5 py-4 ${n.leida ? "" : "bg-surface-container-low"}`}>
                <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-high text-secondary"><Icon name={canalIcon(n.canal)} className="text-[20px]" /></div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-title-sm text-title-sm text-on-surface">{n.asunto ?? "(sin asunto)"}</p>
                    {!n.leida && <span className="h-2 w-2 rounded-full bg-primary" />}
                  </div>
                  {n.mensaje && <p className="font-body-sm text-body-sm text-on-surface-variant">{n.mensaje}</p>}
                  <div className="mt-1 flex flex-wrap items-center gap-2 font-body-sm text-body-sm text-secondary">
                    <Badge tone="neutral">{n.canal}</Badge>
                    <Badge tone={estadoNotifTone(n.estado)}>{n.estado}</Badge>
                    {n.destino && <span className="font-data-mono text-data-mono">{n.destino}</span>}
                    <span className="text-outline">· {formatDateTime(n.creado_en ?? n.enviado_at)}</span>
                  </div>
                  {(n.enviado_at || n.entregado_at || n.leida_at) && (
                    <div className="mt-2 flex items-center gap-3 font-body-sm text-body-sm text-outline">
                      {n.enviado_at && <span><Icon name="send" className="text-[14px]" /> {formatDateTime(n.enviado_at)}</span>}
                      {n.entregado_at && <span><Icon name="done_all" className="text-[14px]" /> {formatDateTime(n.entregado_at)}</span>}
                      {n.leida_at && <span><Icon name="visibility" className="text-[14px]" /> {formatDateTime(n.leida_at)}</span>}
                    </div>
                  )}
                </div>
                {!n.leida && <button className="btn-ghost text-body-sm" onClick={() => marcar.mutate(n.id)}><Icon name="mark_email_read" className="text-[18px]" /> Marcar leída</button>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
