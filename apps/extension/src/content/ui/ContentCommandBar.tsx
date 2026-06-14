import { useEffect, useMemo, useState } from "react";

import { captureCurrentPage } from "../../lib/capture";
import type { DetectedPage } from "../../lib/page-detect";
import { loadApiBaseUrl, saveApiBaseUrl } from "../../lib/settings";
import type { CollectionRunPayload, CollectionTaskPayload, CollectionTaskResult, JsonObject } from "../../types/contracts";
import {
  CREATE_COLLECTION_TASK_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CaptureSummary,
  type CreateCollectionTaskMessage,
  type UploadCollectionMessage
} from "../../types/messages";
import {
  buildPipelineSteps,
  captureSummaryStatusText,
  detectedObjectSubtitle,
  detectedObjectTitle,
  formatConfidencePercent,
  platformName,
  type CommandBarStatus
} from "./command-bar-model";
import {
  buildExportFilename,
  buildPayloadJson,
  buildRawItemsCsv,
  downloadTextFile
} from "./export-payload";
import { getPageSnapshot } from "./page-snapshot";

type UploadCollectionResponse =
  | {
      collection_run_id: string;
      raw_item_count: number;
      voc_unit_count: number;
    }
  | { error: string };

type CreateCollectionTaskResponse = CollectionTaskResult | { error: string };

export function ContentCommandBar({
  detectedPage,
  sourceUrl,
  documentRoot,
  onDismiss
}: {
  detectedPage: DetectedPage;
  sourceUrl: string;
  documentRoot: Document;
  onDismiss: () => void;
}) {
  const [apiBaseUrl, setApiBaseUrl] = useState("http://localhost:8000");
  const [expanded, setExpanded] = useState(true);
  const [status, setStatus] = useState<CommandBarStatus>("ready");
  const [captureSummary, setCaptureSummary] = useState<CaptureSummary | null>(null);
  const [payload, setPayload] = useState<CollectionRunPayload | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadCollectionResponse | null>(null);
  const [collectionTaskResult, setCollectionTaskResult] = useState<CreateCollectionTaskResponse | null>(null);
  const [taskBusy, setTaskBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadApiBaseUrl()
      .then((value) => {
        if (!cancelled) {
          setApiBaseUrl(value);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiBaseUrl("http://localhost:8000");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setExpanded(true);
    setStatus("ready");
    setCaptureSummary(null);
    setPayload(null);
    setUploadResult(null);
    setCollectionTaskResult(null);
    setTaskBusy(false);
    setError(null);
    setNotice(null);
  }, [sourceUrl]);

  const snapshot = useMemo(
    () => getPageSnapshot(detectedPage, documentRoot, sourceUrl),
    [detectedPage, documentRoot, sourceUrl]
  );
  const pipelineSteps = buildPipelineSteps(status, captureSummary);
  const confidence = captureSummary ? formatConfidencePercent(captureSummary.coverage_confidence) : "-";
  const canCreateServerTask = shouldOfferServerTask(detectedPage, captureSummary);
  const isBusy = status === "capturing" || status === "uploading" || taskBusy;

  async function handlePreview() {
    setStatus("capturing");
    setError(null);
    setNotice(null);
    setUploadResult(null);

    try {
      const result = await captureCurrentPage({
        url: sourceUrl,
        documentRoot
      });
      setPayload(result.payload);
      setCaptureSummary(result.summary);
      setStatus("previewed");
      setExpanded(true);
      setCollectionTaskResult(null);
    } catch (nextError) {
      setError(stableError(nextError));
      setStatus("error");
    }
  }

  async function handleUpload() {
    setError(null);
    setNotice(null);
    setStatus(payload ? "uploading" : "capturing");

    try {
      const nextPayload = payload ?? (await captureForUpload()).payload;
      if (nextPayload.raw_items.length === 0) {
        throw new Error("collection_run_requires_raw_items_submit_server_task");
      }
      setStatus("uploading");
      const normalizedApiBaseUrl = await saveApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      const response = await sendRuntimeMessage<UploadCollectionResponse>({
        type: UPLOAD_COLLECTION_MESSAGE_TYPE,
        apiBaseUrl: normalizedApiBaseUrl,
        payload: nextPayload
      });

      if ("error" in response) {
        throw new Error(response.error);
      }

      setUploadResult(response);
      setStatus("uploaded");
      setExpanded(true);
    } catch (nextError) {
      setError(stableError(nextError));
      setStatus("error");
    }
  }

  async function handleCreateServerTask() {
    if (!canCreateServerTask || !captureSummary || detectedPage.platform !== "reddit") {
      return;
    }

    setTaskBusy(true);
    setError(null);
    setNotice(null);
    setCollectionTaskResult(null);

    try {
      const normalizedApiBaseUrl = await saveApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      const response = await sendRuntimeMessage<CreateCollectionTaskResponse>({
        type: CREATE_COLLECTION_TASK_MESSAGE_TYPE,
        apiBaseUrl: normalizedApiBaseUrl,
        payload: buildServerCollectionTaskPayload({
          detectedPage,
          sourceUrl,
          captureSummary,
          payload
        })
      });

      if ("error" in response) {
        throw new Error(response.error);
      }

      setCollectionTaskResult(response);
      setNotice(`服务端补采任务已提交：${response.collection_task_id}`);
      setExpanded(true);
    } catch (nextError) {
      setError(stableError(nextError));
    } finally {
      setTaskBusy(false);
    }
  }

  async function captureForUpload() {
    const result = await captureCurrentPage({
      url: sourceUrl,
      documentRoot
    });
    setPayload(result.payload);
    setCaptureSummary(result.summary);
    return result;
  }

  function handleAiInsight() {
    setNotice(
      captureSummary
        ? "AI 洞察入口已就绪：当前 MVP 会先回传 Canonical VOC，再由后台生成策略 notes。"
        : "先采集预览，确认 Raw VOC 与 schema 覆盖后再进入 AI 洞察。"
    );
    setExpanded(true);
  }

  function handleExportJson() {
    if (!payload) {
      return;
    }

    downloadTextFile(buildExportFilename(payload, "json"), "application/json", buildPayloadJson(payload));
    setNotice("已导出当前采集 payload JSON。");
  }

  function handleExportCsv() {
    if (!payload) {
      return;
    }

    downloadTextFile(buildExportFilename(payload, "csv"), "text/csv;charset=utf-8", buildRawItemsCsv(payload));
    setNotice("已导出当前 Raw VOC CSV 摘要。");
  }

  return (
    <section className="ph-shell" aria-label="Plugin Hub VOC Command Bar">
      <div className="ph-command">
        <div className="ph-brand">
          <div className="ph-brand-mark" aria-hidden="true">
            PH
          </div>
          <div>
            <strong>Plugin Hub</strong>
            <span>VOC Collector</span>
          </div>
        </div>

        <div className="ph-badges" aria-label="平台与登录状态">
          <span className={`ph-badge ph-badge--${detectedPage.platform}`}>{platformName(detectedPage)}</span>
          <span className="ph-badge">Guest mode</span>
        </div>

        <dl className="ph-object" aria-label="检测对象">
          <div>
            <dt>检测对象</dt>
            <dd>{detectedObjectTitle(detectedPage)}</dd>
          </div>
          <div>
            <dt>Marketplace</dt>
            <dd>{snapshot.marketplace ?? snapshot.subreddit ?? "-"}</dd>
          </div>
          <div>
            <dt>类型</dt>
            <dd>{detectedObjectSubtitle(detectedPage)}</dd>
          </div>
          <div>
            <dt>{detectedPage.platform === "amazon" ? "评分" : "来源"}</dt>
            <dd>{detectedPage.platform === "amazon" ? snapshot.rating ?? "-" : ".json + DOM fallback"}</dd>
          </div>
          <div>
            <dt>{detectedPage.platform === "amazon" ? "全球评分" : "Thread"}</dt>
            <dd>{detectedPage.platform === "amazon" ? snapshot.reviewCount ?? "-" : detectedObjectTitle(detectedPage)}</dd>
          </div>
        </dl>

        <div className="ph-actions">
          <button type="button" className="ph-button ph-button--secondary" onClick={handlePreview} disabled={isBusy}>
            {status === "capturing" ? "采集中" : "采集预览"}
          </button>
          <button type="button" className="ph-button ph-button--primary" onClick={handleUpload} disabled={isBusy}>
            {status === "uploading" ? "回传中" : "采集并回传"}
          </button>
          <button type="button" className="ph-button ph-button--secondary" onClick={handleAiInsight}>
            AI 洞察
          </button>
          <button
            type="button"
            className="ph-icon-button"
            aria-label={expanded ? "折叠 Plugin Hub 操作台" : "展开 Plugin Hub 操作台"}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "收起" : "展开"}
          </button>
          <button type="button" className="ph-icon-button" aria-label="关闭 Plugin Hub 操作台" onClick={onDismiss}>
            关闭
          </button>
        </div>
      </div>

      {expanded ? (
        <>
          <div className="ph-pipeline" aria-label="VOC Pipeline">
            <div className="ph-pipeline-title">
              <strong>VOC Pipeline</strong>
              <span>Amazon 与 Reddit 进入同一 Canonical VOC 模型</span>
            </div>
            <ol>
              {pipelineSteps.map((step, index) => (
                <li key={step.label} className={`ph-step ph-step--${step.state}`}>
                  <span className="ph-step-index">{index + 1}</span>
                  <div>
                    <strong>{step.label}</strong>
                    <span>{step.detail}</span>
                  </div>
                </li>
              ))}
            </ol>
            <div className="ph-confidence">
              <span>覆盖率 / Confidence</span>
              <strong>{confidence}</strong>
            </div>
          </div>

          <div className="ph-footer">
            <p>
              免登录可预览 schema；登录仅用于云端历史与团队协作。支持来源：
              <strong> Amazon</strong> / <strong>Reddit</strong>
            </p>
            <label>
              <span>API</span>
              <input
                type="url"
                value={apiBaseUrl}
                aria-label="私有服务器 API 地址"
                onChange={(event) => setApiBaseUrl(event.currentTarget.value)}
              />
            </label>
            {payload ? (
              <div className="ph-export-actions" aria-label="本地导出">
                <button type="button" className="ph-mini-button" onClick={handleExportJson}>
                  导出 JSON
                </button>
                <button type="button" className="ph-mini-button" onClick={handleExportCsv}>
                  导出 CSV
                </button>
              </div>
            ) : null}
            {canCreateServerTask ? (
              <button type="button" className="ph-mini-button" onClick={handleCreateServerTask} disabled={isBusy}>
                {taskBusy ? "提交中" : "服务端补采"}
              </button>
            ) : null}
            {captureSummary ? (
              <span className="ph-run-state">
                Raw {captureSummary.raw_item_count} · {captureSummaryStatusText(captureSummary)}
              </span>
            ) : null}
            {uploadResult && !("error" in uploadResult) ? (
              <span className="ph-run-state">
                Run {uploadResult.collection_run_id} · VOC {uploadResult.voc_unit_count}
              </span>
            ) : null}
            {collectionTaskResult && !("error" in collectionTaskResult) ? (
              <span className="ph-run-state">
                Task {collectionTaskResult.collection_task_id} · {collectionTaskResult.status}
              </span>
            ) : null}
            {notice ? <span className="ph-notice">{notice}</span> : null}
            {error ? <span className="ph-error">失败：{error}</span> : null}
          </div>
        </>
      ) : null}
    </section>
  );
}

function shouldOfferServerTask(detectedPage: DetectedPage, summary: CaptureSummary | null): boolean {
  return (
    detectedPage.platform === "reddit" &&
    summary?.raw_item_count === 0 &&
    summary.stop_reason === "reddit_json_unavailable_dom_empty"
  );
}

function buildServerCollectionTaskPayload({
  detectedPage,
  sourceUrl,
  captureSummary,
  payload
}: {
  detectedPage: Extract<DetectedPage, { platform: "reddit" }>;
  sourceUrl: string;
  captureSummary: CaptureSummary;
  payload: CollectionRunPayload | null;
}): CollectionTaskPayload {
  const context: JsonObject = {
    page_kind: captureSummary.page_kind,
    thread_id: detectedPage.threadId,
    client_capture_method: payload?.run.capture_method ?? "extension_reddit_dom_fallback",
    client_raw_item_count: captureSummary.raw_item_count,
    client_coverage_confidence: captureSummary.coverage_confidence,
    client_stop_reason: captureSummary.stop_reason ?? "unknown"
  };

  copyCoverageScopeScalar(context, payload?.run.coverage_scope, "json_url");
  copyCoverageScopeScalar(context, payload?.run.coverage_scope, "json_error");
  copyCoverageScopeScalar(context, payload?.run.coverage_scope, "dom_stop_reason");
  copyCoverageScopeScalar(context, payload?.run.coverage_scope, "fallback_parser");
  copyCoverageScopeScalar(context, payload?.run.coverage_scope, "comment_node_count");

  return {
    task: {
      platform: "reddit",
      source_url: sourceUrl,
      requested_capture_method: "server_reddit_json_proxy",
      trigger_reason: captureSummary.stop_reason ?? "reddit_capture_unavailable",
      context
    }
  };
}

function copyCoverageScopeScalar(context: JsonObject, coverageScope: JsonObject | undefined, key: string): void {
  const value = coverageScope?.[key];
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    context[key] = value;
  }
}

async function sendRuntimeMessage<TResponse>(
  message: UploadCollectionMessage | CreateCollectionTaskMessage
): Promise<TResponse> {
  return chrome.runtime.sendMessage(message) as Promise<TResponse>;
}

function stableError(error: unknown): string {
  return error instanceof Error ? error.message : "plugin_hub_command_bar_failed:unknown";
}
