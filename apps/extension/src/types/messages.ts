import type { CaptureRuntimeSettings } from "../lib/capture-types";
import type {
  CollectionRunPayload,
  CollectionTaskPayload,
  InsightBriefsResponse,
  Platform,
  PlatformSettingResult,
  StrategyNotesResponse
} from "./contracts";

export const CAPTURE_CURRENT_PAGE_MESSAGE_TYPE = "PLUGIN_HUB_CAPTURE_CURRENT_PAGE";
export const UPLOAD_COLLECTION_MESSAGE_TYPE = "PLUGIN_HUB_UPLOAD_COLLECTION";
export const CREATE_COLLECTION_TASK_MESSAGE_TYPE = "PLUGIN_HUB_CREATE_COLLECTION_TASK";
export const GET_PLATFORM_SETTING_MESSAGE_TYPE = "PLUGIN_HUB_GET_PLATFORM_SETTING";
export const GET_STRATEGY_NOTES_MESSAGE_TYPE = "PLUGIN_HUB_GET_STRATEGY_NOTES";
export const GET_INSIGHT_BRIEFS_MESSAGE_TYPE = "PLUGIN_HUB_GET_INSIGHT_BRIEFS";

export interface CaptureCurrentPageMessage {
  type: typeof CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
  runtimeSettings?: CaptureRuntimeSettings;
}

export interface CaptureSummary {
  platform: "amazon" | "reddit" | "instagram";
  page_kind: "amazon_reviews" | "reddit_thread" | "instagram_media_comments";
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

export interface GetPlatformSettingMessage {
  type: typeof GET_PLATFORM_SETTING_MESSAGE_TYPE;
  apiBaseUrl: string;
  platform: Platform;
}

export type GetPlatformSettingResponse = PlatformSettingResult | { error: string };

export interface GetStrategyNotesMessage {
  type: typeof GET_STRATEGY_NOTES_MESSAGE_TYPE;
  apiBaseUrl: string;
  platform: Platform;
}

export type GetStrategyNotesResponse = StrategyNotesResponse | { error: string };

export interface GetInsightBriefsMessage {
  type: typeof GET_INSIGHT_BRIEFS_MESSAGE_TYPE;
  apiBaseUrl: string;
  platform: Platform;
}

export type GetInsightBriefsResponse = InsightBriefsResponse | { error: string };
