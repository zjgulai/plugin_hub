import {
  extensionTargetConfig,
  normalizeExtensionTarget,
  type ExtensionTarget
} from "./src/lib/extension-target";

export function buildManifest(targetInput: ExtensionTarget) {
  const target = normalizeExtensionTarget(targetInput);
  const targetConfig = extensionTargetConfig(target);
  const manifest = {
    manifest_version: 3,
    name: targetConfig.name,
    version: "0.1.0",
    description: targetConfig.description,
    permissions: ["activeTab", "storage"],
    host_permissions: [...targetConfig.hostPermissions],
    background: {
      service_worker: "background/service-worker.js",
      type: "module"
    },
    icons: {
      "16": "icons/icon-16.png",
      "32": "icons/icon-32.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    },
    content_scripts: [
      {
        matches: [...targetConfig.contentMatches],
        js: ["content/content-script.js"]
      }
    ],
    action: {
      default_icon: {
        "16": "icons/icon-16.png",
        "32": "icons/icon-32.png",
        "48": "icons/icon-48.png",
        "128": "icons/icon-128.png"
      },
      default_popup: "popup/index.html",
      default_title: targetConfig.defaultTitle
    }
  } satisfies chrome.runtime.ManifestV3;

  return manifest;
}

const manifest = buildManifest("amazon");

export default manifest;
