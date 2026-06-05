const manifest = {
  manifest_version: 3,
  name: "Plugin Hub VOC Collector",
  version: "0.1.0",
  description: "Collects supported VOC pages for Plugin Hub.",
  permissions: ["activeTab", "scripting"],
  host_permissions: ["https://*.amazon.*/*", "https://*.reddit.com/*"],
  action: {
    default_title: "Plugin Hub VOC Collector"
  }
} satisfies chrome.runtime.ManifestV3;

export default manifest;
