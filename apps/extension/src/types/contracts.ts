export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

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
