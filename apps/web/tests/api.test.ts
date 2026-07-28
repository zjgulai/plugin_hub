import { describe, expect, it, vi } from "vitest";

import {
  captureRedditThreadByUrl,
  fetchCaptureCapabilities,
  fetchCollectionTasks,
  fetchInsightBriefs,
  fetchPlatformSettingAuditEvents,
  fetchPlatformSettings,
  fetchStrategyNotes,
  fetchVocUnits,
  preflightInstagramGraphLiveReadAuthorization,
  updatePlatformSetting
} from "../src/lib/api";

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

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/voc-units?limit=500&offset=0&platform=amazon"
    );
    expect(result.items[0]?.source_object_id).toBe("R123");
  });

  it("accepts Instagram VOC units from the shared API contract", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            source_object_id: "18000000000000001",
            platform: "instagram",
            source_kind: "instagram_comment",
            source_url: "https://www.instagram.com/p/example/",
            captured_at: "2026-06-05T10:00:00.000Z",
            created_at: "2026-06-05T08:30:00.000Z",
            body: "This pump is quiet enough for night sessions.",
            author_display: "customer_one",
            parent_id: null,
            reply_role: "top_level_comment",
            commercial_object_type: "instagram_media",
            quality_flags: [],
            coverage_confidence: 0.86,
            platform_extension: {
              media_id: "17900000000000001",
              like_count: 4
            }
          }
        ]
      })
    });

    const result = await fetchVocUnits("http://localhost:8000", "instagram", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/voc-units?limit=500&offset=0&platform=instagram"
    );
    expect(result.items[0]?.platform).toBe("instagram");
    expect(result.items[0]?.platform_extension.media_id).toBe("17900000000000001");
  });

  it("omits the platform query for all VOC units", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] })
    });

    await fetchVocUnits("http://localhost:8000", "all", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/voc-units?limit=500&offset=0"
    );
  });

  it("removes multiple trailing slashes from the base URL", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [] })
    });

    await fetchVocUnits("http://localhost:8000///", "reddit", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/voc-units?limit=500&offset=0&platform=reddit"
    );
  });

  it("loads every VOC page before returning dashboard evidence", async () => {
    const item = (sourceObjectId: string) => ({
      source_object_id: sourceObjectId,
      platform: "amazon",
      source_kind: "amazon_review",
      source_url: "https://www.amazon.com/product-reviews/B000000001",
      captured_at: "2026-06-05T00:00:00.000Z",
      body: "Evidence",
      quality_flags: [],
      coverage_confidence: 0.88,
      platform_extension: {}
    });
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [item("R1"), item("R2")],
          total: 3,
          limit: 2,
          offset: 0,
          snapshot_max_id: 42
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [item("R3")],
          total: 3,
          limit: 2,
          offset: 2,
          snapshot_max_id: 42
        })
      });

    const result = await fetchVocUnits("http://localhost:8000", "all", fetcher);

    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/voc-units?limit=500&offset=2&snapshot_max_id=42"
    );
    expect(result.items.map((unit) => unit.source_object_id)).toEqual(["R1", "R2", "R3"]);
    expect(result.total).toBe(3);
  });

  it("accepts the zero snapshot boundary for an empty database", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [],
        total: 0,
        limit: 500,
        offset: 0,
        snapshot_max_id: 0
      })
    });

    const result = await fetchVocUnits("http://localhost:8000", "all", fetcher);

    expect(result.snapshot_max_id).toBe(0);
    expect(result.items).toEqual([]);
  });

  it("keeps every page on the server-provided stable snapshot boundary", async () => {
    const item = (sourceObjectId: string, collectionRunId: string) => ({
      source_object_id: sourceObjectId,
      collection_run_id: collectionRunId,
      platform: "amazon",
      source_kind: "amazon_review",
      source_url: `https://www.amazon.com/review/${sourceObjectId}`,
      captured_at: "2026-07-28T00:00:00.000Z",
      body: "Evidence",
      quality_flags: [],
      coverage_confidence: 0.88,
      platform_extension: {}
    });
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [item("R4", "run-4"), item("R3", "run-3")],
          total: 4,
          limit: 2,
          offset: 0,
          snapshot_max_id: 104
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [item("R2", "run-2"), item("R1", "run-1")],
          total: 4,
          limit: 2,
          offset: 2,
          snapshot_max_id: 104
        })
      });

    const result = await fetchVocUnits("http://localhost:8000", "all", fetcher);

    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/voc-units?limit=500&offset=2&snapshot_max_id=104"
    );
    expect(result.items.map((unit) => unit.source_object_id)).toEqual(["R4", "R3", "R2", "R1"]);
    expect(result.total).toBe(4);
    expect(result.snapshot_max_id).toBe(104);
  });

  it("refuses multi-page responses without a stable snapshot boundary", async () => {
    const item = {
      source_object_id: "R1",
      platform: "amazon",
      source_kind: "amazon_review",
      source_url: "https://www.amazon.com/review/R1",
      captured_at: "2026-07-28T00:00:00.000Z",
      body: "Evidence",
      quality_flags: [],
      coverage_confidence: 0.88,
      platform_extension: {}
    };
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [item], total: 2, limit: 1, offset: 0 })
    });

    await expect(fetchVocUnits("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "voc_units_invalid_response:snapshot_boundary_required"
    );
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

describe("fetchInsightBriefs", () => {
  it("fetches professional insight briefs by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
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
        ]
      })
    });

    const result = await fetchInsightBriefs("http://localhost:8000///", "reddit", fetcher);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/insights/briefs?platform=reddit"
    );
    expect(result.items[0]?.language).toBe("zh-CN");
    expect(result.items[0]?.confidence.level).toBe("low");
    expect(result.items[0]?.business_signals[0]?.signal_type).toBe("conversion_blocker");
    expect(result.items[0]?.action_plan[0]?.expected_metric).toBe("CVR");
    expect(result.items[0]?.data_gaps[0]?.gap_type).toBe("low_sample");
  });

  it("rejects invalid insight brief response payloads", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            brief_id: "brief_bad",
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
              coverage_confidence: "0.58"
            },
            headline: "Bad payload",
            executive_findings: [],
            business_signals: [],
            action_plan: [],
            evidence_refs: [],
            confidence: {
              level: "low",
              reason: "bad",
              evidence_count: 0,
              source_diversity: "single_thread",
              coverage_notes: []
            },
            data_gaps: [],
            generation_method: "deterministic_template_v1",
            created_at: "2026-07-08T00:00:00+00:00"
          }
        ]
      })
    });

    await expect(fetchInsightBriefs("http://localhost:8000", "all", fetcher)).rejects.toThrow(
      "insight_briefs_invalid_response:scope_coverage_confidence_required"
    );
  });
});

describe("fetchCollectionTasks", () => {
  it("fetches server-side collection tasks by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        open_total: 137,
        open_totals: {
          amazon: 3,
          reddit: 133,
          instagram: 1
        },
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
    expect(result.open_total).toBe(137);
    expect(result.open_totals).toEqual({ amazon: 3, reddit: 133, instagram: 1 });
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

describe("fetchCaptureCapabilities", () => {
  it("fetches capture capability readiness without a platform filter", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            platform: "instagram",
            capture_method: "server_instagram_graph_comments",
            mode: "server",
            status: "task_authorization_required",
            configured: true,
            requires_authorization: true,
            live_read_enabled: true,
            live_write_enabled: false,
            writes_canonical_voc: true,
            required_context_keys: [
              "media_id",
              "authorization_scope",
              "authorized_by",
              "authorized_at",
              "environment",
              "production_write"
            ],
            evidence_grade: "L1-public-or-runtime",
            next_required_action: "submit_task_authorization_context_to_preflight",
            side_effect_boundary: "capability_read_only_no_meta_graph_call_no_production_write",
            notes: "Requires backend-only Meta token and task authorization."
          }
        ]
      })
    });

    const result = await fetchCaptureCapabilities("http://localhost:8000///", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/capture-capabilities");
    expect(result.items[0]).toMatchObject({
      platform: "instagram",
      capture_method: "server_instagram_graph_comments",
      status: "task_authorization_required",
      evidence_grade: "L1-public-or-runtime",
      next_required_action: "submit_task_authorization_context_to_preflight",
      side_effect_boundary: "capability_read_only_no_meta_graph_call_no_production_write",
      required_context_keys: [
        "media_id",
        "authorization_scope",
        "authorized_by",
        "authorized_at",
        "environment",
        "production_write"
      ]
    });
  });

  it("rejects invalid capture capability status values", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            platform: "instagram",
            capture_method: "server_instagram_graph_comments",
            mode: "server",
            status: "unknown",
            configured: false,
            requires_authorization: true,
            live_read_enabled: false,
            live_write_enabled: false,
            writes_canonical_voc: true,
            required_context_keys: ["media_id"],
            evidence_grade: "L1-public-or-runtime",
            next_required_action: "confirm_data_rights_then_configure_backend_only_meta_token",
            side_effect_boundary: "capability_read_only_no_meta_graph_call_no_production_write",
            notes: "Invalid status."
          }
        ]
      })
    });

    await expect(fetchCaptureCapabilities("http://localhost:8000", fetcher)).rejects.toThrow(
      "capture_capabilities_invalid_response:status_required"
    );
  });

  it("throws a status-keyed error for capability endpoint failures", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "unavailable" })
    });

    await expect(fetchCaptureCapabilities("http://localhost:8000", fetcher)).rejects.toThrow(
      "capture_capabilities_fetch_failed:503"
    );
  });
});

describe("fetchPlatformSettings", () => {
  it("fetches platform settings from the backend", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            platform: "amazon",
            enabled: true,
            config: {
              page_limit: 4,
              marketplaces: ["US", "UK"],
              notes: "Focused rollout."
            },
            updated_at: "2026-06-21T00:00:00.000Z",
            updated_by: "dashboard-ui",
            source: "stored"
          }
        ]
      })
    });

    const result = await fetchPlatformSettings("http://localhost:8000///", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/platform-settings");
    expect(result.items[0]).toMatchObject({
      platform: "amazon",
      enabled: true,
      source: "stored",
      config: {
        page_limit: 4,
        marketplaces: ["US", "UK"],
        notes: "Focused rollout."
      }
    });
  });

  it("rejects invalid platform setting source values", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            platform: "amazon",
            enabled: true,
            config: {},
            updated_at: "2026-06-21T00:00:00.000Z",
            updated_by: "dashboard-ui",
            source: "runtime"
          }
        ]
      })
    });

    await expect(fetchPlatformSettings("http://localhost:8000", fetcher)).rejects.toThrow(
      "platform_settings_invalid_response:source_required"
    );
  });
});

describe("updatePlatformSetting", () => {
  it("patches one platform setting", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        platform: "reddit",
        enabled: false,
        config: {
          json_proxy_enabled: true,
          max_comment_depth: 5,
          notes: "Queue only."
        },
        updated_at: "2026-06-21T01:00:00.000Z",
        updated_by: "dashboard-ui",
        source: "stored"
      })
    });

    const result = await updatePlatformSetting(
      "http://localhost:8000///",
      "reddit",
      {
        enabled: false,
        updated_by: "dashboard-ui",
        config: {
          json_proxy_enabled: true,
          max_comment_depth: 5,
          notes: "Queue only."
        }
      },
      fetcher
    );

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/platform-settings/reddit",
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          enabled: false,
          updated_by: "dashboard-ui",
          config: {
            json_proxy_enabled: true,
            max_comment_depth: 5,
            notes: "Queue only."
          }
        })
      }
    );
    expect(result.enabled).toBe(false);
    expect(result.config.max_comment_depth).toBe(5);
  });

  it("includes backend details for update failures", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "page_limit_out_of_range" })
    });

    await expect(
      updatePlatformSetting("http://localhost:8000", "amazon", {}, fetcher)
    ).rejects.toThrow("platform_setting_update_failed:422:page_limit_out_of_range");
  });
});

describe("fetchPlatformSettingAuditEvents", () => {
  it("fetches audit events for one platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            id: 1,
            platform: "instagram",
            changed_fields: ["enabled", "config.comment_limit"],
            previous_enabled: false,
            new_enabled: true,
            previous_config: {
              comment_limit: 50
            },
            new_config: {
              comment_limit: 25
            },
            changed_by: "dashboard-ui",
            created_at: "2026-06-21T01:30:00.000Z"
          }
        ]
      })
    });

    const result = await fetchPlatformSettingAuditEvents(
      "http://localhost:8000///",
      "instagram",
      fetcher
    );

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/platform-settings/instagram/audit-events"
    );
    expect(result.items[0]).toMatchObject({
      id: 1,
      platform: "instagram",
      changed_fields: ["enabled", "config.comment_limit"],
      changed_by: "dashboard-ui"
    });
  });
});

describe("preflightInstagramGraphLiveReadAuthorization", () => {
  it("posts task context to the Instagram Graph live-read preflight endpoint", async () => {
    const context = {
      media_id: "17900000000000001",
      authorization_scope: "instagram_graph_live_read",
      authorized_by: "local-test",
      authorized_at: "2026-06-21T00:00:00Z",
      environment: "local",
      production_write: false
    };
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        platform: "instagram",
        capture_method: "server_instagram_graph_comments",
        status: "ready",
        configured: true,
        live_read_enabled: true,
        task_authorization_ready: true,
        ready_for_worker: true,
        required_context_keys: [
          "media_id",
          "authorization_scope",
          "authorized_by",
          "authorized_at",
          "environment",
          "production_write"
        ],
        missing_context_keys: [],
        invalid_context_keys: [],
        blocking_code: null,
        evidence_grade: "L2-fixture-or-dry-run",
        next_required_action: "run_authorized_read_only_task_only_after_approval",
        side_effect_boundary: "dry_preflight_only_no_meta_graph_call_no_production_write",
        notes: "Preflight only."
      })
    });

    const result = await preflightInstagramGraphLiveReadAuthorization(
      "http://localhost:8000///",
      context,
      fetcher
    );

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/capture-authorizations/instagram-graph-live-read/preflight",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          context
        })
      }
    );
    expect(result).toMatchObject({
      platform: "instagram",
      capture_method: "server_instagram_graph_comments",
      status: "ready",
      ready_for_worker: true,
      evidence_grade: "L2-fixture-or-dry-run",
      next_required_action: "run_authorized_read_only_task_only_after_approval",
      side_effect_boundary: "dry_preflight_only_no_meta_graph_call_no_production_write"
    });
  });

  it("rejects invalid preflight status values", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        platform: "instagram",
        capture_method: "server_instagram_graph_comments",
        status: "unknown",
        configured: true,
        live_read_enabled: true,
        task_authorization_ready: true,
        ready_for_worker: true,
        required_context_keys: [],
        missing_context_keys: [],
        invalid_context_keys: [],
        blocking_code: null,
        evidence_grade: "L2-fixture-or-dry-run",
        next_required_action: "run_authorized_read_only_task_only_after_approval",
        side_effect_boundary: "dry_preflight_only_no_meta_graph_call_no_production_write",
        notes: "Invalid status."
      })
    });

    await expect(
      preflightInstagramGraphLiveReadAuthorization("http://localhost:8000", {}, fetcher)
    ).rejects.toThrow("instagram_graph_live_read_preflight_invalid_response:status_required");
  });

  it("throws a status-keyed error for preflight endpoint failures", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "unavailable" })
    });

    await expect(
      preflightInstagramGraphLiveReadAuthorization("http://localhost:8000", {}, fetcher)
    ).rejects.toThrow("instagram_graph_live_read_preflight_failed:503");
  });
});

describe("captureRedditThreadByUrl", () => {
  it("posts a Reddit thread URL to the direct JSON capture endpoint", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        collection_run_id: "run_123",
        raw_item_count: 2,
        voc_unit_count: 2,
        json_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1",
        more_node_count: 0,
        stop_reason: null,
        coverage_confidence: 0.92
      })
    });

    const result = await captureRedditThreadByUrl(
      "http://localhost:8000///",
      "https://www.reddit.com/r/Coffee/comments/thread123/example/",
      fetcher
    );

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/reddit-thread-captures", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        source_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/"
      })
    });
    expect(result).toEqual({
      collection_run_id: "run_123",
      raw_item_count: 2,
      voc_unit_count: 2,
      json_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1",
      more_node_count: 0,
      stop_reason: null,
      coverage_confidence: 0.92
    });
  });
});
