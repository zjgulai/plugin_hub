export type JsonScalar = string | number | boolean | null;
export type JsonValue = JsonScalar | JsonValue[] | { [key: string]: JsonValue };

export type VocPlatform = "amazon" | "reddit";
export type VocPlatformFilter = VocPlatform | "all";

export type VocUnit = {
  source_object_id: string;
  platform: VocPlatform;
  source_kind: string;
  title: string | null;
  body: string;
  quality_flags: string[];
  coverage_confidence: number;
  platform_extension: Record<string, JsonValue>;
  source_url: string;
  captured_at: string;
  created_at: string | null;
  asin: string | null;
  marketplace: string | null;
  thread_id: string | null;
  parent_id: string | null;
  depth: number | null;
  reply_role: string | null;
  collection_run_id: string | null;
  author_display: string | null;
  commercial_object_type: string | null;
  brand: string | null;
  product_title: string | null;
};

export type VocUnitsResponse = {
  items: VocUnit[];
};

export type StrategyNote = {
  strategy_type: string;
  topic: string;
  evidence_count: number;
  evidence_examples: JsonValue[];
  recommendation: string;
  evidence_strength: number;
  quality_flags: string[];
};

export type StrategyNotesResponse = {
  items: StrategyNote[];
};

type FetchResponse = {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
};

export type VocUnitsFetcher = (url: string) => Promise<FetchResponse>;

export async function fetchVocUnits(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<VocUnitsResponse> {
  const response = await fetcher(buildVocUnitsUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`voc_units_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response);
  return {
    items: parseVocUnitsResponse(payload)
  };
}

export async function fetchStrategyNotes(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<StrategyNotesResponse> {
  const response = await fetcher(buildStrategyNotesUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`strategy_notes_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response);
  return {
    items: parseStrategyNotesResponse(payload)
  };
}

function buildVocUnitsUrl(apiBaseUrl: string, platform: VocPlatformFilter): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/voc-units`;
  if (platform === "all") {
    return endpoint;
  }

  return `${endpoint}?platform=${platform}`;
}

function buildStrategyNotesUrl(apiBaseUrl: string, platform: VocPlatformFilter): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/insights/strategy-notes`;
  if (platform === "all") {
    return endpoint;
  }

  return `${endpoint}?platform=${platform}`;
}

async function parseJson(response: FetchResponse): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    throw new Error("voc_units_invalid_response:json_parse_failed", {
      cause: error
    });
  }
}

function parseVocUnitsResponse(payload: unknown): VocUnit[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("voc_units_invalid_response:items_array_required");
  }

  return payload.items.map(parseVocUnit);
}

function parseStrategyNotesResponse(payload: unknown): StrategyNote[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("strategy_notes_invalid_response:items_array_required");
  }

  return payload.items.map(parseStrategyNote);
}

function parseVocUnit(value: unknown): VocUnit {
  if (!isRecord(value)) {
    throw new Error("voc_units_invalid_response:item_object_required");
  }

  return {
    source_object_id: requiredString(value.source_object_id, "source_object_id"),
    platform: requiredPlatform(value.platform),
    source_kind: requiredString(value.source_kind, "source_kind"),
    title: optionalString(value.title),
    body: requiredString(value.body, "body"),
    quality_flags: stringList(value.quality_flags),
    coverage_confidence: requiredFiniteNumber(value.coverage_confidence, "coverage_confidence"),
    platform_extension: jsonObject(value.platform_extension),
    source_url: requiredString(value.source_url, "source_url"),
    captured_at: requiredString(value.captured_at, "captured_at"),
    created_at: optionalString(value.created_at),
    asin: optionalString(value.asin),
    marketplace: optionalString(value.marketplace),
    thread_id: optionalString(value.thread_id),
    parent_id: optionalString(value.parent_id),
    depth: optionalNumber(value.depth),
    reply_role: optionalString(value.reply_role),
    collection_run_id: optionalString(value.collection_run_id),
    author_display: optionalString(value.author_display),
    commercial_object_type: optionalString(value.commercial_object_type),
    brand: optionalString(value.brand),
    product_title: optionalString(value.product_title)
  };
}

function parseStrategyNote(value: unknown): StrategyNote {
  if (!isRecord(value)) {
    throw new Error("strategy_notes_invalid_response:item_object_required");
  }

  return {
    strategy_type: requiredString(value.strategy_type, "strategy_type"),
    topic: requiredString(value.topic, "topic"),
    evidence_count: requiredFiniteInteger(value.evidence_count, "evidence_count"),
    evidence_examples: jsonList(value.evidence_examples),
    recommendation: requiredString(value.recommendation, "recommendation"),
    evidence_strength: requiredFiniteNumber(
      value.evidence_strength,
      "evidence_strength",
      "strategy_notes_invalid_response"
    ),
    quality_flags: stringList(value.quality_flags)
  };
}

function requiredPlatform(value: unknown): VocPlatform {
  if (value === "amazon" || value === "reddit") {
    return value;
  }

  throw new Error("voc_units_invalid_response:item_platform_required");
}

function requiredString(value: unknown, field: string): string {
  if (typeof value === "string") {
    return value;
  }

  throw new Error(`voc_units_invalid_response:${field}_required`);
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function requiredFiniteNumber(
  value: unknown,
  field: string,
  errorPrefix = "voc_units_invalid_response"
): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  throw new Error(`${errorPrefix}:${field}_required`);
}

function requiredFiniteInteger(value: unknown, field: string): number {
  if (typeof value === "number" && Number.isSafeInteger(value)) {
    return value;
  }

  throw new Error(`strategy_notes_invalid_response:${field}_required`);
}

function optionalNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

function jsonObject(value: unknown): Record<string, JsonValue> {
  if (!isRecord(value)) {
    return {};
  }

  const output: Record<string, JsonValue> = {};
  for (const [key, item] of Object.entries(value)) {
    if (isJsonValue(item)) {
      output[key] = item;
    }
  }
  return output;
}

function jsonList(value: unknown): JsonValue[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isJsonValue);
}

function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  ) {
    return true;
  }

  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }

  if (isRecord(value)) {
    return Object.values(value).every(isJsonValue);
  }

  return false;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
