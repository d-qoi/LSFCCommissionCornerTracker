import { defineConfig } from "vite";
import solid from "vite-plugin-solid";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import devtools from "solid-devtools/vite";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    devtools({
      autoname: true,
    }),
    tanstackRouter({ target: "solid", autoCodeSplitting: true }),
    solid(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
