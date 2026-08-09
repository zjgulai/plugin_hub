import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_API_BASE_URL,
  clearPendingCollectionUpload,
  loadPendingCollectionUpload,
  normalizeApiBaseUrl,
  normalizeApiKey,
  normalizeTrustedApiBaseUrl,
  retargetPendingCollectionUpload,
  resolvePendingUpload,
  savePendingCollectionUpload,
  type PendingCollectionUpload
} from "../src/lib/settings";

afterEach(() => {
  vi.unstubAllGlobals();
});

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

  it("allows only the production API and explicit loopback development origins", () => {
    expect(normalizeTrustedApiBaseUrl("https://plugin.lute-tlz-dddd.top/")).toBe(
      "https://plugin.lute-tlz-dddd.top"
    );
    expect(normalizeTrustedApiBaseUrl("http://localhost:8000///")).toBe(
      "http://localhost:8000"
    );
    expect(normalizeTrustedApiBaseUrl("http://127.0.0.1:9000")).toBe(
      "http://127.0.0.1:9000"
    );
    expect(() => normalizeTrustedApiBaseUrl("https://www.amazon.com")).toThrow(
      "api_base_url_untrusted"
    );
    expect(() => normalizeTrustedApiBaseUrl("https://api.example.com")).toThrow(
      "api_base_url_untrusted"
    );
    expect(() =>
      normalizeTrustedApiBaseUrl("https://plugin.lute-tlz-dddd.top/proxy")
    ).toThrow("api_base_url_untrusted");
  });

  it("normalizes API keys without accepting weak non-empty values", () => {
    expect(normalizeApiKey(" ")).toBe("");
    expect(normalizeApiKey(` ${"k".repeat(32)} `)).toBe("k".repeat(32));
    expect(() => normalizeApiKey("too-short")).toThrow("api_key_too_short");
  });

  it("restores the same pending payload after a popup restart and clears it after success", async () => {
    const sessionStore: Record<string, unknown> = {};
    vi.stubGlobal("chrome", {
      storage: {
        session: {
          get: vi.fn(async (key: string) => ({ [key]: sessionStore[key] })),
          set: vi.fn(async (values: Record<string, unknown>) => Object.assign(sessionStore, values)),
          remove: vi.fn(async (key: string) => {
            delete sessionStore[key];
          })
        }
      }
    });
    const original = {
      apiBaseUrl: "http://localhost:8000",
      capture: {
        payload: { captured_at: "2026-07-28T00:00:00.000Z" },
        summary: { platform: "amazon" }
      }
    } as unknown as PendingCollectionUpload;

    await savePendingCollectionUpload(original);
    const restored = await loadPendingCollectionUpload();
    const capture = vi.fn().mockResolvedValue({ apiBaseUrl: "http://localhost:9000" });
    const retried = await resolvePendingUpload(restored, capture);
    const retargeted = retargetPendingCollectionUpload(
      retried,
      " http://127.0.0.1:9000/// "
    );

    expect(capture).not.toHaveBeenCalled();
    expect(retried).toEqual(original);
    expect(retargeted.apiBaseUrl).toBe("http://127.0.0.1:9000");
    expect(retargeted.capture).toBe(original.capture);
    await clearPendingCollectionUpload();
    await expect(loadPendingCollectionUpload()).resolves.toBeNull();
  });
});
