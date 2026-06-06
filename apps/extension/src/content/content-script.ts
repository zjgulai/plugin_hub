import { captureCurrentPage } from "../lib/capture";
import { detectPage } from "../lib/page-detect";
import type { CaptureCurrentPageResponse } from "../types/messages";

const CAPTURE_CURRENT_PAGE_MESSAGE_TYPE = "PLUGIN_HUB_CAPTURE_CURRENT_PAGE";

interface CaptureCurrentPageMessage {
  type: typeof CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
}

const detectedPage = detectPage(window.location.href);

window.dispatchEvent(
  new CustomEvent("plugin-hub-page-detected", {
    detail: detectedPage
  })
);

chrome.runtime.onMessage.addListener(
  (message: unknown, _sender, sendResponse: (response: CaptureCurrentPageResponse) => void) => {
    if (!isCaptureCurrentPageMessage(message)) {
      return false;
    }

    void captureCurrentPage({
      url: window.location.href,
      documentRoot: document
    })
      .then((result) => sendResponse(result))
      .catch((error: unknown) =>
        sendResponse({
          error: error instanceof Error ? error.message : "capture_current_page_failed:unknown"
        })
      );

    return true;
  }
);

function isCaptureCurrentPageMessage(message: unknown): message is CaptureCurrentPageMessage {
  return isRecord(message) && message.type === CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
