import { describe, expect, it, vi } from "vitest";

import {
  fetchAnalysisSnapshotDetail,
  fetchAnalysisSnapshots,
  type ApiFetcher
} from "../src/lib/api";

const RUN = {
  analysis_run_id: "analysis_amazon_current",
  platform: "amazon",
  language: "zh-CN",
  scope: {
    platform: "amazon",
    analysis_policy: "exclude_reddit_more_node",
    source_unit_limit: 2000,
    truncated: false
  },
  collection_run_ids: ["run_amazon_1", "run_amazon_2"],
  input_digest: "sha256:input-current",
  template_contract: {
    brief_template_id: "amazon_voc_operator_brief",
    brief_template_version: "2026-07-10",
    generation_method: "deterministic_template_v1"
  },
  snapshot_schema_version: "analysis_snapshot_v1",
  generation_method: "deterministic_template_v1",
  source_unit_count: 10,
  analysis_unit_count: 10,
  truncated: false,
  artifact_count: 2,
  output_digest: "sha256:output-current",
  created_at: "2026-08-21T02:39:26+00:00"
} as const;

const ARTIFACTS = [
  {
    analysis_snapshot_id: "snapshot_edge_1",
    analysis_run_id: RUN.analysis_run_id,
    artifact_type: "relation_edge",
    artifact_key: "edge_review_product",
    schema_version: "relation_edge_v1",
    payload: { collection_run_id: "run_amazon_2", evidence_ref_ids: ["voc_1"] },
    payload_digest: "sha256:edge-current",
    created_at: RUN.created_at
  },
  {
    analysis_snapshot_id: "snapshot_brief_1",
    analysis_run_id: RUN.analysis_run_id,
    artifact_type: "insight_brief",
    artifact_key: "brief_amazon",
    schema_version: "insight_brief_v1",
    payload: { headline: "raw payload text must stay hidden" },
    payload_digest: "sha256:brief-current",
    created_at: RUN.created_at
  }
] as const;

function fetcherFor(payload: unknown, status = 200): ApiFetcher {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  }));
}

describe("analysis snapshot API", () => {
  it("parses strict paginated history and uses the bounded list URL", async () => {
    const fetcher = fetcherFor({ items: [RUN], total: 1, limit: 50, offset: 0 });

    const result = await fetchAnalysisSnapshots("http://localhost:8000/", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/insights/snapshots?limit=50&offset=0"
    );
    expect(result.items).toEqual([RUN]);
    expect(result.total).toBe(1);
  });

  it("parses detail artifacts and preserves structured payload metadata", async () => {
    const fetcher = fetcherFor({ run: RUN, artifacts: ARTIFACTS });

    const result = await fetchAnalysisSnapshotDetail(
      "http://localhost:8000",
      RUN.analysis_run_id,
      fetcher
    );

    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/api/insights/snapshots/${RUN.analysis_run_id}`
    );
    expect(result.artifacts).toHaveLength(2);
    expect(result.artifacts[0]?.payload).toEqual({
      collection_run_id: "run_amazon_2",
      evidence_ref_ids: ["voc_1"]
    });
  });

  it("fails closed when pagination is missing", async () => {
    await expect(
      fetchAnalysisSnapshots("http://localhost:8000", fetcherFor({ items: [RUN] }))
    ).rejects.toThrow("analysis_snapshots_invalid_response:pagination_required");
  });

  it("fails closed when an artifact points at another run", async () => {
    const mismatchedArtifact = {
      ...ARTIFACTS[0],
      analysis_run_id: "analysis_other"
    };

    await expect(
      fetchAnalysisSnapshotDetail(
        "http://localhost:8000",
        RUN.analysis_run_id,
        fetcherFor({ run: RUN, artifacts: [mismatchedArtifact, ARTIFACTS[1]] })
      )
    ).rejects.toThrow("analysis_snapshot_detail_invalid_response:artifact_run_mismatch");
  });

  it("fails closed when stored artifact_count and detail length diverge", async () => {
    await expect(
      fetchAnalysisSnapshotDetail(
        "http://localhost:8000",
        RUN.analysis_run_id,
        fetcherFor({ run: RUN, artifacts: [ARTIFACTS[0]] })
      )
    ).rejects.toThrow("analysis_snapshot_detail_invalid_response:artifact_count_mismatch");
  });

  it("fails closed when the returned run does not match the selected run", async () => {
    await expect(
      fetchAnalysisSnapshotDetail(
        "http://localhost:8000",
        "analysis_amazon_other",
        fetcherFor({ run: RUN, artifacts: ARTIFACTS })
      )
    ).rejects.toThrow("analysis_snapshot_detail_invalid_response:selected_run_mismatch");
  });

  it("fails closed on duplicate artifact identities", async () => {
    await expect(
      fetchAnalysisSnapshotDetail(
        "http://localhost:8000",
        RUN.analysis_run_id,
        fetcherFor({ run: RUN, artifacts: [ARTIFACTS[0], ARTIFACTS[0]] })
      )
    ).rejects.toThrow("analysis_snapshot_detail_invalid_response:duplicate_artifact_identity");
  });

  it("fails closed on a non-2xx snapshot list response", async () => {
    await expect(
      fetchAnalysisSnapshots("http://localhost:8000", fetcherFor({}, 503))
    ).rejects.toThrow("analysis_snapshots_fetch_failed:503");
  });
});
