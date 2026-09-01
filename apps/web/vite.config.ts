import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    proxy: {
      // Local dev only: routes /api/* to the FastAPI service so the
      // frontend never hardcodes an absolute backend URL.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // FastAPI routes are /health, /workspaces, ... — strip the /api prefix.
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    host: true,
    port: 43147,
    allowedHosts: true,
  },
});
