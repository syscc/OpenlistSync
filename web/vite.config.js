import { fileURLToPath, URL } from "node:url";
import { readFileSync } from "node:fs";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import yaml from "@modyfi/vite-plugin-yaml";
import vueDevTools from "vite-plugin-vue-devtools";

const appVersion = readFileSync(new URL("../version.txt", import.meta.url), "utf8")
  .split(/\r?\n/, 1)[0]
  .split(",", 1)[0]
  .trim();

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), yaml(), vueDevTools()],
  define: {
    "import.meta.env.VITE_APP_VERSION": JSON.stringify(appVersion),
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 18023,
    open: true,
    proxy: {
      "/svr": {
        target: "http://127.0.0.1:8023",
        changeOrigin: true,
      },
    },
  },
});
