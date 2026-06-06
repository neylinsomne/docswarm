import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, KpiCard, LoadingState, EmptyState, ProgressBar } from "../components/ui";
import { Icon } from "../components/Icon";
import { estadoContratoTone, formatDate, formatMoney } from "../lib/format";

export function Dashboard() {
  const { isAdmin } = useAuth();
  return isAdmin ? <DashboardAdmin /> : <DashboardProveedor />;
}

function DashboardAdmin() {
  const navigate = useNavigate();
  const cambios = useQuery({ queryKey: ["cambios", "dash"], queryFn: () => api.listarCambios({ limit: 8 }) });
  const contratos = useQuery({ queryKey: ["contratos", "dash"], queryFn: () => api.listarContratos({ limit: 100 }) });
  const empresas = useQuery({ queryKey: ["empresas", "dash"], queryFn: () => api.listarEmpresas({ limit: 200 }) });

  const proveedores = (empresas.data ?? []).filter((e) => (e.tipo ?? e.tipo_empresa) !== "COMPRADOR").length || empresas.data?.length || 0;
  const vigentes = (contratos.data ?? []).filter((c) => c.estado === "VIGENTE").length;
  const cambiosMes = cambios.data?.length ?? 0;
  const totalAfectados = (cambios.data ?? []).reduce((a, c) => a + (c.docs_afectados ?? 0), 0);
  const totalPend = (cambios.data ?? []).reduce((a, c) => a + (c.docs_pendientes ?? 0), 0);
  const pctPend = totalAfectados > 0 ? Math.round((totalPend / totalAfectados) * 100) : 0;

  return (
    <>
      <PageHeader title="Resumen del sistema" subtitle="Métricas principales y actividad reciente." />
      <div className="mb-stack-relaxed grid grid-cols-1 gap-gutter md:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Proveedores" value={proveedores} icon="business" />
        <KpiCard title="Contratos vigentes" value={vigentes} icon="description" tone="ok" />
        <KpiCard title="Cambios recientes" value={cambiosMes} icon="sync_alt" />
        <KpiCard title="% docs pendientes" value={`${pctPend}%`} icon="pending_actions" tone={pctPend > 30 ? "danger" : "warn"} trend={`${totalPend} sin firmar`} />
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-low p-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">Cambios recientes</h3>
          <Link to="/cambios" className="flex items-center gap-1 font-body-sm text-body-sm font-semibold text-primary hover:text-surface-tint">
            Ver todos <Icon name="arrow_forward" className="text-[16px]" />
          </Link>
        </div>
        {cambios.isLoading ? (
          <LoadingState />
        ) : !cambios.data?.length ? (
          <EmptyState icon="sync_alt" title="Sin cambios registrados" hint="Registra un cambio de cláusula o precio en el módulo Cambios." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-bright">
                  <th className="th w-[120px]">Fecha</th>
                  <th className="th">Objeto</th>
                  <th className="th w-[120px]">Tipo</th>
                  <th className="th w-[200px]">Firmados</th>
                  <th className="th w-[60px]"></th>
                </tr>
              </thead>
              <tbody className="font-body-md text-body-md text-on-surface">
                {cambios.data.map((c) => (
                  <tr key={c.id} onClick={() => navigate(`/cambios?id=${c.id}`)} className="h-[48px] cursor-pointer border-b border-outline-variant transition-colors hover:bg-surface-container-highest">
                    <td className="td font-data-mono text-data-mono text-secondary">{formatDate(c.creado_en)}</td>
                    <td className="td font-semibold">{c.objeto_titulo ?? c.objeto_codigo ?? `#${c.id}`}</td>
                    <td className="td"><Badge tone={c.tipo_objeto === "PRECIO" ? "info" : "neutral"}>{c.tipo_objeto}</Badge></td>
                    <td className="td"><ProgressBar value={c.docs_firmados ?? 0} total={c.docs_afectados ?? 0} /></td>
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

function DashboardProveedor() {
  const navigate = useNavigate();
  const contratos = useQuery({ queryKey: ["contratos", "dash-prov"], queryFn: () => api.listarContratos({ limit: 100 }) });
  const noLeidas = useQuery({ queryKey: ["notif-conteo-dash"], queryFn: () => api.conteoNoLeidas() });
  const cambios = useQuery({ queryKey: ["cambios", "dash-prov"], queryFn: () => api.listarCambios({ limit: 10 }) });

  const mis = contratos.data ?? [];
  const pendFirma = mis.filter((c) => !c.firmado_proveedor).length;

  return (
    <>
      <PageHeader title="Mi panel" subtitle="Tus contratos, firmas pendientes y avisos." />
      <div className="mb-stack-relaxed grid grid-cols-1 gap-gutter md:grid-cols-3">
        <KpiCard title="Mis contratos" value={mis.length} icon="description" />
        <KpiCard title="Pendientes de firma" value={pendFirma} icon="draw" tone={pendFirma ? "warn" : "ok"} />
        <KpiCard title="Avisos sin leer" value={noLeidas.data ?? 0} icon="notifications" tone={(noLeidas.data ?? 0) > 0 ? "info" : "neutral"} />
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-low p-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">Cambios que me afectan</h3>
          <Link to="/cambios" className="flex items-center gap-1 font-body-sm text-body-sm font-semibold text-primary hover:text-surface-tint">
            Ver todos <Icon name="arrow_forward" className="text-[16px]" />
          </Link>
        </div>
        {cambios.isLoading ? (
          <LoadingState />
        ) : !cambios.data?.length ? (
          <EmptyState icon="check_circle" title="Sin cambios pendientes" hint="No tienes actualizaciones de contrato por revisar." />
        ) : (
          <ul className="divide-y divide-outline-variant">
            {cambios.data.map((c) => (
              <li key={c.id} onClick={() => navigate(`/cambios?id=${c.id}`)} className="flex cursor-pointer items-center justify-between px-4 py-3 hover:bg-surface-container-highest">
                <div className="flex items-center gap-3">
                  <Icon name={c.tipo_objeto === "PRECIO" ? "payments" : "gavel"} className="text-outline" />
                  <div>
                    <p className="font-semibold text-on-surface">{c.objeto_titulo ?? `Cambio #${c.id}`}</p>
                    <p className="font-body-sm text-body-sm text-secondary">{c.descripcion ?? c.tipo_objeto}</p>
                  </div>
                </div>
                <Icon name="chevron_right" className="text-outline" />
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-stack-relaxed card overflow-hidden">
        <div className="border-b border-outline-variant bg-surface-container-low p-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">Mis contratos</h3>
        </div>
        {contratos.isLoading ? <LoadingState /> : (
          <table className="w-full border-collapse text-left">
            <thead><tr className="border-b border-outline-variant bg-surface-bright">
              <th className="th">Contrato</th><th className="th w-[140px]">Estado</th><th className="th w-[160px]">Valor</th><th className="th w-[120px]">Firmado</th>
            </tr></thead>
            <tbody className="font-body-md text-body-md">
              {mis.slice(0, 6).map((c) => (
                <tr key={c.id} onClick={() => navigate(`/contratos/${c.id}`)} className="h-[48px] cursor-pointer border-b border-outline-variant hover:bg-surface-container-highest">
                  <td className="td font-semibold">{c.titulo}</td>
                  <td className="td"><Badge tone={estadoContratoTone(c.estado)}>{c.estado}</Badge></td>
                  <td className="td font-data-mono text-data-mono">{formatMoney(c.valor, c.moneda)}</td>
                  <td className="td"><Badge tone={c.firmado_proveedor ? "ok" : "warn"}>{c.firmado_proveedor ? "Sí" : "Pendiente"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
