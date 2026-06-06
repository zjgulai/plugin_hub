import { beforeEach, describe, expect, it } from "vitest";

import { buildRedditJsonUrl, captureCurrentPage, inferMarketplace } from "../src/lib/capture";

const CAPTURED_AT = "2026-06-06T00:00:00.000Z";

describe("captureCurrentPage", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("captures Amazon reviews by following next-page links within the page budget", async () => {
    document.body.innerHTML = amazonPageHtml({
      reviewId: "R1",
      body: "The lid leaks after a week.",
      nextHref: "/product-reviews/B000000001?pageNumber=2"
    });
    const fetchedUrls: string[] = [];

    const result = await captureCurrentPage({
      url: "https://www.amazon.com/product-reviews/B000000001?pageNumber=1",
      capturedAt: CAPTURED_AT,
      documentRoot: document,
      fetchText: async (url) => {
        fetchedUrls.push(url);
        return amazonPageHtml({
          reviewId: "R2",
          body: "The replacement worked better."
        });
      }
    });

    expect(fetchedUrls).toEqual([
      "https://www.amazon.com/product-reviews/B000000001?pageNumber=2"
    ]);
    expect(result.payload.run.platform).toBe("amazon");
    expect(result.payload.run.capture_method).toBe("extension_dom_next_link_walk");
    expect(result.payload.run.stop_reason).toBe("no_next_page");
    expect(result.payload.run.coverage_scope.pages).toEqual([
      {
        url: "https://www.amazon.com/product-reviews/B000000001?pageNumber=1",
        observed_page: 1,
        raw_item_count: 1,
        next_page_url: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2"
      },
      {
        url: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
        observed_page: 2,
        raw_item_count: 1,
        next_page_url: null
      }
    ]);
    expect(result.summary.raw_item_count).toBe(2);
    expect(result.payload.raw_items.map((item) => item.source_object_id)).toEqual(["R1", "R2"]);
  });

  it("captures Reddit threads through the .json entrypoint", async () => {
    const result = await captureCurrentPage({
      url: "https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/",
      capturedAt: CAPTURED_AT,
      fetchJson: async (url) => {
        expect(url).toBe(
          "https://www.reddit.com/r/Coffee/comments/thread123/best_grinder/.json?raw_json=1"
        );
        return redditThreadPayload();
      }
    });

    expect(result.payload.run.platform).toBe("reddit");
    expect(result.payload.run.capture_method).toBe("extension_reddit_json");
    expect(result.payload.run.stop_reason).toBe("more_nodes_not_expanded");
    expect(result.payload.run.coverage_scope.more_node_count).toBe(1);
    expect(result.payload.raw_items.map((item) => item.source_object_id)).toEqual([
      "t3_thread123",
      "t1_comment456",
      "more_more789"
    ]);
  });

  it("rejects unsupported pages before building upload payloads", async () => {
    await expect(
      captureCurrentPage({
        url: "https://example.com/products/B000000001"
      })
    ).rejects.toThrow("unsupported_page");
  });
});

describe("capture helpers", () => {
  it("builds Reddit JSON URLs and infers Amazon marketplaces", () => {
    expect(buildRedditJsonUrl("https://www.reddit.com/r/Coffee/comments/thread123/title/")).toBe(
      "https://www.reddit.com/r/Coffee/comments/thread123/title/.json?raw_json=1"
    );
    expect(inferMarketplace("https://www.amazon.co.uk/product-reviews/B000000001")).toBe(
      "amazon.co.uk"
    );
  });
});

function amazonPageHtml({
  reviewId,
  body,
  nextHref
}: {
  reviewId: string;
  body: string;
  nextHref?: string;
}) {
  const pageNumber = nextHref ? "1" : "2";
  return `
    <main>
      <ul><li class="a-selected">${pageNumber}</li></ul>
      <div data-hook="review" data-review-id="${reviewId}">
        <i data-hook="review-star-rating">4.0 out of 5 stars</i>
        <a data-hook="review-title"><span>Useful detail</span></a>
        <span data-hook="review-body">${body}</span>
      </div>
      ${nextHref ? `<ul><li class="a-last"><a href="${nextHref}">Next</a></li></ul>` : ""}
    </main>
  `;
}

function redditThreadPayload(): unknown {
  return [
    {
      data: {
        children: [
          {
            kind: "t3",
            data: {
              name: "t3_thread123",
              id: "thread123",
              title: "Best grinder?",
              selftext: "Looking for a quieter grinder.",
              author: "buyer",
              subreddit: "Coffee",
              created_utc: 1780602718,
              score: 42
            }
          }
        ]
      }
    },
    {
      data: {
        children: [
          {
            kind: "t1",
            data: {
              name: "t1_comment456",
              id: "comment456",
              body: "Motor noise is the real issue.",
              parent_id: "t3_thread123",
              link_id: "t3_thread123",
              depth: 0,
              replies: ""
            }
          },
          {
            kind: "more",
            data: {
              id: "more789",
              parent_id: "t3_thread123",
              children: ["comment789"],
              depth: 0
            }
          }
        ]
      }
    }
  ];
}
