import React from "react";

import type {
  AnalysisArtifactSnapshot,
  AnalysisArtifactType,
  AnalysisRunSnapshot,
  AnalysisSnapshotDetail,
  JsonValue
} from "../lib/api";

type AnalysisSnapshotHistoryProps = {
  snapshots: AnalysisRunSnapshot[];
  total: number;
  selectedRunId: string | null;
  detail: AnalysisSnapshotDetail | null;
  listError: string | null;
  detailError: string | null;
};

const ARTIFACT_LABELS: Record<AnalysisArtifactType, string> = {
  relation_edge: "Relation edges",
  enriched_voc_signal: "VOC signals",
  strategy_note: "Strategy notes",
  insight_brief: "Insight briefs"
};

const ARTIFACT_TYPES = Object.keys(ARTIFACT_LABELS) as AnalysisArtifactType[];

export function AnalysisSnapshotHistory({
  snapshots,
  total,
  selectedRunId,
  detail,
  listError,
  detailError
}: AnalysisSnapshotHistoryProps) {
  const orderedSnapshots = snapshots.slice().sort(compareNewestFirst);

  return (
    <section id="snapshot-history" className="snapshotLedger" aria-label="洞察快照历史">
      <header className="snapshotLedger__header">
        <div>
          <p className="panelKicker">Post-migration evidence ledger</p>
          <h2>洞察快照账本</h2>
          <p>
            只展示通过显式 snapshot API 持久化的不可变历史；实时洞察与迁移前输出不在此冒充历史。
          </p>
        </div>
        <div className="snapshotLedger__counter" aria-label={`${total} 个历史快照`}>
          <strong>{total}</strong>
          <span>immutable runs</span>
        </div>
      </header>

      {listError ? (
        <LedgerNotice
          tone="error"
          title="快照历史加载失败"
          detail={listError}
        />
      ) : orderedSnapshots.length === 0 ? (
        <LedgerNotice
          tone="empty"
          title="暂无迁移后洞察快照"
          detail="这里不会把实时重算冒充历史记录；请先通过受控 snapshot API 创建基线。"
        />
      ) : (
        <div className="snapshotLedger__workspace">
          <SnapshotTimeline
            snapshots={orderedSnapshots}
            total={total}
            selectedRunId={selectedRunId}
          />
          <SnapshotDetailPane
            snapshots={orderedSnapshots}
            historyWindowComplete={total <= orderedSnapshots.length}
            selectedRunId={selectedRunId}
            detail={detail}
            detailError={detailError}
          />
        </div>
      )}
    </section>
  );
}

function SnapshotTimeline({
  snapshots,
  total,
  selectedRunId
}: {
  snapshots: AnalysisRunSnapshot[];
  total: number;
  selectedRunId: string | null;
}) {
  const loadedLabel = total > snapshots.length
    ? `${snapshots.length} / ${total} loaded`
    : `${snapshots.length} loaded`;
  return (
    <nav className="snapshotTimeline" aria-label="快照时间线">
      <div className="snapshotTimeline__label">
        <span>Timeline</span>
        <strong>{loadedLabel}</strong>
      </div>
      <ol>
        {snapshots.map((run, index) => {
          const selected = run.analysis_run_id === selectedRunId;
          return (
            <li key={run.analysis_run_id} className={selected ? "is-selected" : undefined}>
              <a
                href={`/?snapshot=${encodeURIComponent(run.analysis_run_id)}#snapshot-history`}
                aria-current={selected ? "true" : undefined}
              >
                <span className="snapshotTimeline__index">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="snapshotTimeline__content">
                  <span>
                    <b className={`platformTag platformTag--${run.platform}`}>
                      {run.platform}
                    </b>
                    <time dateTime={run.created_at}>{formatDate(run.created_at)}</time>
                  </span>
                  <strong>{run.analysis_unit_count} units · {run.artifact_count} artifacts</strong>
                  <code>{shortDigest(run.output_digest)}</code>
                </span>
                <span className="snapshotTimeline__action">
                  {selected ? "已打开" : "查看账本"}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function SnapshotDetailPane({
  snapshots,
  historyWindowComplete,
  selectedRunId,
  detail,
  detailError
}: {
  snapshots: AnalysisRunSnapshot[];
  historyWindowComplete: boolean;
  selectedRunId: string | null;
  detail: AnalysisSnapshotDetail | null;
  detailError: string | null;
}) {
  if (detailError) {
    return (
      <LedgerNotice
        tone="error"
        title="快照详情加载失败"
        detail={detailError}
      />
    );
  }
  if (!selectedRunId) {
    return (
      <div className="snapshotDetail snapshotDetail--prompt">
        <span className="snapshotDetail__glyph" aria-hidden="true">↳</span>
        <h3>选择一个快照查看 lineage 与差异</h3>
        <p>详情按需读取，首屏不会先拉列表再串行请求 artifact。</p>
      </div>
    );
  }
  if (!detail || detail.run.analysis_run_id !== selectedRunId) {
    return (
      <LedgerNotice
        tone="empty"
        title="快照详情不可用"
        detail="所选历史记录没有返回可验证的 run/artifact 契约。"
      />
    );
  }

  const previousRun = previousComparableRun(snapshots, detail.run);
  const predecessorNotLoaded = previousRun === null && !historyWindowComplete;
  const counts = artifactCounts(detail.artifacts);
  return (
    <article className="snapshotDetail">
      <SnapshotRunHeader
        run={detail.run}
        previousRun={previousRun}
        predecessorNotLoaded={predecessorNotLoaded}
      />
      <SnapshotDiff
        run={detail.run}
        previousRun={previousRun}
        predecessorNotLoaded={predecessorNotLoaded}
      />
      <SnapshotLineage run={detail.run} counts={counts} />
      <ArtifactIndex artifacts={detail.artifacts} counts={counts} />
    </article>
  );
}

function SnapshotRunHeader({
  run,
  previousRun,
  predecessorNotLoaded
}: {
  run: AnalysisRunSnapshot;
  previousRun: AnalysisRunSnapshot | null;
  predecessorNotLoaded: boolean;
}) {
  const outputChanged = previousRun ? previousRun.output_digest !== run.output_digest : null;
  return (
    <header className="snapshotDetail__header">
      <div>
        <span className={`platformTag platformTag--${run.platform}`}>{run.platform}</span>
        <p>{run.language} · {run.snapshot_schema_version}</p>
        <h3>{formatDate(run.created_at)}</h3>
      </div>
      <div className="snapshotDigestState">
        <span>compare</span>
        <strong>
          {predecessorNotLoaded
            ? "比较窗口不完整"
            : outputChanged === null
            ? "首个可比较快照"
            : outputChanged
              ? "输出已变化"
              : "输出未变化"}
        </strong>
      </div>
    </header>
  );
}

function SnapshotDiff({
  run,
  previousRun,
  predecessorNotLoaded
}: {
  run: AnalysisRunSnapshot;
  previousRun: AnalysisRunSnapshot | null;
  predecessorNotLoaded: boolean;
}) {
  const comparison = previousRun
    ? [
        ["分析单元", formatDelta(run.analysis_unit_count - previousRun.analysis_unit_count)],
        ["Artifacts", formatDelta(run.artifact_count - previousRun.artifact_count)],
        ["Collection runs", formatDelta(run.collection_run_ids.length - previousRun.collection_run_ids.length)],
        ["Input digest", run.input_digest === previousRun.input_digest ? "same" : "changed"]
      ]
    : predecessorNotLoaded
      ? [
          ["分析单元", "unknown"],
          ["Artifacts", "unknown"],
          ["Collection runs", "unknown"],
          ["Input digest", "unknown"]
        ]
      : [
        ["分析单元", String(run.analysis_unit_count)],
        ["Artifacts", String(run.artifact_count)],
        ["Collection runs", String(run.collection_run_ids.length)],
        ["Input digest", "baseline"]
      ];

  return (
    <section className="snapshotDiff" aria-label="同平台快照比较">
      <div className="snapshotSubheading">
        <span>Same-platform diff</span>
        <strong>
          {previousRun
            ? formatDate(previousRun.created_at)
            : predecessorNotLoaded
              ? "predecessor unknown beyond loaded window"
              : "no prior run"}
        </strong>
      </div>
      <dl>
        {comparison.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function SnapshotLineage({
  run,
  counts
}: {
  run: AnalysisRunSnapshot;
  counts: Record<AnalysisArtifactType, number>;
}) {
  const templateVersion = stringMetadata(
    run.template_contract.brief_template_version,
    "template version unknown"
  );
  const artifactTotal = ARTIFACT_TYPES.reduce((total, type) => total + counts[type], 0);
  return (
    <section className="snapshotLineage" aria-label="快照 lineage">
      <div className="snapshotSubheading">
        <span>Immutable lineage</span>
        <strong>{run.collection_run_ids.length} 个 collection run</strong>
      </div>
      <ol>
        <LineageStep index="01" label="collection runs" value={`${run.collection_run_ids.length} fixed inputs`} />
        <LineageStep index="02" label="input digest" value={shortDigest(run.input_digest)} mono />
        <LineageStep index="03" label="template contract" value={`${templateVersion} · ${run.generation_method}`} />
        <LineageStep index="04" label="immutable artifacts" value={`${artifactTotal} indexed rows`} />
        <LineageStep index="05" label="output digest" value={shortDigest(run.output_digest)} mono />
      </ol>
    </section>
  );
}

function LineageStep({
  index,
  label,
  value,
  mono = false
}: {
  index: string;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <li>
      <span>{index}</span>
      <div>
        <small>{label}</small>
        <strong className={mono ? "is-mono" : undefined}>{value}</strong>
      </div>
    </li>
  );
}

function ArtifactIndex({
  artifacts,
  counts
}: {
  artifacts: AnalysisArtifactSnapshot[];
  counts: Record<AnalysisArtifactType, number>;
}) {
  return (
    <section className="artifactIndex" aria-label="Artifact 索引">
      <div className="snapshotSubheading">
        <span>Artifact index</span>
        <strong>metadata only · payload hidden</strong>
      </div>
      <div className="artifactDistribution">
        {ARTIFACT_TYPES.map((type) => (
          <div key={type}>
            <span>{ARTIFACT_LABELS[type]}</span>
            <strong>{counts[type]}</strong>
          </div>
        ))}
      </div>
      <ol className="artifactRows">
        {artifacts.slice(0, 12).map((artifact) => (
          <li key={artifact.analysis_snapshot_id}>
            <span className={`artifactType artifactType--${artifact.artifact_type}`}>
              {ARTIFACT_LABELS[artifact.artifact_type]}
            </span>
            <div>
              <strong>{artifact.artifact_key}</strong>
              <small>{artifact.schema_version}</small>
            </div>
            <code>{shortDigest(artifact.payload_digest)}</code>
          </li>
        ))}
      </ol>
      {artifacts.length > 12 ? (
        <p className="artifactIndex__limit">
          当前仅展示 12 / {artifacts.length} 条 metadata；完整 payload 未注入页面。
        </p>
      ) : null}
    </section>
  );
}

function LedgerNotice({
  tone,
  title,
  detail
}: {
  tone: "empty" | "error";
  title: string;
  detail: string;
}) {
  return (
    <div className={`snapshotNotice snapshotNotice--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function previousComparableRun(
  snapshots: AnalysisRunSnapshot[],
  selected: AnalysisRunSnapshot
): AnalysisRunSnapshot | null {
  const selectedTime = Date.parse(selected.created_at);
  return snapshots
    .filter(
      (candidate) =>
        candidate.platform === selected.platform &&
        candidate.analysis_run_id !== selected.analysis_run_id &&
        Date.parse(candidate.created_at) < selectedTime
    )
    .sort(compareNewestFirst)[0] ?? null;
}

function artifactCounts(
  artifacts: AnalysisArtifactSnapshot[]
): Record<AnalysisArtifactType, number> {
  const counts: Record<AnalysisArtifactType, number> = {
    relation_edge: 0,
    enriched_voc_signal: 0,
    strategy_note: 0,
    insight_brief: 0
  };
  for (const artifact of artifacts) {
    counts[artifact.artifact_type] += 1;
  }
  return counts;
}

function compareNewestFirst(left: AnalysisRunSnapshot, right: AnalysisRunSnapshot): number {
  return Date.parse(right.created_at) - Date.parse(left.created_at) ||
    right.analysis_run_id.localeCompare(left.analysis_run_id);
}

function formatDelta(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}

function shortDigest(value: string): string {
  return value.length > 28 ? `${value.slice(0, 19)}…${value.slice(-6)}` : value;
}

function stringMetadata(value: JsonValue | undefined, fallback: string): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
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
    minute: "2-digit",
    hour12: false
  }).format(date);
}
