import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TARGETS = ["amazon", "reddit"];
const CONFIG_BY_TARGET = {
  amazon: {
    manifestName: "Plugin Hub Amazon VOC Collector",
    zipSlug: "plugin-hub-amazon-voc",
    requiredHost: "https://www.amazon.com/*",
    forbiddenHost: "https://www.reddit.com/*"
  },
  reddit: {
    manifestName: "Plugin Hub Reddit VOC Collector",
    zipSlug: "plugin-hub-reddit-voc",
    requiredHost: "https://www.reddit.com/*",
    forbiddenHost: "https://www.amazon.com/*"
  }
};

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = join(repoRoot, "tmp", "outputs");
const targets = resolveTargets(process.argv[2]);

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

const results = [];

for (const target of targets) {
  results.push(verifyTarget(target));
}

console.log(JSON.stringify({ ok: true, results }, null, 2));

function verifyTarget(target) {
  const config = CONFIG_BY_TARGET[target];
  const distDir = join(repoRoot, "apps", "extension", "dist", target);
  const manifestPath = join(distDir, "manifest.json");

  for (const fileName of requiredDistFiles) {
    assertFile(join(distDir, fileName), `extension_dist_missing:${target}:${fileName}`);
  }

  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  assertEqual(manifest.manifest_version, 3, `manifest_version_must_be_3:${target}`);
  assertEqual(manifest.name, config.manifestName, `manifest_name_changed:${target}`);
  assertArrayIncludes(manifest.permissions, "activeTab", `permission_activeTab_required:${target}`);
  assertArrayIncludes(manifest.permissions, "storage", `permission_storage_required:${target}`);
  assertArrayIncludes(manifest.host_permissions, config.requiredHost, `host_permission_required:${target}`);
  assertArrayExcludes(manifest.host_permissions, config.forbiddenHost, `host_permission_forbidden:${target}`);
  assertArrayIncludes(manifest.host_permissions, "http://localhost/*", `localhost_host_permission_required:${target}`);

  const contentScripts = Array.isArray(manifest.content_scripts) ? manifest.content_scripts : [];
  const mainContentScript = contentScripts.find((script) => {
    return Array.isArray(script.js) && script.js.includes("content/content-script.js");
  });
  if (!mainContentScript) {
    throw new Error(`content_script_manifest_entry_required:${target}`);
  }
  assertArrayIncludes(mainContentScript.matches, config.requiredHost, `content_script_match_required:${target}`);
  assertArrayExcludes(mainContentScript.matches, config.forbiddenHost, `content_script_match_forbidden:${target}`);

  const contentScriptSize = statSync(join(distDir, "content", "content-script.js")).size;
  if (contentScriptSize > 300_000) {
    throw new Error(`content_script_too_large:${target}:${contentScriptSize}`);
  }

  const version = typeof manifest.version === "string" ? manifest.version : "unknown";
  const zipPath = join(outputDir, `${config.zipSlug}-${version}.zip`);
  assertFile(zipPath, `extension_zip_missing:${target}:${zipPath}`);

  const zipEntries = listZipEntries(zipPath);
  for (const fileName of requiredDistFiles) {
    assertArrayIncludes(zipEntries, fileName, `extension_zip_entry_missing:${target}:${fileName}`);
  }

  return {
    target,
    manifest_version: manifest.manifest_version,
    version,
    content_script_size: contentScriptSize,
    zip_path: zipPath,
    zip_entries: zipEntries.length
  };
}

function resolveTargets(target) {
  if (target === undefined) {
    return TARGETS;
  }

  if (TARGETS.includes(target)) {
    return [target];
  }

  throw new Error(`unsupported_extension_target:${target}`);
}

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

function assertArrayExcludes(value, forbidden, errorCode) {
  if (Array.isArray(value) && value.includes(forbidden)) {
    throw new Error(errorCode);
  }
}
