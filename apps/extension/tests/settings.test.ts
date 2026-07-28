import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_API_BASE_URL,
  clearPendingCollectionUpload,
  loadPendingCollectionUpload,
  normalizeApiBaseUrl,
  normalizeApiKey,
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
      apiBaseUrl: "https://api.example.com",
      capture: {
        payload: { captured_at: "2026-07-28T00:00:00.000Z" },
        summary: { platform: "amazon" }
      }
    } as unknown as PendingCollectionUpload;

    await savePendingCollectionUpload(original);
    const restored = await loadPendingCollectionUpload();
    const capture = vi.fn().mockResolvedValue({ apiBaseUrl: "https://other.example.com" });
    const retried = await resolvePendingUpload(restored, capture);
    const retargeted = retargetPendingCollectionUpload(
      retried,
      " https://corrected.example.com/// "
    );

    expect(capture).not.toHaveBeenCalled();
    expect(retried).toEqual(original);
    expect(retargeted.apiBaseUrl).toBe("https://corrected.example.com");
    expect(retargeted.capture).toBe(original.capture);
    await clearPendingCollectionUpload();
    await expect(loadPendingCollectionUpload()).resolves.toBeNull();
  });
});
