import type { DataAssetRun } from "../lib/api";

export function DataAssetRunTable({ runs }: { runs: DataAssetRun[] }) {
  if (runs.length === 0) {
    return (
      <section className="emptyState" aria-label="空采集历史">
        <p className="emptyState__title">暂无采集批次</p>
        <p className="emptyState__body">数据库尚未保存 collection run。</p>
      </section>
    );
  }

  return (
    <div className="tableShell">
      <table className="evidenceTable assetRunTable">
        <caption className="visuallyHidden">
          最近采集批次及 raw、canonical、可分析证据和一致性状态。
        </caption>
        <thead>
          <tr>
            <th scope="col">采集时间</th>
            <th scope="col">平台</th>
            <th scope="col">Run</th>
            <th scope="col">Raw / Canonical</th>
            <th scope="col">可分析 / 占位</th>
            <th scope="col">覆盖</th>
            <th scope="col">状态</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.collection_run_id}>
              <td>{formatDate(run.created_at)}</td>
              <td>{run.platform}</td>
              <td>
                <code>{run.collection_run_id}</code>
                <small>{run.capture_method}</small>
              </td>
              <td>{run.raw_item_count} / {run.canonical_voc_count}</td>
              <td>{run.analysis_eligible_voc_count} / {run.placeholder_voc_count}</td>
              <td>{Math.round(run.coverage_confidence * 100)}%</td>
              <td>
                <span className={`runState runState--${run.asset_state}`}>
                  {stateLabel(run.asset_state)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      }).format(date);
}

function stateLabel(state: DataAssetRun["asset_state"]): string {
  if (state === "complete") {
    return "完整";
  }
  if (state === "empty") {
    return "空批次";
  }
  return "不一致";
}
