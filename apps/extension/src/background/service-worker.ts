import {
  createCollectionTask,
  uploadCollectionRun,
  type CollectionRunUploadResult
} from "../lib/upload-client";
import type { CollectionRunPayload, CollectionTaskPayload, CollectionTaskResult } from "../types/contracts";
import {
  CREATE_COLLECTION_TASK_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CreateCollectionTaskMessage,
  type UploadCollectionMessage
} from "../types/messages";

type UploadCollectionResponse = CollectionRunUploadResult | { error: string };
type CreateCollectionTaskResponse = CollectionTaskResult | { error: string };

chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if (isUploadCollectionMessage(message)) {
    void uploadCollectionRun(message.apiBaseUrl, message.payload)
      .then((result) => sendResponse(result satisfies UploadCollectionResponse))
      .catch((error: unknown) =>
        sendResponse({
          error: error instanceof Error ? error.message : "collection_run_upload_failed:unknown"
        } satisfies UploadCollectionResponse)
      );

    return true;
  }

  if (isCreateCollectionTaskMessage(message)) {
    void createCollectionTask(message.apiBaseUrl, message.payload)
      .then((result) => sendResponse(result satisfies CreateCollectionTaskResponse))
      .catch((error: unknown) =>
        sendResponse({
          error: error instanceof Error ? error.message : "collection_task_create_failed:unknown"
        } satisfies CreateCollectionTaskResponse)
      );

    return true;
  }

  return false;
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

function isCreateCollectionTaskMessage(message: unknown): message is CreateCollectionTaskMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === CREATE_COLLECTION_TASK_MESSAGE_TYPE &&
    typeof message.apiBaseUrl === "string" &&
    isCollectionTaskPayloadLike(message.payload)
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

function isCollectionTaskPayloadLike(value: unknown): value is CollectionTaskPayload {
  if (!isRecord(value) || !isRecord(value.task)) {
    return false;
  }

  return (
    typeof value.task.platform === "string" &&
    typeof value.task.source_url === "string" &&
    typeof value.task.requested_capture_method === "string" &&
    typeof value.task.trigger_reason === "string" &&
    "context" in value.task
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
