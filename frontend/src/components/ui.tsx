import type { ReactNode } from "react";
import { useEffect } from "react";
import { Icon } from "./Icon";
import { toneClass, type BadgeTone } from "../lib/format";

// ---- Badge ----
export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold tracking-wide ${toneClass(
        tone,
      )}`}
    >
      {children}
    </span>
  );
}

// ---- Spinner ----
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      aria-label="Cargando"
    />
  );
}

export function LoadingState({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-on-surface-variant">
      <Spinner className="text-primary" />
      <span className="font-body-md text-body-md">{label}</span>
    </div>
  );
}

export function EmptyState({ icon = "inbox", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-on-surface-variant">
      <Icon name={icon} className="text-[40px] text-outline" />
      <p className="font-title-sm text-title-sm text-on-surface">{title}</p>
      {hint && <p className="font-body-sm text-body-sm max-w-sm">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-danger-fg">
      <Icon name="error" className="text-[40px]" />
      <p className="font-body-md text-body-md max-w-md">{message}</p>
    </div>
  );
}

// ---- KPI Card ----
export function KpiCard({
  title,
  value,
  icon,
  trend,
  tone = "neutral",
}: {
  title: string;
  value: ReactNode;
  icon: string;
  trend?: string;
  tone?: BadgeTone;
}) {
  const trendColor =
    tone === "ok" ? "text-ok-fg" : tone === "danger" ? "text-danger-fg" : "text-secondary";
  return (
    <div className="card p-4 flex flex-col justify-between h-[120px]">
      <div className="flex justify-between items-start">
        <span className="font-label-caps text-label-caps text-secondary uppercase tracking-wider">
          {title}
        </span>
        <Icon name={icon} className="text-outline text-[20px]" />
      </div>
      <div className="flex items-end gap-3 mt-auto">
        <span className="font-display-lg text-display-lg text-on-surface leading-none">{value}</span>
        {trend && (
          <span className={`flex items-center font-data-mono text-data-mono mb-1 ${trendColor}`}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}

// ---- Progress bar (firmados/afectados) ----
export function ProgressBar({ value, total }: { value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  const tone = pct >= 100 ? "bg-ok-fg" : pct > 0 ? "bg-warn-fg" : "bg-outline-variant";
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-surface-container-high overflow-hidden">
        <div className={`h-full ${tone} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-data-mono text-data-mono text-secondary whitespace-nowrap">
        {value}/{total}
      </span>
    </div>
  );
}

// ---- Modal ----
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg" | "xl";
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const width = size === "xl" ? "max-w-3xl" : size === "lg" ? "max-w-2xl" : "max-w-lg";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-on-surface/40 p-4 py-10">
      <div className={`card w-full ${width} shadow-xl animate-[fadeIn_.15s_ease-out]`}>
        <div className="flex items-center justify-between border-b border-outline-variant px-5 py-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">{title}</h3>
          <button onClick={onClose} className="text-outline hover:text-on-surface">
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>
        <div className="px-5 py-5 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-outline-variant px-5 py-4">{footer}</div>
        )}
      </div>
    </div>
  );
}

// ---- Drawer (panel lateral derecho, para detalles) ----
export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-on-surface/40">
      <div className="w-full max-w-xl bg-surface-container-lowest shadow-2xl h-full flex flex-col animate-[slideIn_.18s_ease-out]">
        <div className="flex items-center justify-between border-b border-outline-variant px-5 py-4">
          <h3 className="font-title-sm text-title-sm text-on-surface">{title}</h3>
          <button onClick={onClose} className="text-outline hover:text-on-surface">
            <Icon name="close" className="text-[20px]" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-outline-variant px-5 py-4">{footer}</div>
        )}
      </div>
    </div>
  );
}

// ---- Field wrapper ----
export function Field({
  label,
  children,
  hint,
  required,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="label">
        {label} {required && <span className="text-error">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 font-body-sm text-body-sm text-outline">{hint}</p>}
    </div>
  );
}
