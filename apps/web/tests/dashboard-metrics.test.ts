import { describe, expect, it } from "vitest";

import {
  getIntegrityIssueCount,
  getIntegrityMetricDisplay
} from "../src/lib/dashboard-metrics";

describe("dashboard metrics", () => {
  it("marks asset integrity as unknown when the summary is unavailable", () => {
    const issueCount = getIntegrityIssueCount(null);

    expect(issueCount).toBeNull();
    expect(getIntegrityMetricDisplay(issueCount)).toEqual({
      value: "unknown",
      tone: "warning"
    });
  });

  it("keeps clear and risk states when the summary is available", () => {
    expect(getIntegrityMetricDisplay(0)).toEqual({ value: 0, tone: "clear" });
    expect(getIntegrityMetricDisplay(3)).toEqual({ value: 3, tone: "risk" });

    const issueCount = getIntegrityIssueCount({
      runs_with_count_mismatch: 1,
      orphan_raw_count: 2,
      orphan_voc_count: 3
    });

    expect(issueCount).toBe(6);
    expect(getIntegrityMetricDisplay(issueCount)).toEqual({ value: 6, tone: "risk" });
  });
});
