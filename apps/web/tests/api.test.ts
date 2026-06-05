import { describe, expect, it, vi } from "vitest";

import { fetchVocUnits } from "../src/lib/api";

describe("fetchVocUnits", () => {
  it("fetches VOC units by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            source_object_id: "R123",
            platform: "amazon",
            source_kind: "amazon_review",
            source_url: "https://www.amazon.com/product-reviews/B000000001",
            captured_at: "2026-06-05T00:00:00.000Z",
            body: "Switch broke after two weeks.",
            quality_flags: [],
            coverage_confidence: 0.88,
            platform_extension: {}
          }
        ]
      })
    });

    const result = await fetchVocUnits("http://localhost:8000", "amazon", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/voc-units?platform=amazon");
    expect(result.items[0]?.source_object_id).toBe("R123");
  });

  it("omits the platform query for all VOC units", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] })
    });

    await fetchVocUnits("http://localhost:8000", "all", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/voc-units");
  });

  it("removes multiple trailing slashes from the base URL", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] })
    });

    await fetchVocUnits("http://localhost:8000///", "reddit", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/voc-units?platform=reddit");
  });

  it("throws a status-keyed error for non-ok responses", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ detail: "bad gateway" })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_fetch_failed:502"
    );
  });

  it("rejects invalid VOC unit response payloads", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: "not-an-array" })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:items_array_required"
    );
  });

  it("rejects non-object VOC unit items", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [null] })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:item_object_required"
    );
  });

  it("rejects VOC units with missing required source URL", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            source_object_id: "R123",
            platform: "amazon",
            source_kind: "amazon_review",
            captured_at: "2026-06-05T00:00:00.000Z",
            body: "Missing source URL.",
            quality_flags: [],
            coverage_confidence: 0.88,
            platform_extension: {}
          }
        ]
      })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:source_url_required"
    );
  });

  it("rejects VOC units with invalid platform values", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            source_object_id: "R123",
            platform: "shopify",
            source_kind: "amazon_review",
            source_url: "https://www.amazon.com/product-reviews/B000000001",
            captured_at: "2026-06-05T00:00:00.000Z",
            body: "Invalid platform.",
            quality_flags: [],
            coverage_confidence: 0.88,
            platform_extension: {}
          }
        ]
      })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:item_platform_required"
    );
  });

  it("wraps JSON parse failures in a stable response error", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError("invalid json");
      }
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:json_parse_failed"
    );
  });
});
