import {
  assertJsonObject,
  assertJsonValue,
  type CollectionRunPayload,
  type CollectionTaskPayload,
  type CollectionTaskResult,
  type CollectionTaskStatus,
  type PlatformSettingResult,
  type StrategyNote,
  type StrategyNotesResponse,
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

export async function getPlatformSetting(
  apiBaseUrl: string,
  platform: Platform,
  fetcher: UploadFetcher = fetch
): Promise<PlatformSettingResult> {
  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/platform-settings/${platform}`, {
    method: "GET",
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`platform_setting_fetch_failed:${response.status}`);
  }

  return parsePlatformSettingResult(await response.json(), platform);
}

export async function getStrategyNotes(
  apiBaseUrl: string,
  platform: Platform,
  fetcher: UploadFetcher = fetch
): Promise<StrategyNotesResponse> {
  const response = await fetcher(
    `${trimBaseUrl(apiBaseUrl)}/api/insights/strategy-notes?platform=${encodeURIComponent(platform)}`,
    {
      method: "GET",
      headers: {
        Accept: "application/json"
      }
    }
  );

  if (!response.ok) {
    throw new Error(`strategy_notes_fetch_failed:${response.status}`);
  }

  return parseStrategyNotesResponse(await response.json());
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

function parsePlatformSettingResult(
  value: unknown,
  expectedPlatform: Platform
): PlatformSettingResult {
  if (!isRecord(value)) {
    throw new TypeError("platform_setting_response_object_required");
  }

  const platform = value.platform;
  const enabled = value.enabled;
  const config = value.config;
  const updatedAt = value.updated_at;
  const updatedBy = value.updated_by;
  const source = value.source;

  if (
    !isPlatform(platform) ||
    platform !== expectedPlatform ||
    typeof enabled !== "boolean" ||
    typeof updatedAt !== "string" ||
    typeof updatedBy !== "string" ||
    typeof source !== "string"
  ) {
    throw new TypeError("platform_setting_response_invalid");
  }

  assertJsonObject(config);

  return {
    platform,
    enabled,
    config,
    updated_at: updatedAt,
    updated_by: updatedBy,
    source
  };
}

function parseStrategyNotesResponse(value: unknown): StrategyNotesResponse {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new TypeError("strategy_notes_response_invalid");
  }

  return {
    items: value.items.map(parseStrategyNote)
  };
}

function parseStrategyNote(value: unknown): StrategyNote {
  if (!isRecord(value)) {
    throw new TypeError("strategy_note_response_invalid");
  }

  const strategyType = value.strategy_type;
  const topic = value.topic;
  const evidenceCount = value.evidence_count;
  const evidenceExamples = value.evidence_examples;
  const recommendation = value.recommendation;
  const evidenceStrength = value.evidence_strength;
  const qualityFlags = value.quality_flags;

  if (
    typeof strategyType !== "string" ||
    typeof topic !== "string" ||
    typeof evidenceCount !== "number" ||
    !Array.isArray(evidenceExamples) ||
    typeof recommendation !== "string" ||
    typeof evidenceStrength !== "number" ||
    !Array.isArray(qualityFlags) ||
    !qualityFlags.every((flag) => typeof flag === "string")
  ) {
    throw new TypeError("strategy_note_response_invalid");
  }

  for (const example of evidenceExamples) {
    assertJsonValue(example);
  }

  return {
    strategy_type: strategyType,
    topic,
    evidence_count: evidenceCount,
    evidence_examples: evidenceExamples,
    recommendation,
    evidence_strength: evidenceStrength,
    quality_flags: qualityFlags
  };
}

function isPlatform(value: unknown): value is Platform {
  return value === "amazon" || value === "reddit" || value === "instagram";
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
