import type { CollectionRunPayload, CollectionTaskPayload } from "./contracts";

export const CAPTURE_CURRENT_PAGE_MESSAGE_TYPE = "PLUGIN_HUB_CAPTURE_CURRENT_PAGE";
export const UPLOAD_COLLECTION_MESSAGE_TYPE = "PLUGIN_HUB_UPLOAD_COLLECTION";
export const CREATE_COLLECTION_TASK_MESSAGE_TYPE = "PLUGIN_HUB_CREATE_COLLECTION_TASK";

export interface CaptureCurrentPageMessage {
  type: typeof CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
}

export interface CaptureSummary {
  platform: "amazon" | "reddit";
  page_kind: "amazon_reviews" | "reddit_thread";
  raw_item_count: number;
  stop_reason: string | null;
  coverage_confidence: number;
}

export interface CaptureCurrentPageSuccess {
  payload: CollectionRunPayload;
  summary: CaptureSummary;
}

export type CaptureCurrentPageResponse = CaptureCurrentPageSuccess | { error: string };

export interface UploadCollectionMessage {
  type: typeof UPLOAD_COLLECTION_MESSAGE_TYPE;
  apiBaseUrl: string;
  payload: CollectionRunPayload;
}

export interface CreateCollectionTaskMessage {
  type: typeof CREATE_COLLECTION_TASK_MESSAGE_TYPE;
  apiBaseUrl: string;
  payload: CollectionTaskPayload;
}
