import type { DataAssetSummary } from "./api";

type IntegritySummary = Pick<
  DataAssetSummary,
  "runs_with_count_mismatch" | "orphan_raw_count" | "orphan_voc_count"
>;

export type IntegrityMetricDisplay = {
  value: number | "unknown";
  tone: "warning" | "risk" | "clear";
};

export function getIntegrityIssueCount(
  summary: IntegritySummary | null
): number | null {
  return summary
    ? summary.runs_with_count_mismatch +
        summary.orphan_raw_count +
        summary.orphan_voc_count
    : null;
}

export function getIntegrityMetricDisplay(
  issueCount: number | null
): IntegrityMetricDisplay {
  if (issueCount === null) {
    return { value: "unknown", tone: "warning" };
  }
  return {
    value: issueCount,
    tone: issueCount > 0 ? "risk" : "clear"
  };
}
