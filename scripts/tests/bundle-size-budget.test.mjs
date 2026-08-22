import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve, win32 } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import * as bundleSizeBudget from "../check-bundle-size-budget.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const checkerPath = resolve(repoRoot, "scripts", "check-bundle-size-budget.mjs");

test("CLI reports every Web and Extension metric when artifacts are within budget", () => {
  const fixtureRoot = createFixture();
  try {
    const result = runChecker(fixtureRoot);

    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(result.stdout), {
      ok: true,
      results: {
        extensions: [
          {
            content_script_gzip: 27,
            content_script_raw: 7,
            package_zip_raw: 3,
            popup_gzip: 25,
            popup_raw: 5,
            service_worker_raw: 6,
            target: "alpha",
            target_dist_raw: 18
          }
        ],
        units: "bytes",
        web: {
          page_client_raw: 11,
          route_loaded_js_gzip: 58,
          server_page_raw: 11
        }
      },
      schema_version: 1
    });
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI fails closed when an Extension metric exceeds its hard budget", () => {
  const fixtureRoot = createFixture();
  try {
    writeText(
      join(fixtureRoot, "apps", "extension", "dist", "alpha", "content", "content-script.js"),
      Buffer.alloc(101, "x")
    );

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_budget_exceeded:extension:alpha:content_script_raw:101:100",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI fails closed with a stable receipt when an expected output is missing", () => {
  const fixtureRoot = createFixture();
  try {
    rmSync(
      join(fixtureRoot, "apps", "extension", "dist", "alpha", "popup", "Popup.js")
    );

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_output_required:apps/extension/dist/alpha/popup/Popup.js",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("receipt paths normalize Windows separators to POSIX", () => {
  const windowsRelativePath = win32.relative(
    "C:\\repo",
    "C:\\repo\\apps\\extension\\dist\\alpha\\popup\\Popup.js"
  );

  assert.equal(typeof bundleSizeBudget.formatBundleSizeReceiptPath, "function");
  assert.equal(
    bundleSizeBudget.formatBundleSizeReceiptPath(windowsRelativePath, win32.sep),
    "apps/extension/dist/alpha/popup/Popup.js"
  );
});

test("CLI rejects duplicate Web route entries instead of double-counting them", () => {
  const fixtureRoot = createFixture();
  try {
    writeJson(join(fixtureRoot, "apps", "web", ".next", "app-build-manifest.json"), {
      pages: {
        "/page": [
          "static/chunks/runtime.js",
          "static/chunks/runtime.js",
          "static/chunks/app/page-abcd.js"
        ]
      }
    });

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_manifest_duplicate:/page:static/chunks/runtime.js",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI rejects duplicate Extension targets before measuring outputs", () => {
  const fixtureRoot = createFixture();
  try {
    writeJson(join(fixtureRoot, "apps", "extension", "extension-targets.json"), {
      targets: ["alpha", "alpha"],
      targetConfigs: {
        alpha: { packageSlug: "plugin-hub-alpha" }
      }
    });

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_extension_target_duplicate:alpha",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI rejects a budget manifest that omits a required hard limit", () => {
  const fixtureRoot = createFixture();
  try {
    const budgetPath = join(fixtureRoot, "bundle-size-budgets.json");
    const budgets = JSON.parse(readFileSync(budgetPath, "utf8"));
    delete budgets.extension.content_script_raw;
    writeJson(budgetPath, budgets);

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_budget_invalid:extension:content_script_raw",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI requires exactly one Web page client chunk", () => {
  const fixtureRoot = createFixture();
  try {
    writeJson(join(fixtureRoot, "apps", "web", ".next", "app-build-manifest.json"), {
      pages: {
        "/page": ["static/chunks/runtime.js"]
      }
    });

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_web_page_chunk_count_invalid:0",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI fails closed when a Web metric exceeds its hard budget", () => {
  const fixtureRoot = createFixture();
  try {
    const budgetPath = join(fixtureRoot, "bundle-size-budgets.json");
    const budgets = JSON.parse(readFileSync(budgetPath, "utf8"));
    budgets.web.route_loaded_js_gzip = 57;
    writeJson(budgetPath, budgets);

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_budget_exceeded:web:route_loaded_js_gzip:58:57",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI rejects an unsupported budget schema version", () => {
  const fixtureRoot = createFixture();
  try {
    const budgetPath = join(fixtureRoot, "bundle-size-budgets.json");
    const budgets = JSON.parse(readFileSync(budgetPath, "utf8"));
    budgets.schema_version = 2;
    writeJson(budgetPath, budgets);

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_budget_schema_unsupported:2",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI rejects budget units other than decimal bytes", () => {
  const fixtureRoot = createFixture();
  try {
    const budgetPath = join(fixtureRoot, "bundle-size-budgets.json");
    const budgets = JSON.parse(readFileSync(budgetPath, "utf8"));
    budgets.units = "kib";
    writeJson(budgetPath, budgets);

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_budget_units_unsupported:kib",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

test("CLI rejects Web manifest paths that escape the build directory", () => {
  const fixtureRoot = createFixture();
  try {
    writeText(join(fixtureRoot, "apps", "outside.js"), "outside");
    writeJson(join(fixtureRoot, "apps", "web", ".next", "app-build-manifest.json"), {
      pages: {
        "/page": [
          "../../outside.js",
          "static/chunks/app/page-abcd.js"
        ]
      }
    });

    const result = runChecker(fixtureRoot);

    assert.notEqual(result.status, 0);
    assert.deepEqual(JSON.parse(result.stderr), {
      error: "bundle_size_manifest_path_invalid:../../outside.js",
      ok: false
    });
    assert.equal(result.stdout, "");
  } finally {
    rmSync(fixtureRoot, { force: true, recursive: true });
  }
});

function runChecker(fixtureRoot) {
  return spawnSync(
    process.execPath,
    [
      checkerPath,
      "--repo-root",
      fixtureRoot,
      "--budget-file",
      join(fixtureRoot, "bundle-size-budgets.json")
    ],
    { cwd: repoRoot, encoding: "utf8" }
  );
}

function createFixture() {
  const fixtureRoot = mkdtempSync(join(tmpdir(), "plugin-hub-bundle-budget-"));
  writeJson(join(fixtureRoot, "bundle-size-budgets.json"), {
    schema_version: 1,
    units: "bytes",
    web: {
      route_loaded_js_gzip: 100,
      page_client_raw: 100,
      server_page_raw: 100
    },
    extension: {
      content_script_raw: 100,
      content_script_gzip: 100,
      popup_raw: 100,
      popup_gzip: 100,
      service_worker_raw: 100,
      target_dist_raw: 100,
      package_zip_raw: 100
    }
  });
  writeJson(join(fixtureRoot, "apps", "extension", "extension-targets.json"), {
    targets: ["alpha"],
    targetConfigs: {
      alpha: { packageSlug: "plugin-hub-alpha" }
    }
  });
  writeJson(join(fixtureRoot, "apps", "extension", "extension-versions.json"), {
    alpha: "1.2.3"
  });
  writeJson(join(fixtureRoot, "apps", "web", ".next", "app-build-manifest.json"), {
    pages: {
      "/page": [
        "static/chunks/runtime.js",
        "static/chunks/app/page-abcd.js"
      ]
    }
  });
  writeText(join(fixtureRoot, "apps", "web", ".next", "static", "chunks", "runtime.js"), "runtime");
  writeText(
    join(fixtureRoot, "apps", "web", ".next", "static", "chunks", "app", "page-abcd.js"),
    "page-client"
  );
  writeText(join(fixtureRoot, "apps", "web", ".next", "server", "app", "page.js"), "server-page");
  writeText(
    join(fixtureRoot, "apps", "extension", "dist", "alpha", "content", "content-script.js"),
    "content"
  );
  writeText(
    join(fixtureRoot, "apps", "extension", "dist", "alpha", "popup", "Popup.js"),
    "popup"
  );
  writeText(
    join(fixtureRoot, "apps", "extension", "dist", "alpha", "background", "service-worker.js"),
    "worker"
  );
  writeText(join(fixtureRoot, "tmp", "outputs", "plugin-hub-alpha-1.2.3.zip"), "zip");
  return fixtureRoot;
}

function writeJson(filePath, value) {
  writeText(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function writeText(filePath, value) {
  mkdirSync(dirname(filePath), { recursive: true });
  writeFileSync(filePath, value);
}
