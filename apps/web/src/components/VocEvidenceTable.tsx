import type { VocUnit } from "../lib/api";
import { QualityBadge } from "./QualityBadge";

type VocEvidenceTableProps = {
  units: VocUnit[];
};

export function VocEvidenceTable({ units }: VocEvidenceTableProps) {
  if (units.length === 0) {
    return (
      <section className="emptyState" aria-label="空证据状态">
        <p className="emptyState__title">暂无 VOC 证据</p>
        <p className="emptyState__body">当前 API 没有返回可展示的 CanonicalVocUnit。</p>
      </section>
    );
  }

  return (
    <div className="tableShell">
      <table className="evidenceTable">
        <thead>
          <tr>
            <th scope="col">平台</th>
            <th scope="col">对象 / 来源</th>
            <th scope="col">证据正文</th>
            <th scope="col">质量</th>
            <th scope="col">上下文</th>
            <th scope="col">Flags</th>
          </tr>
        </thead>
        <tbody>
          {units.map((unit) => (
            <tr key={`${unit.platform}:${unit.source_object_id}`}>
              <td>
                <span className={`platformTag platformTag--${unit.platform}`}>
                  {formatPlatform(unit.platform)}
                </span>
              </td>
              <td>
                <div className="sourceCell">
                  <p className="sourceCell__title">{unit.title ?? unit.source_object_id}</p>
                  <p className="sourceCell__meta">{unit.source_kind}</p>
                  <a href={unit.source_url} className="sourceCell__link">
                    {unit.source_object_id}
                  </a>
                </div>
              </td>
              <td>
                <div className="evidenceText">
                  <p>{unit.body}</p>
                  <time dateTime={unit.captured_at}>{formatDate(unit.captured_at)}</time>
                </div>
              </td>
              <td>
                <QualityBadge
                  confidence={unit.coverage_confidence}
                  flags={unit.quality_flags}
                />
              </td>
              <td>
                <ContextSummary unit={unit} />
              </td>
              <td>
                <FlagList flags={unit.quality_flags} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ContextSummary({ unit }: { unit: VocUnit }) {
  if (unit.platform === "amazon") {
    return (
      <dl className="contextList">
        <div>
          <dt>ASIN</dt>
          <dd>{unit.asin ?? "unknown"}</dd>
        </div>
        <div>
          <dt>Market</dt>
          <dd>{unit.marketplace ?? "unknown"}</dd>
        </div>
      </dl>
    );
  }

  return (
    <dl className="contextList">
      <div>
        <dt>Thread</dt>
        <dd>{unit.thread_id ?? "unknown"}</dd>
      </div>
      <div>
        <dt>Depth</dt>
        <dd>{unit.depth ?? 0}</dd>
      </div>
      <div>
        <dt>Role</dt>
        <dd>{unit.reply_role ?? "unknown"}</dd>
      </div>
    </dl>
  );
}

function FlagList({ flags }: { flags: string[] }) {
  if (flags.length === 0) {
    return <span className="flagList__empty">无</span>;
  }

  return (
    <ul className="flagList">
      {flags.map((flag) => (
        <li key={flag}>{flag}</li>
      ))}
    </ul>
  );
}

function formatPlatform(platform: VocUnit["platform"]): string {
  return platform === "amazon" ? "Amazon" : "Reddit";
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
