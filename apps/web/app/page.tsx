import { VocEvidenceTable } from "../src/components/VocEvidenceTable";
import { fetchVocUnits, type VocUnit } from "../src/lib/api";

export const dynamic = "force-dynamic";

type LoadState = {
  units: VocUnit[];
  error: string | null;
};

export default async function Page() {
  const apiBaseUrl = process.env.PLUGIN_HUB_API_URL ?? "http://localhost:8000";
  const { units, error } = await loadVocUnits(apiBaseUrl);
  const metrics = getMetrics(units);

  return (
    <main className="workspace">
      <header className="workspaceHeader">
        <div>
          <p className="eyebrow">VOC Hub</p>
          <h1>证据工作台</h1>
        </div>
        <div className="apiStatus">
          <span>API</span>
          <strong>{apiBaseUrl}</strong>
        </div>
      </header>

      <section className="summaryGrid" aria-label="VOC 摘要指标">
        <MetricTile label="证据数" value={metrics.total} tone="neutral" />
        <MetricTile label="Amazon" value={metrics.amazon} tone="amazon" />
        <MetricTile label="Reddit" value={metrics.reddit} tone="reddit" />
        <MetricTile label="有 flags" value={metrics.flagged} tone="warning" />
      </section>

      {error ? <ErrorNotice error={error} /> : null}

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
        <VocEvidenceTable units={units} />
      </section>
    </main>
  );
}

async function loadVocUnits(apiBaseUrl: string): Promise<LoadState> {
  try {
    const data = await fetchVocUnits(apiBaseUrl, "all");
    return {
      units: data.items,
      error: null
    };
  } catch (error) {
    return {
      units: [],
      error: error instanceof Error ? error.message : "voc_units_fetch_failed:unknown"
    };
  }
}

function MetricTile({
  label,
  value,
  tone
}: {
  label: string;
  value: number;
  tone: "neutral" | "amazon" | "reddit" | "warning";
}) {
  return (
    <div className={`metricTile metricTile--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ErrorNotice({ error }: { error: string }) {
  return (
    <section className="errorNotice" aria-label="API 拉取失败">
      <div>
        <h2>API 拉取失败</h2>
        <p>{error}</p>
      </div>
      <p>检查 `PLUGIN_HUB_API_URL` 是否指向已启动的后端，并确认 `/api/voc-units` 可访问。</p>
    </section>
  );
}

function getMetrics(units: VocUnit[]) {
  const total = units.length;
  const amazon = units.filter((unit) => unit.platform === "amazon").length;
  const reddit = units.filter((unit) => unit.platform === "reddit").length;
  const flagged = units.filter((unit) => unit.quality_flags.length > 0).length;
  const averageConfidence =
    total === 0
      ? 0
      : Math.round(
          (units.reduce((sum, unit) => sum + unit.coverage_confidence, 0) / total) * 100
        );

  return {
    total,
    amazon,
    reddit,
    flagged,
    averageConfidence
  };
}
