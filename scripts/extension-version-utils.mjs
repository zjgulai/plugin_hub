import { readFileSync } from "node:fs";
import { join } from "node:path";

const RELEASE_TYPES = new Set(["major", "minor", "patch"]);

export function loadExtensionVersionState(repoRoot) {
  const targetRegistryPath = join(repoRoot, "apps", "extension", "extension-targets.json");
  const versionRegistryPath = join(repoRoot, "apps", "extension", "extension-versions.json");
  const targetRegistry = readJson(targetRegistryPath);
  const rawVersions = readJson(versionRegistryPath);
  const targets = validateTargets(targetRegistry.targets);
  const targetConfigs = validateTargetConfigs(targetRegistry.targetConfigs, targets);
  const versions = validateManagedVersions(rawVersions, targets);

  return {
    targetConfigs,
    targets,
    versions,
    versionRegistryPath
  };
}

export function validateManagedVersions(value, targets) {
  if (!isRecord(value)) {
    throw new Error("extension_version_registry_required");
  }

  const expectedTargets = [...targets].sort();
  const actualTargets = Object.keys(value).sort();
  if (
    expectedTargets.length !== actualTargets.length ||
    expectedTargets.some((target, index) => target !== actualTargets[index])
  ) {
    throw new Error(
      `extension_version_targets_mismatch:${expectedTargets.join(",")}:${actualTargets.join(",")}`
    );
  }

  return Object.fromEntries(
    targets.map((target) => [target, formatManagedExtensionVersion(value[target], target)])
  );
}

export function parseManagedExtensionVersion(value, label = "version") {
  if (typeof value !== "string") {
    throw new Error(`extension_version_required:${label}`);
  }

  const parts = value.split(".");
  if (parts.length !== 3) {
    throw new Error(`extension_version_must_be_semver:${label}:${value}`);
  }

  const numbers = parts.map((part) => {
    if (!/^(0|[1-9]\d*)$/.test(part)) {
      throw new Error(`extension_version_segment_invalid:${label}:${value}`);
    }
    const number = Number(part);
    if (number > 65_535) {
      throw new Error(`extension_version_segment_overflow:${label}:${value}`);
    }
    return number;
  });

  if (numbers.every((number) => number === 0)) {
    throw new Error(`extension_version_all_zero:${label}:${value}`);
  }

  return numbers;
}

export function formatManagedExtensionVersion(value, label = "version") {
  return parseManagedExtensionVersion(value, label).join(".");
}

export function compareManagedExtensionVersions(left, right) {
  const leftParts = parseManagedExtensionVersion(left, "left");
  const rightParts = parseManagedExtensionVersion(right, "right");

  for (let index = 0; index < leftParts.length; index += 1) {
    const difference = leftParts[index] - rightParts[index];
    if (difference !== 0) {
      return Math.sign(difference);
    }
  }
  return 0;
}

export function bumpManagedExtensionVersion(currentVersion, releaseType) {
  if (!RELEASE_TYPES.has(releaseType)) {
    throw new Error(`extension_version_release_type_invalid:${String(releaseType)}`);
  }

  const parts = parseManagedExtensionVersion(currentVersion, "current");
  const index = releaseType === "major" ? 0 : releaseType === "minor" ? 1 : 2;
  if (parts[index] === 65_535) {
    throw new Error(`extension_version_bump_overflow:${releaseType}:${currentVersion}`);
  }

  parts[index] += 1;
  for (let resetIndex = index + 1; resetIndex < parts.length; resetIndex += 1) {
    parts[resetIndex] = 0;
  }

  return parts.join(".");
}

function validateTargets(value) {
  if (
    !Array.isArray(value) ||
    value.length === 0 ||
    value.some((target) => typeof target !== "string" || target.length === 0) ||
    new Set(value).size !== value.length
  ) {
    throw new Error("extension_targets_invalid");
  }
  return value;
}

function validateTargetConfigs(value, targets) {
  if (!isRecord(value) || targets.some((target) => !isRecord(value[target]))) {
    throw new Error("extension_target_configs_invalid");
  }
  return value;
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
