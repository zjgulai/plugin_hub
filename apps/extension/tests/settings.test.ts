import { describe, expect, it } from "vitest";

import {
  DEFAULT_API_BASE_URL,
  normalizeApiBaseUrl,
  normalizeApiKey
} from "../src/lib/settings";

describe("extension settings", () => {
  it("defaults packaged collectors to the production Plugin Hub API", () => {
    expect(DEFAULT_API_BASE_URL).toBe("https://plugin.lute-tlz-dddd.top");
  });

  it("normalizes API base URLs", () => {
    expect(normalizeApiBaseUrl(" http://localhost:8000/// ")).toBe("http://localhost:8000");
    expect(normalizeApiBaseUrl("")).toBe(DEFAULT_API_BASE_URL);
  });

  it("rejects non-http API base URLs", () => {
    expect(() => normalizeApiBaseUrl("plugin-hub.local")).toThrow("api_base_url_invalid");
    expect(() => normalizeApiBaseUrl("file:///tmp/plugin-hub")).toThrow("api_base_url_must_be_http");
  });

  it("normalizes API keys without accepting weak non-empty values", () => {
    expect(normalizeApiKey(" ")).toBe("");
    expect(normalizeApiKey(` ${"k".repeat(32)} `)).toBe("k".repeat(32));
    expect(() => normalizeApiKey("too-short")).toThrow("api_key_too_short");
  });
});
