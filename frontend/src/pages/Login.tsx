import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";
import { Icon } from "../components/Icon";
import { Spinner } from "../components/ui";

const DEMO = [
  { label: "Bayern (ADMIN)", email: "bayern.demo@docswarm.local", pass: "Demo1234*" },
  { label: "Proveedor · Semillas", email: "semillas.demo@docswarm.local", pass: "Demo1234*" },
  { label: "Proveedor · Campo", email: "campo.demo@docswarm.local", pass: "Demo1234*" },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible iniciar sesión.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-gutter">
      <main className="w-full max-w-[420px]">
        <div className="mb-stack-relaxed text-center">
          <h1 className="mb-stack-compact font-display-lg text-display-lg text-on-surface">DocSwarm</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">Digital Clerkship</p>
        </div>
        <div className="card p-container-margin shadow-sm">
          <h2 className="mb-stack-relaxed font-title-sm text-title-sm text-on-surface">
            Acceso a la plataforma
          </h2>
          <form onSubmit={submit} className="flex flex-col gap-stack-relaxed">
            <div>
              <label className="label" htmlFor="email">Correo electrónico</label>
              <div className="relative">
                <Icon name="mail" className="absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-outline" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input pl-10"
                  placeholder="usuario@empresa.com"
                />
              </div>
            </div>
            <div>
              <label className="label" htmlFor="password">Contraseña</label>
              <div className="relative">
                <Icon name="lock" className="absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-outline" />
                <input
                  id="password"
                  type={show ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-10 pr-10"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface"
                >
                  <Icon name={show ? "visibility_off" : "visibility"} className="text-[20px]" />
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-danger-bg px-3 py-2 text-danger-fg">
                <Icon name="error" className="text-[18px]" />
                <span className="font-body-sm text-body-sm">{error}</span>
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary mt-stack-compact w-full py-3">
              {loading ? <Spinner /> : <>Iniciar sesión <Icon name="arrow_forward" className="text-[20px]" /></>}
            </button>
          </form>

          <div className="mt-stack-relaxed border-t border-outline-variant pt-stack-relaxed">
            <p className="mb-2 font-label-caps text-label-caps uppercase text-on-surface-variant">
              Cuentas demo
            </p>
            <div className="flex flex-col gap-1">
              {DEMO.map((d) => (
                <button
                  key={d.email}
                  type="button"
                  onClick={() => { setEmail(d.email); setPassword(d.pass); }}
                  className="flex items-center justify-between rounded-lg px-2 py-1.5 text-left hover:bg-surface-container-high"
                >
                  <span className="font-body-sm text-body-sm text-on-surface">{d.label}</span>
                  <span className="font-data-mono text-data-mono text-outline">{d.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        <footer className="mt-stack-relaxed text-center font-body-sm text-body-sm text-on-surface-variant">
          <p className="flex items-center justify-center gap-2">
            <Icon name="security" className="text-[16px]" /> Auth: JWT Bearer · es · © DocSwarm
          </p>
        </footer>
      </main>
    </div>
  );
}
