import { useEffect, useMemo, useState } from "react";

import type { CaptureCurrentPageInput, CaptureRuntimeSettings } from "../../lib/capture-types";
import { amazonRuntimeSettingsFromPlatformSetting } from "../../lib/platform-runtime-settings";
import type { DetectedPage } from "../../lib/page-detect";
import {
  DEFAULT_API_BASE_URL,
  loadApiBaseUrl,
  saveApiBaseUrl
} from "../../lib/settings";
import type {
  CollectionRunPayload,
  CollectionTaskPayload,
  CollectionTaskResult,
  InsightBrief,
  InsightBriefsResponse,
  JsonObject,
  Platform,
  StrategyNotesResponse
} from "../../types/contracts";
import {
  CREATE_COLLECTION_TASK_MESSAGE_TYPE,
  GET_INSIGHT_BRIEFS_MESSAGE_TYPE,
  GET_PLATFORM_SETTING_MESSAGE_TYPE,
  UPLOAD_COLLECTION_MESSAGE_TYPE,
  type CaptureSummary,
  type CreateCollectionTaskMessage,
  type GetInsightBriefsMessage,
  type GetInsightBriefsResponse,
  type GetPlatformSettingMessage,
  type GetPlatformSettingResponse,
  type GetStrategyNotesMessage,
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
type DrawerTabKey = "plan" | "raw" | "schema" | "insight" | "handoff";
type NextActionKind = "preview" | "upload" | "server_task" | "insight" | "busy" | "blocked";

type NextActionState = {
  kind: NextActionKind;
  label: string;
  title: string;
  detail: string;
  disabled: boolean;
};

type DrawerTabState = {
  key: DrawerTabKey;
  label: string;
  title: string;
  detail: string;
  state: "waiting" | "active" | "done" | "error";
};

type RecoverySuggestion = {
  tone: "info" | "warning" | "error";
  title: string;
  detail: string;
};

export function ContentCommandBar({
  detectedPage,
  sourceUrl,
  documentRoot,
  onDismiss,
  captureCurrentPage
}: {
  detectedPage: DetectedPage;
  sourceUrl: string;
  documentRoot: Document;
  onDismiss: () => void;
  captureCurrentPage: (input: CaptureCurrentPageInput) => Promise<{
    payload: CollectionRunPayload;
    summary: CaptureSummary;
  }>;
}) {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [expanded, setExpanded] = useState(true);
  const [status, setStatus] = useState<CommandBarStatus>("ready");
  const [captureSummary, setCaptureSummary] = useState<CaptureSummary | null>(null);
  const [payload, setPayload] = useState<CollectionRunPayload | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadCollectionResponse | null>(null);
  const [insightBriefs, setInsightBriefs] = useState<InsightBriefsResponse | null>(null);
  const [strategyNotes, setStrategyNotes] = useState<StrategyNotesResponse | null>(null);
  const [collectionTaskResult, setCollectionTaskResult] = useState<CreateCollectionTaskResponse | null>(null);
  const [taskBusy, setTaskBusy] = useState(false);
  const [insightBusy, setInsightBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [activeDrawerTab, setActiveDrawerTab] = useState<DrawerTabKey>("plan");

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
          setApiBaseUrl(DEFAULT_API_BASE_URL);
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
    setInsightBriefs(null);
    setStrategyNotes(null);
    setCollectionTaskResult(null);
    setTaskBusy(false);
    setInsightBusy(false);
    setError(null);
    setNotice(null);
    setActiveDrawerTab("plan");
  }, [sourceUrl]);

  const snapshot = useMemo(
    () => getPageSnapshot(detectedPage, documentRoot, sourceUrl),
    [detectedPage, documentRoot, sourceUrl]
  );
  const pipelineSteps = buildPipelineSteps(status, captureSummary);
  const confidence = captureSummary ? formatConfidencePercent(captureSummary.coverage_confidence) : "-";
  const canCreateServerTask = shouldOfferServerTask(detectedPage, captureSummary);
  const isInstagramAuthorizationGated = detectedPage.platform === "instagram";
  const isBusy = status === "capturing" || status === "uploading" || taskBusy || insightBusy;
  const nextAction = nextActionForState(
    status,
    captureSummary,
    canCreateServerTask,
    taskBusy,
    isInstagramAuthorizationGated
  );
  const drawerTabs = buildDrawerTabs({
    status,
    captureSummary,
    uploadResult,
    insightBriefs,
    strategyNotes,
    collectionTaskResult,
    canCreateServerTask,
    authorizationGated: isInstagramAuthorizationGated
  });
  const activeDrawerTabState = drawerTabs.find((tab) => tab.key === activeDrawerTab) ?? drawerTabs[0];
  const recoverySuggestion = recoverySuggestionForState({
    detectedPage,
    captureSummary,
    collectionTaskResult,
    canCreateServerTask,
    authorizationGated: isInstagramAuthorizationGated,
    error,
    apiBaseUrl
  });

  async function handlePreview() {
    setStatus("capturing");
    setError(null);
    setNotice(null);
    setUploadResult(null);
    setInsightBriefs(null);
    setStrategyNotes(null);

    try {
      const result = await captureCurrentPage({
        url: sourceUrl,
        documentRoot,
        runtimeSettings: await loadCaptureRuntimeSettings()
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
    setInsightBriefs(null);
    setStrategyNotes(null);
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
      documentRoot,
      runtimeSettings: await loadCaptureRuntimeSettings()
    });
    setPayload(result.payload);
    setCaptureSummary(result.summary);
    return result;
  }

  async function loadCaptureRuntimeSettings(): Promise<CaptureRuntimeSettings | undefined> {
    if (detectedPage.platform !== "amazon") {
      return undefined;
    }

    try {
      const normalizedApiBaseUrl = await saveApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      const response = await sendRuntimeMessage<GetPlatformSettingResponse>({
        type: GET_PLATFORM_SETTING_MESSAGE_TYPE,
        apiBaseUrl: normalizedApiBaseUrl,
        platform: "amazon"
      });

      if ("error" in response) {
        setNotice("未读取到后台 Amazon 配置，使用默认页预算。");
        return undefined;
      }

      const runtimeSettings = amazonRuntimeSettingsFromPlatformSetting(response);
      if (!runtimeSettings?.amazonPageLimit) {
        setNotice("后台 Amazon 页预算为空，使用默认页预算。");
      }
      return runtimeSettings;
    } catch (error) {
      if (error instanceof Error && error.message === "platform_disabled_by_settings") {
        throw error;
      }
      setNotice("未读取到后台 Amazon 配置，使用默认页预算。");
      return undefined;
    }
  }

  async function handleAiInsight() {
    if (!captureSummary) {
      setNotice("先采集预览，确认 Raw VOC 与 schema 覆盖后再进入 AI 洞察。");
      setExpanded(true);
      return;
    }

    setInsightBusy(true);
    setError(null);
    setNotice(null);

    try {
      if (!isInsightPlatform(detectedPage.platform)) {
        throw new Error("insight_briefs_platform_required");
      }
      const normalizedApiBaseUrl = await saveApiBaseUrl(apiBaseUrl);
      setApiBaseUrl(normalizedApiBaseUrl);
      const response = await sendRuntimeMessage<GetInsightBriefsResponse>({
        type: GET_INSIGHT_BRIEFS_MESSAGE_TYPE,
        apiBaseUrl: normalizedApiBaseUrl,
        platform: detectedPage.platform
      });

      if ("error" in response) {
        throw new Error(response.error);
      }

      setInsightBriefs(response);
      setStrategyNotes(null);
      setNotice(response.items.length > 0 ? "已读取后台经营诊断。" : "后台暂无该平台经营诊断。");
      setExpanded(true);
    } catch (nextError) {
      setError(stableError(nextError));
    } finally {
      setInsightBusy(false);
    }
  }

  function handlePrimaryAction() {
    if (nextAction.kind === "preview") {
      void handlePreview();
      return;
    }
    if (nextAction.kind === "upload") {
      void handleUpload();
      return;
    }
    if (nextAction.kind === "server_task") {
      void handleCreateServerTask();
      return;
    }
    if (nextAction.kind === "insight") {
      void handleAiInsight();
    }
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

  const objectTitle = detectedObjectTitle(detectedPage);
  const sourceTitle = snapshot.title ?? objectTitle;
  const sourceLocation = snapshot.marketplace ?? snapshot.subreddit ?? snapshot.instagramMediaKind ?? "-";
  const primaryInsightBrief = insightBriefs ? selectPrimaryInsightBrief(insightBriefs.items) : null;

  return (
    <aside
      className={`ph-shell ph-shell--${detectedPage.platform} ${
        expanded ? "ph-shell--open" : "ph-shell--collapsed"
      }`}
      aria-label="Plugin Hub VOC Drawer"
    >
      {expanded ? (
        <div className="ph-drawer">
          <header className="ph-drawer-header">
            <div className="ph-brand">
              <div className="ph-brand-mark" aria-hidden="true">
                PH
              </div>
              <div>
                <strong>Plugin Hub</strong>
                <span>{platformName(detectedPage)} VOC</span>
              </div>
            </div>
            <div className="ph-header-actions">
              <button
                type="button"
                className="ph-ghost-button"
                aria-label="折叠 Plugin Hub 抽屉"
                onClick={() => setExpanded(false)}
              >
                收起
              </button>
              <button type="button" className="ph-ghost-button" aria-label="关闭 Plugin Hub 抽屉" onClick={onDismiss}>
                关闭
              </button>
            </div>
          </header>

          <nav className="ph-loop-tabs" aria-label="Loop 工程阶段" role="tablist">
            {drawerTabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeDrawerTab === tab.key}
                className={`ph-loop-tab ph-loop-tab--${tab.state}`}
                onClick={() => setActiveDrawerTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <section
            className={`ph-section ph-stage-panel ph-stage-panel--${activeDrawerTabState.state}`}
            aria-label="当前 Loop 阶段"
            role="tabpanel"
          >
            <span>{activeDrawerTabState.label}</span>
            <strong>{activeDrawerTabState.title}</strong>
            <p>{activeDrawerTabState.detail}</p>
          </section>

          <section className="ph-section ph-source" aria-label="检测对象">
            <div className="ph-section-kicker">
              <span className={`ph-badge ph-badge--${detectedPage.platform}`}>{platformName(detectedPage)}</span>
              <span className="ph-badge">{detectedPage.platform === "instagram" ? "Auth gated" : "Guest mode"}</span>
            </div>
            <h2>{sourceTitle}</h2>
            <dl className="ph-meta-grid">
              <div>
                <dt>{primaryObjectLabel(detectedPage)}</dt>
                <dd>{objectTitle}</dd>
              </div>
              <div>
                <dt>{sourceContextLabel(detectedPage)}</dt>
                <dd>{sourceLocation}</dd>
              </div>
              <div>
                <dt>类型</dt>
                <dd>{detectedObjectSubtitle(detectedPage)}</dd>
              </div>
              <div>
                <dt>{evidenceMethodLabel(detectedPage)}</dt>
                <dd>{evidenceMethodValue(detectedPage, snapshot)}</dd>
              </div>
              <div>
                <dt>{strategyLabel(detectedPage)}</dt>
                <dd>{strategyValue(detectedPage, snapshot)}</dd>
              </div>
            </dl>
          </section>

          <section className="ph-section ph-action-panel" aria-label="采集操作">
            <div className="ph-next-action">
              <span>Next Step</span>
              <strong>{nextAction.title}</strong>
              <p>{nextAction.detail}</p>
            </div>
            <button
              type="button"
              className="ph-button ph-button--primary"
              onClick={handlePrimaryAction}
              disabled={isBusy || nextAction.disabled}
            >
              {nextAction.label}
            </button>
            {payload ? (
              <div className="ph-secondary-actions">
                <button type="button" className="ph-mini-button" onClick={handlePreview} disabled={isBusy}>
                  重新预览
                </button>
                <button type="button" className="ph-mini-button" onClick={() => void handleAiInsight()} disabled={isBusy}>
                  {insightBusy ? "读取中" : "AI 洞察"}
                </button>
              </div>
            ) : null}
          </section>

          {recoverySuggestion ? (
            <section
              className={`ph-section ph-recovery ph-recovery--${recoverySuggestion.tone}`}
              aria-label="恢复建议"
              role={recoverySuggestion.tone === "error" ? "alert" : "status"}
            >
              <strong>{recoverySuggestion.title}</strong>
              <p>{recoverySuggestion.detail}</p>
            </section>
          ) : null}

          <section className="ph-section ph-metrics" aria-label="采集概览">
            <div>
              <span>Raw</span>
              <strong>{captureSummary?.raw_item_count ?? "-"}</strong>
            </div>
            <div>
              <span>VOC</span>
              <strong>{uploadResult && !("error" in uploadResult) ? uploadResult.voc_unit_count : "-"}</strong>
            </div>
            <div>
              <span>Coverage</span>
              <strong>{confidence}</strong>
            </div>
          </section>

          <section className="ph-section ph-pipeline" aria-label="VOC Pipeline">
            <div className="ph-section-heading">
              <strong>VOC Pipeline</strong>
              <span>{platformName(detectedPage)} capture path</span>
            </div>
            <ol className="ph-pipeline-list">
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
          </section>

          <section className="ph-section ph-evidence" aria-label="采集证据">
            <div className="ph-section-heading">
              <strong>Evidence</strong>
              <span>{captureSummary ? captureSummaryStatusText(captureSummary) : "等待采集"}</span>
            </div>
            <div className="ph-button-row">
              {payload ? (
                <>
                  <button type="button" className="ph-mini-button" onClick={handleExportJson}>
                    导出 JSON
                  </button>
                  <button type="button" className="ph-mini-button" onClick={handleExportCsv}>
                    导出 CSV
                  </button>
                </>
              ) : null}
              {canCreateServerTask ? (
                <button type="button" className="ph-mini-button" onClick={handleCreateServerTask} disabled={isBusy}>
                  {taskBusy ? "提交中" : "服务端补采"}
                </button>
              ) : null}
            </div>
            <div className="ph-status-stack" aria-live="polite">
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
              {error ? (
                <span className="ph-error" role="alert">
                  错误：{error}
                </span>
              ) : null}
            </div>
          </section>

          {insightBriefs ? (
            <section className="ph-section ph-insights ph-insight-brief" aria-label="经营诊断">
              <div className="ph-section-heading">
                <strong>经营诊断</strong>
                <span>{insightBriefs.items.length} insight briefs</span>
              </div>
              {primaryInsightBrief ? (
                <InsightBriefSummary brief={primaryInsightBrief} />
              ) : (
                <span className="ph-run-state">暂无后台经营诊断</span>
              )}
            </section>
          ) : strategyNotes ? (
            <section className="ph-section ph-insights" aria-label="AI 洞察">
              <div className="ph-section-heading">
                <strong>AI Insights</strong>
                <span>{strategyNotes.items.length} strategy notes</span>
              </div>
              {strategyNotes.items.length > 0 ? (
                <ol className="ph-pipeline-list">
                  {strategyNotes.items.slice(0, 3).map((note) => (
                    <li key={`${note.topic}:${note.evidence_count}`} className="ph-step ph-step--active">
                      <span className="ph-step-index">{note.evidence_count}</span>
                      <div>
                        <strong>{note.topic}</strong>
                        <span>{note.recommendation}</span>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <span className="ph-run-state">暂无后台 strategy notes</span>
              )}
            </section>
          ) : null}

          <details className="ph-section ph-settings">
            <summary>回传设置</summary>
            <label>
              <span>API 地址</span>
              <input
                type="url"
                name="plugin-hub-api-base-url"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                value={apiBaseUrl}
                aria-label="私有服务器 API 地址"
                onChange={(event) => setApiBaseUrl(event.currentTarget.value)}
              />
            </label>
          </details>
        </div>
      ) : (
        <button
          type="button"
          className="ph-rail"
          aria-label="展开 Plugin Hub 抽屉"
          onClick={() => setExpanded(true)}
        >
          <span className="ph-rail-mark" aria-hidden="true">
            PH
          </span>
          <span className="ph-rail-copy">
            <strong>{platformName(detectedPage)}</strong>
            <span>{objectTitle}</span>
          </span>
          <span className="ph-rail-state">{railStatusText(status, captureSummary, uploadResult)}</span>
        </button>
      )}
    </aside>
  );
}

function InsightBriefSummary({ brief }: { brief: InsightBrief }) {
  const primaryAction = brief.action_plan[0];
  const primaryGap = brief.data_gaps[0];
  const primaryEvidence = brief.evidence_refs[0];

  return (
    <article className="ph-brief-card">
      <h3>{brief.headline}</h3>
      <dl className="ph-brief-meta">
        <div>
          <dt>confidence</dt>
          <dd>{brief.confidence.level}</dd>
        </div>
        <div>
          <dt>evidence</dt>
          <dd>{brief.confidence.evidence_count}</dd>
        </div>
      </dl>
      <p className="ph-brief-reason">{brief.confidence.reason}</p>
      {primaryAction ? (
        <section className="ph-brief-block" aria-label="优先行动">
          <span>{primaryAction.expected_metric}</span>
          <strong>{primaryAction.title}</strong>
          <p>{primaryAction.recommendation}</p>
        </section>
      ) : null}
      {primaryGap ? (
        <section className="ph-brief-block" aria-label="证据缺口">
          <span>Data Gap</span>
          <strong>{primaryGap.description}</strong>
          <p>{primaryGap.recommended_collection}</p>
        </section>
      ) : null}
      {primaryEvidence ? (
        <blockquote className="ph-brief-quote">
          <span>Evidence</span>
          <p>{primaryEvidence.quote}</p>
        </blockquote>
      ) : null}
    </article>
  );
}

function selectPrimaryInsightBrief(briefs: InsightBrief[]): InsightBrief | null {
  return briefs
    .slice()
    .sort((left, right) => insightBriefScore(right) - insightBriefScore(left))[0] ?? null;
}

function insightBriefScore(brief: InsightBrief): number {
  const confidenceScore = {
    high: 4,
    medium: 3,
    low: 2,
    hypothesis: 1
  }[brief.confidence.level] ?? 0;
  return confidenceScore * 10 + brief.confidence.evidence_count;
}

function buildDrawerTabs({
  status,
  captureSummary,
  uploadResult,
  insightBriefs,
  strategyNotes,
  collectionTaskResult,
  canCreateServerTask,
  authorizationGated
}: {
  status: CommandBarStatus;
  captureSummary: CaptureSummary | null;
  uploadResult: UploadCollectionResponse | null;
  insightBriefs: InsightBriefsResponse | null;
  strategyNotes: StrategyNotesResponse | null;
  collectionTaskResult: CreateCollectionTaskResponse | null;
  canCreateServerTask: boolean;
  authorizationGated: boolean;
}): DrawerTabState[] {
  const hasRawItems = Boolean(captureSummary && captureSummary.raw_item_count > 0);
  const hasUpload = Boolean(uploadResult && !("error" in uploadResult));
  const hasTask = Boolean(collectionTaskResult && !("error" in collectionTaskResult));
  const hasInsightBriefs = Boolean(insightBriefs);
  const emptyRaw = Boolean(captureSummary && captureSummary.raw_item_count === 0);
  const failed = status === "error";

  return [
    {
      key: "plan",
      label: "计划",
      title: authorizationGated ? "授权门禁优先" : "确认采集计划",
      detail: authorizationGated
        ? "当前平台需要后端授权后才能进入 live read，插件侧只展示对象与门禁状态。"
        : "先确认页面对象、采集方法和下一步动作，再进入 Raw 预览。",
      state: status === "ready" || status === "capturing" || authorizationGated ? "active" : "done"
    },
    {
      key: "raw",
      label: "Raw",
      title: captureSummary ? `Raw ${captureSummary.raw_item_count}` : "等待 Raw 采集",
      detail: captureSummary
        ? captureSummaryStatusText(captureSummary)
        : "尚未读取页面 Raw VOC，先执行采集预览。",
      state: failed || emptyRaw ? "error" : hasRawItems ? "done" : status === "capturing" ? "active" : "waiting"
    },
    {
      key: "schema",
      label: "Schema",
      title: hasRawItems ? "Schema Mapping 就绪" : "等待有效 Raw",
      detail: hasRawItems
        ? "Raw item 已保留 schema、payload hash 与 coverage scope，可回传生成 Canonical VOC。"
        : emptyRaw
          ? "当前页面没有有效 raw，需走补采或授权路径。"
          : "Schema 映射依赖 Raw 预览结果。",
      state: failed || emptyRaw ? "error" : hasRawItems || hasUpload ? "done" : "waiting"
    },
    {
      key: "insight",
      label: "洞察",
      title: insightBriefs
        ? `${insightBriefs.items.length} 条经营诊断`
        : strategyNotes
          ? `${strategyNotes.items.length} 条策略 notes`
          : "等待后台洞察",
      detail: insightBriefs
        ? "已读取后台经营诊断，可快速判断优先运营动作。"
        : strategyNotes
          ? "已读取后台 strategy notes，可继续判断选品、Listing 或广告动作。"
        : hasUpload
          ? "Canonical VOC 已写入后台，可以读取经营诊断。"
          : "洞察需要先完成回传或后台已有经营诊断。",
      state: hasInsightBriefs || strategyNotes ? "done" : hasUpload ? "active" : "waiting"
    },
    {
      key: "handoff",
      label: "回传",
      title: hasTask ? "补采任务已提交" : hasUpload ? "后台已写入" : canCreateServerTask ? "待提交补采" : "等待回传",
      detail: hasTask
        ? "服务端补采任务已进入后台队列，请在 VOC Hub 继续复核状态。"
        : hasUpload
          ? "Canonical VOC 已进入后台，可在 VOC Hub 复核证据。"
          : canCreateServerTask
            ? "Reddit browser capture 返回 Raw 0，建议提交 server capture queue。"
            : "预览确认后再写入后台，避免把低证据内容直接升级。",
      state: hasTask || hasUpload ? "done" : canCreateServerTask || status === "previewed" ? "active" : "waiting"
    }
  ];
}

function recoverySuggestionForState({
  detectedPage,
  captureSummary,
  collectionTaskResult,
  canCreateServerTask,
  authorizationGated,
  error,
  apiBaseUrl
}: {
  detectedPage: DetectedPage;
  captureSummary: CaptureSummary | null;
  collectionTaskResult: CreateCollectionTaskResponse | null;
  canCreateServerTask: boolean;
  authorizationGated: boolean;
  error: string | null;
  apiBaseUrl: string;
}): RecoverySuggestion | null {
  if (error) {
    return {
      tone: "error",
      title: "恢复建议",
      detail: recoveryDetailForError(error, apiBaseUrl)
    };
  }

  if (collectionTaskResult && !("error" in collectionTaskResult)) {
    return {
      tone: "info",
      title: "补采已进入队列",
      detail: `任务 ${collectionTaskResult.collection_task_id} 当前为 ${collectionTaskResult.status}，请在 VOC Hub 的任务状态继续复核。`
    };
  }

  if (authorizationGated) {
    return {
      tone: "warning",
      title: "授权门禁",
      detail: "当前 Instagram 页面只展示目标对象和 Meta API 路径；需要后端授权、credential 与任务审批后才能进入 live read。"
    };
  }

  if (canCreateServerTask) {
    return {
      tone: "warning",
      title: "恢复建议：服务端补采",
      detail: "Reddit JSON 与 DOM 都没有有效 raw，请提交 server capture queue，并在 VOC Hub 复核 pending、retry 或 failed 状态。"
    };
  }

  if (detectedPage.platform === "reddit" && captureSummary?.stop_reason === "reddit_json_unavailable_dom_fallback") {
    return {
      tone: "info",
      title: "降级采集提示",
      detail: "Reddit JSON 不可达，当前结果来自 DOM fallback；回传后需关注 coverage confidence 和 quality flags。"
    };
  }

  return null;
}

function recoveryDetailForError(error: string, apiBaseUrl: string): string {
  if (error === "collection_run_requires_raw_items_submit_server_task") {
    return "当前预览没有有效 Raw VOC，先提交服务端补采任务或切换到可访问的页面后再回传。";
  }
  if (error === "platform_disabled_by_settings") {
    return "后台平台配置已关闭，先在 VOC Hub 启用该平台或切换到已启用平台。";
  }
  if (error.includes(":401")) {
    return "API Key 缺失或无权执行当前操作；请在扩展 popup 中更新生产 API Key 后重试。";
  }
  if (error.includes("fetch") || error.includes("network")) {
    return `网络或 API 不可达（当前 API：${apiBaseUrl}）。展开“回传设置”确认地址；如果使用本地 API，请先启动后端后重试；不要把本次结果记为平台采集成功。`;
  }
  return `保留当前状态并复核错误码：${error}`;
}

function nextActionForState(
  status: CommandBarStatus,
  captureSummary: CaptureSummary | null,
  canCreateServerTask: boolean,
  taskBusy: boolean,
  authorizationGated: boolean
): NextActionState {
  if (status === "capturing") {
    return {
      kind: "busy",
      label: "采集中…",
      title: "读取当前页面",
      detail: "正在提取页面上下文和 Raw VOC。",
      disabled: true
    };
  }
  if (status === "uploading") {
    return {
      kind: "busy",
      label: "回传中…",
      title: "写入后台",
      detail: "正在把采集结果写入私有 API。",
      disabled: true
    };
  }
  if (taskBusy) {
    return {
      kind: "busy",
      label: "提交中…",
      title: "创建补采任务",
      detail: "正在向后台队列提交服务端补采请求。",
      disabled: true
    };
  }
  if (authorizationGated) {
    return {
      kind: "blocked",
      label: "等待授权",
      title: "需要后端授权采集",
      detail: "Instagram 插件已隔离打包；采集需 Meta API 授权或 fixture 后端入口。",
      disabled: true
    };
  }
  if (status === "uploaded") {
    return {
      kind: "insight",
      label: "查看 AI 洞察",
      title: "进入策略分析",
      detail: "Canonical VOC 已写入后台，可以继续查看策略 notes。",
      disabled: false
    };
  }
  if (canCreateServerTask) {
    return {
      kind: "server_task",
      label: "服务端补采",
      title: "需要服务端补采",
      detail: "Reddit JSON 与 DOM 都没有有效 raw，建议提交后台补采任务。",
      disabled: false
    };
  }
  if (captureSummary) {
    return {
      kind: "upload",
      label: "回传到后台",
      title: "确认并写入",
      detail: "预览已经生成，下一步把 Canonical VOC 输入写入后台。",
      disabled: false
    };
  }
  return {
    kind: "preview",
    label: "采集预览",
    title: "先预览证据",
    detail: "读取当前页面，确认 Raw VOC 与覆盖范围后再回传。",
    disabled: false
  };
}

function railStatusText(
  status: CommandBarStatus,
  captureSummary: CaptureSummary | null,
  uploadResult: UploadCollectionResponse | null
): string {
  if (status === "uploaded" && uploadResult && !("error" in uploadResult)) {
    return `VOC ${uploadResult.voc_unit_count}`;
  }
  if (status === "capturing") {
    return "采集中";
  }
  if (status === "uploading") {
    return "回传中";
  }
  if (status === "error") {
    return "需处理";
  }
  if (captureSummary) {
    return `Raw ${captureSummary.raw_item_count}`;
  }
  return "Ready";
}

function shouldOfferServerTask(detectedPage: DetectedPage, summary: CaptureSummary | null): boolean {
  return (
    detectedPage.platform === "reddit" &&
    summary?.raw_item_count === 0 &&
    summary.stop_reason === "reddit_json_unavailable_dom_empty"
  );
}

function isInsightPlatform(platform: DetectedPage["platform"]): platform is Platform {
  return platform === "amazon" || platform === "reddit" || platform === "instagram";
}

function primaryObjectLabel(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return "ASIN";
  }
  if (detectedPage.platform === "reddit") {
    return "Thread";
  }
  if (detectedPage.platform === "instagram") {
    return "Shortcode";
  }
  return "Object";
}

function sourceContextLabel(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return "Marketplace";
  }
  if (detectedPage.platform === "reddit") {
    return "Subreddit";
  }
  if (detectedPage.platform === "instagram") {
    return "Media";
  }
  return "Source";
}

function evidenceMethodLabel(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return "评分";
  }
  if (detectedPage.platform === "instagram") {
    return "入口";
  }
  return "来源";
}

function evidenceMethodValue(detectedPage: DetectedPage, snapshot: ReturnType<typeof getPageSnapshot>): string {
  if (detectedPage.platform === "amazon") {
    return snapshot.rating ?? "-";
  }
  if (detectedPage.platform === "instagram") {
    return "Meta API";
  }
  return ".json + DOM";
}

function strategyLabel(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return "评论数";
  }
  if (detectedPage.platform === "instagram") {
    return "状态";
  }
  return "补充策略";
}

function strategyValue(detectedPage: DetectedPage, snapshot: ReturnType<typeof getPageSnapshot>): string {
  if (detectedPage.platform === "amazon") {
    return snapshot.reviewCount ?? "-";
  }
  if (detectedPage.platform === "instagram") {
    return "授权待接入";
  }
  return "DOM fallback";
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
  message:
    | UploadCollectionMessage
    | CreateCollectionTaskMessage
    | GetPlatformSettingMessage
    | GetInsightBriefsMessage
    | GetStrategyNotesMessage
): Promise<TResponse> {
  return chrome.runtime.sendMessage(message) as Promise<TResponse>;
}

function stableError(error: unknown): string {
  return error instanceof Error ? error.message : "plugin_hub_command_bar_failed:unknown";
}
