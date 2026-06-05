import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    lib: {
      entry: {
        "amazon-parser": "./src/lib/amazon-parser.ts",
        contracts: "./src/types/contracts.ts",
        "page-detect": "./src/lib/page-detect.ts",
        "reddit-parser": "./src/lib/reddit-parser.ts"
      },
      formats: ["es"],
      fileName: (_format, entryName) => `${entryName}.js`
    }
  }
});
