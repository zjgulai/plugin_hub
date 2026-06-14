import { createRoot, type Root } from "react-dom/client";

import { captureCurrentPage } from "../lib/capture";
import { detectPage, type DetectedPage } from "../lib/page-detect";
import type { CaptureCurrentPageResponse } from "../types/messages";
import { ContentCommandBar } from "./ui/ContentCommandBar";
import { CONTENT_COMMAND_BAR_CSS } from "./ui/content-command-bar.css";

const CAPTURE_CURRENT_PAGE_MESSAGE_TYPE = "PLUGIN_HUB_CAPTURE_CURRENT_PAGE";
const COMMAND_BAR_HOST_ID = "plugin-hub-voc-command-bar";
const URL_POLL_INTERVAL_MS = 750;

interface CaptureCurrentPageMessage {
  type: typeof CAPTURE_CURRENT_PAGE_MESSAGE_TYPE;
}

type MountedCommandBar = {
  host: HTMLDivElement;
  root: Root;
};

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

function renderOnUrlChange(): void {
  if (window.location.href === lastObservedUrl) {
    return;
  }

  renderForCurrentPage();
}

function renderForCurrentPage(): void {
  const url = window.location.href;
  const detectedPage = detectPage(url);
  lastObservedUrl = url;
  dispatchDetectedPage(detectedPage);

  if (detectedPage.platform === "unknown" || dismissedUrl === url) {
    unmountCommandBar();
    return;
  }

  mountCommandBar(detectedPage, url);
}

function dispatchDetectedPage(detectedPage: DetectedPage): void {
  window.dispatchEvent(
    new CustomEvent("plugin-hub-page-detected", {
      detail: detectedPage
    })
  );
}

function mountCommandBar(detectedPage: DetectedPage, url: string): void {
  const mounted = ensureCommandBarMounted();
  moveHostToBestPosition(mounted.host, detectedPage);
  mounted.root.render(
    <ContentCommandBar
      detectedPage={detectedPage}
      sourceUrl={url}
      documentRoot={document}
      onDismiss={() => {
        dismissedUrl = window.location.href;
        unmountCommandBar();
      }}
    />
  );
}

function ensureCommandBarMounted(): MountedCommandBar {
  if (mountedCommandBar) {
    return mountedCommandBar;
  }

  const host = document.createElement("div");
  host.id = COMMAND_BAR_HOST_ID;
  host.style.position = "relative";
  host.style.zIndex = "2147483640";
  host.style.clear = "both";

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

function moveHostToBestPosition(host: HTMLDivElement, detectedPage: DetectedPage): void {
  if (detectedPage.platform === "amazon") {
    const anchor =
      queryHTMLElement("#dp-container") ??
      queryHTMLElement("#ppd") ??
      queryHTMLElement("#dp") ??
      queryHTMLElement("main") ??
      queryHTMLElement("#a-page");
    insertBeforeAnchor(host, anchor);
    return;
  }

  if (detectedPage.platform === "reddit") {
    const anchor =
      queryHTMLElement("shreddit-post") ??
      queryHTMLElement("[data-testid='post-container']") ??
      queryHTMLElement(".thing.link") ??
      queryHTMLElement("main");
    insertAfterAnchor(host, anchor);
    return;
  }

  document.body.prepend(host);
}

function insertBeforeAnchor(host: HTMLDivElement, anchor: HTMLElement | null): void {
  if (!anchor || !anchor.parentElement) {
    document.body.prepend(host);
    return;
  }

  if (host.nextElementSibling === anchor) {
    return;
  }

  anchor.insertAdjacentElement("beforebegin", host);
}

function insertAfterAnchor(host: HTMLDivElement, anchor: HTMLElement | null): void {
  if (!anchor || !anchor.parentElement) {
    document.body.prepend(host);
    return;
  }

  if (host.previousElementSibling === anchor) {
    return;
  }

  anchor.insertAdjacentElement("afterend", host);
}

function queryHTMLElement(selector: string): HTMLElement | null {
  const element = document.querySelector(selector);
  return element instanceof HTMLElement ? element : null;
}
