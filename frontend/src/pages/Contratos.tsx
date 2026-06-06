import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, LoadingState } from "../components/ui";
import { Icon } from "../components/Icon";
import { estadoContratoTone, formatDate, formatMoney } from "../lib/format";
import { ESTADOS_CONTRATO } from "../lib/types";

export function Contratos() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [estado, setEstado] = useState("");

  const lista = useQuery({
    queryKey: ["contratos", { estado }],
    queryFn: () => api.listarContratos({ estado: estado || undefined, limit: 200 }),
  });

  return (
    <>
      <PageHeader
        title={isAdmin ? "Contratos" : "Mis contratos"}
        subtitle={isAdmin ? "Todos los contratos con proveedores." : "Tus contratos con Bayern."}
        actions={isAdmin && <button className="btn-primary" onClick={() => navigate("/contratos/nuevo")}><Icon name="add" className="text-[18px]" /> Crear contrato</button>}
      />

      <div className="card mb-stack-relaxed flex flex-wrap items-center gap-3 p-3">
        <span className="font-label-caps text-label-caps uppercase text-secondary">Estado</span>
        <button onClick={() => setEstado("")} className={`rounded-full px-3 py-1 text-body-sm ${estado === "" ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant"}`}>Todos</button>
        {ESTADOS_CONTRATO.map((s) => (
          <button key={s} onClick={() => setEstado(s)} className={`rounded-full px-3 py-1 text-body-sm ${estado === s ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant"}`}>{s}</button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {lista.isLoading ? <LoadingState /> : lista.isError ? (
          <EmptyState icon="error" title="No se pudo cargar" hint={(lista.error as Error).message} />
        ) : !lista.data?.length ? (
          <EmptyState icon="description" title="Sin contratos" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] border-collapse text-left">
              <thead><tr className="border-b border-outline-variant bg-surface-bright">
                <th className="th w-[140px]">Número</th><th className="th">Título</th><th className="th">Proveedor</th><th className="th w-[120px]">Estado</th><th className="th w-[150px]">Valor</th><th className="th w-[110px]">Firmado</th><th className="th w-[50px]"></th>
              </tr></thead>
              <tbody className="font-body-md text-body-md text-on-surface">
                {lista.data.map((c) => (
                  <tr key={c.id} onClick={() => navigate(`/contratos/${c.id}`)} className="h-[48px] cursor-pointer border-b border-outline-variant hover:bg-surface-container-highest">
                    <td className="td font-data-mono text-data-mono text-secondary">{c.numero ?? `#${c.id}`}</td>
                    <td className="td font-semibold">{c.titulo}</td>
                    <td className="td">{c.proveedor_nombre ?? "—"}</td>
                    <td className="td"><Badge tone={estadoContratoTone(c.estado)}>{c.estado}</Badge></td>
                    <td className="td font-data-mono text-data-mono">{formatMoney(c.valor, c.moneda)}</td>
                    <td className="td"><Badge tone={c.firmado_proveedor ? "ok" : "warn"}>{c.firmado_proveedor ? "Sí" : "No"}</Badge></td>
                    <td className="td text-right"><Icon name="chevron_right" className="text-outline" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
