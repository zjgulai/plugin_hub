import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(repoRoot, "apps", "extension", "dist");
const manifestPath = join(distDir, "manifest.json");
const outputDir = join(repoRoot, "tmp", "outputs");

if (!existsSync(manifestPath)) {
  throw new Error("extension_dist_manifest_required");
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const version = typeof manifest.version === "string" ? manifest.version : "unknown";
const zipPath = join(outputDir, `plugin-hub-extension-${version}.zip`);

mkdirSync(outputDir, { recursive: true });
rmSync(zipPath, { force: true });

const result = spawnSync("zip", ["-r", "-q", zipPath, "."], {
  cwd: distDir,
  stdio: "inherit"
});

if (result.status !== 0) {
  throw new Error(`extension_zip_failed:${result.status ?? "unknown"}`);
}

console.log(zipPath);
