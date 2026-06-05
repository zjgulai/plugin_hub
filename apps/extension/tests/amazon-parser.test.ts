import { afterEach, describe, expect, it } from "vitest";

import { parseAmazonReviews } from "../src/lib/amazon-parser";
import { assertJsonObject } from "../src/types/contracts";

const BASE_INPUT = {
  asin: "B000000001",
  marketplace: "amazon.com",
  sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=3",
  segment: "critical_reviews",
  capturedAt: "2026-06-05T08:00:00.000Z"
};

describe("parseAmazonReviews", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("parses review fields, pagination context, source_object_id, and core raw_payload fields", () => {
    document.body.innerHTML = `
      <ul class="a-pagination">
        <li class="a-selected"><a href="/product-reviews/B000000001?pageNumber=3">3</a></li>
        <li class="a-last"><a href="/product-reviews/B000000001?pageNumber=4">Next page</a></li>
      </ul>
      <div data-hook="review" id="R1234567890AB">
        <a class="a-profile" href="/gp/profile/amzn1.account.TEST">Reviewer</a>
        <i data-hook="review-star-rating"><span>4.0 out of 5 stars</span></i>
        <a data-hook="review-title" href="/gp/customer-reviews/R1234567890AB/ref=cm_cr_getr_d_rvw_ttl">
          <span>4.0 out of 5 stars</span>
          <span>Works well after a week</span>
        </a>
        <span data-hook="review-body"><span>Battery life is better than expected.</span></span>
        <span data-hook="avp-badge">Verified Purchase</span>
        <span data-hook="helpful-vote-statement">8 people found this helpful</span>
        <img data-hook="review-image-tile" src="/review-image.jpg" />
      </div>
    `;

    const firstResult = parseAmazonReviews({
      ...BASE_INPUT,
      sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
      sortBy: "recent",
      filterByStar: "one_star"
    });
    const secondResult = parseAmazonReviews({
      ...BASE_INPUT,
      sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
      sortBy: "recent",
      filterByStar: "one_star"
    });

    expect(firstResult.stopReason).toBeNull();
    expect(firstResult.nextPageUrl).toBe(
      "https://www.amazon.com/product-reviews/B000000001?pageNumber=4"
    );
    expect(firstResult.rawItems).toHaveLength(1);

    const item = firstResult.rawItems[0];
    expect(item).toEqual(
      expect.objectContaining({
        platform: "amazon",
        source_kind: "amazon_review",
        source_object_id: "R1234567890AB",
        raw_schema_version: "raw_amazon_review_v1",
        parser_version: "amazon-dom-parser@0.1.0",
        captured_at: BASE_INPUT.capturedAt
      })
    );
    expect(item.raw_payload).toEqual(
      expect.objectContaining({
        asin: BASE_INPUT.asin,
        marketplace: BASE_INPUT.marketplace,
        segment: BASE_INPUT.segment,
        source_url: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
        source_object_id: "R1234567890AB",
        review_id: "R1234567890AB",
        rating: 4,
        title: "Works well after a week",
        body: "Battery life is better than expected.",
        verified_purchase: true,
        helpful_vote: 8,
        review_page: 3,
        review_position: 1,
        reviewer_profile_url: "https://www.amazon.com/gp/profile/amzn1.account.TEST",
        media_refs: ["https://www.amazon.com/review-image.jpg"],
        sort_by: "recent",
        filter_by_star: "one_star",
        captured_at: BASE_INPUT.capturedAt
      })
    );
    expect(item.raw_payload_hash).toBe(secondResult.rawItems[0].raw_payload_hash);
  });

  it("returns empty_dom while still parsing a next page link from an empty review DOM", () => {
    document.body.innerHTML = `
      <ul class="a-pagination">
        <li class="a-last"><a href="/product-reviews/B000000001?pageNumber=2">Next page</a></li>
      </ul>
    `;

    const result = parseAmazonReviews(BASE_INPUT);

    expect(result.rawItems).toEqual([]);
    expect(result.stopReason).toBe("empty_dom");
    expect(result.nextPageUrl).toBe(
      "https://www.amazon.com/product-reviews/B000000001?pageNumber=2"
    );
  });

  it("returns null when the DOM has no next page link", () => {
    document.body.innerHTML = `
      <div data-hook="review" id="RNO_NEXT_LINK">
        <i data-hook="review-star-rating"><span>5.0 out of 5 stars</span></i>
        <span data-hook="review-body"><span>No pagination after this review.</span></span>
      </div>
    `;

    expect(parseAmazonReviews(BASE_INPUT).nextPageUrl).toBeNull();
  });

  it("parses singular helpful vote text", () => {
    document.body.innerHTML = `
      <div data-hook="review" id="RONEHELPFUL">
        <span data-hook="helpful-vote-statement">One person found this helpful</span>
      </div>
    `;

    const [item] = parseAmazonReviews(BASE_INPUT).rawItems;

    expect(item.raw_payload.helpful_vote).toBe(1);
  });

  it("falls back to the sourceUrl pageNumber query parameter and stable missing review id", () => {
    document.body.innerHTML = `
      <div data-hook="review">
        <span data-hook="review-body"><span>Review without a native id.</span></span>
      </div>
    `;

    const [item] = parseAmazonReviews({
      ...BASE_INPUT,
      sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=5"
    }).rawItems;

    expect(item.source_object_id).toBe("missing_review_5_1");
    expect(item.raw_payload.review_id).toBe("missing_review_5_1");
    expect(item.raw_payload.review_page).toBe(5);
  });

  it("keeps unparsable numeric fields null so raw_payload remains JSON-safe", () => {
    document.body.innerHTML = `
      <div data-hook="review" id="RBADNUMBERS">
        <i data-hook="review-star-rating"><span>Not a rating</span></i>
        <span data-hook="helpful-vote-statement">Several people found this helpful</span>
      </div>
    `;

    const [item] = parseAmazonReviews(BASE_INPUT).rawItems;

    expect(item.raw_payload.rating).toBeNull();
    expect(item.raw_payload.helpful_vote).toBeNull();
    expect(() => assertJsonObject(item.raw_payload)).not.toThrow();
  });

  it("falls back from invalid capturedAt without aborting page parsing", () => {
    document.body.innerHTML = `
      <div data-hook="review" id="RBADTIME">
        <span data-hook="review-body"><span>Still parse this review.</span></span>
      </div>
    `;

    const [item] = parseAmazonReviews({
      ...BASE_INPUT,
      capturedAt: "not-a-date"
    }).rawItems;

    expect(item.captured_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(item.raw_payload.captured_at).toBe(item.captured_at);
  });

  it("drops non-http urls from pagination, reviewer profile, and media refs", () => {
    document.body.innerHTML = `
      <ul class="a-pagination">
        <li class="a-last"><a href="javascript:alert(1)">Next page</a></li>
      </ul>
      <div data-hook="review" id="RBADURLS">
        <a class="a-profile" href="javascript:alert(1)">Reviewer</a>
        <img data-hook="review-image-tile" src="data:image/png;base64,AAAA" />
        <video src="blob:https://www.amazon.com/review-video"></video>
      </div>
    `;

    const result = parseAmazonReviews(BASE_INPUT);
    const [item] = result.rawItems;

    expect(result.nextPageUrl).toBeNull();
    expect(item.raw_payload.reviewer_profile_url).toBeNull();
    expect(item.raw_payload.media_refs).toEqual([]);
  });

  it("parses selected page text when Amazon renders pagination without an anchor", () => {
    document.body.innerHTML = `
      <ul class="a-pagination">
        <li class="a-selected"><span>6</span></li>
      </ul>
      <div data-hook="review">
        <span data-hook="review-body"><span>Review on selected span page.</span></span>
      </div>
    `;

    const [item] = parseAmazonReviews({
      ...BASE_INPUT,
      sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2"
    }).rawItems;

    expect(item.raw_payload.review_page).toBe(6);
    expect(item.source_object_id).toBe("missing_review_6_1");
  });
});
