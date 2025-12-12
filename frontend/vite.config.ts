import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { TanStackRouterVite } from "@tanstack/router-plugin/vite"
import { defineConfig } from "vite"
import tsconfigPaths from "vite-tsconfig-paths"

// https://vite.dev/config/
export default defineConfig({
  plugins: [tsconfigPaths(), TanStackRouterVite(), react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
  },
})
