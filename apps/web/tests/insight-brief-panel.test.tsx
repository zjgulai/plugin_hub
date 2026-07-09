import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InsightBriefPanel } from "../src/components/InsightBriefPanel";

describe("InsightBriefPanel", () => {
  it("renders consultant-grade headline, action, evidence, and data gaps", () => {
    const html = renderToStaticMarkup(
      createElement(InsightBriefPanel, {
        briefs: [
          {
            brief_id: "brief_reddit_thread_t3_thread123",
            template_id: "reddit_community_commerce_v1",
            template_version: "v1",
            language: "zh-CN",
            advisor_profile: "cross_border_ecommerce_ops",
            scope: {
              platform: "reddit",
              source_object_type: "reddit_thread",
              source_object_id: "t3_thread123",
              source_url: "https://www.reddit.com/r/shopify/comments/thread123/example/",
              collection_run_ids: ["run_001"],
              coverage_scope: "single_thread",
              coverage_confidence: 0.58
            },
            headline: "Reddit 样本显示转化与信任阻力。",
            executive_findings: [
              {
                finding_id: "finding_001",
                title: "转化阻力需要运营解释",
                business_meaning: "影响 CVR、售前解释效率和社群内容切入角度。",
                priority: "P1",
                confidence_level: "low",
                evidence_ref_ids: ["evidence_001"]
              }
            ],
            business_signals: [
              {
                signal_id: "signal_001",
                signal_type: "conversion_blocker",
                topic: "trust_gap",
                aspect: "trust_and_conversion",
                customer_language: ["I still get visitors but no sales."],
                business_impact: "影响 CVR、售前解释效率和社群内容切入角度。",
                severity: "medium",
                priority: "P1",
                evidence_strength: "medium",
                confidence_reason: "证据可支持方向判断，但需要补样复核。",
                evidence_ref_ids: ["evidence_001"],
                quality_flags: ["low_coverage"]
              }
            ],
            action_plan: [
              {
                action_id: "action_001",
                action_type: "content",
                title: "把信任疑虑转成 FAQ 与社群内容选题",
                recommendation: "整理用户原话，补充评价、支付安全和结账解释。",
                why_now: "当前讨论已经指向有流量但转化受阻。",
                expected_metric: "CVR",
                owner_role: "content_ops",
                priority: "P1",
                effort: "low",
                evidence_ref_ids: ["evidence_001"]
              }
            ],
            evidence_refs: [
              {
                evidence_ref_id: "evidence_001",
                voc_unit_id: "t3_thread123",
                platform: "reddit",
                source_kind: "reddit_thread",
                source_object_id: "t3_thread123",
                quote: "I still get visitors but no sales.",
                normalized_quote: "用户讨论指向转化或信任阻力。",
                rating: null,
                relation_edge_ids: [],
                quality_flags: ["low_coverage"],
                source_url: "https://www.reddit.com/r/shopify/comments/thread123/example/"
              }
            ],
            confidence: {
              level: "low",
              reason: "样本量或覆盖置信偏低，建议作为待验证运营假设。",
              evidence_count: 2,
              source_diversity: "single_thread",
              coverage_notes: ["coverage_confidence=0.58"]
            },
            data_gaps: [
              {
                gap_type: "low_sample",
                description: "当前样本量不足，强结论需要更多 VOC 证据支撑。",
                recommended_collection: "继续采集同 subreddit 的相邻 thread 和更多评论。",
                blocks_confidence: true
              }
            ],
            generation_method: "deterministic_template_v1",
            created_at: "2026-07-08T00:00:00+00:00"
          }
        ],
        error: null
      })
    );

    expect(html).toContain("VOC 经营诊断");
    expect(html).toContain("Reddit 样本显示转化与信任阻力。");
    expect(html).toContain("把信任疑虑转成 FAQ 与社群内容选题");
    expect(html).toContain("当前样本量不足");
    expect(html).toContain("I still get visitors but no sales.");
  });
});
