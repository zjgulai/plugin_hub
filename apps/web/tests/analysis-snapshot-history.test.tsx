import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AnalysisSnapshotHistory } from "../src/components/AnalysisSnapshotHistory";
import type {
  AnalysisRunSnapshot,
  AnalysisSnapshotDetail
} from "../src/lib/api";

const PRIOR_RUN: AnalysisRunSnapshot = {
  analysis_run_id: "analysis_amazon_prior",
  platform: "amazon",
  language: "zh-CN",
  scope: { analysis_policy: "exclude_reddit_more_node" },
  collection_run_ids: ["run_amazon_1"],
  input_digest: "sha256:input-prior",
  template_contract: {
    brief_template_id: "amazon_voc_operator_brief",
    brief_template_version: "2026-07-10"
  },
  snapshot_schema_version: "analysis_snapshot_v1",
  generation_method: "deterministic_template_v1",
  source_unit_count: 7,
  analysis_unit_count: 7,
  truncated: false,
  artifact_count: 3,
  output_digest: "sha256:output-prior",
  created_at: "2026-08-20T02:39:26+00:00"
};

const CURRENT_RUN: AnalysisRunSnapshot = {
  ...PRIOR_RUN,
  analysis_run_id: "analysis_amazon_current",
  collection_run_ids: ["run_amazon_1", "run_amazon_2"],
  input_digest: "sha256:input-current",
  source_unit_count: 10,
  analysis_unit_count: 10,
  artifact_count: 4,
  output_digest: "sha256:output-current",
  created_at: "2026-08-21T02:39:26+00:00"
};

const DETAIL: AnalysisSnapshotDetail = {
  run: CURRENT_RUN,
  artifacts: [
    {
      analysis_snapshot_id: "snapshot_edge_1",
      analysis_run_id: CURRENT_RUN.analysis_run_id,
      artifact_type: "relation_edge",
      artifact_key: "edge_review_product",
      schema_version: "relation_edge_v1",
      payload: { body: "raw payload text must stay hidden" },
      payload_digest: "sha256:edge-current",
      created_at: CURRENT_RUN.created_at
    },
    {
      analysis_snapshot_id: "snapshot_signal_1",
      analysis_run_id: CURRENT_RUN.analysis_run_id,
      artifact_type: "enriched_voc_signal",
      artifact_key: "signal_durability",
      schema_version: "enriched_voc_signal_v1",
      payload: { customer_language: ["raw payload text must stay hidden"] },
      payload_digest: "sha256:signal-current",
      created_at: CURRENT_RUN.created_at
    },
    {
      analysis_snapshot_id: "snapshot_note_1",
      analysis_run_id: CURRENT_RUN.analysis_run_id,
      artifact_type: "strategy_note",
      artifact_key: "topic_durability",
      schema_version: "strategy_note_v1",
      payload: { recommendation: "raw payload text must stay hidden" },
      payload_digest: "sha256:note-current",
      created_at: CURRENT_RUN.created_at
    },
    {
      analysis_snapshot_id: "snapshot_brief_1",
      analysis_run_id: CURRENT_RUN.analysis_run_id,
      artifact_type: "insight_brief",
      artifact_key: "brief_amazon",
      schema_version: "insight_brief_v1",
      payload: { headline: "raw payload text must stay hidden" },
      payload_digest: "sha256:brief-current",
      created_at: CURRENT_RUN.created_at
    }
  ]
};

describe("AnalysisSnapshotHistory", () => {
  it("renders a selected evidence ledger, same-platform diff, and lineage without payload text", () => {
    const html = renderToStaticMarkup(
      <AnalysisSnapshotHistory
        snapshots={[CURRENT_RUN, PRIOR_RUN]}
        total={2}
        selectedRunId={CURRENT_RUN.analysis_run_id}
        detail={DETAIL}
        listError={null}
        detailError={null}
      />
    );

    expect(html).toContain("洞察快照账本");
    expect(html).toContain("输出已变化");
    expect(html).toContain("+3");
    expect(html).toContain("2 个 collection run");
    expect(html).toContain("Relation edges");
    expect(html).toContain("Insight briefs");
    expect(html).toContain("collection runs");
    expect(html).toContain("output digest");
    expect(html).not.toContain("raw payload text must stay hidden");
  });

  it("keeps predecessor state unknown when the loaded history window is incomplete", () => {
    const html = renderToStaticMarkup(
      <AnalysisSnapshotHistory
        snapshots={[CURRENT_RUN]}
        total={3}
        selectedRunId={CURRENT_RUN.analysis_run_id}
        detail={DETAIL}
        listError={null}
        detailError={null}
      />
    );

    expect(html).toContain("1 / 3 loaded");
    expect(html).toContain("比较窗口不完整");
    expect(html).toContain("predecessor unknown beyond loaded window");
    expect(html.match(/>unknown</g)).toHaveLength(4);
    expect(html).not.toContain("首个可比较快照");
    expect(html).not.toContain("no prior run");
    expect(html).not.toContain(">baseline<");
  });

  it("keeps baseline labels when the complete history has no prior run", () => {
    const html = renderToStaticMarkup(
      <AnalysisSnapshotHistory
        snapshots={[CURRENT_RUN]}
        total={1}
        selectedRunId={CURRENT_RUN.analysis_run_id}
        detail={DETAIL}
        listError={null}
        detailError={null}
      />
    );

    expect(html).toContain("1 loaded");
    expect(html).toContain("首个可比较快照");
    expect(html).toContain("no prior run");
    expect(html).toContain(">baseline<");
    expect(html).not.toContain("比较窗口不完整");
  });

  it("prompts for an explicit selection without fetching detail by default", () => {
    const html = renderToStaticMarkup(
      <AnalysisSnapshotHistory
        snapshots={[CURRENT_RUN, PRIOR_RUN]}
        total={2}
        selectedRunId={null}
        detail={null}
        listError={null}
        detailError={null}
      />
    );

    expect(html).toContain("选择一个快照查看 lineage 与差异");
    expect(html).toContain(`snapshot=${CURRENT_RUN.analysis_run_id}`);
  });

  it("keeps the empty history state explicit about the migration boundary", () => {
    const html = renderToStaticMarkup(
      <AnalysisSnapshotHistory
        snapshots={[]}
        total={0}
        selectedRunId={null}
        detail={null}
        listError={null}
        detailError={null}
      />
    );

    expect(html).toContain("暂无迁移后洞察快照");
    expect(html).toContain("不会把实时重算冒充历史记录");
  });
});
