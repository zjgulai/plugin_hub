import { describe, expect, it, vi } from "vitest";

import { fetchCollectionTasks, fetchStrategyNotes, fetchVocUnits } from "../src/lib/api";

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

describe("fetchStrategyNotes", () => {
  it("fetches strategy notes from the insight endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            strategy_type: "voc_template",
            topic: "durability",
            evidence_count: 2,
            evidence_examples: [
              {
                body: "Broke after two weeks.",
                platform: "amazon"
              }
            ],
            recommendation: "Prioritize durability fixes.",
            evidence_strength: 0.72,
            quality_flags: ["low_coverage"]
          }
        ]
      })
    });

    const result = await fetchStrategyNotes("http://localhost:8000", "all", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/insights/strategy-notes"
    );
    expect(result.items[0]).toEqual({
      strategy_type: "voc_template",
      topic: "durability",
      evidence_count: 2,
      evidence_examples: [
        {
          body: "Broke after two weeks.",
          platform: "amazon"
        }
      ],
      recommendation: "Prioritize durability fixes.",
      evidence_strength: 0.72,
      quality_flags: ["low_coverage"]
    });
  });

  it("fetches strategy notes by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] })
    });

    await fetchStrategyNotes("http://localhost:8000///", "reddit", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/insights/strategy-notes?platform=reddit"
    );
  });

  it("rejects invalid strategy note response payloads", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            strategy_type: "voc_template",
            topic: "durability",
            evidence_count: "2",
            evidence_examples: [],
            recommendation: "Prioritize durability fixes.",
            evidence_strength: 0.72,
            quality_flags: []
          }
        ]
      })
    });

    await expect(fetchStrategyNotes("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "strategy_notes_invalid_response:evidence_count_required"
    );
  });
});

describe("fetchCollectionTasks", () => {
  it("fetches server-side collection tasks by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            collection_task_id: "task_123",
            platform: "reddit",
            source_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/",
            requested_capture_method: "server_reddit_json_proxy",
            trigger_reason: "reddit_json_unavailable_dom_empty",
            status: "retry_scheduled",
            context: {
              thread_id: "thread123"
            },
            created_at: "2026-06-14T00:00:00.000Z",
            updated_at: "2026-06-14T00:00:00.000Z"
          }
        ]
      })
    });

    const result = await fetchCollectionTasks("http://localhost:8000///", "reddit", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/collection-tasks?platform=reddit");
    expect(result.items[0]).toMatchObject({
      collection_task_id: "task_123",
      platform: "reddit",
      status: "retry_scheduled"
    });
  });

  it("rejects invalid task status values", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            collection_task_id: "task_123",
            platform: "reddit",
            source_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/",
            requested_capture_method: "server_reddit_json_proxy",
            trigger_reason: "reddit_json_unavailable_dom_empty",
            status: "unknown",
            context: {},
            created_at: "2026-06-14T00:00:00.000Z",
            updated_at: "2026-06-14T00:00:00.000Z"
          }
        ]
      })
    });

    await expect(fetchCollectionTasks("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "collection_tasks_invalid_response:status_required"
    );
  });
});
