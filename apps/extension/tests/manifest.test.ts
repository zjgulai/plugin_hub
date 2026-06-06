import { describe, expect, it } from "vitest";

import manifest from "../manifest.config";

describe("extension manifest", () => {
  it("declares install and toolbar icons", () => {
    expect(manifest.icons).toEqual({
      "16": "icons/icon-16.png",
      "32": "icons/icon-32.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    });
    expect(manifest.action?.default_icon).toEqual(manifest.icons);
  });

  it("allows local API hosts without pinning a single port", () => {
    expect(manifest.host_permissions).toContain("http://localhost/*");
    expect(manifest.host_permissions).toContain("http://127.0.0.1/*");
    expect(manifest.host_permissions).not.toContain("http://localhost:8000/*");
  });

  it("keeps permissions scoped to the implemented browser APIs", () => {
    expect(manifest.permissions).toEqual(["activeTab", "storage"]);
  });
});
