import type { DetectedPage } from "../../lib/page-detect";

export type PageSnapshot = {
  title: string | null;
  marketplace: string | null;
  rating: string | null;
  reviewCount: string | null;
  subreddit: string | null;
};

export function getPageSnapshot(detectedPage: DetectedPage, documentRoot: Document, sourceUrl: string): PageSnapshot {
  if (detectedPage.platform === "amazon") {
    return {
      title: textFromSelector(documentRoot, "#productTitle") ?? textFromSelector(documentRoot, "h1"),
      marketplace: marketplaceFromUrl(sourceUrl),
      rating: extractAmazonRating(documentRoot),
      reviewCount: extractAmazonReviewCount(documentRoot),
      subreddit: null
    };
  }

  if (detectedPage.platform === "reddit") {
    return {
      title:
        textFromSelector(documentRoot, "shreddit-post h1") ??
        textFromSelector(documentRoot, "[slot='title']") ??
        textFromSelector(documentRoot, "h1"),
      marketplace: null,
      rating: null,
      reviewCount: null,
      subreddit: subredditFromUrl(sourceUrl)
    };
  }

  return {
    title: null,
    marketplace: null,
    rating: null,
    reviewCount: null,
    subreddit: null
  };
}

function extractAmazonRating(documentRoot: Document): string | null {
  const raw =
    textFromSelector(documentRoot, "[data-hook='rating-out-of-text']") ??
    textFromSelector(documentRoot, "#acrPopover [class*='a-icon-alt']") ??
    attributeFromSelector(documentRoot, "#acrPopover", "title");

  return raw ? normalizeRatingText(raw) : null;
}

function extractAmazonReviewCount(documentRoot: Document): string | null {
  const raw = textFromSelector(documentRoot, "#acrCustomerReviewText");
  if (!raw) {
    return null;
  }

  const match = raw.match(/[\d,.]+/);
  return match?.[0] ?? raw;
}

function normalizeRatingText(value: string): string {
  const match = value.match(/\d+(?:\.\d+)?/);
  return match?.[0] ?? value;
}

function marketplaceFromUrl(sourceUrl: string): string | null {
  try {
    return new URL(sourceUrl).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function subredditFromUrl(sourceUrl: string): string | null {
  try {
    const [, subredditPrefix, subreddit] = new URL(sourceUrl).pathname.split("/");
    return subredditPrefix === "r" && subreddit ? `r/${subreddit}` : null;
  } catch {
    return null;
  }
}

function textFromSelector(documentRoot: Document, selector: string): string | null {
  const text = documentRoot.querySelector(selector)?.textContent?.trim().replace(/\s+/g, " ");
  return text || null;
}

function attributeFromSelector(documentRoot: Document, selector: string, attributeName: string): string | null {
  const value = documentRoot.querySelector(selector)?.getAttribute(attributeName)?.trim();
  return value || null;
}
