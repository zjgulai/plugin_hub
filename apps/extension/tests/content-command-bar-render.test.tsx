import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContentCommandBar } from "../src/content/ui/ContentCommandBar";
import { CREATE_COLLECTION_TASK_MESSAGE_TYPE } from "../src/types/messages";

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
        />
      );
    });

    expect(rootElement.textContent).toContain("Plugin Hub");
    expect(rootElement.textContent).toContain("Guest mode");
    expect(rootElement.textContent).toContain("B08MHGST8X");
    expect(rootElement.textContent).toContain("VOC Pipeline");

    const previewButton = Array.from(rootElement.querySelectorAll("button")).find(
      (button) => button.textContent === "采集预览"
    );
    expect(previewButton).toBeDefined();

    await act(async () => {
      previewButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(rootElement.textContent).toContain("Raw 1");
    expect(rootElement.textContent).toContain("58%");
    expect(rootElement.textContent).toContain("导出 JSON");
    expect(rootElement.textContent).toContain("导出 CSV");
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
});
