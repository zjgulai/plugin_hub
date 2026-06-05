import { describe, expect, it } from "vitest";

import type { CollectionRunPayload } from "../src/types/contracts";
import {
  type UploadFetcher,
  uploadCollectionRun
} from "../src/lib/upload-client";

const payload = {
  run: {
    platform: "amazon",
    source_url: "https://www.amazon.com/product-reviews/B000000001",
    capture_method: "browser_extension",
    coverage_scope: {
      page_kind: "amazon_reviews",
      asin: "B000000001",
      segments: ["all_reviews"],
      page_count: 1
    },
    stop_reason: null,
    coverage_confidence: 0.91
  },
  raw_items: [
    {
      platform: "amazon",
      source_kind: "amazon_review",
      source_object_id: "R000000001",
      raw_schema_version: "raw_amazon_review_v1",
      parser_version: "amazon-dom-parser@0.1.0",
      raw_payload: {
        review_id: "R000000001",
        body: "Works well",
        rating: 5,
        media_refs: []
      },
      raw_payload_hash: "hash-1",
      captured_at: "2026-06-06T01:02:03.000Z"
    }
  ]
} satisfies CollectionRunPayload;

describe("uploadCollectionRun", () => {
  it("posts the collection run payload and returns the created counters", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetcher: UploadFetcher = async (url, init) => {
      calls.push({ url, init });

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).resolves.toEqual({
      collection_run_id: "run-1",
      raw_item_count: 1,
      voc_unit_count: 1
    });

    expect(calls).toHaveLength(1);
    expect(calls[0]).toEqual({
      url: "https://api.example.com/api/collection-runs",
      init: {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      }
    });
  });

  it("removes multiple trailing slashes from the base URL", async () => {
    let postedUrl: string | null = null;
    const fetcher: UploadFetcher = async (url) => {
      postedUrl = url;

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await uploadCollectionRun("https://api.example.com///", payload, fetcher);

    expect(postedUrl).toBe("https://api.example.com/api/collection-runs");
  });

  it("throws a status-keyed error for non-ok responses", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "backend unavailable" })
    });

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).rejects.toThrow(
      "collection_run_upload_failed:503"
    );
  });

  it("rejects invalid upload response objects", async () => {
    const fetcher: UploadFetcher = async () => ({
      ok: true,
      status: 201,
      json: async () => ({
        collection_run_id: "run-1",
        raw_item_count: "1",
        voc_unit_count: 1
      })
    });

    await expect(uploadCollectionRun("https://api.example.com", payload, fetcher)).rejects.toThrow(
      "collection_run_upload_response_invalid"
    );
  });

  it("serializes coverage scope and raw item payload without dropping JSON fields", async () => {
    let body: BodyInit | null | undefined;
    const fetcher: UploadFetcher = async (_url, init) => {
      body = init.body;

      return {
        ok: true,
        status: 201,
        json: async () => ({
          collection_run_id: "run-1",
          raw_item_count: 1,
          voc_unit_count: 1
        })
      };
    };

    await uploadCollectionRun("https://api.example.com", payload, fetcher);

    expect(typeof body).toBe("string");
    const serializedPayload = JSON.parse(body as string) as CollectionRunPayload;
    expect(serializedPayload.run.coverage_scope).toEqual(payload.run.coverage_scope);
    expect(serializedPayload.raw_items[0]?.raw_payload).toEqual(payload.raw_items[0].raw_payload);
  });

  it("rejects non-object coverage scope before sending the request", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      run: {
        ...payload.run,
        coverage_scope: ["invalid"]
      }
    } as unknown as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_object_required");
    expect(called).toBe(false);
  });

  it("rejects non-finite coverage confidence before JSON.stringify can coerce it", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      run: {
        ...payload.run,
        coverage_confidence: Number.NaN
      }
    } as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_number_must_be_finite");
    expect(called).toBe(false);
  });

  it("rejects non-finite raw payload numbers before sending the request", async () => {
    let called = false;
    const fetcher: UploadFetcher = async () => {
      called = true;
      throw new Error("fetcher_should_not_be_called");
    };
    const invalidPayload = {
      ...payload,
      raw_items: [
        {
          ...payload.raw_items[0],
          raw_payload: {
            ...payload.raw_items[0].raw_payload,
            rating: Number.POSITIVE_INFINITY
          }
        }
      ]
    } as CollectionRunPayload;

    await expect(
      uploadCollectionRun("https://api.example.com", invalidPayload, fetcher)
    ).rejects.toThrow("json_number_must_be_finite");
    expect(called).toBe(false);
  });
});
