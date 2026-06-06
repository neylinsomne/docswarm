import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, todas las llamadas a /api y /health se redirigen al core API.
// Cambia VITE_API_TARGET para apuntar a otro backend (por defecto localhost:8008).
const API_TARGET = process.env.VITE_API_TARGET || "http://localhost:8008";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
    },
  },
});
