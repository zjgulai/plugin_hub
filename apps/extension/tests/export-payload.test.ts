import { describe, expect, it } from "vitest";

import {
  buildExportFilename,
  buildPayloadJson,
  buildRawItemsCsv
} from "../src/content/ui/export-payload";
import type { CollectionRunPayload } from "../src/types/contracts";

describe("content command bar payload export", () => {
  it("builds full JSON payload exports", () => {
    const payload = samplePayload();

    expect(JSON.parse(buildPayloadJson(payload))).toEqual(payload);
  });

  it("builds raw item CSV exports without inventing canonical fields", () => {
    expect(buildRawItemsCsv(samplePayload())).toBe(
      [
        "platform,source_kind,source_object_id,captured_at,raw_schema_version,parser_version,title,body,rating,source_url",
        "amazon,amazon_review,R1,2026-06-13T00:00:00.000Z,raw_amazon_review_v1,amazon-dom-parser@0.1.0,Great scrub,\"Smooth, but lid leaks\",4,https://www.amazon.com/review/R1",
        ""
      ].join("\n")
    );
  });

  it("builds stable export filenames from coverage scope", () => {
    expect(buildExportFilename(samplePayload(), "json")).toMatch(
      /^plugin-hub-amazon-B08MHGST8X-\d{4}-\d{2}-\d{2}T.*\.json$/
    );
  });
});

function samplePayload(): CollectionRunPayload {
  return {
    run: {
      platform: "amazon",
      source_url: "https://www.amazon.com/dp/B08MHGST8X",
      capture_method: "extension_dom_embedded_reviews",
      coverage_scope: {
        page_kind: "amazon_reviews",
        asin: "B08MHGST8X"
      },
      stop_reason: "embedded_reviews_only",
      coverage_confidence: 0.58
    },
    raw_items: [
      {
        platform: "amazon",
        source_kind: "amazon_review",
        source_object_id: "R1",
        raw_schema_version: "raw_amazon_review_v1",
        parser_version: "amazon-dom-parser@0.1.0",
        raw_payload_hash: "hash",
        captured_at: "2026-06-13T00:00:00.000Z",
        raw_payload: {
          title: "Great scrub",
          body: "Smooth, but lid leaks",
          rating: 4,
          url: "https://www.amazon.com/review/R1"
        }
      }
    ]
  };
}
