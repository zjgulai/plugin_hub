export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export function assertJsonValue(value: unknown): asserts value is JsonValue {
  if (value === null) {
    return;
  }

  switch (typeof value) {
    case "string":
    case "boolean":
      return;
    case "number":
      if (!Number.isFinite(value)) {
        throw new TypeError("json_number_must_be_finite");
      }
      return;
    case "object":
      assertJsonContainer(value);
      return;
    default:
      throw new TypeError("value_must_be_json_serializable");
  }
}

export function assertJsonObject(value: unknown): asserts value is JsonObject {
  assertJsonValue(value);

  if (!isPlainObject(value)) {
    throw new TypeError("json_object_required");
  }
}

function assertJsonContainer(value: object): void {
  if (Array.isArray(value)) {
    for (const item of value) {
      assertJsonValue(item);
    }
    return;
  }

  if (!isPlainObject(value)) {
    throw new TypeError("value_must_be_json_serializable");
  }

  for (const key of Reflect.ownKeys(value)) {
    if (typeof key !== "string") {
      throw new TypeError("json_object_keys_must_be_strings");
    }
    assertJsonValue(value[key]);
  }
}

function isPlainObject(value: unknown): value is { [key: string]: unknown } {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

export type Platform = "amazon" | "reddit";

export type SourceKind = "amazon_review" | "reddit_thread" | "reddit_comment";

export interface CollectionRunCreate {
  platform: Platform;
  source_url: string;
  capture_method: string;
  coverage_scope: JsonObject;
  stop_reason: string | null;
  coverage_confidence: number;
}

export interface CollectionRun extends CollectionRunCreate {
  collection_run_id: string;
  created_at: string;
}

export interface CollectionRunPayload {
  run: CollectionRunCreate;
  raw_items: RawSourceItem[];
}

export type CollectionTaskStatus =
  | "pending"
  | "running"
  | "retry_scheduled"
  | "completed"
  | "failed";

export interface CollectionTaskCreate {
  platform: Platform;
  source_url: string;
  requested_capture_method: string;
  trigger_reason: string;
  context: JsonObject;
}

export interface CollectionTaskPayload {
  task: CollectionTaskCreate;
}

export interface CollectionTaskResult extends CollectionTaskCreate {
  collection_task_id: string;
  status: CollectionTaskStatus;
  created_at: string;
  updated_at: string;
}

export interface RawSourceItem {
  platform: Platform;
  source_kind: SourceKind;
  source_object_id: string;
  raw_schema_version: string;
  parser_version: string;
  raw_payload: JsonObject;
  raw_payload_hash: string;
  captured_at: string;
}

export interface CanonicalVocUnit {
  platform: Platform;
  source_kind: SourceKind;
  source_object_id: string;
  collection_run_id: string;
  source_url: string;
  captured_at: string;
  created_at: string | null;
  author_display: string | null;
  author_type: string | null;
  title: string | null;
  body: string;
  language: string | null;
  media_refs: string[];
  commercial_object_type: string | null;
  brand: string | null;
  product_title: string | null;
  asin: string | null;
  parent_asin: string | null;
  marketplace: string | null;
  category: string | null;
  thread_id: string | null;
  parent_id: string | null;
  depth: number | null;
  reply_role: string | null;
  quality_flags: string[];
  coverage_confidence: number;
  platform_extension: JsonObject;
}
