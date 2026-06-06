import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Proveedores } from "./pages/Proveedores";
import { Contratos } from "./pages/Contratos";
import { ContratoDetalle } from "./pages/ContratoDetalle";
import { CrearContrato } from "./pages/CrearContrato";
import { AsistenteContrato } from "./pages/AsistenteContrato";
import { Catalogo } from "./pages/Catalogo";
import { Cambios } from "./pages/Cambios";
import { Notificaciones } from "./pages/Notificaciones";
import { Busqueda } from "./pages/Busqueda";
import { Documentos } from "./pages/Documentos";
import { MiEmpresa } from "./pages/MiEmpresa";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth();
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  const { session } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/proveedores" element={<AdminOnly><Proveedores /></AdminOnly>} />
        <Route path="/contratos" element={<Contratos />} />
        <Route path="/contratos/asistente" element={<AdminOnly><AsistenteContrato /></AdminOnly>} />
        <Route path="/contratos/nuevo" element={<AdminOnly><CrearContrato /></AdminOnly>} />
        <Route path="/contratos/:id" element={<ContratoDetalle />} />
        <Route path="/catalogo" element={<AdminOnly><Catalogo /></AdminOnly>} />
        <Route path="/cambios" element={<Cambios />} />
        <Route path="/notificaciones" element={<Notificaciones />} />
        <Route path="/documentos" element={<Documentos />} />
        <Route path="/buscar" element={<Busqueda />} />
        <Route path="/mi-empresa" element={<MiEmpresa />} />
      </Route>
      <Route path="*" element={<Navigate to={session ? "/dashboard" : "/login"} replace />} />
    </Routes>
  );
}
