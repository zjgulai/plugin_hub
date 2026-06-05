import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

import manifest from "./manifest.config";

export default defineConfig({
  plugins: [react(), chromeExtensionAssets()],
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
        "background/service-worker": "./src/background/service-worker.ts",
        contracts: "./src/types/contracts.ts",
        "content/content-script": "./src/content/content-script.ts",
        "page-detect": "./src/lib/page-detect.ts",
        "popup/Popup": "./src/popup/Popup.tsx",
        "reddit-parser": "./src/lib/reddit-parser.ts",
        "upload-client": "./src/lib/upload-client.ts"
      },
      formats: ["es"],
      fileName: (_format, entryName) => `${entryName}.js`
    }
  }
});

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
