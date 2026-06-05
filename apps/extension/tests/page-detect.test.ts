import { describe, expect, it } from "vitest";

import { detectPage } from "../src/lib/page-detect";

describe("detectPage", () => {
  it("detects Amazon review pages", () => {
    expect(
      detectPage("https://www.amazon.com/product-reviews/B000000001/ref=cm_cr_dp_d_show_all_btm")
    ).toEqual({
      platform: "amazon",
      pageKind: "amazon_reviews",
      asin: "B000000001"
    });
  });

  it("detects Amazon review pages on supported marketplaces", () => {
    expect(detectPage("https://www.amazon.co.uk/product-reviews/B000000001")).toEqual({
      platform: "amazon",
      pageKind: "amazon_reviews",
      asin: "B000000001"
    });
  });

  it("detects Reddit thread pages", () => {
    expect(
      detectPage("https://www.reddit.com/r/example/comments/thread123/example_title/")
    ).toEqual({
      platform: "reddit",
      pageKind: "reddit_thread",
      threadId: "thread123"
    });
  });

  it("returns unknown for unsupported URLs", () => {
    expect(detectPage("https://example.com/products/B000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
  });

  it("returns unknown for invalid URL strings", () => {
    expect(detectPage("not a valid url")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
  });

  it("does not detect lowercase or invalid Amazon ASINs", () => {
    expect(detectPage("https://www.amazon.com/product-reviews/b000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
    expect(detectPage("https://www.amazon.com/product-reviews/B00000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
  });

  it("does not detect spoofed Amazon hostnames", () => {
    expect(detectPage("https://amazon.com.evil.example/product-reviews/B000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
    expect(detectPage("https://amazon.co.uk.evil.example/product-reviews/B000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
    expect(detectPage("https://www.amazon.evil.example/product-reviews/B000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
    expect(detectPage("https://notamazon.com/product-reviews/B000000001")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
  });

  it("does not detect non-thread Reddit URLs", () => {
    expect(detectPage("https://www.reddit.com/r/example/")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
    expect(detectPage("https://www.reddit.com/r/example/search/?q=thread123")).toEqual({
      platform: "unknown",
      pageKind: "unknown"
    });
  });
});
