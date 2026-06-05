type DetectedPage =
  | {
      platform: "amazon";
      pageKind: "amazon_reviews";
      asin: string;
    }
  | {
      platform: "reddit";
      pageKind: "reddit_thread";
      threadId: string;
    }
  | {
      platform: "unknown";
      pageKind: "unknown";
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

const detectedPage = detectCurrentPage(window.location.href);

window.dispatchEvent(
  new CustomEvent("plugin-hub-page-detected", {
    detail: detectedPage
  })
);

function detectCurrentPage(url: string): DetectedPage {
  let parsedUrl: URL;

  try {
    parsedUrl = new URL(url);
  } catch {
    return unknownPage();
  }

  const hostname = parsedUrl.hostname.toLowerCase();
  const pathSegments = parsedUrl.pathname.split("/").filter(Boolean);

  if (AMAZON_ALLOWED_HOSTNAMES.has(hostname)) {
    return detectAmazonReviewsPage(pathSegments);
  }

  if (hostname === "reddit.com" || hostname === "www.reddit.com" || hostname === "old.reddit.com") {
    return detectRedditThreadPage(pathSegments);
  }

  return unknownPage();
}

function detectAmazonReviewsPage(pathSegments: string[]): DetectedPage {
  const productReviewsIndex = pathSegments.indexOf("product-reviews");
  const asin = productReviewsIndex === -1 ? null : pathSegments[productReviewsIndex + 1];

  if (!asin || !AMAZON_ASIN_PATTERN.test(asin)) {
    return unknownPage();
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
    return unknownPage();
  }

  return {
    platform: "reddit",
    pageKind: "reddit_thread",
    threadId
  };
}

function unknownPage(): DetectedPage {
  return {
    platform: "unknown",
    pageKind: "unknown"
  };
}
