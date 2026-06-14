import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(repoRoot, "apps", "extension", "dist");
const manifestPath = join(distDir, "manifest.json");
const outputDir = join(repoRoot, "tmp", "outputs");

const requiredDistFiles = [
  "manifest.json",
  "content/content-script.js",
  "background/service-worker.js",
  "popup/index.html",
  "popup/Popup.js",
  "icons/icon-16.png",
  "icons/icon-32.png",
  "icons/icon-48.png",
  "icons/icon-128.png"
];

for (const fileName of requiredDistFiles) {
  assertFile(join(distDir, fileName), `extension_dist_missing:${fileName}`);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
assertEqual(manifest.manifest_version, 3, "manifest_version_must_be_3");
assertEqual(manifest.name, "Plugin Hub VOC Collector", "manifest_name_changed");
assertArrayIncludes(manifest.permissions, "activeTab", "permission_activeTab_required");
assertArrayIncludes(manifest.permissions, "storage", "permission_storage_required");
assertArrayIncludes(manifest.host_permissions, "https://www.amazon.com/*", "amazon_host_permission_required");
assertArrayIncludes(manifest.host_permissions, "https://www.reddit.com/*", "reddit_host_permission_required");
assertArrayIncludes(manifest.host_permissions, "http://localhost/*", "localhost_host_permission_required");

const contentScripts = Array.isArray(manifest.content_scripts) ? manifest.content_scripts : [];
const mainContentScript = contentScripts.find((script) => {
  return Array.isArray(script.js) && script.js.includes("content/content-script.js");
});
if (!mainContentScript) {
  throw new Error("content_script_manifest_entry_required");
}
assertArrayIncludes(mainContentScript.matches, "https://www.amazon.com/*", "content_script_amazon_match_required");
assertArrayIncludes(mainContentScript.matches, "https://www.reddit.com/*", "content_script_reddit_match_required");

const contentScriptSize = statSync(join(distDir, "content", "content-script.js")).size;
if (contentScriptSize > 300_000) {
  throw new Error(`content_script_too_large:${contentScriptSize}`);
}

const version = typeof manifest.version === "string" ? manifest.version : "unknown";
const zipPath = join(outputDir, `plugin-hub-extension-${version}.zip`);
assertFile(zipPath, `extension_zip_missing:${zipPath}`);

const zipEntries = listZipEntries(zipPath);
for (const fileName of requiredDistFiles) {
  assertArrayIncludes(zipEntries, fileName, `extension_zip_entry_missing:${fileName}`);
}

console.log(
  JSON.stringify(
    {
      ok: true,
      manifest_version: manifest.manifest_version,
      version,
      content_script_size: contentScriptSize,
      zip_path: zipPath,
      zip_entries: zipEntries.length
    },
    null,
    2
  )
);

function listZipEntries(zipPath) {
  const result = spawnSync("unzip", ["-Z1", zipPath], {
    encoding: "utf8"
  });

  if (result.status !== 0) {
    throw new Error(`extension_zip_list_failed:${result.status ?? "unknown"}`);
  }

  return result.stdout.split("\n").filter(Boolean);
}

function assertFile(filePath, errorCode) {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    throw new Error(errorCode);
  }
}

function assertEqual(actual, expected, errorCode) {
  if (actual !== expected) {
    throw new Error(`${errorCode}:${String(actual)}`);
  }
}

function assertArrayIncludes(value, expected, errorCode) {
  if (!Array.isArray(value) || !value.includes(expected)) {
    throw new Error(errorCode);
  }
}
