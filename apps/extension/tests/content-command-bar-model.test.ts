import { describe, expect, it } from "vitest";

import {
  buildPipelineSteps,
  captureSummaryStatusText,
  detectedObjectSubtitle,
  detectedObjectTitle,
  formatConfidencePercent,
  platformName
} from "../src/content/ui/command-bar-model";
import { getPageSnapshot } from "../src/content/ui/page-snapshot";

describe("content command bar model", () => {
  it("formats supported platform labels and detected objects", () => {
    const amazonPage = {
      platform: "amazon",
      pageKind: "amazon_reviews",
      entryPageKind: "amazon_product_detail",
      asin: "B08MHGST8X"
    } as const;

    expect(platformName(amazonPage)).toBe("Amazon");
    expect(detectedObjectTitle(amazonPage)).toBe("B08MHGST8X");
    expect(detectedObjectSubtitle(amazonPage)).toBe("Product Detail");
  });

  it("builds previewed pipeline state from capture summary", () => {
    const steps = buildPipelineSteps("previewed", {
      platform: "amazon",
      page_kind: "amazon_reviews",
      raw_item_count: 8,
      stop_reason: "embedded_reviews_only",
      coverage_confidence: 0.82
    });

    expect(steps.map((step) => step.state)).toEqual(["done", "done", "active", "waiting", "waiting"]);
    expect(steps[0]?.detail).toBe("8 raw");
    expect(formatConfidencePercent(0.82)).toBe("82%");
  });

  it("does not mark schema mapping ready when a Reddit capture returns zero raw items", () => {
    const summary = {
      platform: "reddit",
      page_kind: "reddit_thread",
      raw_item_count: 0,
      stop_reason: "reddit_json_unavailable_dom_empty",
      coverage_confidence: 0.2
    } as const;
    const steps = buildPipelineSteps("previewed", summary);

    expect(steps.map((step) => step.state)).toEqual(["error", "waiting", "waiting", "waiting", "waiting"]);
    expect(steps[1]?.detail).toBe("无 raw 可映射");
    expect(steps[2]?.detail).toBe("等待有效 raw");
    expect(captureSummaryStatusText(summary)).toBe("Reddit JSON 不可达，DOM 无有效帖子");
  });
});

describe("content command bar page snapshot", () => {
  it("extracts Amazon product context from the current document", () => {
    document.body.innerHTML = `
      <h1 id="productTitle">Aromasong Vanilla Coconut Shea Sugar Scrub</h1>
      <span id="acrCustomerReviewText">355 ratings</span>
      <span id="acrPopover" title="4.4 out of 5 stars"></span>
    `;

    const snapshot = getPageSnapshot(
      {
        platform: "amazon",
        pageKind: "amazon_reviews",
        entryPageKind: "amazon_product_detail",
        asin: "B08MHGST8X"
      },
      document,
      "https://www.amazon.com/Aromasong/dp/B08MHGST8X"
    );

    expect(snapshot.title).toBe("Aromasong Vanilla Coconut Shea Sugar Scrub");
    expect(snapshot.marketplace).toBe("amazon.com");
    expect(snapshot.rating).toBe("4.4");
    expect(snapshot.reviewCount).toBe("355");
  });

  it("extracts Reddit subreddit context from thread URLs", () => {
    document.body.innerHTML = "<h1>Best grinder?</h1>";

    const snapshot = getPageSnapshot(
      {
        platform: "reddit",
        pageKind: "reddit_thread",
        threadId: "thread123"
      },
      document,
      "https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/"
    );

    expect(snapshot.title).toBe("Best grinder?");
    expect(snapshot.subreddit).toBe("r/Coffee");
  });
});
