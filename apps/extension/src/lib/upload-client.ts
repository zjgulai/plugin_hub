import {
  assertJsonObject,
  assertJsonValue,
  type CollectionRunPayload,
  type CollectionTaskPayload,
  type CollectionTaskResult,
  type CollectionTaskStatus,
  type Platform
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

export async function createCollectionTask(
  apiBaseUrl: string,
  payload: CollectionTaskPayload,
  fetcher: UploadFetcher = fetch
): Promise<CollectionTaskResult> {
  assertCollectionTaskPayloadJson(payload);

  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/collection-tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`collection_task_create_failed:${response.status}`);
  }

  return parseCollectionTaskResult(await response.json());
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

function assertCollectionTaskPayloadJson(payload: CollectionTaskPayload): void {
  assertJsonValue(payload);
  assertJsonObject(payload.task.context);
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

function parseCollectionTaskResult(value: unknown): CollectionTaskResult {
  if (!isRecord(value)) {
    throw new TypeError("collection_task_response_object_required");
  }

  const collectionTaskId = value.collection_task_id;
  const platform = value.platform;
  const sourceUrl = value.source_url;
  const requestedCaptureMethod = value.requested_capture_method;
  const triggerReason = value.trigger_reason;
  const status = value.status;
  const context = value.context;
  const createdAt = value.created_at;
  const updatedAt = value.updated_at;

  if (
    typeof collectionTaskId !== "string" ||
    !isPlatform(platform) ||
    typeof sourceUrl !== "string" ||
    typeof requestedCaptureMethod !== "string" ||
    typeof triggerReason !== "string" ||
    !isCollectionTaskStatus(status) ||
    typeof createdAt !== "string" ||
    typeof updatedAt !== "string"
  ) {
    throw new TypeError("collection_task_response_invalid");
  }

  assertJsonObject(context);

  return {
    collection_task_id: collectionTaskId,
    platform,
    source_url: sourceUrl,
    requested_capture_method: requestedCaptureMethod,
    trigger_reason: triggerReason,
    status,
    context,
    created_at: createdAt,
    updated_at: updatedAt
  };
}

function isPlatform(value: unknown): value is Platform {
  return value === "amazon" || value === "reddit";
}

function isCollectionTaskStatus(value: unknown): value is CollectionTaskStatus {
  return (
    value === "pending" ||
    value === "running" ||
    value === "retry_scheduled" ||
    value === "completed" ||
    value === "failed"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
