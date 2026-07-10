import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadExtensionVersionState } from "./extension-version-utils.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const versionState = loadExtensionVersionState(repoRoot);
const targetConfigs = versionState.targetConfigs;
const targetsInRegistry = versionState.targets;
const outputDir = join(repoRoot, "tmp", "outputs");
const targets = resolveTargets(process.argv[2]);

mkdirSync(outputDir, { recursive: true });

for (const target of targets) {
  const distDir = join(repoRoot, "apps", "extension", "dist", target);
  const manifestPath = join(distDir, "manifest.json");

  if (!existsSync(manifestPath)) {
    throw new Error(`extension_dist_manifest_required:${target}`);
  }

  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const version = versionState.versions[target];
  if (manifest.version !== version) {
    throw new Error(
      `extension_manifest_version_mismatch:${target}:${version}:${String(manifest.version)}`
    );
  }
  const packageSlug = targetConfig(target).packageSlug;
  const zipPath = join(outputDir, `${packageSlug}-${version}.zip`);
  const unpackedPath = join(outputDir, `${packageSlug}-${version}-unpacked`);

  rmSync(zipPath, { force: true });
  rmSync(unpackedPath, { recursive: true, force: true });
  cpSync(distDir, unpackedPath, { recursive: true });

  const result = spawnSync("zip", ["-r", "-q", zipPath, "."], {
    cwd: distDir,
    stdio: "inherit"
  });

  if (result.status !== 0) {
    throw new Error(`extension_zip_failed:${target}:${result.status ?? "unknown"}`);
  }

  console.log(zipPath);
  console.log(unpackedPath);
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
  if (!config || typeof config.packageSlug !== "string") {
    throw new Error(`extension_target_config_required:${target}`);
  }
  return config;
}
