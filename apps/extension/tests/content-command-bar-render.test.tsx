import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContentCommandBar } from "../src/content/ui/ContentCommandBar";
import { captureCurrentPage } from "../src/lib/capture";
import type { CollectionRunPayload } from "../src/types/contracts";
import {
  CREATE_COLLECTION_TASK_MESSAGE_TYPE,
  GET_PLATFORM_SETTING_MESSAGE_TYPE,
  GET_STRATEGY_NOTES_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CaptureSummary
} from "../src/types/messages";

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("ContentCommandBar", () => {
  let rootElement: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.stubGlobal("chrome", {
      storage: {
        local: {
          get: vi.fn(async () => ({ pluginHubApiBaseUrl: "http://localhost:8000" })),
          set: vi.fn(async () => undefined)
        }
      },
      runtime: {
        sendMessage: vi.fn(async () => ({
          collection_run_id: "run_test",
          raw_item_count: 1,
          voc_unit_count: 1
        }))
      }
    });

    document.body.innerHTML = `
      <h1 id="productTitle">Aromasong Vanilla Coconut Shea Sugar Scrub</h1>
      <span id="acrCustomerReviewText">355 ratings</span>
      <span id="acrPopover" title="4.4 out of 5 stars"></span>
      <section id="cm-cr-dp-review-list">
        <div data-hook="review" id="R3K2DOANUAPY96">
          <i data-hook="review-star-rating"><span>5 out of 5 stars</span></i>
          <a href="/review/R3K2DOANUAPY96/ref=cm_cr_dp_d_rvw_ttl?ie=UTF8">
            Great device for a good price
          </a>
          <div data-hook="reviewText">
            <div data-hook="reviewRichContentContainer">
              <span>Setup was fast and the sound is clear.</span>
            </div>
          </div>
        </div>
      </section>
    `;
    rootElement = document.createElement("div");
    document.body.append(rootElement);
    root = createRoot(rootElement);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    vi.unstubAllGlobals();
  });

  it("renders the selected command bar concept and captures a preview", async () => {
    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B08MHGST8X"
          }}
          sourceUrl="https://www.amazon.com/Aromasong-Vanilla-Coconut-Sugar-Scrub/dp/B08MHGST8X"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    expect(rootElement.textContent).toContain("Plugin Hub");
    expect(rootElement.querySelector("[aria-label='Plugin Hub VOC Drawer']")).toBeTruthy();
    expect(rootElement.textContent).toContain("Guest mode");
    expect(rootElement.textContent).toContain("Amazon VOC");
    expect(rootElement.textContent).toContain("B08MHGST8X");
    expect(rootElement.textContent).toContain("VOC Pipeline");
    expect(rootElement.textContent).toContain("计划");
    expect(rootElement.textContent).toContain("Schema");
    expect(rootElement.textContent).toContain("洞察");
    expect(rootElement.textContent).toContain("回传");
    expect(rootElement.querySelector("[aria-label='Loop 工程阶段']")).toBeTruthy();
    expect(rootElement.textContent).not.toContain("Amazon 与 Reddit");

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    expect(previewButton).toBeDefined();

    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("Raw 1");
    expect(rootElement.textContent).toContain("58%");
    expect(rootElement.textContent).toContain("确认并写入");
    expect(rootElement.textContent).toContain("回传到后台");
    expect(rootElement.textContent).toContain("导出 JSON");
    expect(rootElement.textContent).toContain("导出 CSV");

    const uploadButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "回传到后台"
    );
    await act(async () => {
      uploadButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("Run run_test · VOC 1");
    expect(rootElement.textContent).toContain("查看 AI 洞察");

    const collapseButton = rootElement.querySelector<HTMLButtonElement>("[aria-label='折叠 Plugin Hub 抽屉']");
    await act(async () => {
      collapseButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.querySelector("[aria-label='展开 Plugin Hub 抽屉']")).toBeTruthy();
    expect(rootElement.textContent).toContain("VOC 1");
    expect(rootElement.textContent).not.toContain("VOC Pipeline");
  }, 20_000);

  it("passes the saved Amazon page budget from backend settings into capture preview", async () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    sendMessage.mockImplementation(async (message: unknown) => {
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === GET_PLATFORM_SETTING_MESSAGE_TYPE
      ) {
        return {
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
        };
      }

      return {
        collection_run_id: "run_test",
        raw_item_count: 1,
        voc_unit_count: 1
      };
    });
    const captureSpy = vi.fn(captureCurrentPage);

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B08MHGST8X"
          }}
          sourceUrl="https://www.amazon.com/Aromasong-Vanilla-Coconut-Sugar-Scrub/dp/B08MHGST8X"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureSpy}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(captureSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        runtimeSettings: expect.objectContaining({
          amazonPageLimit: 2,
          platformSettingSource: "stored",
          platformSettingUpdatedAt: "2026-06-22T00:00:00.000Z"
        })
      })
    );
    expect(rootElement.textContent).toContain("Raw 1");
  }, 20_000);

  it("loads backend AI insight notes after Amazon VOC upload", async () => {
    vi.mocked(chrome.storage.local.get).mockImplementation(async () => ({}));
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    sendMessage.mockImplementation(async (message: unknown) => {
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === GET_PLATFORM_SETTING_MESSAGE_TYPE
      ) {
        return {
          platform: "amazon",
          enabled: true,
          config: {
            page_limit: 1,
            marketplaces: ["US"],
            notes: ""
          },
          updated_at: "2026-06-22T00:00:00.000Z",
          updated_by: "operator",
          source: "stored"
        };
      }

      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === UPLOAD_COLLECTION_MESSAGE_TYPE
      ) {
        return {
          collection_run_id: "run_test",
          raw_item_count: 1,
          voc_unit_count: 1
        };
      }

      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === GET_STRATEGY_NOTES_MESSAGE_TYPE
      ) {
        return {
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
        };
      }

      return { error: "unexpected_message" };
    });

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B08MHGST8X"
          }}
          sourceUrl="https://www.amazon.com/Aromasong-Vanilla-Coconut-Sugar-Scrub/dp/B08MHGST8X"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    const uploadButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "回传到后台"
    );
    await act(async () => {
      uploadButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    const insightButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "查看 AI 洞察"
    );
    await act(async () => {
      insightButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(sendMessage).toHaveBeenCalledWith({
      type: GET_STRATEGY_NOTES_MESSAGE_TYPE,
      apiBaseUrl: "https://plugin.lute-tlz-dddd.top",
      platform: "amazon"
    });
    expect(rootElement.textContent).toContain("noise");
    expect(rootElement.textContent).toContain("Prioritize reducing noise complaints.");
  }, 20_000);

  it("falls back to the default Amazon page budget when backend settings cannot be read", async () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    sendMessage.mockResolvedValue({
      error: "platform_setting_fetch_failed:503"
    });

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B08MHGST8X"
          }}
          sourceUrl="https://www.amazon.com/Aromasong-Vanilla-Coconut-Sugar-Scrub/dp/B08MHGST8X"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("Raw 1");
    expect(rootElement.textContent).toContain("未读取到后台 Amazon 配置，使用默认页预算。");
  }, 20_000);

  it("clears captured payload state when the detected source URL changes", async () => {
    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B08MHGST8X"
          }}
          sourceUrl="https://www.amazon.com/Aromasong-Vanilla-Coconut-Sugar-Scrub/dp/B08MHGST8X"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(rootElement.textContent).toContain("Raw 1");

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "amazon",
            pageKind: "amazon_reviews",
            entryPageKind: "amazon_product_detail",
            asin: "B000000001"
          }}
          sourceUrl="https://www.amazon.com/Another-Product/dp/B000000001"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    expect(rootElement.textContent).toContain("B000000001");
    expect(rootElement.textContent).not.toContain("Raw 1");
    expect(rootElement.textContent).not.toContain("导出 JSON");
  }, 20_000);

  it("offers a server-side task when Reddit browser capture returns zero raw items", async () => {
    document.body.innerHTML = `
      <main>
        <h1>You've been blocked by network security.</h1>
        <p>To continue, log in to your Reddit account or use your developer token</p>
      </main>
    `;
    document.body.append(rootElement);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("reddit_json_fetch_failed:network");
      })
    );
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    sendMessage.mockResolvedValueOnce({
      collection_task_id: "task_test",
      platform: "reddit",
      source_url: "https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/",
      requested_capture_method: "server_reddit_json_proxy",
      trigger_reason: "reddit_json_unavailable_dom_empty",
      status: "pending",
      context: {
        thread_id: "thread123"
      },
      created_at: "2026-06-14T00:00:00.000Z",
      updated_at: "2026-06-14T00:00:00.000Z"
    });

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "reddit",
            pageKind: "reddit_thread",
            threadId: "thread123"
          }}
          sourceUrl="https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={captureCurrentPage}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("Raw 0");
    expect(rootElement.textContent).toContain("服务端补采");
    expect(rootElement.textContent).toContain("恢复建议：服务端补采");
    expect(rootElement.textContent).toContain("server capture queue");

    const taskButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "服务端补采"
    );
    await act(async () => {
      taskButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(sendMessage).toHaveBeenCalledWith({
      type: CREATE_COLLECTION_TASK_MESSAGE_TYPE,
      apiBaseUrl: "http://localhost:8000",
      payload: {
        task: {
          platform: "reddit",
          source_url: "https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/",
          requested_capture_method: "server_reddit_json_proxy",
          trigger_reason: "reddit_json_unavailable_dom_empty",
          context: expect.objectContaining({
            thread_id: "thread123",
            client_raw_item_count: 0,
            client_stop_reason: "reddit_json_unavailable_dom_empty"
          })
        }
      }
    });
    expect(rootElement.textContent).toContain("Task task_test · pending");
  }, 20_000);

  it("shows the effective API URL when Reddit upload cannot reach the backend", async () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    sendMessage.mockResolvedValue({ error: "Failed to fetch" });
    const redditPayload = {
      run: {
        platform: "reddit",
        source_url: "https://www.reddit.com/r/shopify/comments/1umbsm4/shopify_store_traffic_is_100_visitorsday_but/",
        capture_method: "extension_reddit_dom_fallback",
        coverage_scope: {
          page_kind: "reddit_thread",
          thread_id: "1umbsm4",
          fallback_parser: "reddit_dom",
          raw_item_count: 1
        },
        stop_reason: "reddit_json_unavailable_dom_fallback",
        coverage_confidence: 0.35
      },
      raw_items: [
        {
          platform: "reddit",
          source_kind: "reddit_thread",
          source_object_id: "t3_1umbsm4",
          raw_schema_version: "raw_reddit_thread_v1",
          parser_version: "reddit-dom-parser@0.1.0",
          raw_payload: {
            title: "Shopify store traffic is 100+ visitors/day but sales suddenly stopped.",
            source_url: "https://www.reddit.com/r/shopify/comments/1umbsm4/shopify_store_traffic_is_100_visitorsday_but/"
          },
          raw_payload_hash: "fnv1a64:test",
          captured_at: "2026-07-07T00:00:00.000Z"
        }
      ]
    } satisfies CollectionRunPayload;
    const redditSummary = {
      platform: "reddit",
      page_kind: "reddit_thread",
      raw_item_count: 1,
      stop_reason: "reddit_json_unavailable_dom_fallback",
      coverage_confidence: 0.35
    } satisfies CaptureSummary;

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "reddit",
            pageKind: "reddit_thread",
            threadId: "1umbsm4"
          }}
          sourceUrl="https://www.reddit.com/r/shopify/comments/1umbsm4/shopify_store_traffic_is_100_visitorsday_but/"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={vi.fn(async () => ({
            payload: redditPayload,
            summary: redditSummary
          }))}
        />
      );
    });

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    const uploadButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "回传到后台"
    );
    await act(async () => {
      uploadButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("当前 API：http://localhost:8000");
    expect(rootElement.textContent).toContain("展开“回传设置”确认地址");
  }, 20_000);

  it("renders Instagram target as authorization-gated without enabling page capture", async () => {
    document.head.innerHTML = '<meta property="og:title" content="Instagram post by tester" />';
    document.body.innerHTML = "<main></main>";
    document.body.append(rootElement);

    await act(async () => {
      root.render(
        <ContentCommandBar
          detectedPage={{
            platform: "instagram",
            pageKind: "instagram_media",
            mediaKind: "post",
            shortcode: "ABC123_def-"
          }}
          sourceUrl="https://www.instagram.com/p/ABC123_def-/"
          documentRoot={document}
          onDismiss={vi.fn()}
          captureCurrentPage={vi.fn(async () => {
            throw new Error("instagram_capture_requires_authorized_backend");
          })}
        />
      );
    });

    expect(rootElement.textContent).toContain("Instagram VOC");
    expect(rootElement.textContent).toContain("Auth gated");
    expect(rootElement.textContent).toContain("ABC123_def-");
    expect(rootElement.textContent).toContain("需要后端授权采集");
    expect(rootElement.textContent).toContain("授权门禁");
    expect(rootElement.textContent).toContain("Meta API");
    const gatedButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "等待授权"
    );
    expect(gatedButton).toBeDefined();
    expect(gatedButton?.disabled).toBe(true);
    expect(rootElement.textContent).not.toContain("回传到后台");
  }, 20_000);
});
