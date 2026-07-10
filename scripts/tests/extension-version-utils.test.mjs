import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  bumpManagedExtensionVersion,
  compareManagedExtensionVersions,
  loadExtensionVersionState,
  parseManagedExtensionVersion,
  validateManagedVersions
} from "../extension-version-utils.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

test("loads one managed version for every extension target", () => {
  const state = loadExtensionVersionState(repoRoot);

  assert.deepEqual(state.targets, ["amazon", "reddit", "instagram"]);
  assert.deepEqual(state.versions, {
    amazon: "0.2.0",
    reddit: "0.2.0",
    instagram: "0.2.0"
  });
});

test("accepts only the managed three-part Chrome-compatible version subset", () => {
  assert.deepEqual(parseManagedExtensionVersion("2.10.3"), [2, 10, 3]);
  for (const invalidVersion of [
    "0.0.0",
    "1",
    "1.0",
    "1.0.0.0",
    "1.01.0",
    "1.0.0-beta.1",
    "65536.0.0"
  ]) {
    assert.throws(() => parseManagedExtensionVersion(invalidVersion));
  }
});

test("requires version registry targets to exactly match extension targets", () => {
  assert.throws(() =>
    validateManagedVersions({ amazon: "1.0.0", reddit: "1.0.0" }, [
      "amazon",
      "reddit",
      "instagram"
    ])
  );
  assert.throws(() =>
    validateManagedVersions(
      { amazon: "1.0.0", reddit: "1.0.0", instagram: "1.0.0", extra: "1.0.0" },
      ["amazon", "reddit", "instagram"]
    )
  );
});

test("bumps one semantic segment and rejects overflow", () => {
  assert.equal(bumpManagedExtensionVersion("1.2.3", "major"), "2.0.0");
  assert.equal(bumpManagedExtensionVersion("1.2.3", "minor"), "1.3.0");
  assert.equal(bumpManagedExtensionVersion("1.2.3", "patch"), "1.2.4");
  assert.throws(() => bumpManagedExtensionVersion("65535.1.1", "major"));
  assert.throws(() => bumpManagedExtensionVersion("1.65535.1", "minor"));
  assert.throws(() => bumpManagedExtensionVersion("1.1.65535", "patch"));
});

test("compares managed versions numerically", () => {
  assert.equal(compareManagedExtensionVersions("1.10.0", "1.9.9"), 1);
  assert.equal(compareManagedExtensionVersions("1.2.3", "1.2.3"), 0);
  assert.equal(compareManagedExtensionVersions("0.9.9", "1.0.0"), -1);
});

test("CLI dry-run reports one independent bump without writing the registry", () => {
  const registryPath = resolve(repoRoot, "apps", "extension", "extension-versions.json");
  const before = readFileSync(registryPath, "utf8");
  const result = spawnSync(
    process.execPath,
    [
      "scripts/manage-extension-version.mjs",
      "bump",
      "--",
      "reddit",
      "patch",
      "--dry-run"
    ],
    { cwd: repoRoot, encoding: "utf8" }
  );

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), {
    command: "bump",
    current_version: "0.2.0",
    dry_run: true,
    next_version: "0.2.1",
    ok: true,
    target: "reddit"
  });
  assert.equal(readFileSync(registryPath, "utf8"), before);
});

test("CLI check rejects unexpected arguments", () => {
  const result = spawnSync(
    process.execPath,
    ["scripts/manage-extension-version.mjs", "check", "reddit"],
    { cwd: repoRoot, encoding: "utf8" }
  );

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /extension_version_command_arguments_invalid:check:reddit/);
});

test("CLI applies one independent bump with an atomic registry replacement", () => {
  const temporaryRoot = mkdtempSync(join(tmpdir(), "plugin-hub-extension-version-"));
  try {
    const temporaryExtensionDir = join(temporaryRoot, "apps", "extension");
    const temporaryScriptsDir = join(temporaryRoot, "scripts");
    mkdirSync(temporaryExtensionDir, { recursive: true });
    mkdirSync(temporaryScriptsDir, { recursive: true });
    copyFileSync(
      resolve(repoRoot, "apps", "extension", "extension-targets.json"),
      join(temporaryExtensionDir, "extension-targets.json")
    );
    copyFileSync(
      resolve(repoRoot, "apps", "extension", "extension-versions.json"),
      join(temporaryExtensionDir, "extension-versions.json")
    );
    copyFileSync(
      resolve(repoRoot, "scripts", "extension-version-utils.mjs"),
      join(temporaryScriptsDir, "extension-version-utils.mjs")
    );
    copyFileSync(
      resolve(repoRoot, "scripts", "manage-extension-version.mjs"),
      join(temporaryScriptsDir, "manage-extension-version.mjs")
    );

    const result = spawnSync(
      process.execPath,
      ["scripts/manage-extension-version.mjs", "bump", "amazon", "minor"],
      { cwd: temporaryRoot, encoding: "utf8" }
    );

    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(
      JSON.parse(readFileSync(join(temporaryExtensionDir, "extension-versions.json"), "utf8")),
      {
        amazon: "0.3.0",
        reddit: "0.2.0",
        instagram: "0.2.0"
      }
    );
    assert.deepEqual(JSON.parse(result.stdout), {
      command: "bump",
      current_version: "0.2.0",
      dry_run: false,
      next_version: "0.3.0",
      ok: true,
      target: "amazon"
    });
  } finally {
    rmSync(temporaryRoot, { force: true, recursive: true });
  }
});
