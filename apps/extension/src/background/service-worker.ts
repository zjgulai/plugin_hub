import {
  createCollectionTask,
  getInsightBriefs,
  getPlatformSetting,
  getStrategyNotes,
  uploadCollectionRun,
  type CollectionRunUploadResult
} from "../lib/upload-client";
import {
  CURRENT_EXTENSION_TARGET,
  extensionTargetConfig
} from "../lib/extension-target";
import { loadApiBaseUrl, loadApiKey } from "../lib/settings";
import type {
  CollectionRunPayload,
  CollectionTaskPayload,
  CollectionTaskResult,
  InsightBriefsResponse,
  Platform,
  PlatformSettingResult,
  StrategyNotesResponse
} from "../types/contracts";
import {
  CREATE_COLLECTION_TASK_MESSAGE_TYPE,
  GET_INSIGHT_BRIEFS_MESSAGE_TYPE,
  GET_PLATFORM_SETTING_MESSAGE_TYPE,
  GET_STRATEGY_NOTES_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CreateCollectionTaskMessage,
  type GetInsightBriefsMessage,
  type GetPlatformSettingMessage,
  type GetStrategyNotesMessage,
  type UploadCollectionMessage
} from "../types/messages";

type UploadCollectionResponse = CollectionRunUploadResult | { error: string };
type CreateCollectionTaskResponse = CollectionTaskResult | { error: string };
type GetPlatformSettingResponse = PlatformSettingResult | { error: string };
type GetStrategyNotesResponse = StrategyNotesResponse | { error: string };
type GetInsightBriefsResponse = InsightBriefsResponse | { error: string };
type ServiceWorkerMessage =
  | UploadCollectionMessage
  | CreateCollectionTaskMessage
  | GetPlatformSettingMessage
  | GetStrategyNotesMessage
  | GetInsightBriefsMessage;
type ServiceWorkerResponse =
  | UploadCollectionResponse
  | CreateCollectionTaskResponse
  | GetPlatformSettingResponse
  | GetStrategyNotesResponse
  | GetInsightBriefsResponse;

const TARGET_CONFIG = extensionTargetConfig(CURRENT_EXTENSION_TARGET);

chrome.runtime.onMessage.addListener((message: unknown, sender, sendResponse) => {
  if (!isServiceWorkerMessage(message)) {
    return false;
  }

  if (!isTrustedMessageSender(sender)) {
    sendResponse({ error: "runtime_message_sender_untrusted" } satisfies ServiceWorkerResponse);
    return false;
  }

  void handleServiceWorkerMessage(message)
    .then((result) => sendResponse(result))
    .catch((error: unknown) =>
      sendResponse({
        error: error instanceof Error ? error.message : messageFailureCode(message)
      } satisfies ServiceWorkerResponse)
    );

  return true;
});

async function handleServiceWorkerMessage(
  message: ServiceWorkerMessage
): Promise<ServiceWorkerResponse> {
  const apiBaseUrl = await loadApiBaseUrl();
  const apiKey = await loadApiKey();

  if (isUploadCollectionMessage(message)) {
    return uploadCollectionRun(apiBaseUrl, message.payload, undefined, apiKey);
  }
  if (isCreateCollectionTaskMessage(message)) {
    return createCollectionTask(apiBaseUrl, message.payload, undefined, apiKey);
  }
  if (isGetPlatformSettingMessage(message)) {
    return getPlatformSetting(apiBaseUrl, message.platform, undefined, apiKey);
  }
  if (isGetStrategyNotesMessage(message)) {
    return getStrategyNotes(apiBaseUrl, message.platform, undefined, apiKey);
  }
  return getInsightBriefs(apiBaseUrl, message.platform, undefined, apiKey);
}

function isServiceWorkerMessage(message: unknown): message is ServiceWorkerMessage {
  return (
    isUploadCollectionMessage(message) ||
    isCreateCollectionTaskMessage(message) ||
    isGetPlatformSettingMessage(message) ||
    isGetStrategyNotesMessage(message) ||
    isGetInsightBriefsMessage(message)
  );
}

function isTrustedMessageSender(sender: chrome.runtime.MessageSender): boolean {
  if (!chrome.runtime.id || sender.id !== chrome.runtime.id) {
    return false;
  }

  const senderUrlValue = sender.url ?? sender.tab?.url;
  if (!senderUrlValue) {
    return false;
  }

  let senderUrl: URL;
  try {
    senderUrl = new URL(senderUrlValue);
  } catch {
    return false;
  }

  if (senderUrl.protocol === "chrome-extension:") {
    return senderUrl.host === chrome.runtime.id;
  }

  if (!sender.tab) {
    return false;
  }

  return TARGET_CONFIG.contentMatches.some((matchPattern) => {
    const allowedOrigin = matchPattern.endsWith("/*")
      ? matchPattern.slice(0, -2)
      : matchPattern;
    return senderUrl.origin === allowedOrigin;
  });
}

function messageFailureCode(message: ServiceWorkerMessage): string {
  if (isUploadCollectionMessage(message)) {
    return "collection_run_upload_failed:unknown";
  }
  if (isCreateCollectionTaskMessage(message)) {
    return "collection_task_create_failed:unknown";
  }
  if (isGetPlatformSettingMessage(message)) {
    return "platform_setting_fetch_failed:unknown";
  }
  if (isGetStrategyNotesMessage(message)) {
    return "strategy_notes_fetch_failed:unknown";
  }
  return "insight_briefs_fetch_failed:unknown";
}

function isUploadCollectionMessage(message: unknown): message is UploadCollectionMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === UPLOAD_COLLECTION_MESSAGE_TYPE &&
    isCollectionRunPayloadLike(message.payload)
  );
}

function isCreateCollectionTaskMessage(message: unknown): message is CreateCollectionTaskMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === CREATE_COLLECTION_TASK_MESSAGE_TYPE &&
    isCollectionTaskPayloadLike(message.payload)
  );
}

function isGetPlatformSettingMessage(message: unknown): message is GetPlatformSettingMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === GET_PLATFORM_SETTING_MESSAGE_TYPE &&
    isPlatform(message.platform)
  );
}

function isGetStrategyNotesMessage(message: unknown): message is GetStrategyNotesMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === GET_STRATEGY_NOTES_MESSAGE_TYPE &&
    isPlatform(message.platform)
  );
}

function isGetInsightBriefsMessage(message: unknown): message is GetInsightBriefsMessage {
  if (!isRecord(message)) {
    return false;
  }

  return (
    message.type === GET_INSIGHT_BRIEFS_MESSAGE_TYPE &&
    isPlatform(message.platform)
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

function isPlatform(value: unknown): value is Platform {
  return value === "amazon" || value === "reddit" || value === "instagram";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
