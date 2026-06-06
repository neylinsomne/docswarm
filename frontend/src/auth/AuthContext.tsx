import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, clearSession, getSession } from "../lib/api";
import type { Session } from "../lib/types";

interface AuthState {
  session: Session | null;
  isAdmin: boolean;
  isProveedor: boolean;
  login: (email: string, password: string) => Promise<Session>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => getSession());

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  // Si cualquier llamada devuelve 401, cerramos sesión.
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("docswarm:unauthorized", handler);
    return () => window.removeEventListener("docswarm:unauthorized", handler);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const s = await api.login(email, password);
    setSession(s);
    return s;
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      session,
      isAdmin: session?.tipo_empresa === "COMPRADOR",
      isProveedor: session?.tipo_empresa === "PROVEEDOR",
      login,
      logout,
    }),
    [session, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
