import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadExtensionVersionState } from "./extension-version-utils.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const versionState = loadExtensionVersionState(repoRoot);
const targetConfigs = versionState.targetConfigs;
const targetsInRegistry = versionState.targets;
const outputDir = join(repoRoot, "tmp", "outputs");
const targets = resolveTargets(process.argv[2]);

const baseRequiredDistFiles = [
  "manifest.json",
  "content/content-script.js",
  "background/service-worker.js",
  "popup/index.html",
  "popup/Popup.js"
];

const results = [];

for (const target of targets) {
  results.push(verifyTarget(target));
}

console.log(JSON.stringify({ ok: true, results }, null, 2));

function verifyTarget(target) {
  const config = targetConfig(target);
  const verifyConfig = config.verify ?? {};
  const distDir = join(repoRoot, "apps", "extension", "dist", target);
  const manifestPath = join(distDir, "manifest.json");

  for (const fileName of baseRequiredDistFiles) {
    assertFile(join(distDir, fileName), `extension_dist_missing:${target}:${fileName}`);
  }

  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const iconFileNames = manifestIconFiles(manifest, target);
  const requiredDistFiles = [...baseRequiredDistFiles, ...iconFileNames];
  for (const fileName of iconFileNames) {
    assertFile(join(distDir, fileName), `extension_dist_missing:${target}:${fileName}`);
  }

  assertEqual(manifest.manifest_version, 3, `manifest_version_must_be_3:${target}`);
  assertEqual(manifest.name, config.name, `manifest_name_changed:${target}`);
  assertEqual(
    manifest.version,
    versionState.versions[target],
    `manifest_version_changed:${target}`
  );
  assertArrayIncludes(manifest.permissions, "activeTab", `permission_activeTab_required:${target}`);
  assertArrayIncludes(manifest.permissions, "storage", `permission_storage_required:${target}`);
  for (const sourceMatch of config.contentMatches) {
    assertArrayExcludes(
      manifest.host_permissions,
      sourceMatch,
      `source_host_fetch_permission_forbidden:${target}:${sourceMatch}`
    );
  }
  for (const forbiddenHost of verifyConfig.forbiddenHosts) {
    assertArrayExcludes(manifest.host_permissions, forbiddenHost, `host_permission_forbidden:${target}`);
  }
  for (const apiHostPermission of verifyConfig.requiredApiHostPermissions) {
    assertArrayIncludes(
      manifest.host_permissions,
      apiHostPermission,
      `api_host_permission_required:${target}:${apiHostPermission}`
    );
  }

  const contentScripts = Array.isArray(manifest.content_scripts) ? manifest.content_scripts : [];
  const mainContentScript = contentScripts.find((script) => {
    return Array.isArray(script.js) && script.js.includes("content/content-script.js");
  });
  if (!mainContentScript) {
    throw new Error(`content_script_manifest_entry_required:${target}`);
  }
  assertArrayIncludes(mainContentScript.matches, verifyConfig.requiredHost, `content_script_match_required:${target}`);
  for (const forbiddenHost of verifyConfig.forbiddenHosts) {
    assertArrayExcludes(mainContentScript.matches, forbiddenHost, `content_script_match_forbidden:${target}`);
  }

  const contentScriptSize = statSync(join(distDir, "content", "content-script.js")).size;
  if (contentScriptSize > 300_000) {
    throw new Error(`content_script_too_large:${target}:${contentScriptSize}`);
  }

  const version = versionState.versions[target];
  const zipPath = join(outputDir, `${config.packageSlug}-${version}.zip`);
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
    return targetsInRegistry;
  }

  if (targetsInRegistry.includes(target)) {
    return [target];
  }

  throw new Error(`unsupported_extension_target:${target}`);
}

function targetConfig(target) {
  const config = targetConfigs[target];
  if (
    !config ||
    typeof config.name !== "string" ||
    typeof config.packageSlug !== "string" ||
    !Array.isArray(config.contentMatches) ||
    typeof config.verify?.requiredHost !== "string" ||
    !Array.isArray(config.verify?.forbiddenHosts) ||
    !Array.isArray(config.verify?.requiredApiHostPermissions)
  ) {
    throw new Error(`extension_target_config_required:${target}`);
  }
  return config;
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

function manifestIconFiles(manifest, target) {
  const iconPaths = [
    ...iconMapValues(manifest.icons, `manifest_icons_required:${target}`),
    ...iconMapValues(manifest.action?.default_icon, `manifest_action_icons_required:${target}`)
  ];
  const uniqueIconPaths = [...new Set(iconPaths)];
  if (uniqueIconPaths.length < 4) {
    throw new Error(`manifest_icon_paths_incomplete:${target}`);
  }
  return uniqueIconPaths;
}

function iconMapValues(value, errorCode) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(errorCode);
  }
  return ["16", "32", "48", "128"].map((size) => {
    const iconPath = value[size];
    if (typeof iconPath !== "string" || !iconPath.endsWith(`icon-${size}.png`)) {
      throw new Error(`${errorCode}:${size}`);
    }
    return iconPath;
  });
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
