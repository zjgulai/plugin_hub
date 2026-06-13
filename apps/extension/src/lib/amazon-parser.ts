import {
  assertJsonObject,
  type JsonObject,
  type JsonValue,
  type RawSourceItem
} from "../types/contracts";

const PLATFORM = "amazon";
const SOURCE_KIND = "amazon_review";
const RAW_SCHEMA_VERSION = "raw_amazon_review_v1";
const PARSER_VERSION = "amazon-dom-parser@0.1.0";

export interface ParseAmazonReviewsInput {
  asin: string;
  marketplace: string;
  sourceUrl: string;
  segment: string;
  sortBy?: string | null;
  filterByStar?: string | null;
  capturedAt?: string;
  root?: ParentNode;
}

export interface ParseAmazonReviewsResult {
  rawItems: RawSourceItem[];
  stopReason: "empty_dom" | null;
  nextPageUrl: string | null;
}

export function parseAmazonReviews(input: ParseAmazonReviewsInput): ParseAmazonReviewsResult {
  const root = resolveRoot(input.root);
  const capturedAt = parseCapturedAt(input.capturedAt);
  const nextPageUrl = parseNextPageUrl(root, input.sourceUrl);
  const reviewPage = parseReviewPage(root, input.sourceUrl);
  const reviews = collectReviewContainers(root);

  if (reviews.length === 0) {
    return {
      rawItems: [],
      stopReason: "empty_dom",
      nextPageUrl
    };
  }

  return {
    rawItems: reviews.map((review, index) =>
      buildRawSourceItem({
        review,
        input,
        capturedAt,
        reviewPage,
        reviewPosition: index + 1
      })
    ),
    stopReason: null,
    nextPageUrl
  };
}

function buildRawSourceItem({
  review,
  input,
  capturedAt,
  reviewPage,
  reviewPosition
}: {
  review: HTMLElement;
  input: ParseAmazonReviewsInput;
  capturedAt: string;
  reviewPage: number | null;
  reviewPosition: number;
}): RawSourceItem {
  const reviewId = parseReviewId(review, reviewPage, reviewPosition);
  const sourceObjectId = reviewId;
  const rawPayload = {
    platform: PLATFORM,
    source_kind: SOURCE_KIND,
    source_object_id: sourceObjectId,
    asin: input.asin,
    marketplace: input.marketplace,
    source_url: input.sourceUrl,
    segment: input.segment,
    sort_by: input.sortBy ?? null,
    filter_by_star: input.filterByStar ?? input.segment,
    review_id: reviewId,
    rating: parseRating(review),
    title: parseReviewTitle(review),
    body: parseReviewBody(review),
    verified_purchase: parseVerifiedPurchase(review),
    helpful_vote: parseHelpfulVote(review),
    review_page: reviewPage,
    review_position: reviewPosition,
    reviewer_profile_url: parseReviewerProfileUrl(review, input.sourceUrl),
    media_refs: parseMediaRefs(review, input.sourceUrl),
    captured_at: capturedAt,
    raw_schema_version: RAW_SCHEMA_VERSION,
    parser_version: PARSER_VERSION
  } satisfies JsonObject;

  assertJsonObject(rawPayload);

  return {
    platform: PLATFORM,
    source_kind: SOURCE_KIND,
    source_object_id: sourceObjectId,
    raw_schema_version: RAW_SCHEMA_VERSION,
    parser_version: PARSER_VERSION,
    raw_payload: rawPayload,
    raw_payload_hash: stableHash(rawPayload),
    captured_at: capturedAt
  };
}

function resolveRoot(root: ParentNode | undefined): ParentNode {
  if (root) {
    return root;
  }

  if (typeof document === "undefined") {
    throw new TypeError("document_required");
  }

  return document;
}

function parseReviewId(review: HTMLElement, reviewPage: number | null, reviewPosition: number): string {
  const explicitId = normalizeNullable(
    review.getAttribute("data-review-id") ?? review.getAttribute("id")
  );

  if (explicitId) {
    return explicitId;
  }

  const reviewLinkId = parseReviewIdFromLink(review);

  if (reviewLinkId) {
    return reviewLinkId;
  }

  return `missing_review_${reviewPage ?? "unknown"}_${reviewPosition}`;
}

function parseRating(review: HTMLElement): number | null {
  const ratingElement = review.querySelector(
    '[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]'
  );
  const ratingText = normalizeNullable(
    ratingElement?.getAttribute("aria-label") ?? ratingElement?.textContent ?? null
  );

  if (!ratingText) {
    return null;
  }

  const match = ratingText.match(/(\d+(?:\.\d+)?)\s*out\s*of\s*5/i);
  if (!match) {
    return null;
  }

  return parseFiniteNumber(match[1]);
}

function parseReviewTitle(review: HTMLElement): string | null {
  const titleElement = review.querySelector(
    '[data-hook="review-title"], a[href*="/review/"], a[href*="/gp/customer-reviews/"]'
  );

  if (!titleElement) {
    return null;
  }

  const spanTitle = Array.from(titleElement.querySelectorAll("span"))
    .map((span) => normalizeNullable(span.textContent))
    .filter((text): text is string => text !== null)
    .reverse()
    .find((text) => !isRatingText(text));

  if (spanTitle) {
    return spanTitle;
  }

  const titleText = normalizeNullable(titleElement.textContent);
  return titleText ? stripRatingPrefix(titleText) : null;
}

function parseReviewBody(review: HTMLElement): string | null {
  const bodyElement = review.querySelector(
    [
      '[data-hook="review-body"]',
      '[data-hook="reviewRichContentContainer"]',
      '[data-hook="reviewTextContainer"] [data-hook="reviewText"]',
      '[data-hook="reviewText"]'
    ].join(", ")
  );
  const bodyText = normalizeNullable(bodyElement?.textContent ?? null);

  return bodyText ? cleanAmazonReviewBodyText(bodyText) : null;
}

function parseVerifiedPurchase(review: HTMLElement): boolean {
  const badgeText = normalizeNullable(review.querySelector('[data-hook="avp-badge"]')?.textContent ?? null);
  return badgeText?.toLowerCase().includes("verified purchase") ?? false;
}

function parseHelpfulVote(review: HTMLElement): number | null {
  const helpfulText = normalizeNullable(
    review.querySelector('[data-hook="helpful-vote-statement"]')?.textContent ?? null
  );

  if (!helpfulText) {
    return null;
  }

  if (/^one\s+person\s+found\s+this\s+helpful$/i.test(helpfulText)) {
    return 1;
  }

  const match = helpfulText.match(/([\d,]+)\s+(?:person|people)\s+found\s+this\s+helpful/i);
  if (!match) {
    return null;
  }

  return parsePositiveInteger(match[1].replace(/,/g, ""));
}

function parseReviewerProfileUrl(review: HTMLElement, sourceUrl: string): string | null {
  const profileLink = review.querySelector<HTMLAnchorElement>(
    '[data-hook="genome-widget"] a[href], a.a-profile[href], .a-profile[href]'
  );

  return toAbsoluteUrl(profileLink?.getAttribute("href") ?? null, sourceUrl);
}

function parseMediaRefs(review: HTMLElement, sourceUrl: string): string[] {
  const mediaElements = Array.from(
    review.querySelectorAll(
      [
        '[data-hook="review-image-tile"][src]',
        '[data-hook="review-image-tile"] img[src]',
        "img.review-image-tile[src]",
        "video[src]",
        "video source[src]"
      ].join(", ")
    )
  );
  const mediaRefs = new Set<string>();

  for (const element of mediaElements) {
    const absoluteUrl = toAbsoluteUrl(element.getAttribute("src"), sourceUrl);

    if (absoluteUrl) {
      mediaRefs.add(absoluteUrl);
    }
  }

  return Array.from(mediaRefs);
}

function collectReviewContainers(root: ParentNode): HTMLElement[] {
  const reviewElements = Array.from(
    root.querySelectorAll<HTMLElement>('[data-hook="review"], [id^="customer_review-"], [id^="customer_review_"]')
  );
  const seen = new Set<HTMLElement>();
  const uniqueReviewElements: HTMLElement[] = [];

  for (const reviewElement of reviewElements) {
    if (!seen.has(reviewElement)) {
      seen.add(reviewElement);
      uniqueReviewElements.push(reviewElement);
    }
  }

  return uniqueReviewElements;
}

function parseReviewIdFromLink(review: HTMLElement): string | null {
  const reviewLink = review.querySelector<HTMLAnchorElement>(
    'a[href*="/review/"], a[href*="/gp/customer-reviews/"]'
  );
  const href = normalizeNullable(reviewLink?.getAttribute("href") ?? null);

  if (!href) {
    return null;
  }

  const match = href.match(/\/(?:review|gp\/customer-reviews)\/(R[A-Z0-9]+)/i);
  return match?.[1] ?? null;
}

function parseNextPageUrl(root: ParentNode, sourceUrl: string): string | null {
  const nextLink = root.querySelector<HTMLAnchorElement>("li.a-last a[href]");
  return toAbsoluteUrl(nextLink?.getAttribute("href") ?? null, sourceUrl);
}

function parseReviewPage(root: ParentNode, sourceUrl: string): number | null {
  const selectedPageText = normalizeNullable(root.querySelector(".a-selected")?.textContent ?? null);
  const selectedPage = selectedPageText ? parsePositiveInteger(selectedPageText) : null;

  if (selectedPage !== null) {
    return selectedPage;
  }

  try {
    return parsePositiveInteger(new URL(sourceUrl).searchParams.get("pageNumber"));
  } catch {
    return null;
  }
}

function parseCapturedAt(value: string | undefined): string {
  const parsedDate = value ? new Date(value) : new Date();

  if (Number.isNaN(parsedDate.getTime())) {
    return new Date().toISOString();
  }

  return parsedDate.toISOString();
}

function toAbsoluteUrl(value: string | null, sourceUrl: string): string | null {
  const normalizedValue = normalizeNullable(value);

  if (!normalizedValue) {
    return null;
  }

  try {
    const parsedUrl = new URL(normalizedValue, sourceUrl);

    if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
      return null;
    }

    return parsedUrl.toString();
  } catch {
    return null;
  }
}

function normalizeNullable(value: string | null | undefined): string | null {
  const normalized = value?.replace(/\s+/g, " ").trim() ?? "";
  return normalized.length > 0 ? normalized : null;
}

function stripRatingPrefix(value: string): string | null {
  const stripped = value.replace(/^\d+(?:\.\d+)?\s*out\s*of\s*5\s*stars\s*/i, "").trim();
  return stripped.length > 0 ? stripped : null;
}

function cleanAmazonReviewBodyText(value: string): string | null {
  const cleaned = value
    .replace(/Brief content visible,\s*double tap to read full content\./gi, " ")
    .replace(/Full content visible,\s*double tap to read brief content\./gi, " ")
    .replace(/Read moreRead less/gi, " ")
    .replace(/\bRead more\b/gi, " ")
    .replace(/\bRead less\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();

  return cleaned.length > 0 ? cleaned : null;
}

function isRatingText(value: string): boolean {
  return /^\d+(?:\.\d+)?\s*out\s*of\s*5\s*stars$/i.test(value);
}

function parseFiniteNumber(value: string): number | null {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parsePositiveInteger(value: string | null): number | null {
  if (!value) {
    return null;
  }

  const normalizedValue = value.replace(/,/g, "").trim();
  if (!/^\d+$/.test(normalizedValue)) {
    return null;
  }

  const parsed = Number.parseInt(normalizedValue, 10);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function stableHash(value: JsonValue): string {
  const canonicalValue = stableStringify(value);
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;

  for (let index = 0; index < canonicalValue.length; index += 1) {
    hash ^= BigInt(canonicalValue.charCodeAt(index));
    hash = BigInt.asUintN(64, hash * prime);
  }

  return `fnv1a64:${hash.toString(16).padStart(16, "0")}`;
}

function stableStringify(value: JsonValue): string {
  if (value === null) {
    return "null";
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }

  switch (typeof value) {
    case "string":
    case "number":
    case "boolean":
      return JSON.stringify(value);
    case "object":
      return `{${Object.entries(value)
        .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
        .map(([key, nestedValue]) => `${JSON.stringify(key)}:${stableStringify(nestedValue)}`)
        .join(",")}}`;
  }

  throw new TypeError("unsupported_json_value");
}
