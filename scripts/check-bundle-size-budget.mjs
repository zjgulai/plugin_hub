import {
  readFileSync,
  readdirSync,
  statSync
} from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

import { loadExtensionVersionState } from "./extension-version-utils.mjs";

const defaultRepoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WEB_METRICS = [
  "route_loaded_js_gzip",
  "page_client_raw",
  "server_page_raw"
];
const EXTENSION_METRICS = [
  "content_script_raw",
  "content_script_gzip",
  "popup_raw",
  "popup_gzip",
  "service_worker_raw",
  "target_dist_raw",
  "package_zip_raw"
];

export function formatBundleSizeReceiptPath(pathValue, nativeSeparator = sep) {
  return nativeSeparator === "/" ? pathValue : pathValue.split(nativeSeparator).join("/");
}

export function collectBundleSizeResults(repoRoot) {
  const webNextDir = join(repoRoot, "apps", "web", ".next");
  const appBuildManifest = readJson(join(webNextDir, "app-build-manifest.json"));
  const routeFiles = appBuildManifest.pages["/page"];
  for (const filePath of routeFiles) {
    if (typeof filePath !== "string") {
      throw new Error(`bundle_size_manifest_path_invalid:${String(filePath)}`);
    }
    const relativePath = relative(webNextDir, resolve(webNextDir, filePath));
    if (
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) {
      throw new Error(`bundle_size_manifest_path_invalid:${String(filePath)}`);
    }
  }
  const duplicateRouteFile = routeFiles.find(
    (filePath, index) => routeFiles.indexOf(filePath) !== index
  );
  if (duplicateRouteFile) {
    throw new Error(`bundle_size_manifest_duplicate:/page:${duplicateRouteFile}`);
  }
  const routeJsFiles = routeFiles.filter((filePath) => filePath.endsWith(".js"));
  const pageClientFiles = routeJsFiles.filter((filePath) =>
    /^static\/chunks\/app\/page-[^/]+\.js$/.test(filePath)
  );
  if (pageClientFiles.length !== 1) {
    throw new Error(
      `bundle_size_web_page_chunk_count_invalid:${pageClientFiles.length}`
    );
  }
  const web = {
    route_loaded_js_gzip: routeJsFiles.reduce(
      (total, filePath) => total + gzipSize(repoRoot, join(webNextDir, filePath)),
      0
    ),
    page_client_raw: fileSize(repoRoot, join(webNextDir, pageClientFiles[0])),
    server_page_raw: fileSize(repoRoot, join(webNextDir, "server", "app", "page.js"))
  };

  assertUniqueExtensionTargets(repoRoot);
  const versionState = loadExtensionVersionState(repoRoot);
  const extensions = versionState.targets.map((target) => {
    const distDir = join(repoRoot, "apps", "extension", "dist", target);
    const contentScriptPath = join(distDir, "content", "content-script.js");
    const popupPath = join(distDir, "popup", "Popup.js");
    const serviceWorkerPath = join(distDir, "background", "service-worker.js");
    const packageSlug = versionState.targetConfigs[target].packageSlug;
    const packagePath = join(
      repoRoot,
      "tmp",
      "outputs",
      `${packageSlug}-${versionState.versions[target]}.zip`
    );

    return {
      target,
      content_script_raw: fileSize(repoRoot, contentScriptPath),
      content_script_gzip: gzipSize(repoRoot, contentScriptPath),
      popup_raw: fileSize(repoRoot, popupPath),
      popup_gzip: gzipSize(repoRoot, popupPath),
      service_worker_raw: fileSize(repoRoot, serviceWorkerPath),
      target_dist_raw: directorySize(repoRoot, distDir),
      package_zip_raw: fileSize(repoRoot, packagePath)
    };
  });

  return {
    units: "bytes",
    web,
    extensions
  };
}

function assertUniqueExtensionTargets(repoRoot) {
  const registry = readJson(
    join(repoRoot, "apps", "extension", "extension-targets.json")
  );
  if (!Array.isArray(registry.targets)) {
    return;
  }
  const seenTargets = new Set();
  for (const target of registry.targets) {
    if (seenTargets.has(target)) {
      throw new Error(`bundle_size_extension_target_duplicate:${String(target)}`);
    }
    seenTargets.add(target);
  }
}

function runCli() {
  const options = parseArguments(process.argv.slice(2));
  const budgets = readJson(options.budgetFile);
  validateBudgets(budgets);
  const results = collectBundleSizeResults(options.repoRoot);
  enforceBudgets(results, budgets);
  process.stdout.write(
    `${JSON.stringify({ ok: true, results, schema_version: 1 }, null, 2)}\n`
  );
}

function validateBudgets(budgets) {
  if (budgets?.schema_version !== 1) {
    throw new Error(
      `bundle_size_budget_schema_unsupported:${String(budgets?.schema_version)}`
    );
  }
  if (budgets.units !== "bytes") {
    throw new Error(
      `bundle_size_budget_units_unsupported:${String(budgets.units)}`
    );
  }
  for (const metric of WEB_METRICS) {
    assertBudgetValue(budgets?.web?.[metric], "web", metric);
  }
  for (const metric of EXTENSION_METRICS) {
    assertBudgetValue(budgets?.extension?.[metric], "extension", metric);
  }
}

function assertBudgetValue(value, scope, metric) {
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`bundle_size_budget_invalid:${scope}:${metric}`);
  }
}

function enforceBudgets(results, budgets) {
  for (const metric of WEB_METRICS) {
    assertWithinBudget("web", metric, results.web[metric], budgets.web[metric]);
  }
  for (const extension of results.extensions) {
    for (const metric of EXTENSION_METRICS) {
      assertWithinBudget(
        `extension:${extension.target}`,
        metric,
        extension[metric],
        budgets.extension[metric]
      );
    }
  }
}

function assertWithinBudget(scope, metric, actual, budget) {
  if (actual > budget) {
    throw new Error(
      `bundle_size_budget_exceeded:${scope}:${metric}:${actual}:${budget}`
    );
  }
}

function parseArguments(argumentsList) {
  let repoRoot = defaultRepoRoot;
  let budgetFile = join(defaultRepoRoot, "scripts", "bundle-size-budgets.json");

  for (let index = 0; index < argumentsList.length; index += 2) {
    const flag = argumentsList[index];
    const value = argumentsList[index + 1];
    if (flag === "--repo-root" && value) {
      repoRoot = resolve(value);
    } else if (flag === "--budget-file" && value) {
      budgetFile = resolve(value);
    } else {
      throw new Error(`bundle_size_arguments_invalid:${argumentsList.join(":")}`);
    }
  }

  return { budgetFile, repoRoot };
}

function directorySize(repoRoot, directoryPath) {
  return readdirSync(directoryPath, { withFileTypes: true }).reduce((total, entry) => {
    const entryPath = join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      return total + directorySize(repoRoot, entryPath);
    }
    return total + fileSize(repoRoot, entryPath);
  }, 0);
}

function fileSize(repoRoot, filePath) {
  let stats;
  try {
    stats = statSync(filePath);
  } catch {
    throw new Error(
      `bundle_size_output_required:${formatBundleSizeReceiptPath(relative(repoRoot, filePath))}`
    );
  }
  if (!stats.isFile()) {
    throw new Error(
      `bundle_size_output_required:${formatBundleSizeReceiptPath(relative(repoRoot, filePath))}`
    );
  }
  return stats.size;
}

function gzipSize(repoRoot, filePath) {
  fileSize(repoRoot, filePath);
  return gzipSync(readFileSync(filePath)).byteLength;
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    runCli();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${JSON.stringify({ error: message, ok: false })}\n`);
    process.exitCode = 1;
  }
}
