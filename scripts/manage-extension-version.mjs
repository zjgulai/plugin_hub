import { renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  bumpManagedExtensionVersion,
  loadExtensionVersionState,
  validateManagedVersions
} from "./extension-version-utils.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const state = loadExtensionVersionState(repoRoot);
const [command = "list", ...args] = process.argv.slice(2);

if (command === "list" || command === "check") {
  if (args.length > 0) {
    throw new Error(`extension_version_command_arguments_invalid:${command}:${args.join(",")}`);
  }
  printResult({ command, ok: true, versions: state.versions });
} else if (command === "bump") {
  bumpVersion(args);
} else {
  throw new Error(`extension_version_command_invalid:${command}`);
}

function bumpVersion(args) {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const [target, releaseType, ...flags] = normalizedArgs;
  const unknownFlags = flags.filter((flag) => flag !== "--dry-run");
  if (!state.targets.includes(target)) {
    throw new Error(`unsupported_extension_target:${String(target)}`);
  }
  if (unknownFlags.length > 0) {
    throw new Error(`extension_version_flag_invalid:${unknownFlags.join(",")}`);
  }

  const currentVersion = state.versions[target];
  const nextVersion = bumpManagedExtensionVersion(currentVersion, releaseType);
  const nextVersions = Object.fromEntries(
    state.targets.map((candidate) => [
      candidate,
      candidate === target ? nextVersion : state.versions[candidate]
    ])
  );
  validateManagedVersions(nextVersions, state.targets);

  const dryRun = flags.includes("--dry-run");
  if (!dryRun) {
    writeJsonAtomically(state.versionRegistryPath, nextVersions);
  }

  printResult({
    command,
    current_version: currentVersion,
    dry_run: dryRun,
    next_version: nextVersion,
    ok: true,
    target
  });
}

function writeJsonAtomically(filePath, value) {
  const temporaryPath = `${filePath}.${process.pid}.tmp`;
  try {
    writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
    renameSync(temporaryPath, filePath);
  } finally {
    rmSync(temporaryPath, { force: true });
  }
}

function printResult(value) {
  console.log(JSON.stringify(value, null, 2));
}
