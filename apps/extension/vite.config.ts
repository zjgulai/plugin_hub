import react from "@vitejs/plugin-react";
import { build as buildWithEsbuild } from "esbuild";
import process from "node:process";
import { defineConfig, type Plugin } from "vite";

import { buildManifest } from "./manifest.config";
import {
  extensionTargetConfig,
  normalizeExtensionTarget,
  type ExtensionTarget
} from "./src/lib/extension-target";

const extensionTarget = normalizeExtensionTarget(process.env.PLUGIN_HUB_EXTENSION_TARGET);

export default defineConfig(({ mode }) => {
  return {
    plugins: [
      react(),
      standaloneContentScript(extensionTarget),
      chromeExtensionAssets(extensionTarget)
    ],
    define: {
      "process.env.NODE_ENV": JSON.stringify(mode === "production" ? "production" : "development"),
      __PLUGIN_HUB_EXTENSION_TARGET__: JSON.stringify(extensionTarget)
    },
    test: {
      environment: "jsdom",
      globals: true,
      testTimeout: 20_000,
      hookTimeout: 20_000
    },
    build: {
      outDir: `dist/${extensionTarget}`,
      emptyOutDir: true,
      lib: {
        entry: {
          "background/service-worker": "./src/background/service-worker.ts",
          "popup/Popup": "./src/popup/Popup.tsx"
        },
        formats: ["es"],
        fileName: (_format, entryName) => `${entryName}.js`
      },
      rollupOptions: {
        output: {
          assetFileNames: "[name][extname]"
        }
      }
    }
  };
});

function standaloneContentScript(target: ExtensionTarget): Plugin {
  return {
    name: "plugin-hub-standalone-content-script",
    async generateBundle() {
      const result = await buildWithEsbuild({
        entryPoints: [new URL(`./src/content/content-script.${target}.tsx`, import.meta.url).pathname],
        bundle: true,
        define: {
          "process.env.NODE_ENV": JSON.stringify("production"),
          __PLUGIN_HUB_EXTENSION_TARGET__: JSON.stringify(target)
        },
        format: "iife",
        legalComments: "none",
        minify: true,
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

function chromeExtensionAssets(target: ExtensionTarget): Plugin {
  return {
    name: "plugin-hub-chrome-extension-assets",
    generateBundle() {
      const targetConfig = extensionTargetConfig(target);
      this.emitFile({
        type: "asset",
        fileName: "manifest.json",
        source: JSON.stringify(buildManifest(target), null, 2)
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
          `    <title>${targetConfig.popupTitle}</title>`,
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
