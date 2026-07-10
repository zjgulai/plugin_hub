import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

import {
  CURRENT_EXTENSION_TARGET,
  extensionTargetConfig
} from "../lib/extension-target";
import type { CaptureRuntimeSettings } from "../lib/capture-types";
import { amazonRuntimeSettingsFromPlatformSetting } from "../lib/platform-runtime-settings";
import {
  DEFAULT_API_BASE_URL,
  loadApiKey,
  loadApiBaseUrl,
  normalizeApiBaseUrl,
  saveApiBaseUrl,
  saveApiKey
} from "../lib/settings";
import {
  CAPTURE_CURRENT_PAGE_MESSAGE_TYPE,
  GET_PLATFORM_SETTING_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CaptureCurrentPageResponse,
  type CaptureCurrentPageMessage,
  type CaptureSummary,
  type GetPlatformSettingMessage,
  type GetPlatformSettingResponse,
  type UploadCollectionMessage
} from "../types/messages";

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

const TARGET_CONFIG = extensionTargetConfig(CURRENT_EXTENSION_TARGET);

export function Popup() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [apiKey, setApiKey] = useState("");
  const [status, setStatus] = useState<PopupStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  useEffect(() => {
    void loadApiBaseUrl().then(setApiBaseUrl).catch(() => setApiBaseUrl(DEFAULT_API_BASE_URL));
    void loadApiKey().then(setApiKey).catch(() => setApiKey(""));
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    try {
      const normalizedApiBaseUrl = normalizeApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      await saveApiBaseUrl(normalizedApiBaseUrl);
      await saveApiKey(apiKey);
      const runtimeSettings = await loadCaptureRuntimeSettings(normalizedApiBaseUrl);

      setStatus("capturing");
      const tabId = await getActiveTabId();
      const captureResponse = await sendTabMessage<CaptureCurrentPageResponse>(tabId, {
        type: CAPTURE_CURRENT_PAGE_MESSAGE_TYPE,
        runtimeSettings
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
    <>
      <style>{POPUP_STYLE}</style>
      <main className={`popupShell popupShell--${CURRENT_EXTENSION_TARGET}`} aria-label="Plugin Hub VOC Collector">
      <header className="popupHeader">
        <div className="popupMark" aria-hidden="true">
          PH
        </div>
        <div>
          <p>Plugin Hub</p>
          <h1>{TARGET_CONFIG.shortName} 采集</h1>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="popupForm">
        <label htmlFor="api-base-url">
          <span>API 地址</span>
        </label>
        <input
          id="api-base-url"
          name="api-base-url"
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="https://plugin.example.com…"
          value={apiBaseUrl}
          onChange={(event) => setApiBaseUrl(event.currentTarget.value)}
          required
        />
        <label htmlFor="api-key">
          <span>API Key</span>
        </label>
        <input
          id="api-key"
          name="api-key"
          type="password"
          autoComplete="new-password"
          spellCheck={false}
          placeholder="生产环境必填"
          value={apiKey}
          onChange={(event) => setApiKey(event.currentTarget.value)}
        />
        <button type="submit" disabled={status === "capturing" || status === "uploading"}>
          {buttonLabel(status)}
        </button>
      </form>

      <StatusPanel status={status} error={error} result={result} />
    </main>
    </>
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
    return (
      <section className="popupStatus" role="status">
        <strong>Ready</strong>
        <span>{TARGET_CONFIG.idleStatusText}</span>
      </section>
    );
  }

  if (status === "capturing") {
    return (
      <section className="popupStatus popupStatus--busy" role="status">
        <strong>采集中…</strong>
        <span>正在读取当前页面的 Raw VOC。</span>
      </section>
    );
  }

  if (status === "uploading") {
    return (
      <section className="popupStatus popupStatus--busy" role="status">
        <strong>回传中…</strong>
        <span>正在写入私有服务器。</span>
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className="popupStatus popupStatus--error" role="alert">
        <strong>错误</strong>
        <span>{error}</span>
      </section>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <section className="popupResult" aria-label="采集结果">
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
    return "采集中…";
  }
  if (status === "uploading") {
    return "回传中…";
  }
  return "采集并回传";
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
  message: CaptureCurrentPageMessage
): Promise<TResponse> {
  return chrome.tabs.sendMessage(tabId, message) as Promise<TResponse>;
}

async function sendRuntimeMessage<TResponse>(
  message: UploadCollectionMessage | GetPlatformSettingMessage
): Promise<TResponse> {
  return chrome.runtime.sendMessage(message) as Promise<TResponse>;
}

async function loadCaptureRuntimeSettings(
  apiBaseUrl: string
): Promise<CaptureRuntimeSettings | undefined> {
  if (TARGET_CONFIG.platform !== "amazon") {
    return undefined;
  }

  const response = await sendRuntimeMessage<GetPlatformSettingResponse>({
    type: GET_PLATFORM_SETTING_MESSAGE_TYPE,
    apiBaseUrl,
    platform: "amazon"
  });

  if ("error" in response) {
    return undefined;
  }

  return amazonRuntimeSettingsFromPlatformSetting(response);
}

const POPUP_STYLE = `
:root {
  color-scheme: light;
}

* {
  box-sizing: border-box;
}

body {
  width: 360px;
  min-width: 320px;
  margin: 0;
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.92), transparent 220px),
    linear-gradient(180deg, #f7f9fd 0%, #eef1f6 54%, #dfe4ec 100%);
  color: #20242c;
  font-family: "SF Pro Text", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 14px;
  letter-spacing: 0;
}

button,
input {
  font: inherit;
}

button {
  touch-action: manipulation;
}

button:focus-visible,
input:focus-visible {
  outline: 3px solid rgba(62, 120, 214, 0.34);
  outline-offset: 2px;
}

.popupShell {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(185, 193, 207, 0.72);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(247, 249, 252, 0.72)),
    rgba(255, 255, 255, 0.58);
}

.popupHeader {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(185, 193, 207, 0.82);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  box-shadow: 0 10px 26px rgba(35, 45, 62, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.popupMark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid #9fb5d8;
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff, #e7f0ff);
  color: #3e78d6;
  font-size: 12px;
  font-weight: 900;
}

.popupShell--amazon .popupMark {
  border-color: rgba(194, 138, 44, 0.45);
  background: linear-gradient(180deg, #ffffff, #fbf1de);
  color: #a46b12;
}

.popupShell--reddit .popupMark {
  border-color: rgba(201, 77, 72, 0.45);
  background: linear-gradient(180deg, #ffffff, #fae7e5);
  color: #b13f37;
}

.popupShell--instagram .popupMark {
  border-color: rgba(187, 79, 147, 0.45);
  background: linear-gradient(180deg, #ffffff, #f8e7f2);
  color: #9c3f7a;
}

.popupHeader p,
.popupHeader h1 {
  margin: 0;
}

.popupHeader p,
.popupForm span,
.popupResult dt {
  color: #747d8c;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.popupHeader h1 {
  margin-top: 3px;
  color: #20242c;
  font-family: "SF Pro Display", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 18px;
  font-weight: 760;
  line-height: 1.12;
}

.popupForm {
  display: grid;
  gap: 8px;
}

.popupForm input {
  width: 100%;
  min-height: 40px;
  padding: 9px 10px;
  border: 1px solid rgba(185, 193, 207, 0.9);
  border-radius: 7px;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  box-shadow: inset 0 1px 2px rgba(35, 45, 62, 0.08), 0 1px 0 rgba(255, 255, 255, 0.78);
  color: #20242c;
  font-weight: 760;
}

.popupForm button {
  min-height: 42px;
  border: 1px solid rgba(36, 95, 184, 0.86);
  border-radius: 7px;
  background: linear-gradient(180deg, #5f94e5, #3e78d6);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.36), 0 8px 18px rgba(36, 95, 184, 0.22);
  color: #ffffff;
  cursor: pointer;
  font-weight: 760;
}

.popupForm button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.popupStatus,
.popupResult {
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid rgba(185, 193, 207, 0.82);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  box-shadow: 0 10px 24px rgba(35, 45, 62, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.popupStatus strong {
  font-size: 14px;
}

.popupStatus span {
  color: #444c59;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.popupStatus--busy {
  border-color: rgba(183, 131, 33, 0.34);
  background: linear-gradient(180deg, #ffffff, #fbefd7);
}

.popupStatus--error {
  border-color: rgba(201, 77, 72, 0.38);
  background: linear-gradient(180deg, #ffffff, #fae7e5);
  color: #7f2723;
}

.popupResult dl {
  display: grid;
  gap: 8px;
  margin: 0;
}

.popupResult dl div {
  min-width: 0;
  padding: 8px;
  border: 1px solid rgba(217, 222, 232, 0.96);
  border-radius: 7px;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  box-shadow: inset 0 1px 2px rgba(35, 45, 62, 0.08), 0 1px 0 rgba(255, 255, 255, 0.78);
}

.popupResult dd {
  margin: 3px 0 0;
  font-weight: 760;
  overflow-wrap: anywhere;
}
`;

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(<Popup />);
}
