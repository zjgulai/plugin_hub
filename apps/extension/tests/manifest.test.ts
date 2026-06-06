import { describe, expect, it } from "vitest";

import manifest from "../manifest.config";

describe("extension manifest", () => {
  it("allows local API hosts without pinning a single port", () => {
    expect(manifest.host_permissions).toContain("http://localhost/*");
    expect(manifest.host_permissions).toContain("http://127.0.0.1/*");
    expect(manifest.host_permissions).not.toContain("http://localhost:8000/*");
  });
});
