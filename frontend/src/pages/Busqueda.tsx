import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, LoadingState } from "../components/ui";
import { Icon } from "../components/Icon";
import { estadoContratoTone, formatMoney } from "../lib/format";
import type { BusquedaContenido } from "../lib/types";

type Tab = "contenido" | "contratos" | "empresas";

export function Busqueda() {
  const { isAdmin } = useAuth();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [submitted, setSubmitted] = useState(params.get("q") ?? "");
  const [tab, setTab] = useState<Tab>("contenido");

  useEffect(() => { const p = params.get("q"); if (p) { setQ(p); setSubmitted(p); } }, [params]);

  const submit = (e: React.FormEvent) => { e.preventDefault(); setSubmitted(q); setParams(q ? { q } : {}); };

  const contenido = useQuery({ queryKey: ["buscar-contenido", submitted], queryFn: () => api.buscarContenido(submitted), enabled: tab === "contenido" && !!submitted });
  const contratos = useQuery({ queryKey: ["buscar-contratos", submitted], queryFn: () => api.buscarContratos(submitted), enabled: tab === "contratos" && !!submitted });
  const empresas = useQuery({ queryKey: ["buscar-empresas", submitted], queryFn: () => api.buscarEmpresas(submitted), enabled: tab === "empresas" && !!submitted });

  const tabs: { key: Tab; label: string; icon: string; show: boolean }[] = [
    { key: "contenido", label: "Contenido (semántica)", icon: "manage_search", show: true },
    { key: "contratos", label: "Contratos por nombre", icon: "description", show: true },
    { key: "empresas", label: "Empresas por perfil", icon: "business", show: isAdmin },
  ];

  return (
    <>
      <PageHeader title="Búsqueda global" subtitle="Búsqueda vectorial por contenido, contratos y empresas." />
      <form onSubmit={submit} className="mb-stack-relaxed">
        <div className="relative">
          <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-[22px] text-outline" />
          <input autoFocus className="input py-3 pl-11 text-body-md" placeholder="Escribe tu búsqueda y pulsa Enter…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </form>

      <div className="mb-4 flex gap-1 rounded-lg bg-surface-container p-1 w-fit">
        {tabs.filter((t) => t.show).map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={`flex items-center gap-1 rounded-lg px-4 py-1.5 text-body-sm font-semibold ${tab === t.key ? "bg-surface-container-lowest text-primary shadow-sm" : "text-secondary"}`}>
            <Icon name={t.icon} className="text-[18px]" /> {t.label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {!submitted ? <EmptyState icon="search" title="Empieza a buscar" hint="Los resultados aparecen aquí." /> :
          tab === "contenido" ? <ResultContenido data={contenido.data as BusquedaContenido[] | undefined} loading={contenido.isLoading} /> :
          tab === "contratos" ? (
            contratos.isLoading ? <LoadingState /> : !contratos.data?.length ? <EmptyState icon="description" title="Sin contratos" /> : (
              <ul className="divide-y divide-outline-variant">
                {contratos.data.map((c) => (
                  <li key={c.id}><Link to={`/contratos/${c.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-surface-container-highest">
                    <div><p className="font-semibold text-on-surface">{c.titulo}</p><p className="font-body-sm text-body-sm text-secondary">{c.numero ?? `#${c.id}`} · {c.proveedor_nombre ?? ""}</p></div>
                    <div className="flex items-center gap-2"><Badge tone={estadoContratoTone(c.estado)}>{c.estado}</Badge><span className="font-data-mono text-data-mono">{formatMoney(c.valor, c.moneda)}</span></div>
                  </Link></li>
                ))}
              </ul>
            )
          ) : (
            empresas.isLoading ? <LoadingState /> : !empresas.data?.length ? <EmptyState icon="business" title="Sin empresas" /> : (
              <ul className="divide-y divide-outline-variant">
                {empresas.data.map((e) => (
                  <li key={e.id} className="flex items-center justify-between px-5 py-3">
                    <div><p className="font-semibold text-on-surface">{e.nombre}</p><p className="font-body-sm text-body-sm text-secondary">{e.sector ?? ""}{e.nicho ? ` · ${e.nicho}` : ""}</p></div>
                    <span className="font-data-mono text-data-mono text-outline">{e.nit ?? `#${e.id}`}</span>
                  </li>
                ))}
              </ul>
            )
          )}
      </div>
    </>
  );
}

function ResultContenido({ data, loading }: { data?: BusquedaContenido[]; loading: boolean }) {
  if (loading) return <LoadingState />;
  if (!data?.length) return <EmptyState icon="manage_search" title="Sin coincidencias" hint="Prueba con otras palabras." />;
  return (
    <ul className="divide-y divide-outline-variant">
      {data.map((r, i) => {
        const sim = r.similarity ?? r.score;
        return (
          <li key={i} className="px-5 py-4">
            <div className="mb-1 flex items-center justify-between">
              <Link to={`/contratos/${r.contrato_id}`} className="font-title-sm text-title-sm text-primary hover:underline">{r.contrato_titulo ?? `Contrato #${r.contrato_id}`}</Link>
              {sim != null && <Badge tone={sim > 0.7 ? "ok" : sim > 0.4 ? "warn" : "neutral"}>{(sim * 100).toFixed(0)}% match</Badge>}
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">{r.fragmento ?? r.texto}</p>
          </li>
        );
      })}
    </ul>
  );
}
