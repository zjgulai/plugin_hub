import { uploadCollectionRun, type CollectionRunUploadResult } from "../lib/upload-client";
import type { CollectionRunPayload } from "../types/contracts";

const UPLOAD_COLLECTION_MESSAGE_TYPE = "PLUGIN_HUB_UPLOAD_COLLECTION";

interface UploadCollectionMessage {
  type: typeof UPLOAD_COLLECTION_MESSAGE_TYPE;
  apiBaseUrl: string;
  payload: CollectionRunPayload;
}

type UploadCollectionResponse = CollectionRunUploadResult | { error: string };

chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if (!isUploadCollectionMessage(message)) {
    return false;
  }

  void uploadCollectionRun(message.apiBaseUrl, message.payload)
    .then((result) => sendResponse(result satisfies UploadCollectionResponse))
    .catch((error: unknown) =>
      sendResponse({
        error: error instanceof Error ? error.message : "collection_run_upload_failed:unknown"
      } satisfies UploadCollectionResponse)
    );

  return true;
});

function isUploadCollectionMessage(message: unknown): message is UploadCollectionMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === UPLOAD_COLLECTION_MESSAGE_TYPE &&
    typeof message.apiBaseUrl === "string" &&
    isCollectionRunPayloadLike(message.payload)
  );
}

function isCollectionRunPayloadLike(value: unknown): value is CollectionRunPayload {
  if (!isRecord(value) || !isRecord(value.run) || !Array.isArray(value.raw_items)) {
    return false;
  }

  return (
    typeof value.run.platform === "string" &&
    typeof value.run.source_url === "string" &&
    typeof value.run.capture_method === "string" &&
    "coverage_scope" in value.run
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
