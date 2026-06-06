interface IconProps {
  name: string;
  className?: string;
  filled?: boolean;
}

// Material Symbols Outlined (cargado por la fuente en index.html).
export function Icon({ name, className = "", filled = false }: IconProps) {
  return (
    <span className={`material-symbols-outlined ${filled ? "fill" : ""} ${className}`} aria-hidden>
      {name}
    </span>
  );
}
