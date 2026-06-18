import { parseAmazonReviews } from "./amazon-parser";
import type { CaptureCurrentPageInput } from "./capture-types";
import { detectAmazonPageUrl, type AmazonReviewsPage } from "./page-detect";
import type { CollectionRunPayload, RawSourceItem } from "../types/contracts";
import type { CaptureCurrentPageSuccess } from "../types/messages";

const AMAZON_PAGE_LIMIT = 3;

interface AmazonPageEvidence {
  url: string;
  observed_page: number | null;
  raw_item_count: number;
  next_page_url: string | null;
}

export async function captureAmazonCurrentPage(
  input: CaptureCurrentPageInput
): Promise<CaptureCurrentPageSuccess> {
  const detectedPage = detectAmazonPageUrl(input.url);

  if (detectedPage.platform !== "amazon") {
    throw new Error("unsupported_page");
  }

  return captureAmazonReviews({
    ...input,
    entryPageKind: detectedPage.entryPageKind,
    asin: detectedPage.asin
  });
}

async function captureAmazonReviews(
  input: CaptureCurrentPageInput & {
    asin: string;
    entryPageKind: AmazonReviewsPage["entryPageKind"];
  }
): Promise<CaptureCurrentPageSuccess> {
  const capturedAt = parseCapturedAt(input.capturedAt);
  const initialUrl = input.url;
  const marketplace = inferMarketplace(initialUrl);
  const rawItems: RawSourceItem[] = [];
  const pages: AmazonPageEvidence[] = [];
  const seenPageUrls = new Set<string>();
  const seenSourceObjectIds = new Set<string>();
  let pageUrl = initialUrl;
  let pageRoot = input.documentRoot ?? resolveDocumentRoot();
  let stopReason: string | null = null;

  for (let pageIndex = 1; pageIndex <= AMAZON_PAGE_LIMIT; pageIndex += 1) {
    if (seenPageUrls.has(pageUrl)) {
      stopReason = "duplicate_next_page_url";
      break;
    }
    seenPageUrls.add(pageUrl);

    const result = parseAmazonReviews({
      asin: input.asin,
      marketplace,
      sourceUrl: pageUrl,
      segment: "current_review_segment",
      sortBy: readSearchParam(initialUrl, "sortBy"),
      filterByStar: readSearchParam(initialUrl, "filterByStar"),
      capturedAt,
      root: pageRoot
    });

    const newItems = result.rawItems.filter((item) => {
      if (seenSourceObjectIds.has(item.source_object_id)) {
        return false;
      }
      seenSourceObjectIds.add(item.source_object_id);
      return true;
    });
    rawItems.push(...newItems);
    pages.push({
      url: pageUrl,
      observed_page: observedAmazonPage(result.rawItems),
      raw_item_count: newItems.length,
      next_page_url: result.nextPageUrl
    });

    if (result.stopReason) {
      stopReason = result.stopReason;
      break;
    }

    if (!result.nextPageUrl) {
      stopReason = "no_next_page";
      break;
    }

    if (pageIndex === AMAZON_PAGE_LIMIT) {
      stopReason = "page_budget_reached";
      break;
    }

    try {
      pageUrl = result.nextPageUrl;
      pageRoot = parseHtmlRoot(
        await (input.fetchText ?? defaultFetchText)(result.nextPageUrl),
        input.parseHtml
      );
    } catch {
      stopReason = "page_fetch_failed";
      break;
    }
  }

  const coverageConfidence = amazonCoverageConfidence(
    rawItems.length,
    stopReason,
    input.entryPageKind
  );
  const payload: CollectionRunPayload = {
    run: {
      platform: "amazon",
      source_url: initialUrl,
      capture_method:
        input.entryPageKind === "amazon_product_detail"
          ? "extension_dom_embedded_reviews"
          : "extension_dom_next_link_walk",
      coverage_scope: {
        collector_app: "amazon_extension",
        page_kind: "amazon_reviews",
        entry_page_kind: input.entryPageKind,
        asin: input.asin,
        marketplace,
        page_limit: AMAZON_PAGE_LIMIT,
        pages: pages.map((page) => ({
          url: page.url,
          observed_page: page.observed_page,
          raw_item_count: page.raw_item_count,
          next_page_url: page.next_page_url
        }))
      },
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    },
    raw_items: rawItems
  };

  return {
    payload,
    summary: {
      platform: "amazon",
      page_kind: "amazon_reviews",
      raw_item_count: rawItems.length,
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    }
  };
}

export function inferMarketplace(sourceUrl: string): string {
  try {
    return new URL(sourceUrl).hostname.replace(/^www\./, "");
  } catch {
    return "unknown";
  }
}

function parseCapturedAt(value: string | undefined): string {
  const parsedDate = value ? new Date(value) : new Date();
  return Number.isNaN(parsedDate.getTime()) ? new Date().toISOString() : parsedDate.toISOString();
}

function resolveDocumentRoot(): ParentNode {
  if (typeof document === "undefined") {
    throw new Error("document_required");
  }
  return document;
}

function parseHtmlRoot(html: string, parseHtml: ((html: string) => ParentNode) | undefined): ParentNode {
  if (parseHtml) {
    return parseHtml(html);
  }

  if (typeof DOMParser === "undefined") {
    throw new Error("dom_parser_required");
  }

  return new DOMParser().parseFromString(html, "text/html");
}

async function defaultFetchText(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`page_fetch_failed:${response.status}`);
  }
  return response.text();
}

function readSearchParam(sourceUrl: string, key: string): string | null {
  try {
    return new URL(sourceUrl).searchParams.get(key);
  } catch {
    return null;
  }
}

function observedAmazonPage(rawItems: RawSourceItem[]): number | null {
  const value = rawItems[0]?.raw_payload.review_page;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function amazonCoverageConfidence(
  rawItemCount: number,
  stopReason: string | null,
  entryPageKind: AmazonReviewsPage["entryPageKind"]
): number {
  if (rawItemCount === 0) {
    return 0.2;
  }
  if (entryPageKind === "amazon_product_detail") {
    return stopReason === "page_budget_reached" ? 0.62 : 0.58;
  }
  if (stopReason === "no_next_page") {
    return 0.9;
  }
  if (stopReason === "page_budget_reached") {
    return 0.72;
  }
  return 0.55;
}
