import { describe, expect, it } from "vitest";

import { apiFetcherWithKey, loadApiAccessKeys } from "../src/lib/api-auth";
import type { ApiFetcher } from "../src/lib/api";

describe("server-side API auth", () => {
  it("loads distinct read and write keys without placing them in dashboard config", () => {
    expect(
      loadApiAccessKeys({
        PLUGIN_HUB_API_READ_KEY: ` ${"r".repeat(32)} `,
        PLUGIN_HUB_API_WRITE_KEY: ` ${"w".repeat(32)} `
      })
    ).toEqual({
      readKey: "r".repeat(32),
      writeKey: "w".repeat(32)
    });
  });

  it("adds the API key header while preserving request options", async () => {
    let capturedInit: RequestInit | undefined;
    const baseFetcher: ApiFetcher = async (_url, init) => {
      capturedInit = init;
      return { ok: true, status: 200, json: async () => ({}) };
    };

    await apiFetcherWithKey("k".repeat(32), baseFetcher)("https://api.example.com/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });

    const headers = new Headers(capturedInit?.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Plugin-Hub-Api-Key")).toBe("k".repeat(32));
    expect(capturedInit?.method).toBe("POST");
    expect(capturedInit?.body).toBe("{}");
  });
});
