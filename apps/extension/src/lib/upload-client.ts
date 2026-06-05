import {
  assertJsonObject,
  assertJsonValue,
  type CollectionRunPayload
} from "../types/contracts";

export interface CollectionRunUploadResult {
  collection_run_id: string;
  raw_item_count: number;
  voc_unit_count: number;
}

interface UploadHttpResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

export type UploadFetcher = (url: string, init: RequestInit) => Promise<UploadHttpResponse>;

export async function uploadCollectionRun(
  apiBaseUrl: string,
  payload: CollectionRunPayload,
  fetcher: UploadFetcher = fetch
): Promise<CollectionRunUploadResult> {
  assertCollectionRunPayloadJson(payload);

  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/collection-runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`collection_run_upload_failed:${response.status}`);
  }

  return parseUploadResult(await response.json());
}

function trimBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/+$/, "");
}

function assertCollectionRunPayloadJson(payload: CollectionRunPayload): void {
  assertJsonValue(payload);
  assertJsonObject(payload.run.coverage_scope);

  for (const rawItem of payload.raw_items) {
    assertJsonObject(rawItem.raw_payload);
  }
}

function parseUploadResult(value: unknown): CollectionRunUploadResult {
  if (!isRecord(value)) {
    throw new TypeError("collection_run_upload_response_object_required");
  }

  const collectionRunId = value.collection_run_id;
  const rawItemCount = value.raw_item_count;
  const vocUnitCount = value.voc_unit_count;

  if (
    typeof collectionRunId !== "string" ||
    typeof rawItemCount !== "number" ||
    typeof vocUnitCount !== "number"
  ) {
    throw new TypeError("collection_run_upload_response_invalid");
  }

  return {
    collection_run_id: collectionRunId,
    raw_item_count: rawItemCount,
    voc_unit_count: vocUnitCount
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
