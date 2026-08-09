import {
  assertJsonObject,
  assertJsonValue,
  type ActionRecommendation,
  type BriefConfidence,
  type BusinessSignal,
  type CollectionRunPayload,
  type CollectionTaskPayload,
  type CollectionTaskResult,
  type CollectionTaskStatus,
  type DataGap,
  type EvidenceReference,
  type ExecutiveFinding,
  type InsightBrief,
  type InsightBriefsResponse,
  type InsightScope,
  type PlatformSettingResult,
  type StrategyNote,
  type StrategyNotesResponse,
  type Platform
} from "../types/contracts";

export interface CollectionRunUploadResult {
  collection_run_id: string;
  raw_item_count: number;
  voc_unit_count: number;
}

interface UploadHttpResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

export type UploadFetcher = (url: string, init: RequestInit) => Promise<UploadHttpResponse>;

export async function uploadCollectionRun(
  apiBaseUrl: string,
  payload: CollectionRunPayload,
  fetcher: UploadFetcher = fetch,
  apiKey?: string
): Promise<CollectionRunUploadResult> {
  assertCollectionRunPayloadJson(payload);

  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/collection-runs`, {
    method: "POST",
    headers: apiHeaders(
      {
        "Content-Type": "application/json",
        "Idempotency-Key": buildCollectionIdempotencyKey(payload)
      },
      apiKey
    ),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`collection_run_upload_failed:${response.status}`);
  }

  return parseUploadResult(await response.json());
}

export function buildCollectionIdempotencyKey(payload: CollectionRunPayload): string {
  const serialized = JSON.stringify(payload);
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;
  for (let index = 0; index < serialized.length; index += 1) {
    hash ^= BigInt(serialized.charCodeAt(index));
    hash = BigInt.asUintN(64, hash * prime);
  }
  return `capture-fnv1a64-${hash.toString(16).padStart(16, "0")}`;
}

export async function createCollectionTask(
  apiBaseUrl: string,
  payload: CollectionTaskPayload,
  fetcher: UploadFetcher = fetch,
  apiKey?: string
): Promise<CollectionTaskResult> {
  assertCollectionTaskPayloadJson(payload);

  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/collection-tasks`, {
    method: "POST",
    headers: apiHeaders({ "Content-Type": "application/json" }, apiKey),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`collection_task_create_failed:${response.status}`);
  }

  return parseCollectionTaskResult(await response.json());
}

export async function getPlatformSetting(
  apiBaseUrl: string,
  platform: Platform,
  fetcher: UploadFetcher = fetch,
  apiKey?: string
): Promise<PlatformSettingResult> {
  const response = await fetcher(`${trimBaseUrl(apiBaseUrl)}/api/platform-settings/${platform}`, {
    method: "GET",
    headers: apiHeaders({ Accept: "application/json" }, apiKey)
  });

  if (!response.ok) {
    throw new Error(`platform_setting_fetch_failed:${response.status}`);
  }

  return parsePlatformSettingResult(await response.json(), platform);
}

export async function getStrategyNotes(
  apiBaseUrl: string,
  platform: Platform,
  fetcher: UploadFetcher = fetch,
  apiKey?: string
): Promise<StrategyNotesResponse> {
  const response = await fetcher(
    `${trimBaseUrl(apiBaseUrl)}/api/insights/strategy-notes?platform=${encodeURIComponent(platform)}`,
    {
      method: "GET",
      headers: apiHeaders({ Accept: "application/json" }, apiKey)
    }
  );

  if (!response.ok) {
    throw new Error(`strategy_notes_fetch_failed:${response.status}`);
  }

  return parseStrategyNotesResponse(await response.json());
}

export async function getInsightBriefs(
  apiBaseUrl: string,
  platform: Platform,
  fetcher: UploadFetcher = fetch,
  apiKey?: string
): Promise<InsightBriefsResponse> {
  const response = await fetcher(
    `${trimBaseUrl(apiBaseUrl)}/api/insights/briefs?platform=${encodeURIComponent(platform)}`,
    {
      method: "GET",
      headers: apiHeaders({ Accept: "application/json" }, apiKey)
    }
  );

  if (!response.ok) {
    throw new Error(`insight_briefs_fetch_failed:${response.status}`);
  }

  return parseInsightBriefsResponse(await response.json());
}

function trimBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/+$/, "");
}

function apiHeaders(
  headers: Record<string, string>,
  apiKey: string | undefined
): Record<string, string> {
  const normalized = apiKey?.trim();
  return normalized
    ? { ...headers, "X-Plugin-Hub-Api-Key": normalized }
    : headers;
}

function assertCollectionRunPayloadJson(payload: CollectionRunPayload): void {
  assertJsonValue(payload);
  assertJsonObject(payload.run.coverage_scope);

  for (const rawItem of payload.raw_items) {
    assertJsonObject(rawItem.raw_payload);
  }
}

function assertCollectionTaskPayloadJson(payload: CollectionTaskPayload): void {
  assertJsonValue(payload);
  assertJsonObject(payload.task.context);
}

function parseUploadResult(value: unknown): CollectionRunUploadResult {
  if (!isRecord(value)) {
    throw new TypeError("collection_run_upload_response_object_required");
  }

  const collectionRunId = value.collection_run_id;
  const rawItemCount = value.raw_item_count;
  const vocUnitCount = value.voc_unit_count;

  if (
    typeof collectionRunId !== "string" ||
    typeof rawItemCount !== "number" ||
    typeof vocUnitCount !== "number"
  ) {
    throw new TypeError("collection_run_upload_response_invalid");
  }

  return {
    collection_run_id: collectionRunId,
    raw_item_count: rawItemCount,
    voc_unit_count: vocUnitCount
  };
}

function parseCollectionTaskResult(value: unknown): CollectionTaskResult {
  if (!isRecord(value)) {
    throw new TypeError("collection_task_response_object_required");
  }

  const collectionTaskId = value.collection_task_id;
  const platform = value.platform;
  const sourceUrl = value.source_url;
  const requestedCaptureMethod = value.requested_capture_method;
  const triggerReason = value.trigger_reason;
  const status = value.status;
  const context = value.context;
  const createdAt = value.created_at;
  const updatedAt = value.updated_at;

  if (
    typeof collectionTaskId !== "string" ||
    !isPlatform(platform) ||
    typeof sourceUrl !== "string" ||
    typeof requestedCaptureMethod !== "string" ||
    typeof triggerReason !== "string" ||
    !isCollectionTaskStatus(status) ||
    typeof createdAt !== "string" ||
    typeof updatedAt !== "string"
  ) {
    throw new TypeError("collection_task_response_invalid");
  }

  assertJsonObject(context);

  return {
    collection_task_id: collectionTaskId,
    platform,
    source_url: sourceUrl,
    requested_capture_method: requestedCaptureMethod,
    trigger_reason: triggerReason,
    status,
    context,
    created_at: createdAt,
    updated_at: updatedAt
  };
}

function parsePlatformSettingResult(
  value: unknown,
  expectedPlatform: Platform
): PlatformSettingResult {
  if (!isRecord(value)) {
    throw new TypeError("platform_setting_response_object_required");
  }

  const platform = value.platform;
  const enabled = value.enabled;
  const config = value.config;
  const updatedAt = value.updated_at;
  const updatedBy = value.updated_by;
  const source = value.source;

  if (
    !isPlatform(platform) ||
    platform !== expectedPlatform ||
    typeof enabled !== "boolean" ||
    typeof updatedAt !== "string" ||
    typeof updatedBy !== "string" ||
    typeof source !== "string"
  ) {
    throw new TypeError("platform_setting_response_invalid");
  }

  assertJsonObject(config);

  return {
    platform,
    enabled,
    config,
    updated_at: updatedAt,
    updated_by: updatedBy,
    source
  };
}

function parseStrategyNotesResponse(value: unknown): StrategyNotesResponse {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new TypeError("strategy_notes_response_invalid");
  }

  return {
    items: value.items.map(parseStrategyNote)
  };
}

function parseStrategyNote(value: unknown): StrategyNote {
  if (!isRecord(value)) {
    throw new TypeError("strategy_note_response_invalid");
  }

  const strategyType = value.strategy_type;
  const topic = value.topic;
  const evidenceCount = value.evidence_count;
  const evidenceExamples = value.evidence_examples;
  const recommendation = value.recommendation;
  const evidenceStrength = value.evidence_strength;
  const qualityFlags = value.quality_flags;

  if (
    typeof strategyType !== "string" ||
    typeof topic !== "string" ||
    typeof evidenceCount !== "number" ||
    !Array.isArray(evidenceExamples) ||
    typeof recommendation !== "string" ||
    typeof evidenceStrength !== "number" ||
    !Array.isArray(qualityFlags) ||
    !qualityFlags.every((flag) => typeof flag === "string")
  ) {
    throw new TypeError("strategy_note_response_invalid");
  }

  for (const example of evidenceExamples) {
    assertJsonValue(example);
  }

  return {
    strategy_type: strategyType,
    topic,
    evidence_count: evidenceCount,
    evidence_examples: evidenceExamples,
    recommendation,
    evidence_strength: evidenceStrength,
    quality_flags: qualityFlags
  };
}

function parseInsightBriefsResponse(value: unknown): InsightBriefsResponse {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    items: value.items.map(parseInsightBrief)
  };
}

function parseInsightBrief(value: unknown): InsightBrief {
  if (!isRecord(value)) {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    brief_id: requiredString(value.brief_id),
    template_id: requiredString(value.template_id),
    template_version: requiredString(value.template_version),
    language: requiredString(value.language),
    advisor_profile: requiredString(value.advisor_profile),
    scope: parseInsightScope(value.scope),
    headline: requiredString(value.headline),
    executive_findings: objectList(value.executive_findings).map(parseExecutiveFinding),
    business_signals: objectList(value.business_signals).map(parseBusinessSignal),
    action_plan: objectList(value.action_plan).map(parseActionRecommendation),
    evidence_refs: objectList(value.evidence_refs).map(parseEvidenceReference),
    confidence: parseBriefConfidence(value.confidence),
    data_gaps: objectList(value.data_gaps).map(parseDataGap),
    generation_method: requiredString(value.generation_method),
    created_at: requiredString(value.created_at)
  };
}

function parseInsightScope(value: unknown): InsightScope {
  if (!isRecord(value) || !isPlatform(value.platform)) {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    platform: value.platform,
    source_object_type: requiredString(value.source_object_type),
    source_object_id: requiredString(value.source_object_id),
    source_url: requiredString(value.source_url),
    collection_run_ids: stringList(value.collection_run_ids),
    coverage_scope: requiredString(value.coverage_scope),
    coverage_confidence: requiredNumber(value.coverage_confidence)
  };
}

function parseExecutiveFinding(value: Record<string, unknown>): ExecutiveFinding {
  return {
    finding_id: requiredString(value.finding_id),
    title: requiredString(value.title),
    business_meaning: requiredString(value.business_meaning),
    priority: requiredString(value.priority),
    confidence_level: requiredString(value.confidence_level),
    evidence_ref_ids: stringList(value.evidence_ref_ids)
  };
}

function parseBusinessSignal(value: Record<string, unknown>): BusinessSignal {
  return {
    signal_id: requiredString(value.signal_id),
    signal_type: requiredString(value.signal_type),
    topic: requiredString(value.topic),
    aspect: requiredString(value.aspect),
    customer_language: stringList(value.customer_language),
    business_impact: requiredString(value.business_impact),
    severity: requiredString(value.severity),
    priority: requiredString(value.priority),
    evidence_strength: requiredString(value.evidence_strength),
    confidence_reason: requiredString(value.confidence_reason),
    evidence_ref_ids: stringList(value.evidence_ref_ids),
    quality_flags: stringList(value.quality_flags)
  };
}

function parseActionRecommendation(value: Record<string, unknown>): ActionRecommendation {
  return {
    action_id: requiredString(value.action_id),
    action_type: requiredString(value.action_type),
    title: requiredString(value.title),
    recommendation: requiredString(value.recommendation),
    why_now: requiredString(value.why_now),
    expected_metric: requiredString(value.expected_metric),
    owner_role: requiredString(value.owner_role),
    priority: requiredString(value.priority),
    effort: requiredString(value.effort),
    evidence_ref_ids: stringList(value.evidence_ref_ids)
  };
}

function parseEvidenceReference(value: Record<string, unknown>): EvidenceReference {
  if (!isPlatform(value.platform)) {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    evidence_ref_id: requiredString(value.evidence_ref_id),
    voc_unit_id: requiredString(value.voc_unit_id),
    platform: value.platform,
    source_kind: requiredString(value.source_kind),
    source_object_id: requiredString(value.source_object_id),
    quote: requiredString(value.quote),
    normalized_quote: requiredString(value.normalized_quote),
    rating: nullableNumber(value.rating),
    relation_edge_ids: stringList(value.relation_edge_ids),
    quality_flags: stringList(value.quality_flags),
    source_url: requiredString(value.source_url)
  };
}

function parseBriefConfidence(value: unknown): BriefConfidence {
  if (!isRecord(value)) {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    level: requiredString(value.level),
    reason: requiredString(value.reason),
    evidence_count: requiredNumber(value.evidence_count),
    source_diversity: requiredString(value.source_diversity),
    coverage_notes: stringList(value.coverage_notes)
  };
}

function parseDataGap(value: Record<string, unknown>): DataGap {
  if (typeof value.blocks_confidence !== "boolean") {
    throw new TypeError("insight_brief_response_invalid");
  }

  return {
    gap_type: requiredString(value.gap_type),
    description: requiredString(value.description),
    recommended_collection: requiredString(value.recommended_collection),
    blocks_confidence: value.blocks_confidence
  };
}

function requiredString(value: unknown): string {
  if (typeof value !== "string") {
    throw new TypeError("insight_brief_response_invalid");
  }
  return value;
}

function requiredNumber(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new TypeError("insight_brief_response_invalid");
  }
  return value;
}

function nullableNumber(value: unknown): number | null {
  if (value === null) {
    return null;
  }
  return requiredNumber(value);
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new TypeError("insight_brief_response_invalid");
  }
  return value;
}

function objectList(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value) || !value.every(isRecord)) {
    throw new TypeError("insight_brief_response_invalid");
  }
  return value;
}

function isPlatform(value: unknown): value is Platform {
  return value === "amazon" || value === "reddit" || value === "instagram";
}

function isCollectionTaskStatus(value: unknown): value is CollectionTaskStatus {
  return (
    value === "pending" ||
    value === "running" ||
    value === "retry_scheduled" ||
    value === "completed" ||
    value === "failed"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
