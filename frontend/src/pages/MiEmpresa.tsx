import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/Layout";
import { Badge, EmptyState, LoadingState } from "../components/ui";

export function MiEmpresa() {
  const { session } = useAuth();
  const det = useQuery({
    queryKey: ["empresa", session?.empresa_id],
    queryFn: () => api.obtenerEmpresa(session!.empresa_id),
    enabled: !!session?.empresa_id,
  });
  const e = det.data;

  return (
    <>
      <PageHeader title="Mi empresa" subtitle="Datos de perfil de tu empresa proveedora." />
      {det.isLoading ? <LoadingState /> : !e ? <EmptyState icon="store" title="No disponible" /> : (
        <div className="card p-5">
          <h3 className="mb-4 font-headline-md text-headline-md text-on-surface">{e.nombre}</h3>
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <Item label="NIT" value={e.nit} mono /><Item label="Sector" value={e.sector} /><Item label="Nicho" value={e.nicho} />
            <Item label="Ciudad" value={e.ciudad} /><Item label="País" value={e.pais} /><Item label="Estado" value={e.activo === false ? "Inactivo" : "Activo"} />
          </dl>
          {!!e.caracteristicas?.length && (
            <div className="mt-4">
              <p className="label">Características</p>
              <div className="flex flex-wrap gap-2">{e.caracteristicas.map((c, i) => <Badge key={i} tone="info">{c.clave}: {c.valor}</Badge>)}</div>
            </div>
          )}
          {e.metadata && Object.keys(e.metadata).length > 0 && (
            <div className="mt-4">
              <p className="label">Metadata</p>
              <pre className="overflow-x-auto rounded-lg bg-surface-container p-3 font-data-mono text-data-mono">{JSON.stringify(e.metadata, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </>
  );
}

function Item({ label, value, mono }: { label: string; value?: unknown; mono?: boolean }) {
  return (
    <div>
      <dt className="font-label-caps text-label-caps uppercase text-secondary">{label}</dt>
      <dd className={`text-on-surface ${mono ? "font-data-mono text-data-mono" : "font-body-md text-body-md"}`}>{value != null && value !== "" ? String(value) : "—"}</dd>
    </div>
  );
}
