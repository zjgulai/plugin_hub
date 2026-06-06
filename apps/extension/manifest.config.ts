const manifest = {
  manifest_version: 3,
  name: "Plugin Hub VOC Collector",
  version: "0.1.0",
  description: "Collects supported VOC pages for Plugin Hub.",
  permissions: ["activeTab", "storage"],
  host_permissions: [
    "https://amazon.com/*",
    "https://www.amazon.com/*",
    "https://smile.amazon.com/*",
    "https://amazon.co.uk/*",
    "https://www.amazon.co.uk/*",
    "https://amazon.de/*",
    "https://www.amazon.de/*",
    "https://amazon.ca/*",
    "https://www.amazon.ca/*",
    "https://amazon.com.au/*",
    "https://www.amazon.com.au/*",
    "https://amazon.co.jp/*",
    "https://www.amazon.co.jp/*",
    "https://reddit.com/*",
    "https://www.reddit.com/*",
    "https://old.reddit.com/*",
    "http://localhost/*",
    "http://127.0.0.1/*"
  ],
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
      matches: [
        "https://amazon.com/*",
        "https://www.amazon.com/*",
        "https://smile.amazon.com/*",
        "https://amazon.co.uk/*",
        "https://www.amazon.co.uk/*",
        "https://amazon.de/*",
        "https://www.amazon.de/*",
        "https://amazon.ca/*",
        "https://www.amazon.ca/*",
        "https://amazon.com.au/*",
        "https://www.amazon.com.au/*",
        "https://amazon.co.jp/*",
        "https://www.amazon.co.jp/*",
        "https://reddit.com/*",
        "https://www.reddit.com/*",
        "https://old.reddit.com/*"
      ],
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
    default_title: "Plugin Hub VOC Collector"
  }
} satisfies chrome.runtime.ManifestV3;

export default manifest;
