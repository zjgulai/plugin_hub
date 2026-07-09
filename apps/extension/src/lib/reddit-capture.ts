import type { CaptureCurrentPageInput } from "./capture-types";
import { detectRedditThreadPageUrl } from "./page-detect";
import { parseRedditThreadDom, parseRedditThreadJson } from "./reddit-parser";
import type { CollectionRunPayload, JsonObject } from "../types/contracts";
import type { CaptureCurrentPageSuccess } from "../types/messages";

export async function captureRedditCurrentPage(
  input: CaptureCurrentPageInput
): Promise<CaptureCurrentPageSuccess> {
  const detectedPage = detectRedditThreadPageUrl(input.url);

  if (detectedPage.platform !== "reddit") {
    throw new Error("unsupported_page");
  }

  return captureRedditThread({
    ...input,
    threadId: detectedPage.threadId
  });
}

async function captureRedditThread(
  input: CaptureCurrentPageInput & { threadId: string }
): Promise<CaptureCurrentPageSuccess> {
  const capturedAt = parseCapturedAt(input.capturedAt);
  const jsonUrl = buildRedditJsonUrl(input.url);
  let redditPayload: unknown;

  try {
    redditPayload = await (input.fetchJson ?? defaultFetchJson)(jsonUrl);
  } catch (error) {
    return captureRedditThreadDomFallback({
      ...input,
      capturedAt,
      jsonUrl,
      jsonError: errorMessage(error)
    });
  }

  const result = parseRedditThreadJson(redditPayload, input.url, { capturedAt });
  if (result.rawItems.length === 0) {
    return captureRedditThreadDomFallback({
      ...input,
      capturedAt,
      jsonUrl,
      jsonError: result.stopReason ?? "reddit_json_empty"
    });
  }

  const stopReason = result.stopReason ?? (result.moreNodeCount > 0 ? "more_nodes_not_expanded" : null);
  const coverageConfidence = redditCoverageConfidence(result.rawItems.length, result.moreNodeCount, stopReason);
  const coverageScope: JsonObject = {
    collector_app: "reddit_extension",
    page_kind: "reddit_thread",
    thread_id: input.threadId,
    json_url: jsonUrl,
    more_node_count: result.moreNodeCount,
    raw_item_count: result.rawItems.length
  };
  const payload: CollectionRunPayload = {
    run: {
      platform: "reddit",
      source_url: input.url,
      capture_method: "extension_reddit_json",
      coverage_scope: coverageScope,
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    },
    raw_items: result.rawItems
  };

  return {
    payload,
    summary: {
      platform: "reddit",
      page_kind: "reddit_thread",
      raw_item_count: result.rawItems.length,
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    }
  };
}

function captureRedditThreadDomFallback(
  input: CaptureCurrentPageInput & {
    threadId: string;
    capturedAt: string;
    jsonUrl: string;
    jsonError: string;
  }
): CaptureCurrentPageSuccess {
  const result = parseRedditThreadDom(
    input.documentRoot ?? resolveDocumentRoot(),
    input.url,
    input.threadId,
    { capturedAt: input.capturedAt }
  );
  const stopReason =
    result.rawItems.length > 0
      ? "reddit_json_unavailable_dom_fallback"
      : "reddit_json_unavailable_dom_empty";
  const coverageConfidence = redditDomFallbackCoverageConfidence(result.rawItems.length);
  const coverageScope: JsonObject = {
    collector_app: "reddit_extension",
    page_kind: "reddit_thread",
    thread_id: input.threadId,
    json_url: input.jsonUrl,
    json_error: input.jsonError,
    fallback_parser: "reddit_dom",
    dom_stop_reason: result.stopReason,
    comment_node_count: result.commentNodeCount,
    raw_item_count: result.rawItems.length
  };
  const payload: CollectionRunPayload = {
    run: {
      platform: "reddit",
      source_url: input.url,
      capture_method: "extension_reddit_dom_fallback",
      coverage_scope: coverageScope,
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    },
    raw_items: result.rawItems
  };

  return {
    payload,
    summary: {
      platform: "reddit",
      page_kind: "reddit_thread",
      raw_item_count: result.rawItems.length,
      stop_reason: stopReason,
      coverage_confidence: coverageConfidence
    }
  };
}

export function buildRedditJsonUrl(sourceUrl: string): string {
  const url = new URL(sourceUrl);
  url.hash = "";
  if (!url.pathname.endsWith(".json")) {
    url.pathname = `${url.pathname.replace(/\/?$/, "/")}.json`;
  }
  url.searchParams.set("raw_json", "1");
  return url.toString();
}

function parseCapturedAt(value: string | undefined): string {
  const parsedDate = value ? new Date(value) : new Date();
  return Number.isNaN(parsedDate.getTime()) ? new Date().toISOString() : parsedDate.toISOString();
}

function resolveDocumentRoot(): ParentNode {
  if (typeof document === "undefined") {
    throw new Error("document_required");
  }
  return document;
}

async function defaultFetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`reddit_json_fetch_failed:${response.status}`);
  }
  return response.json();
}

function redditCoverageConfidence(
  rawItemCount: number,
  moreNodeCount: number,
  stopReason: string | null
): number {
  if (rawItemCount === 0) {
    return 0.2;
  }
  if (stopReason === "more_nodes_not_expanded" || moreNodeCount > 0) {
    return 0.78;
  }
  return 0.92;
}

function redditDomFallbackCoverageConfidence(rawItemCount: number): number {
  if (rawItemCount === 0) {
    return 0.2;
  }

  return rawItemCount > 1 ? 0.55 : 0.35;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "reddit_json_fetch_failed:unknown";
}
