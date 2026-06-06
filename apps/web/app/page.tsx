import { DashboardAutoRefresh } from "../src/components/DashboardAutoRefresh";
import { VocEvidenceTable } from "../src/components/VocEvidenceTable";
import {
  fetchStrategyNotes,
  fetchVocUnits,
  type StrategyNote,
  type VocPlatform,
  type VocUnit
} from "../src/lib/api";
import { loadDashboardConfig, type DashboardConfig } from "../src/lib/config";

export const dynamic = "force-dynamic";

type DashboardData = {
  units: VocUnit[];
  strategyNotes: StrategyNote[];
  vocError: string | null;
  strategyError: string | null;
  loadedAt: string;
};

type DashboardMetrics = {
  total: number;
  amazon: number;
  reddit: number;
  flagged: number;
  lowConfidence: number;
  averageConfidence: number;
  runCount: number;
  latestCapturedAt: string | null;
};

export default async function Page() {
  const config = loadDashboardConfig();
  const data = await loadDashboardData(config.apiBaseUrl);
  const metrics = getMetrics(data.units, config.lowConfidenceThreshold);
  const apiState = getApiState(data);

  return (
    <main className="dashboardShell">
      <DashboardAutoRefresh intervalSeconds={config.refreshSeconds} />

      <header className="topBar">
        <div className="brandBlock">
          <p className="eyebrow">Plugin Hub</p>
          <h1>VOC 采集监控台</h1>
        </div>
        <div className={`statusPill statusPill--${apiState.tone}`} aria-label="API 状态">
          <span>{apiState.label}</span>
          <strong>{apiState.value}</strong>
        </div>
      </header>

      <section className="commandGrid" aria-label="运行总览">
        <HeroPanel metrics={metrics} config={config} loadedAt={data.loadedAt} />
        <ConfigPanel config={config} />
      </section>

      <CaptureTemplatePanel config={config} />

      <section className="metricGrid" aria-label="监控指标">
        <MetricTile label="证据总量" value={metrics.total} detail={`${metrics.runCount} 个 run`} tone="ink" />
        <MetricTile label="Amazon" value={metrics.amazon} detail="评论证据" tone="amazon" />
        <MetricTile label="Reddit" value={metrics.reddit} detail="Thread / comment" tone="reddit" />
        <MetricTile
          label="低置信度"
          value={metrics.lowConfidence}
          detail={`阈值 ${percent(config.lowConfidenceThreshold)}`}
          tone={metrics.lowConfidence > 0 ? "risk" : "clear"}
        />
        <MetricTile label="质量 Flags" value={metrics.flagged} detail="需复核证据" tone="warning" />
        <MetricTile label="平均覆盖" value={`${metrics.averageConfidence}%`} detail="coverage confidence" tone="clear" />
      </section>

      <section className="opsGrid" aria-label="运行监控">
        <MonitorPanel data={data} metrics={metrics} config={config} />
        <PlatformPanel units={data.units} />
        <StrategyPanel notes={data.strategyNotes} error={data.strategyError} />
      </section>

      {data.vocError ? <ErrorNotice title="VOC 数据拉取失败" error={data.vocError} /> : null}

      <section className="tableSection" aria-label="VOC 证据列表">
        <div className="sectionHeading">
          <div>
            <h2>Canonical VOC Units</h2>
            <p>按平台、对象上下文和质量信号扫描证据。</p>
          </div>
          <div className="confidenceSummary">
            <span>平均置信度</span>
            <strong>{metrics.averageConfidence}%</strong>
          </div>
        </div>
        <VocEvidenceTable units={data.units} />
      </section>
    </main>
  );
}

async function loadDashboardData(apiBaseUrl: string): Promise<DashboardData> {
  const [vocResult, strategyResult] = await Promise.allSettled([
    fetchVocUnits(apiBaseUrl, "all"),
    fetchStrategyNotes(apiBaseUrl, "all")
  ]);

  return {
    units: vocResult.status === "fulfilled" ? vocResult.value.items : [],
    strategyNotes: strategyResult.status === "fulfilled" ? strategyResult.value.items : [],
    vocError: vocResult.status === "rejected" ? stableError(vocResult.reason) : null,
    strategyError: strategyResult.status === "rejected" ? stableError(strategyResult.reason) : null,
    loadedAt: new Date().toISOString()
  };
}

function HeroPanel({
  metrics,
  config,
  loadedAt
}: {
  metrics: DashboardMetrics;
  config: DashboardConfig;
  loadedAt: string;
}) {
  return (
    <section className="heroPanel" aria-label="监控主视图">
      <div>
        <p className="panelKicker">Evidence Operations</p>
        <h2>把 Amazon 与 Reddit VOC 采集变成可观测的数据资产。</h2>
        <p>
          当前站点连接到 {config.apiBaseUrl}，每 {config.refreshSeconds} 秒刷新一次，用于跟踪证据量、
          覆盖置信度、质量 flags 和策略信号。
        </p>
      </div>
      <dl className="heroStats">
        <div>
          <dt>最新采集</dt>
          <dd>{metrics.latestCapturedAt ? formatDate(metrics.latestCapturedAt) : "暂无"}</dd>
        </div>
        <div>
          <dt>最近刷新</dt>
          <dd>{formatDate(loadedAt)}</dd>
        </div>
      </dl>
    </section>
  );
}

function ConfigPanel({ config }: { config: DashboardConfig }) {
  return (
    <section className="configPanel" aria-label="配置参数">
      <div className="sectionMiniHeading">
        <p className="panelKicker">Runtime Config</p>
        <h2>配置参数</h2>
      </div>
      <dl className="configList">
        <ConfigRow label="API Base URL" value={config.apiBaseUrl} />
        <ConfigRow label="环境" value={config.siteEnv} />
        <ConfigRow label="刷新周期" value={`${config.refreshSeconds}s`} />
        <ConfigRow label="启用平台" value={config.enabledPlatforms.join(", ")} />
        <ConfigRow label="Amazon 页预算" value={String(config.amazonPageLimit)} />
        <ConfigRow label="低置信度阈值" value={percent(config.lowConfidenceThreshold)} />
      </dl>
    </section>
  );
}

function CaptureTemplatePanel({ config }: { config: DashboardConfig }) {
  const templates = [
    {
      platform: "amazon" as const,
      title: "Amazon Reviews",
      subtitle: "评论页 DOM + next-page link walk",
      entry: "https://www.amazon.com/product-reviews/{ASIN}",
      method: "extension_dom_next_link_walk",
      coverage: ["ASIN", "marketplace", "page budget", "review count", "stop reason"],
      stop: "无下一页 / 页预算 / 空 DOM / 用户停止",
      enabled: config.enabledPlatforms.includes("amazon")
    },
    {
      platform: "reddit" as const,
      title: "Reddit Thread",
      subtitle: "Thread URL + .json?raw_json=1",
      entry: "https://www.reddit.com/r/{subreddit}/comments/{threadId}/{slug}/",
      method: "extension_reddit_json",
      coverage: ["thread", "comments", "parent_id", "depth", "more nodes"],
      stop: "JSON 缺失 / more node 未展开 / 访问失败",
      enabled: config.enabledPlatforms.includes("reddit")
    }
  ];

  return (
    <section className="templateSection" aria-label="采集模板">
      <div className="sectionMiniHeading">
        <p className="panelKicker">Capture Templates</p>
        <h2>双平台采集模板</h2>
      </div>
      <div className="templateGrid">
        {templates.map((template) => (
          <article
            key={template.platform}
            className={`templateCard templateCard--${template.platform}`}
          >
            <div className="templateCard__header">
              <div>
                <span>{template.enabled ? "enabled" : "disabled"}</span>
                <h3>{template.title}</h3>
              </div>
              <strong>{template.platform}</strong>
            </div>
            <p>{template.subtitle}</p>
            <dl>
              <div>
                <dt>入口</dt>
                <dd>{template.entry}</dd>
              </div>
              <div>
                <dt>采集方法</dt>
                <dd>{template.method}</dd>
              </div>
              <div>
                <dt>停止条件</dt>
                <dd>{template.stop}</dd>
              </div>
            </dl>
            <ul>
              {template.coverage.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}

function MonitorPanel({
  data,
  metrics,
  config
}: {
  data: DashboardData;
  metrics: DashboardMetrics;
  config: DashboardConfig;
}) {
  const checks = [
    {
      label: "VOC API",
      value: data.vocError ? data.vocError : "connected",
      tone: data.vocError ? "risk" : "clear"
    },
    {
      label: "Strategy API",
      value: data.strategyError ? data.strategyError : "connected",
      tone: data.strategyError ? "warning" : "clear"
    },
    {
      label: "Freshness",
      value: freshnessLabel(metrics.latestCapturedAt),
      tone: metrics.latestCapturedAt ? "clear" : "warning"
    },
    {
      label: "Quality Gate",
      value:
        metrics.lowConfidence > 0
          ? `${metrics.lowConfidence} 条低于 ${percent(config.lowConfidenceThreshold)}`
          : "no low-confidence evidence",
      tone: metrics.lowConfidence > 0 ? "risk" : "clear"
    }
  ] as const;

  return (
    <section className="opsPanel" aria-label="接口与质量监控">
      <div className="sectionMiniHeading">
        <p className="panelKicker">Monitor</p>
        <h2>接口与质量</h2>
      </div>
      <ul className="checkList">
        {checks.map((check) => (
          <li key={check.label} className={`checkItem checkItem--${check.tone}`}>
            <span>{check.label}</span>
            <strong>{check.value}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

function PlatformPanel({ units }: { units: VocUnit[] }) {
  const total = units.length;
  const platforms: Array<{ platform: VocPlatform; label: string; count: number }> = [
    {
      platform: "amazon",
      label: "Amazon",
      count: units.filter((unit) => unit.platform === "amazon").length
    },
    {
      platform: "reddit",
      label: "Reddit",
      count: units.filter((unit) => unit.platform === "reddit").length
    }
  ];

  return (
    <section className="opsPanel" aria-label="平台覆盖">
      <div className="sectionMiniHeading">
        <p className="panelKicker">Coverage</p>
        <h2>平台覆盖</h2>
      </div>
      <div className="platformBars">
        {platforms.map((item) => (
          <div key={item.platform} className="platformBar">
            <div className="platformBar__header">
              <span>{item.label}</span>
              <strong>{item.count}</strong>
            </div>
            <div className="platformBar__track">
              <span
                className={`platformBar__fill platformBar__fill--${item.platform}`}
                style={{ width: `${total === 0 ? 0 : Math.round((item.count / total) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function StrategyPanel({
  notes,
  error
}: {
  notes: StrategyNote[];
  error: string | null;
}) {
  return (
    <section className="opsPanel strategyPanel" aria-label="策略信号">
      <div className="sectionMiniHeading">
        <p className="panelKicker">Strategy Signals</p>
        <h2>策略信号</h2>
      </div>
      {error ? <p className="mutedText">{error}</p> : null}
      {notes.length === 0 && !error ? <p className="mutedText">暂无策略信号。</p> : null}
      <ul className="strategyList">
        {notes.slice(0, 4).map((note) => (
          <li key={note.topic}>
            <div>
              <span>{note.topic}</span>
              <strong>{note.evidence_count}</strong>
            </div>
            <p>{note.recommendation}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function MetricTile({
  label,
  value,
  detail,
  tone
}: {
  label: string;
  value: number | string;
  detail: string;
  tone: "ink" | "amazon" | "reddit" | "warning" | "risk" | "clear";
}) {
  return (
    <div className={`metricTile metricTile--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ErrorNotice({ title, error }: { title: string; error: string }) {
  return (
    <section className="errorNotice" aria-label={title}>
      <div>
        <h2>{title}</h2>
        <p>{error}</p>
      </div>
      <p>检查 `PLUGIN_HUB_API_URL` 是否指向已启动的后端，并确认 API 路由可访问。</p>
    </section>
  );
}

function getMetrics(units: VocUnit[], lowConfidenceThreshold: number): DashboardMetrics {
  const total = units.length;
  const amazon = units.filter((unit) => unit.platform === "amazon").length;
  const reddit = units.filter((unit) => unit.platform === "reddit").length;
  const flagged = units.filter((unit) => unit.quality_flags.length > 0).length;
  const lowConfidence = units.filter(
    (unit) => unit.coverage_confidence < lowConfidenceThreshold
  ).length;
  const averageConfidence =
    total === 0
      ? 0
      : Math.round(
          (units.reduce((sum, unit) => sum + unit.coverage_confidence, 0) / total) * 100
        );
  const runCount = new Set(
    units.map((unit) => unit.collection_run_id).filter((value): value is string => value !== null)
  ).size;
  const latestCapturedAt = latestDate(units.map((unit) => unit.captured_at));

  return {
    total,
    amazon,
    reddit,
    flagged,
    lowConfidence,
    averageConfidence,
    runCount,
    latestCapturedAt
  };
}

function getApiState(data: DashboardData) {
  if (data.vocError) {
    return {
      tone: "down",
      label: "API",
      value: "down"
    };
  }
  if (data.strategyError) {
    return {
      tone: "partial",
      label: "API",
      value: "partial"
    };
  }
  return {
    tone: "ok",
    label: "API",
    value: "online"
  };
}

function latestDate(values: string[]): string | null {
  const timestamps = values
    .map((value) => new Date(value).getTime())
    .filter((value) => Number.isFinite(value));

  if (timestamps.length === 0) {
    return null;
  }

  return new Date(Math.max(...timestamps)).toISOString();
}

function freshnessLabel(value: string | null): string {
  if (!value) {
    return "no evidence yet";
  }

  const elapsedMs = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) {
    return "captured";
  }

  const elapsedHours = Math.floor(elapsedMs / 1000 / 60 / 60);
  if (elapsedHours < 1) {
    return "within 1 hour";
  }
  if (elapsedHours < 24) {
    return `${elapsedHours} hours ago`;
  }
  return `${Math.floor(elapsedHours / 24)} days ago`;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function stableError(value: unknown): string {
  return value instanceof Error ? value.message : "request_failed:unknown";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
