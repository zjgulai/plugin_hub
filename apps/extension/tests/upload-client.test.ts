import { describe, expect, it } from "vitest";

import type { CollectionRunPayload, CollectionTaskPayload } from "../src/types/contracts";
import {
  createCollectionTask,
  getInsightBriefs,
  getStrategyNotes,
  getPlatformSetting,
  type UploadFetcher,
  uploadCollectionRun
} from "../src/lib/upload-client";

const payload = {
  run: {
    platform: "amazon",
    source_url: "https://www.amazon.com/product-reviews/B000000001",
    capture_method: "browser_extension",
    coverage_scope: {
      page_kind: "amazon_reviews",
      asin: "B000000001",
      segments: ["all_reviews"],
      page_count: 1
    },
    stop_reason: null,
    coverage_confidence: 0.91
  },
  raw_items: [
    {
      platform: "amazon",
      source_kind: "amazon_review",
      source_object_id: "R000000001",
      raw_schema_version: "raw_amazon_review_v1",
      parser_version: "amazon-dom-parser@0.1.0",
      raw_payload: {
        review_id: "R000000001",
        body: "Works well",
        rating: 5,
        media_refs: []
      },
      raw_payload_hash: "hash-1",
      captured_at: "2026-06-06T01:02:03.000Z"
    }
  ]
} satisfies CollectionRunPayload;

const taskPayload = {
  task: {
    platform: "reddit",
    source_url: "https://www.reddit.com/r/Coffee/comments/thread123/example/",
    requested_capture_method: "server_reddit_json_proxy",
    trigger_reason: "reddit_json_unavailable_dom_empty",
    context: {
      thread_id: "thread123",
      client_raw_item_count: 0
    }
  }
} satisfies CollectionTaskPayload;

describe("uploadCollectionRun", () => {
  it("posts the collection run payload and returns the created counters", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).resolves.toEqual({
      collection_run_id: "run-1",
      raw_item_count: 1,
      voc_unit_count: 1
    });

    expect(calls).toHaveLength(1);
    expect(calls[0]).toEqual({
      url: "https://api.example.com/api/collection-runs",
      init: {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      }
    });
  });

  it("removes multiple trailing slashes from the base URL", async () => {
    let postedUrl: string | null = null;
    const fetcher: UploadFetcher = async (url) => {
      postedUrl = url;

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await uploadCollectionRun("https://api.example.com///", payload, fetcher);

    expect(postedUrl).toBe("https://api.example.com/api/collection-runs");
  });

  it("throws a status-keyed error for non-ok responses", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "backend unavailable" })
    });

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).rejects.toThrow(
      "collection_run_upload_failed:503"
    );
  });

  it("rejects invalid upload response objects", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: true,
      status: 201,
      json: async () => ({
        collection_run_id: "run-1",
        raw_item_count: "1",
        voc_unit_count: 1
      })
    });

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).rejects.toThrow(
      "collection_run_upload_response_invalid"
    );
  });

  it("serializes coverage scope and raw item payload without dropping JSON fields", async () => {
    let body: BodyInit | null | undefined;
    const fetcher: UploadFetcher = async (_url, init) => {
      body = init.body;

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await uploadCollectionRun("https://api.example.com", payload, fetcher);

    expect(typeof body).toBe("string");
    const serializedPayload = JSON.parse(body as string) as CollectionRunPayload;
    expect(serializedPayload.run.coverage_scope).toEqual(payload.run.coverage_scope);
    expect(serializedPayload.raw_items[0]?.raw_payload).toEqual(payload.raw_items[0].raw_payload);
  });

  it("rejects non-object coverage scope before sending the request", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      run: {
        ...payload.run,
        coverage_scope: ["invalid"]
      }
    } as unknown as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_object_required");
    expect(called).toBe(false);
  });

  it("rejects non-finite coverage confidence before JSON.stringify can coerce it", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      run: {
        ...payload.run,
        coverage_confidence: Number.NaN
      }
    } as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_number_must_be_finite");
    expect(called).toBe(false);
  });

  it("rejects non-finite raw payload numbers before sending the request", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      raw_items: [
        {
          ...payload.raw_items[0],
          raw_payload: {
            ...payload.raw_items[0].raw_payload,
            rating: Number.POSITIVE_INFINITY
          }
        }
      ]
    } as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_number_must_be_finite");
    expect(called).toBe(false);
  });
});

describe("createCollectionTask", () => {
  it("posts a server-side collection task and returns the task status", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 202,
        json: async () => ({
          collection_task_id: "task-1",
          platform: "reddit",
          source_url: taskPayload.task.source_url,
          requested_capture_method: "server_reddit_json_proxy",
          trigger_reason: "reddit_json_unavailable_dom_empty",
          status: "retry_scheduled",
          context: taskPayload.task.context,
          created_at: "2026-06-14T00:00:00.000Z",
          updated_at: "2026-06-14T00:00:00.000Z"
        })
      };
    };

    await expect(createCollectionTask("https://api.example.com", taskPayload, fetcher)).resolves.toEqual({
      collection_task_id: "task-1",
      ...taskPayload.task,
      status: "retry_scheduled",
      created_at: "2026-06-14T00:00:00.000Z",
      updated_at: "2026-06-14T00:00:00.000Z"
    });

    expect(calls).toHaveLength(1);
    expect(calls[0]).toEqual({
      url: "https://api.example.com/api/collection-tasks",
      init: {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(taskPayload)
      }
    });
  });

  it("throws a status-keyed error when task creation fails", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "backend unavailable" })
    });

    await expect(createCollectionTask("https://api.example.com", taskPayload, fetcher)).rejects.toThrow(
      "collection_task_create_failed:503"
    );
  });

  it("rejects non-object task context before sending the request", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      task: {
        ...taskPayload.task,
        context: ["invalid"]
      }
    } as unknown as CollectionTaskPayload;

    await expect(createCollectionTask("https://api.example.com", invalidPayload, fetcher)).rejects.toThrow(
      "json_object_required"
    );
    expect(called).toBe(false);
  });

  it("rejects invalid task response objects", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: true,
      status: 202,
      json: async () => ({
        collection_task_id: "task-1",
        platform: "reddit",
        source_url: taskPayload.task.source_url,
        requested_capture_method: "server_reddit_json_proxy",
        trigger_reason: "reddit_json_unavailable_dom_empty",
        status: "unknown",
        context: taskPayload.task.context,
        created_at: "2026-06-14T00:00:00.000Z",
        updated_at: "2026-06-14T00:00:00.000Z"
      })
    });

    await expect(createCollectionTask("https://api.example.com", taskPayload, fetcher)).rejects.toThrow(
      "collection_task_response_invalid"
    );
  });
});

describe("getPlatformSetting", () => {
  it("fetches and parses a backend platform setting", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 200,
        json: async () => ({
          platform: "amazon",
          enabled: true,
          config: {
            page_limit: 2,
            marketplaces: ["US"],
            notes: ""
          },
          updated_at: "2026-06-22T00:00:00.000Z",
          updated_by: "operator",
          source: "stored"
        })
      };
    };

    await expect(getPlatformSetting("https://api.example.com", "amazon", fetcher)).resolves.toEqual({
      platform: "amazon",
      enabled: true,
      config: {
        page_limit: 2,
        marketplaces: ["US"],
        notes: ""
      },
      updated_at: "2026-06-22T00:00:00.000Z",
      updated_by: "operator",
      source: "stored"
    });
    expect(calls).toEqual([
      {
        url: "https://api.example.com/api/platform-settings/amazon",
        init: {
          method: "GET",
          headers: {
            Accept: "application/json"
          }
        }
      }
    ]);
  });

  it("rejects platform-setting responses for another platform", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        platform: "reddit",
        enabled: true,
        config: {},
        updated_at: "2026-06-22T00:00:00.000Z",
        updated_by: "operator",
        source: "stored"
      })
    });

    await expect(getPlatformSetting("https://api.example.com", "amazon", fetcher)).rejects.toThrow(
      "platform_setting_response_invalid"
    );
  });
});

describe("getStrategyNotes", () => {
  it("fetches platform-filtered strategy notes from the backend", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            {
              strategy_type: "voc_template",
              topic: "noise",
              evidence_count: 1,
              evidence_examples: [],
              recommendation: "Prioritize reducing noise complaints.",
              evidence_strength: 0.82,
              quality_flags: []
            }
          ]
        })
      };
    };

    await expect(getStrategyNotes("https://api.example.com///", "amazon", fetcher)).resolves.toEqual({
      items: [
        {
          strategy_type: "voc_template",
          topic: "noise",
          evidence_count: 1,
          evidence_examples: [],
          recommendation: "Prioritize reducing noise complaints.",
          evidence_strength: 0.82,
          quality_flags: []
        }
      ]
    });
    expect(calls).toEqual([
      {
        url: "https://api.example.com/api/insights/strategy-notes?platform=amazon",
        init: {
          method: "GET",
          headers: {
            Accept: "application/json"
          }
        }
      }
    ]);
  });

  it("throws a status-keyed error when strategy notes cannot be read", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: false,
      status: 404,
      json: async () => ({ detail: "route missing" })
    });

    await expect(getStrategyNotes("https://api.example.com", "amazon", fetcher)).rejects.toThrow(
      "strategy_notes_fetch_failed:404"
    );
  });
});

describe("getInsightBriefs", () => {
  it("fetches platform-filtered advisor briefs from the backend", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            {
              brief_id: "brief_amazon_B000000001",
              template_id: "amazon_review_listing_ops_v1",
              template_version: "v1",
              language: "zh-CN",
              advisor_profile: "cross_border_ecommerce_ops",
              scope: {
                platform: "amazon",
                source_object_type: "asin",
                source_object_id: "B000000001",
                source_url: "https://www.amazon.com/product-reviews/B000000001",
                collection_run_ids: ["run_001"],
                coverage_scope: "review_page",
                coverage_confidence: 0.72
              },
              headline: "评论样本显示 Listing 信任补强优先。",
              executive_findings: [],
              business_signals: [
                {
                  signal_id: "signal_001",
                  signal_type: "listing_conversion",
                  topic: "trust_gap",
                  aspect: "review_quality",
                  customer_language: ["Works well"],
                  business_impact: "影响转化和页面说服力。",
                  severity: "medium",
                  priority: "P1",
                  evidence_strength: "medium",
                  confidence_reason: "评论证据可支持页面优化方向。",
                  evidence_ref_ids: ["evidence_001"],
                  quality_flags: []
                }
              ],
              action_plan: [
                {
                  action_id: "action_001",
                  action_type: "listing",
                  title: "补强 Listing 信任解释",
                  recommendation: "把评价中的正向语言转成首屏卖点与 FAQ。",
                  why_now: "当前样本已经指向转化页表达问题。",
                  expected_metric: "CVR",
                  owner_role: "listing_ops",
                  priority: "P1",
                  effort: "low",
                  evidence_ref_ids: ["evidence_001"]
                }
              ],
              evidence_refs: [
                {
                  evidence_ref_id: "evidence_001",
                  voc_unit_id: "voc_001",
                  platform: "amazon",
                  source_kind: "amazon_review",
                  source_object_id: "R000000001",
                  quote: "Works well",
                  normalized_quote: "用户确认产品表现符合预期。",
                  rating: 5,
                  relation_edge_ids: [],
                  quality_flags: [],
                  source_url: "https://www.amazon.com/review/R000000001"
                }
              ],
              confidence: {
                level: "medium",
                reason: "样本可支持运营动作，但仍需要更多评论覆盖。",
                evidence_count: 1,
                source_diversity: "single_asin",
                coverage_notes: ["coverage_confidence=0.72"]
              },
              data_gaps: [
                {
                  gap_type: "low_sample",
                  description: "当前样本量不足，建议继续采集更多 review。",
                  recommended_collection: "继续采集同 ASIN 多页评论。",
                  blocks_confidence: true
                }
              ],
              generation_method: "deterministic_template_v1",
              created_at: "2026-07-08T00:00:00+00:00"
            }
          ]
        })
      };
    };

    await expect(getInsightBriefs("https://api.example.com///", "amazon", fetcher)).resolves.toEqual({
      items: [
        expect.objectContaining({
          brief_id: "brief_amazon_B000000001",
          headline: "评论样本显示 Listing 信任补强优先。",
          confidence: expect.objectContaining({
            level: "medium",
            evidence_count: 1
          }),
          action_plan: [
            expect.objectContaining({
              title: "补强 Listing 信任解释",
              expected_metric: "CVR"
            })
          ]
        })
      ]
    });
    expect(calls).toEqual([
      {
        url: "https://api.example.com/api/insights/briefs?platform=amazon",
        init: {
          method: "GET",
          headers: {
            Accept: "application/json"
          }
        }
      }
    ]);
  });

  it("rejects invalid advisor brief response payloads", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            brief_id: "brief_bad",
            template_id: "amazon_review_listing_ops_v1",
            template_version: "v1",
            language: "zh-CN",
            advisor_profile: "cross_border_ecommerce_ops",
            scope: {
              platform: "amazon",
              source_object_type: "asin",
              source_object_id: "B000000001",
              source_url: "https://www.amazon.com/product-reviews/B000000001",
              collection_run_ids: [],
              coverage_scope: "review_page",
              coverage_confidence: "0.72"
            },
            headline: "Bad payload",
            executive_findings: [],
            business_signals: [],
            action_plan: [],
            evidence_refs: [],
            confidence: {
              level: "medium",
              reason: "bad",
              evidence_count: 0,
              source_diversity: "single_asin",
              coverage_notes: []
            },
            data_gaps: [],
            generation_method: "deterministic_template_v1",
            created_at: "2026-07-08T00:00:00+00:00"
          }
        ]
      })
    });

    await expect(getInsightBriefs("https://api.example.com", "amazon", fetcher)).rejects.toThrow(
      "insight_brief_response_invalid"
    );
  });
});
