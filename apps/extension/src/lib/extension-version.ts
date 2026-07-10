import versionRegistry from "../../extension-versions.json";

import { EXTENSION_TARGETS, type ExtensionTarget } from "./extension-target";

type ExtensionVersionRegistry = Record<ExtensionTarget, string>;

const versions = validateExtensionVersionRegistry(versionRegistry);

export function extensionVersion(target: ExtensionTarget): string {
  const version = versions[target];
  assertManagedExtensionVersion(version, target);
  return version;
}

export function assertManagedExtensionVersion(value: unknown, target: string): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(`extension_version_required:${target}`);
  }

  const parts = value.split(".");
  if (parts.length !== 3) {
    throw new Error(`extension_version_must_be_semver:${target}:${value}`);
  }

  const numbers = parts.map((part) => {
    if (!/^(0|[1-9]\d*)$/.test(part)) {
      throw new Error(`extension_version_segment_invalid:${target}:${value}`);
    }
    const number = Number(part);
    if (number > 65_535) {
      throw new Error(`extension_version_segment_overflow:${target}:${value}`);
    }
    return number;
  });

  if (numbers.every((number) => number === 0)) {
    throw new Error(`extension_version_all_zero:${target}:${value}`);
  }
}

function validateExtensionVersionRegistry(value: Record<string, unknown>): ExtensionVersionRegistry {
  const expectedTargets = [...EXTENSION_TARGETS].sort();
  const actualTargets = Object.keys(value).sort();
  if (
    expectedTargets.length !== actualTargets.length ||
    expectedTargets.some((target, index) => target !== actualTargets[index])
  ) {
    throw new Error(
      `extension_version_targets_mismatch:${expectedTargets.join(",")}:${actualTargets.join(",")}`
    );
  }

  for (const target of EXTENSION_TARGETS) {
    assertManagedExtensionVersion(value[target], target);
  }
  return value as ExtensionVersionRegistry;
}
