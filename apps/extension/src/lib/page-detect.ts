export type AmazonReviewsPage = {
  platform: "amazon";
  pageKind: "amazon_reviews";
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
const AMAZON_BASE_HOSTNAME = "amazon.com";

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
    return detectAmazonReviewsPage(pathSegments);
  }

  if (isRedditHostname(hostname)) {
    return detectRedditThreadPage(pathSegments);
  }

  return UNKNOWN_PAGE;
}

function isAmazonHostname(hostname: string): boolean {
  return hostname === AMAZON_BASE_HOSTNAME || hostname.endsWith(`.${AMAZON_BASE_HOSTNAME}`);
}

function isRedditHostname(hostname: string): boolean {
  return hostname === "reddit.com" || hostname === "www.reddit.com" || hostname === "old.reddit.com";
}

function detectAmazonReviewsPage(pathSegments: string[]): DetectedPage {
  const productReviewsIndex = pathSegments.indexOf("product-reviews");

  if (productReviewsIndex === -1) {
    return UNKNOWN_PAGE;
  }

  const asin = pathSegments[productReviewsIndex + 1];

  if (!asin || !AMAZON_ASIN_PATTERN.test(asin)) {
    return UNKNOWN_PAGE;
  }

  return {
    platform: "amazon",
    pageKind: "amazon_reviews",
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
