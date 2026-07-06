"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import type { JsonValue, VocPlatform, VocUnit } from "../lib/api";
import { QualityBadge } from "./QualityBadge";

type VocEvidenceTableProps = {
  units: VocUnit[];
  lowConfidenceThreshold: number;
};

type PlatformFilter = "all" | VocPlatform;
type QualityFilter = "all" | "review" | "clear";
type SortKey = "captured_desc" | "captured_asc" | "confidence_asc" | "confidence_desc";
type ReviewGuidanceTone = "clear" | "review";
type ReviewFilterChip = {
  label: string;
  value: string;
  active: boolean;
};

const PAGE_SIZE = 50;

export function VocEvidenceTable({ units, lowConfidenceThreshold }: VocEvidenceTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedUnit, setSelectedUnit] = useState<VocUnit | null>(null);

  const platform = readEnum(searchParams.get("platform"), ["all", "amazon", "reddit", "instagram"], "all");
  const quality = readEnum(searchParams.get("quality"), ["all", "review", "clear"], "all");
  const sort = readEnum(
    searchParams.get("sort"),
    ["captured_desc", "captured_asc", "confidence_asc", "confidence_desc"],
    "captured_desc"
  );
  const query = searchParams.get("q")?.trim() ?? "";
  const page = readPage(searchParams.get("page"));

  const filteredUnits = useMemo(
    () => sortUnits(filterUnits(units, platform, quality, query), sort),
    [platform, quality, query, sort, units]
  );
  const pageCount = Math.max(1, Math.ceil(filteredUnits.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const visibleUnits = filteredUnits.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const filterChips = activeFilterChips({ platform, quality, query, sort });
  const hasActiveFilters = filterChips.some((chip) => chip.active);

  function updateFilter(nextValues: Partial<Record<"platform" | "quality" | "sort" | "q" | "page", string>>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(nextValues)) {
      if (!value || isDefaultParam(key, value)) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    }
    if (!("page" in nextValues)) {
      params.delete("page");
    }
    const queryString = params.toString();
    router.replace(queryString ? `/?${queryString}` : "/", { scroll: false });
  }

  if (units.length === 0) {
    return (
      <section className="emptyState" aria-label="空证据状态">
        <p className="emptyState__title">暂无 VOC 证据</p>
        <p className="emptyState__body">当前 API 没有返回可展示的 CanonicalVocUnit。</p>
      </section>
    );
  }

  return (
    <div className="reviewWorkbench">
      <section className="reviewToolbar" aria-label="VOC 复核筛选">
        <div className="segmentedControl" aria-label="平台筛选">
          {(["all", "amazon", "reddit", "instagram"] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={platform === value}
              onClick={() => updateFilter({ platform: value })}
            >
              {platformLabel(value)}
            </button>
          ))}
        </div>

        <label className="reviewSearch">
          <span>搜索</span>
          <input
            name="voc-search"
            type="search"
            inputMode="search"
            autoComplete="off"
            spellCheck={false}
            placeholder="ASIN、Thread、正文或 flag…"
            value={query}
            onChange={(event) => updateFilter({ q: event.currentTarget.value })}
          />
        </label>

        <label className="reviewSelect">
          <span>质量</span>
          <select
            name="quality-filter"
            autoComplete="off"
            value={quality}
            onChange={(event) => updateFilter({ quality: event.currentTarget.value })}
          >
            <option value="all">全部质量</option>
            <option value="review">需复核</option>
            <option value="clear">已校验</option>
          </select>
        </label>

        <label className="reviewSelect">
          <span>排序</span>
          <select
            name="sort"
            autoComplete="off"
            value={sort}
            onChange={(event) => updateFilter({ sort: event.currentTarget.value })}
          >
            <option value="captured_desc">最新采集</option>
            <option value="captured_asc">最早采集</option>
            <option value="confidence_asc">低覆盖优先</option>
            <option value="confidence_desc">高覆盖优先</option>
          </select>
        </label>
      </section>

      <div className="reviewResultBar" aria-live="polite">
        <div className="reviewResultBar__metrics" aria-label="VOC 复核结果摘要">
          <ResultMetric label="当前页" value={visibleUnits.length} />
          <ResultMetric label="筛选结果" value={filteredUnits.length} />
          <ResultMetric label="数据总量" value={units.length} />
        </div>
        <div className="reviewFilterSummary" aria-label="当前筛选条件">
          {filterChips.map((chip) => (
            <span
              key={`${chip.label}:${chip.value}`}
              className={`reviewFilterChip${chip.active ? " reviewFilterChip--active" : ""}`}
            >
              <strong>{chip.label}</strong>
              <span>{chip.value}</span>
            </span>
          ))}
        </div>
        <button
          type="button"
          disabled={!hasActiveFilters}
          onClick={() => updateFilter({ platform: "", quality: "", sort: "", q: "", page: "" })}
        >
          清除筛选
        </button>
      </div>

      {visibleUnits.length === 0 ? (
        <section className="emptyState" aria-label="筛选后空证据状态">
          <p className="emptyState__title">没有匹配的 VOC 证据</p>
          <p className="emptyState__body">调整平台、质量或搜索条件后继续复核。</p>
        </section>
      ) : (
        <div className="tableShell">
          <table className="evidenceTable">
            <caption className="visuallyHidden">
              Canonical VOC 证据复核表，包含平台、来源对象、证据正文、质量、上下文、质量标记和详情操作。
            </caption>
            <thead>
              <tr>
                <th scope="col">平台</th>
                <th scope="col">对象 / 来源</th>
                <th scope="col">证据正文</th>
                <th scope="col">质量</th>
                <th scope="col">上下文</th>
                <th scope="col">Flags</th>
                <th scope="col">操作</th>
              </tr>
            </thead>
            <tbody>
              {visibleUnits.map((unit) => (
                <tr key={unitKey(unit)}>
                  <td>
                    <span className={`platformTag platformTag--${unit.platform}`}>
                      {formatPlatform(unit.platform)}
                    </span>
                  </td>
                  <td>
                    <div className="sourceCell">
                      <p className="sourceCell__title">{unit.title ?? unit.source_object_id}</p>
                      <p className="sourceCell__meta">{unit.source_kind}</p>
                      <a
                        href={unit.source_url}
                        className="sourceCell__link"
                        target="_blank"
                        rel="noreferrer"
                      >
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
                    <QualityBadge confidence={unit.coverage_confidence} flags={unit.quality_flags} />
                  </td>
                  <td>
                    <ContextSummary unit={unit} />
                  </td>
                  <td>
                    <FlagList flags={unit.quality_flags} />
                  </td>
                  <td>
                    <div className="rowActionStack">
                      <button
                        type="button"
                        className="rowActionButton"
                        aria-label={`${reviewActionLabel(unit, lowConfidenceThreshold)} ${unit.source_object_id}`}
                        onClick={() => setSelectedUnit(unit)}
                      >
                        {reviewActionLabel(unit, lowConfidenceThreshold)}
                      </button>
                      <a
                        href={unit.source_url}
                        className="rowSourceAction"
                        target="_blank"
                        rel="noreferrer"
                      >
                        来源
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <nav className="paginationBar" aria-label="VOC 证据分页">
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => updateFilter({ page: String(currentPage - 1) })}
        >
          上一页
        </button>
        <span>
          第 {currentPage} / {pageCount} 页
        </span>
        <button
          type="button"
          disabled={currentPage >= pageCount}
          onClick={() => updateFilter({ page: String(currentPage + 1) })}
        >
          下一页
        </button>
      </nav>

      {selectedUnit ? (
        <VocDetailDrawer
          unit={selectedUnit}
          lowConfidenceThreshold={lowConfidenceThreshold}
          onClose={() => setSelectedUnit(null)}
        />
      ) : null}
    </div>
  );
}

function ResultMetric({ label, value }: { label: string; value: number }) {
  return (
    <span className="reviewResultMetric">
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  );
}

function VocDetailDrawer({
  unit,
  lowConfidenceThreshold,
  onClose
}: {
  unit: VocUnit;
  lowConfidenceThreshold: number;
  onClose: () => void;
}) {
  const drawerRef = useRef<HTMLElement | null>(null);
  const guidance = reviewGuidanceForUnit(unit, lowConfidenceThreshold);

  useEffect(() => {
    drawerRef.current?.focus();
  }, []);

  return (
    <aside
      ref={drawerRef}
      className="vocDetailDrawer"
      role="dialog"
      aria-modal="true"
      aria-label="VOC 证据详情"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          onClose();
        }
      }}
    >
      <div className="vocDetailDrawer__header">
        <div>
          <span className={`platformTag platformTag--${unit.platform}`}>{formatPlatform(unit.platform)}</span>
          <h3>{unit.title ?? unit.source_object_id}</h3>
        </div>
        <button type="button" onClick={onClose} aria-label="关闭 VOC 证据详情">
          关闭
        </button>
      </div>
      <div className="vocDetailDrawer__body">
        <section aria-label="证据正文">
          <h4>证据正文</h4>
          <p>{unit.body}</p>
        </section>
        <dl>
          <DetailRow label="Source Object" value={unit.source_object_id} />
          <DetailRow label="Source Kind" value={unit.source_kind} />
          <DetailRow label="Captured" value={formatDate(unit.captured_at)} />
          <DetailRow label="Coverage" value={`${Math.round(unit.coverage_confidence * 100)}%`} />
          <DetailRow label="Run" value={unit.collection_run_id ?? "-"} />
          <DetailRow label="Author" value={unit.author_display ?? "-"} />
          <DetailRow label="ASIN" value={unit.asin ?? "-"} />
          <DetailRow label="Thread" value={unit.thread_id ?? "-"} />
        </dl>
        <section aria-label="质量标记">
          <h4>质量标记</h4>
          <FlagList flags={unit.quality_flags} />
        </section>
        <section
          className={`reviewGuidance reviewGuidance--${guidance.tone}`}
          aria-label="复核建议"
        >
          <h4>{guidance.title}</h4>
          <p>{guidance.detail}</p>
          <ul>
            {guidance.actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </section>
        <a href={unit.source_url} target="_blank" rel="noreferrer" className="drawerSourceLink">
          打开原始来源
        </a>
      </div>
    </aside>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
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

  if (unit.platform === "instagram") {
    return (
      <dl className="contextList">
        <div>
          <dt>Media</dt>
          <dd>{extensionString(unit.platform_extension.media_id) ?? "unknown"}</dd>
        </div>
        <div>
          <dt>Parent</dt>
          <dd>{unit.parent_id ?? "root"}</dd>
        </div>
        <div>
          <dt>Role</dt>
          <dd>{unit.reply_role ?? "unknown"}</dd>
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

function reviewActionLabel(unit: VocUnit, lowConfidenceThreshold: number): string {
  return requiresReview(unit, lowConfidenceThreshold) ? "复核" : "详情";
}

function requiresReview(unit: VocUnit, lowConfidenceThreshold: number): boolean {
  return unit.quality_flags.length > 0 || unit.coverage_confidence < lowConfidenceThreshold;
}

function reviewGuidanceForUnit(
  unit: VocUnit,
  lowConfidenceThreshold: number
): {
  tone: ReviewGuidanceTone;
  title: string;
  detail: string;
  actions: string[];
} {
  const confidencePercent = Math.round(unit.coverage_confidence * 100);
  const lowConfidence = unit.coverage_confidence < lowConfidenceThreshold;

  if (lowConfidence && unit.quality_flags.length > 0) {
    return {
      tone: "review",
      title: "优先复核",
      detail: `覆盖 ${confidencePercent}%，且包含 ${unit.quality_flags.length} 个 quality flag。先确认原始来源，再决定是否补采。`,
      actions: ["核对原始来源", "检查 quality flags", "必要时创建补采任务"]
    };
  }

  if (unit.quality_flags.length > 0) {
    return {
      tone: "review",
      title: "质量标记复核",
      detail: `该证据包含 ${unit.quality_flags.length} 个 quality flag，进入策略分析前需要人工确认。`,
      actions: ["核对正文语义", "确认平台上下文", "保留复核备注"]
    };
  }

  if (lowConfidence) {
    return {
      tone: "review",
      title: "低覆盖复核",
      detail: `覆盖 ${confidencePercent}%，低于当前阈值 ${Math.round(lowConfidenceThreshold * 100)}%。建议补充同对象更多评论或帖子。`,
      actions: ["复查采集范围", "确认是否触发 page budget", "必要时补采"]
    };
  }

  return {
    tone: "clear",
    title: "可进入分析",
    detail: `覆盖 ${confidencePercent}%，当前没有 quality flag，可作为策略 notes 的候选证据。`,
    actions: ["保留来源链接", "进入主题归类", "回溯到 collection run"]
  };
}

function filterUnits(
  units: VocUnit[],
  platform: PlatformFilter,
  quality: QualityFilter,
  query: string
): VocUnit[] {
  const normalizedQuery = query.trim().toLowerCase();
  return units.filter((unit) => {
    if (platform !== "all" && unit.platform !== platform) {
      return false;
    }
    if (quality === "review" && unit.quality_flags.length === 0) {
      return false;
    }
    if (quality === "clear" && unit.quality_flags.length > 0) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }
    return searchableText(unit).includes(normalizedQuery);
  });
}

function sortUnits(units: VocUnit[], sort: SortKey): VocUnit[] {
  return [...units].sort((left, right) => {
    if (sort === "confidence_asc") {
      return left.coverage_confidence - right.coverage_confidence;
    }
    if (sort === "confidence_desc") {
      return right.coverage_confidence - left.coverage_confidence;
    }

    const delta = dateMs(left.captured_at) - dateMs(right.captured_at);
    return sort === "captured_asc" ? delta : -delta;
  });
}

function searchableText(unit: VocUnit): string {
  return [
    unit.platform,
    unit.source_object_id,
    unit.source_kind,
    unit.title,
    unit.body,
    unit.asin,
    unit.marketplace,
    unit.thread_id,
    unit.parent_id,
    unit.reply_role,
    unit.author_display,
    unit.product_title,
    ...unit.quality_flags
  ]
    .filter((value): value is string => typeof value === "string" && value.length > 0)
    .join(" ")
    .toLowerCase();
}

function readEnum<const T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

function readPage(value: string | null): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

function isDefaultParam(key: string, value: string): boolean {
  return (
    (key === "platform" && value === "all") ||
    (key === "quality" && value === "all") ||
    (key === "sort" && value === "captured_desc") ||
    (key === "page" && value === "1")
  );
}

function activeFilterChips({
  platform,
  quality,
  query,
  sort
}: {
  platform: PlatformFilter;
  quality: QualityFilter;
  query: string;
  sort: SortKey;
}): ReviewFilterChip[] {
  const chips: ReviewFilterChip[] = [
    {
      label: "平台",
      value: platform === "all" ? "全部" : platformLabel(platform),
      active: platform !== "all"
    },
    {
      label: "质量",
      value: qualityLabel(quality),
      active: quality !== "all"
    },
    {
      label: "排序",
      value: sortLabel(sort),
      active: sort !== "captured_desc"
    }
  ];

  if (query.length > 0) {
    chips.push({
      label: "搜索",
      value: query,
      active: true
    });
  }

  return chips;
}

function platformLabel(platform: PlatformFilter): string {
  if (platform === "amazon") {
    return "Amazon";
  }
  if (platform === "reddit") {
    return "Reddit";
  }
  if (platform === "instagram") {
    return "Instagram";
  }
  return "全部";
}

function qualityLabel(quality: QualityFilter): string {
  if (quality === "review") {
    return "需复核";
  }
  if (quality === "clear") {
    return "已校验";
  }
  return "全部";
}

function sortLabel(sort: SortKey): string {
  if (sort === "captured_asc") {
    return "最早采集";
  }
  if (sort === "confidence_asc") {
    return "低覆盖优先";
  }
  if (sort === "confidence_desc") {
    return "高覆盖优先";
  }
  return "最新采集";
}

function formatPlatform(platform: VocUnit["platform"]): string {
  if (platform === "amazon") {
    return "Amazon";
  }
  if (platform === "reddit") {
    return "Reddit";
  }
  return "Instagram";
}

function dateMs(value: string): number {
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function unitKey(unit: VocUnit): string {
  return `${unit.platform}:${unit.source_object_id}:${unit.captured_at}`;
}

function extensionString(value: JsonValue | undefined): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
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
