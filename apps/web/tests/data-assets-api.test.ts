import { describe, expect, it } from "vitest";

import {
  fetchDataAssetRuns,
  fetchDataAssetSummary,
  type ApiFetcher
} from "../src/lib/api";

describe("data asset API client", () => {
  it("parses aggregate durability metrics without raw payloads", async () => {
    let requestedUrl = "";
    const fetcher: ApiFetcher = async (url) => {
      requestedUrl = url;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          collection_run_count: 7,
          raw_item_count: 402,
          canonical_voc_count: 402,
          analysis_eligible_voc_count: 251,
          placeholder_voc_count: 151,
          flagged_voc_count: 3,
          low_confidence_voc_count: 2,
          average_coverage_confidence: 0.82,
          runs_with_count_mismatch: 0,
          orphan_raw_count: 0,
          orphan_voc_count: 0,
          platform_counts: { amazon: 10, reddit: 241, instagram: 0 },
          latest_run_at: "2026-07-07T08:48:25",
          latest_capture_at: "2026-07-07T08:48:25"
        })
      };
    };

    const result = await fetchDataAssetSummary("https://api.example.com/", 0.75, fetcher);

    expect(requestedUrl).toBe(
      "https://api.example.com/api/data-assets/summary?low_confidence_threshold=0.75"
    );
    expect(result.analysis_eligible_voc_count).toBe(251);
    expect(result.placeholder_voc_count).toBe(151);
  });

  it("parses paginated run-level history", async () => {
    const fetcher: ApiFetcher = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            collection_run_id: "run_1",
            platform: "reddit",
            capture_method: "browser_extension",
            stop_reason: null,
            coverage_confidence: 0.8,
            created_at: "2026-07-07T08:48:25",
            first_captured_at: "2026-07-07T08:40:00",
            last_captured_at: "2026-07-07T08:48:00",
            raw_item_count: 10,
            canonical_voc_count: 10,
            analysis_eligible_voc_count: 8,
            placeholder_voc_count: 2,
            asset_state: "complete"
          }
        ],
        total: 1,
        limit: 50,
        offset: 0
      })
    });

    const result = await fetchDataAssetRuns("https://api.example.com", fetcher);

    expect(result.total).toBe(1);
    expect(result.items[0]?.asset_state).toBe("complete");
  });
});
