import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

// Offline demo: relative asset base so FastAPI can serve `dist/` from any
// mount point; dev proxy targets the API on 127.0.0.1 (never `localhost` —
// it can resolve to ::1 while uvicorn listens on IPv4).
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5180,
    warmup: {
      clientFiles: ["./src/main.tsx", "./src/features/graph/GraphScreen.tsx"],
    },
    proxy: {
      "/api": { target: "http://127.0.0.1:8321", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8321", ws: true },
    },
  },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks: {
          sigma: ["sigma", "graphology", "graphology-layout-forceatlas2"],
          charts: ["lightweight-charts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
