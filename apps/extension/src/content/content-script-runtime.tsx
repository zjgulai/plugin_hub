import { createRoot, type Root } from "react-dom/client";

import type { CaptureCurrentPageInput } from "../lib/capture-types";
import type { DetectedPage } from "../lib/page-detect";
import {
  CAPTURE_CURRENT_PAGE_MESSAGE_TYPE,
  type CaptureCurrentPageMessage,
  type CaptureCurrentPageResponse,
  type CaptureCurrentPageSuccess
} from "../types/messages";
import { ContentCommandBar } from "./ui/ContentCommandBar";
import { CONTENT_COMMAND_BAR_CSS } from "./ui/content-command-bar.css";

const COMMAND_BAR_HOST_ID = "plugin-hub-voc-command-bar";
const URL_POLL_INTERVAL_MS = 750;

type MountedCommandBar = {
  host: HTMLDivElement;
  root: Root;
};

type ContentScriptOptions = {
  detectPage: (url: string) => DetectedPage;
  captureCurrentPage: (input: CaptureCurrentPageInput) => Promise<CaptureCurrentPageSuccess>;
};

export function mountContentScript(options: ContentScriptOptions): void {
  let mountedCommandBar: MountedCommandBar | null = null;
  let lastObservedUrl = "";
  let dismissedUrl: string | null = null;

  renderForCurrentPage();
  window.setInterval(renderOnUrlChange, URL_POLL_INTERVAL_MS);
  window.addEventListener("hashchange", renderForCurrentPage);
  window.addEventListener("popstate", renderForCurrentPage);

  chrome.runtime.onMessage.addListener(
    (message: unknown, _sender, sendResponse: (response: CaptureCurrentPageResponse) => void) => {
      if (!isCaptureCurrentPageMessage(message)) {
        return false;
      }

      void options
        .captureCurrentPage({
          url: window.location.href,
          documentRoot: document,
          runtimeSettings: message.runtimeSettings
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

  function renderOnUrlChange(): void {
    if (window.location.href === lastObservedUrl) {
      return;
    }

    renderForCurrentPage();
  }

  function renderForCurrentPage(): void {
    const url = window.location.href;
    const detectedPage = options.detectPage(url);
    lastObservedUrl = url;
    dispatchDetectedPage(detectedPage);

    if (detectedPage.platform === "unknown" || dismissedUrl === url) {
      unmountCommandBar();
      return;
    }

    mountCommandBar(detectedPage, url);
  }

  function mountCommandBar(detectedPage: DetectedPage, url: string): void {
    const mounted = ensureCommandBarMounted();
    if (!mounted.host.isConnected) {
      document.body.append(mounted.host);
    }
    mounted.root.render(
      <ContentCommandBar
        detectedPage={detectedPage}
        sourceUrl={url}
        documentRoot={document}
        onDismiss={() => {
          dismissedUrl = window.location.href;
          unmountCommandBar();
        }}
        captureCurrentPage={options.captureCurrentPage}
      />
    );
  }

  function ensureCommandBarMounted(): MountedCommandBar {
    if (mountedCommandBar) {
      return mountedCommandBar;
    }

    const host = document.createElement("div");
    host.id = COMMAND_BAR_HOST_ID;
    host.style.position = "fixed";
    host.style.inset = "0";
    host.style.zIndex = "2147483640";
    host.style.pointerEvents = "none";

    const shadowRoot = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = CONTENT_COMMAND_BAR_CSS;
    const rootElement = document.createElement("div");
    shadowRoot.append(style, rootElement);

    const root = createRoot(rootElement);
    mountedCommandBar = {
      host,
      root
    };

    return mountedCommandBar;
  }

  function unmountCommandBar(): void {
    if (!mountedCommandBar) {
      return;
    }

    mountedCommandBar.root.unmount();
    mountedCommandBar.host.remove();
    mountedCommandBar = null;
  }
}

function isCaptureCurrentPageMessage(message: unknown): message is CaptureCurrentPageMessage {
  return isRecord(message) && message.type === CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function dispatchDetectedPage(detectedPage: DetectedPage): void {
  window.dispatchEvent(
    new CustomEvent("plugin-hub-page-detected", {
      detail: detectedPage
    })
  );
}
