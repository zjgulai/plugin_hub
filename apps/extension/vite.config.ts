import react from "@vitejs/plugin-react";
import { build as buildWithEsbuild } from "esbuild";
import { defineConfig, type Plugin } from "vite";

import manifest from "./manifest.config";

export default defineConfig(({ mode }) => ({
  plugins: [react(), standaloneContentScript(), chromeExtensionAssets()],
  define: {
    "process.env.NODE_ENV": JSON.stringify(mode === "production" ? "production" : "development")
  },
  test: {
    environment: "jsdom",
    globals: true
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    lib: {
      entry: {
        "background/service-worker": "./src/background/service-worker.ts",
        "popup/Popup": "./src/popup/Popup.tsx"
      },
      formats: ["es"],
      fileName: (_format, entryName) => `${entryName}.js`
    }
  }
}));

function standaloneContentScript(): Plugin {
  return {
    name: "plugin-hub-standalone-content-script",
    async generateBundle() {
      const result = await buildWithEsbuild({
        entryPoints: [new URL("./src/content/content-script.ts", import.meta.url).pathname],
        bundle: true,
        format: "iife",
        platform: "browser",
        target: "es2022",
        write: false
      });
      const output = result.outputFiles[0];

      if (!output) {
        throw new Error("content_script_bundle_required");
      }

      this.emitFile({
        type: "asset",
        fileName: "content/content-script.js",
        source: output.text
      });
    }
  };
}

function chromeExtensionAssets(): Plugin {
  return {
    name: "plugin-hub-chrome-extension-assets",
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "manifest.json",
        source: JSON.stringify(manifest, null, 2)
      });
      this.emitFile({
        type: "asset",
        fileName: "popup/index.html",
        source: [
          "<!doctype html>",
          '<html lang="en">',
          "  <head>",
          '    <meta charset="UTF-8" />',
          '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
          "    <title>Plugin Hub VOC Collector</title>",
          "  </head>",
          "  <body>",
          '    <div id="root"></div>',
          '    <script type="module" src="./Popup.js"></script>',
          "  </body>",
          "</html>"
        ].join("\n")
      });
    }
  };
}
