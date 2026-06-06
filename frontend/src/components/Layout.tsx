import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { Icon } from "./Icon";
import { useState } from "react";

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const NAV_ADMIN: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/proveedores", label: "Proveedores", icon: "business" },
  { to: "/contratos", label: "Contratos", icon: "description" },
  { to: "/contratos/asistente", label: "Asistente IA", icon: "smart_toy" },
  { to: "/catalogo", label: "Catálogo maestro", icon: "inventory_2" },
  { to: "/cambios", label: "Cambios", icon: "sync_alt" },
  { to: "/notificaciones", label: "Notificaciones", icon: "notifications" },
  { to: "/documentos", label: "Documentos", icon: "folder_open" },
  { to: "/buscar", label: "Búsqueda", icon: "search" },
];

const NAV_PROVEEDOR: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/contratos", label: "Mis contratos", icon: "description" },
  { to: "/cambios", label: "Cambios que me afectan", icon: "sync_alt" },
  { to: "/notificaciones", label: "Notificaciones", icon: "notifications" },
  { to: "/documentos", label: "Documentos", icon: "folder_open" },
  { to: "/mi-empresa", label: "Mi empresa", icon: "store" },
];

function Sidebar({ items, onNew }: { items: NavItem[]; onNew: () => void }) {
  return (
    <nav className="fixed left-0 top-0 z-20 flex h-screen w-[260px] flex-col border-r border-outline-variant bg-inverse-surface py-6">
      <div className="px-6 mb-8">
        <h1 className="font-display-lg text-display-lg font-bold text-primary-fixed-dim">DocSwarm</h1>
        <p className="mt-1 font-body-sm text-body-sm text-tertiary-fixed-dim">Digital Clerkship</p>
      </div>
      <button
        onClick={onNew}
        className="mx-4 mb-6 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-on-primary transition-colors hover:bg-surface-tint"
      >
        <Icon name="add" className="text-[18px]" />
        <span className="font-title-sm text-title-sm">Nuevo contrato</span>
      </button>
      <ul className="flex-1 overflow-y-auto">
        {items.map((it) => (
          <li key={it.to}>
            <NavLink
              to={it.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 transition-colors duration-200 ${
                  isActive
                    ? "border-l-4 border-primary-fixed-dim bg-white/10 text-primary-fixed-dim"
                    : "text-surface-variant hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon name={it.icon} />
              <span>{it.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Topbar() {
  const { session, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  const { data: conteo } = useQuery({
    queryKey: ["notif-conteo"],
    queryFn: () => api.conteoNoLeidas(),
    refetchInterval: 30000,
    staleTime: 15000,
  });

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (q.trim()) navigate(`/buscar?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <header className="fixed left-[260px] top-0 z-10 flex h-16 w-[calc(100%-260px)] items-center justify-between border-b border-outline-variant bg-surface px-gutter">
      <form onSubmit={submitSearch} className="max-w-md flex-1">
        <div className="relative w-full text-on-surface-variant">
          <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-[20px]" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="h-10 w-full rounded-lg border border-outline-variant bg-surface-container-low py-2 pl-10 pr-4 font-body-md text-body-md outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            placeholder="Buscar contratos, proveedores, contenido…"
          />
        </div>
      </form>
      <div className="flex items-center gap-5">
        <NavLink to="/notificaciones" className="relative text-on-surface-variant hover:text-primary">
          <Icon name="notifications" className="text-[24px]" />
          {!!conteo && conteo > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold text-on-error">
              {conteo > 99 ? "99+" : conteo}
            </span>
          )}
        </NavLink>
        <div className="flex items-center gap-3 border-l border-outline-variant pl-5">
          <div className="text-right">
            <p className="font-title-sm text-title-sm leading-tight text-on-surface">
              {isAdmin ? "Bayern" : "Proveedor"}
            </p>
            <p className="font-label-caps text-label-caps uppercase leading-tight text-secondary">
              {session?.rol ?? (isAdmin ? "ADMIN" : "PROVEEDOR")}
            </p>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-container text-on-primary">
            <Icon name={isAdmin ? "shield_person" : "store"} className="text-[20px] fill" />
          </div>
        </div>
        <button
          onClick={logout}
          title="Cerrar sesión"
          className="rounded-lg p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high"
        >
          <Icon name="logout" />
        </button>
      </div>
    </header>
  );
}

export function Layout() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const items = isAdmin ? NAV_ADMIN : NAV_PROVEEDOR;
  return (
    <div className="min-h-screen bg-background">
      <Sidebar items={items} onNew={() => navigate(isAdmin ? "/contratos/nuevo" : "/contratos")} />
      <Topbar />
      <main className="ml-[260px] min-h-screen pt-16">
        <div className="mx-auto max-w-[1400px] p-container-margin">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

// Encabezado de página reutilizable.
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-stack-relaxed flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="mb-1 font-headline-md text-headline-md text-on-surface">{title}</h2>
        {subtitle && <p className="font-body-md text-body-md text-secondary">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
