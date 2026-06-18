import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TARGETS = ["amazon", "reddit"];
const ZIP_SLUG_BY_TARGET = {
  amazon: "plugin-hub-amazon-voc",
  reddit: "plugin-hub-reddit-voc"
};

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
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
  const version = typeof manifest.version === "string" ? manifest.version : "unknown";
  const zipPath = join(outputDir, `${ZIP_SLUG_BY_TARGET[target]}-${version}.zip`);

  rmSync(zipPath, { force: true });

  const result = spawnSync("zip", ["-r", "-q", zipPath, "."], {
    cwd: distDir,
    stdio: "inherit"
  });

  if (result.status !== 0) {
    throw new Error(`extension_zip_failed:${target}:${result.status ?? "unknown"}`);
  }

  console.log(zipPath);
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
