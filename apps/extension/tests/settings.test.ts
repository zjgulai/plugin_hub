import { describe, expect, it } from "vitest";

import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "../src/lib/settings";

describe("extension settings", () => {
  it("normalizes API base URLs", () => {
    expect(normalizeApiBaseUrl(" http://localhost:8000/// ")).toBe("http://localhost:8000");
    expect(normalizeApiBaseUrl("")).toBe(DEFAULT_API_BASE_URL);
  });

  it("rejects non-http API base URLs", () => {
    expect(() => normalizeApiBaseUrl("plugin-hub.local")).toThrow("api_base_url_invalid");
    expect(() => normalizeApiBaseUrl("file:///tmp/plugin-hub")).toThrow("api_base_url_must_be_http");
  });
});
