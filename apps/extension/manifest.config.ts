import {
  extensionTargetConfig,
  normalizeExtensionTarget,
  type ExtensionTarget
} from "./src/lib/extension-target";
import { extensionVersion } from "./src/lib/extension-version";

export function buildManifest(targetInput: ExtensionTarget) {
  const target = normalizeExtensionTarget(targetInput);
  const targetConfig = extensionTargetConfig(target);
  const icons = buildIconSet(target);
  const manifest = {
    manifest_version: 3,
    name: targetConfig.name,
    version: extensionVersion(target),
    description: targetConfig.description,
    permissions: ["activeTab", "storage"],
    host_permissions: [...targetConfig.hostPermissions],
    background: {
      service_worker: "background/service-worker.js",
      type: "module"
    },
    icons,
    content_scripts: [
      {
        matches: [...targetConfig.contentMatches],
        js: ["content/content-script.js"]
      }
    ],
    action: {
      default_icon: icons,
      default_popup: "popup/index.html",
      default_title: targetConfig.defaultTitle
    }
  } satisfies chrome.runtime.ManifestV3;

  return manifest;
}

function buildIconSet(target: ExtensionTarget) {
  return {
    "16": `icons/${target}/icon-16.png`,
    "32": `icons/${target}/icon-32.png`,
    "48": `icons/${target}/icon-48.png`,
    "128": `icons/${target}/icon-128.png`
  } satisfies Record<string, string>;
}

const manifest = buildManifest("amazon");

export default manifest;
