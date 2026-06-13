export type AmazonReviewsPage = {
  platform: "amazon";
  pageKind: "amazon_reviews";
  entryPageKind: "amazon_reviews" | "amazon_product_detail";
  asin: string;
};

export type RedditThreadPage = {
  platform: "reddit";
  pageKind: "reddit_thread";
  threadId: string;
};

export type UnknownPage = {
  platform: "unknown";
  pageKind: "unknown";
};

export type DetectedPage = AmazonReviewsPage | RedditThreadPage | UnknownPage;

const UNKNOWN_PAGE: UnknownPage = {
  platform: "unknown",
  pageKind: "unknown"
};

const AMAZON_ASIN_PATTERN = /^[A-Z0-9]{10}$/;
const REDDIT_THREAD_ID_PATTERN = /^[A-Za-z0-9_]+$/;
const AMAZON_ALLOWED_HOSTNAMES = new Set([
  "amazon.com",
  "www.amazon.com",
  "smile.amazon.com",
  "amazon.co.uk",
  "www.amazon.co.uk",
  "amazon.de",
  "www.amazon.de",
  "amazon.ca",
  "www.amazon.ca",
  "amazon.com.au",
  "www.amazon.com.au",
  "amazon.co.jp",
  "www.amazon.co.jp"
]);

export function detectPage(url: string): DetectedPage {
  let parsedUrl: URL;

  try {
    parsedUrl = new URL(url);
  } catch {
    return UNKNOWN_PAGE;
  }

  const hostname = parsedUrl.hostname.toLowerCase();
  const pathSegments = parsedUrl.pathname.split("/").filter(Boolean);

  if (isAmazonHostname(hostname)) {
    return detectAmazonPage(pathSegments);
  }

  if (isRedditHostname(hostname)) {
    return detectRedditThreadPage(pathSegments);
  }

  return UNKNOWN_PAGE;
}

function isAmazonHostname(hostname: string): boolean {
  return AMAZON_ALLOWED_HOSTNAMES.has(hostname);
}

function isRedditHostname(hostname: string): boolean {
  return hostname === "reddit.com" || hostname === "www.reddit.com" || hostname === "old.reddit.com";
}

function detectAmazonPage(pathSegments: string[]): DetectedPage {
  const productReviewsIndex = pathSegments.indexOf("product-reviews");

  if (productReviewsIndex !== -1) {
    return buildAmazonReviewsPage(pathSegments[productReviewsIndex + 1], "amazon_reviews");
  }

  const dpIndex = pathSegments.indexOf("dp");
  if (dpIndex !== -1) {
    return buildAmazonReviewsPage(pathSegments[dpIndex + 1], "amazon_product_detail");
  }

  if (pathSegments[0] === "gp" && pathSegments[1] === "product") {
    return buildAmazonReviewsPage(pathSegments[2], "amazon_product_detail");
  }

  return UNKNOWN_PAGE;
}

function buildAmazonReviewsPage(
  asin: string | undefined,
  entryPageKind: AmazonReviewsPage["entryPageKind"]
): DetectedPage {
  if (!asin || !AMAZON_ASIN_PATTERN.test(asin)) {
    return UNKNOWN_PAGE;
  }

  return {
    platform: "amazon",
    pageKind: "amazon_reviews",
    entryPageKind,
    asin
  };
}

function detectRedditThreadPage(pathSegments: string[]): DetectedPage {
  const [subredditPrefix, subreddit, commentsPrefix, threadId] = pathSegments;

  if (
    subredditPrefix !== "r" ||
    !subreddit ||
    commentsPrefix !== "comments" ||
    !threadId ||
    !REDDIT_THREAD_ID_PATTERN.test(threadId)
  ) {
    return UNKNOWN_PAGE;
  }

  return {
    platform: "reddit",
    pageKind: "reddit_thread",
    threadId
  };
}
