import type { DetectedPage } from "../../lib/page-detect";
import type { CaptureSummary } from "../../types/messages";

export type CommandBarStatus = "ready" | "capturing" | "previewed" | "uploading" | "uploaded" | "error";

export type PipelineStep = {
  label: string;
  detail: string;
  state: "done" | "active" | "waiting" | "error";
};

export function formatConfidencePercent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }

  return `${Math.round(value * 100)}%`;
}

export function platformName(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return "Amazon";
  }
  if (detectedPage.platform === "reddit") {
    return "Reddit";
  }
  return "Unsupported";
}

export function detectedObjectTitle(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return detectedPage.asin;
  }
  if (detectedPage.platform === "reddit") {
    return detectedPage.threadId;
  }
  return "Unknown";
}

export function detectedObjectSubtitle(detectedPage: DetectedPage): string {
  if (detectedPage.platform === "amazon") {
    return detectedPage.entryPageKind === "amazon_product_detail" ? "Product Detail" : "Reviews Page";
  }
  if (detectedPage.platform === "reddit") {
    return "Thread";
  }
  return "Unsupported";
}

export function buildPipelineSteps(status: CommandBarStatus, summary: CaptureSummary | null): PipelineStep[] {
  const hasCapture = Boolean(summary);
  const hasRawItems = Boolean(summary && summary.raw_item_count > 0);
  const failed = status === "error";
  const uploaded = status === "uploaded";
  const uploading = status === "uploading";
  const capturing = status === "capturing";

  return [
    {
      label: "Raw Capture",
      detail: rawCaptureDetail(status, summary),
      state: failed || (hasCapture && !hasRawItems) ? "error" : hasRawItems || uploaded || uploading ? "done" : capturing ? "active" : "waiting"
    },
    {
      label: "Schema Mapping",
      detail: hasRawItems ? "映射就绪" : hasCapture ? "无 raw 可映射" : "等待 raw",
      state: failed ? "error" : hasRawItems || uploaded || uploading ? "done" : "waiting"
    },
    {
      label: "Canonical VOC",
      detail: uploaded ? "已生成" : hasRawItems ? "回传后生成" : hasCapture ? "等待有效 raw" : "等待",
      state: failed ? "error" : uploaded ? "done" : hasRawItems || uploading ? "active" : "waiting"
    },
    {
      label: "AI Insight",
      detail: uploaded ? "可分析" : "等待",
      state: failed ? "error" : uploaded ? "active" : "waiting"
    },
    {
      label: "Strategy Output",
      detail: "等待",
      state: failed ? "error" : "waiting"
    }
  ];
}

function rawCaptureDetail(status: CommandBarStatus, summary: CaptureSummary | null): string {
  if (status === "capturing") {
    return "采集中";
  }
  if (!summary) {
    return "待采集";
  }

  return `${summary.raw_item_count} raw`;
}

export function captureSummaryStatusText(summary: CaptureSummary): string {
  const stopReason = summary.stop_reason ?? "completed";

  if (summary.platform === "reddit") {
    if (stopReason === "reddit_json_unavailable_dom_empty") {
      return "Reddit JSON 不可达，DOM 无有效帖子";
    }
    if (stopReason === "reddit_json_unavailable_dom_fallback") {
      return "Reddit JSON 不可达，已用 DOM 降级";
    }
    if (stopReason === "missing_thread_dom") {
      return "DOM 无有效帖子";
    }
    if (stopReason === "more_nodes_not_expanded") {
      return "部分评论未展开";
    }
  }

  return `Stop ${stopReason}`;
}
