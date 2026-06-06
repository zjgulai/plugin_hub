import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import {
  CAPTURE_CURRENT_PAGE_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CaptureCurrentPageResponse,
  type CaptureSummary,
  type UploadCollectionMessage
} from "../types/messages";

const API_BASE_URL_STORAGE_KEY = "pluginHubApiBaseUrl";
const DEFAULT_API_BASE_URL = "http://localhost:8000";

type PopupStatus = "idle" | "capturing" | "uploading" | "done" | "error";

type UploadCollectionResponse =
  | {
      collection_run_id: string;
      raw_item_count: number;
      voc_unit_count: number;
    }
  | { error: string };

type UploadResult = {
  collectionRunId: string;
  rawItemCount: number;
  vocUnitCount: number;
  captureSummary: CaptureSummary;
};

export function Popup() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [status, setStatus] = useState<PopupStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  useEffect(() => {
    void loadApiBaseUrl().then(setApiBaseUrl).catch(() => setApiBaseUrl(DEFAULT_API_BASE_URL));
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    try {
      const normalizedApiBaseUrl = normalizeApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      await chrome.storage.local.set({ [API_BASE_URL_STORAGE_KEY]: normalizedApiBaseUrl });

      setStatus("capturing");
      const tabId = await getActiveTabId();
      const captureResponse = await sendTabMessage<CaptureCurrentPageResponse>(tabId, {
        type: CAPTURE_CURRENT_PAGE_MESSAGE_TYPE
      });

      if ("error" in captureResponse) {
        throw new Error(captureResponse.error);
      }

      setStatus("uploading");
      const uploadResponse = await sendRuntimeMessage<UploadCollectionResponse>({
        type: UPLOAD_COLLECTION_MESSAGE_TYPE,
        apiBaseUrl: normalizedApiBaseUrl,
        payload: captureResponse.payload
      });

      if ("error" in uploadResponse) {
        throw new Error(uploadResponse.error);
      }

      setResult({
        collectionRunId: uploadResponse.collection_run_id,
        rawItemCount: uploadResponse.raw_item_count,
        vocUnitCount: uploadResponse.voc_unit_count,
        captureSummary: captureResponse.summary
      });
      setStatus("done");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "capture_upload_failed:unknown");
      setStatus("error");
    }
  }

  return (
    <main aria-label="Plugin Hub VOC Collector">
      <header>
        <p>Plugin Hub</p>
        <h1>VOC 采集</h1>
      </header>

      <form onSubmit={handleSubmit}>
        <label htmlFor="api-base-url">API 地址</label>
        <input
          id="api-base-url"
          name="api-base-url"
          type="url"
          value={apiBaseUrl}
          onChange={(event) => setApiBaseUrl(event.currentTarget.value)}
          required
        />
        <button type="submit" disabled={status === "capturing" || status === "uploading"}>
          {buttonLabel(status)}
        </button>
      </form>

      <StatusPanel status={status} error={error} result={result} />
    </main>
  );
}

function StatusPanel({
  status,
  error,
  result
}: {
  status: PopupStatus;
  error: string | null;
  result: UploadResult | null;
}) {
  if (status === "idle") {
    return <p role="status">打开 Amazon 评论页或 Reddit thread 后开始采集。</p>;
  }

  if (status === "capturing") {
    return <p role="status">正在采集当前页面...</p>;
  }

  if (status === "uploading") {
    return <p role="status">正在回传到私有服务器...</p>;
  }

  if (status === "error") {
    return <p role="alert">失败：{error}</p>;
  }

  if (!result) {
    return null;
  }

  return (
    <section aria-label="采集结果">
      <dl>
        <div>
          <dt>Run</dt>
          <dd>{result.collectionRunId}</dd>
        </div>
        <div>
          <dt>Raw</dt>
          <dd>{result.rawItemCount}</dd>
        </div>
        <div>
          <dt>VOC</dt>
          <dd>{result.vocUnitCount}</dd>
        </div>
        <div>
          <dt>Stop</dt>
          <dd>{result.captureSummary.stop_reason ?? "completed"}</dd>
        </div>
      </dl>
    </section>
  );
}

function buttonLabel(status: PopupStatus): string {
  if (status === "capturing") {
    return "采集中";
  }
  if (status === "uploading") {
    return "回传中";
  }
  return "采集并回传";
}

async function loadApiBaseUrl(): Promise<string> {
  const result = await chrome.storage.local.get(API_BASE_URL_STORAGE_KEY);
  const value = result[API_BASE_URL_STORAGE_KEY];
  return typeof value === "string" && value.trim() ? value : DEFAULT_API_BASE_URL;
}

async function getActiveTabId(): Promise<number> {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tabId = tabs[0]?.id;

  if (typeof tabId !== "number") {
    throw new Error("active_tab_required");
  }

  return tabId;
}

async function sendTabMessage<TResponse>(
  tabId: number,
  message: { type: typeof CAPTURE_CURRENT_PAGE_MESSAGE_TYPE }
): Promise<TResponse> {
  return chrome.tabs.sendMessage(tabId, message) as Promise<TResponse>;
}

async function sendRuntimeMessage<TResponse>(
  message: UploadCollectionMessage
): Promise<TResponse> {
  return chrome.runtime.sendMessage(message) as Promise<TResponse>;
}

function normalizeApiBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/+$/, "");
  if (!normalized) {
    return DEFAULT_API_BASE_URL;
  }

  return normalized;
}

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(<Popup />);
}
