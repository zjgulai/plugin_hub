import {
  assertJsonObject,
  type JsonObject,
  type JsonValue,
  type RawSourceItem
} from "../types/contracts";

const PLATFORM = "reddit";
const THREAD_SOURCE_KIND = "reddit_thread";
const COMMENT_SOURCE_KIND = "reddit_comment";
const THREAD_RAW_SCHEMA_VERSION = "raw_reddit_thread_v1";
const COMMENT_RAW_SCHEMA_VERSION = "raw_reddit_comment_v1";
const PARSER_VERSION = "reddit-json-parser@0.1.0";

const THREAD_FIELD_KEYS = [
  "name",
  "id",
  "title",
  "selftext",
  "author",
  "subreddit",
  "subreddit_name_prefixed",
  "created_utc",
  "score",
  "upvote_ratio",
  "num_comments",
  "locked",
  "archived",
  "stickied",
  "link_flair_text",
  "permalink",
  "url"
] as const;

const COMMENT_FIELD_KEYS = [
  "name",
  "id",
  "body",
  "author",
  "parent_id",
  "link_id",
  "thread_id",
  "depth",
  "created_utc",
  "score",
  "is_submitter",
  "controversiality",
  "subreddit",
  "subreddit_name_prefixed",
  "permalink",
  "comment_flair",
  "author_flair_text"
] as const;

const MORE_FIELD_KEYS = ["id", "parent_id", "children", "depth"] as const;

export interface ParseRedditThreadJsonOptions {
  capturedAt?: string;
}

export interface ParseRedditThreadJsonResult {
  rawItems: RawSourceItem[];
  moreNodeCount: number;
  stopReason: "invalid_payload" | "missing_thread" | null;
}

interface RedditListing {
  data: {
    children: unknown[];
  };
}

interface RedditNode {
  kind: string;
  data: Record<string, unknown>;
}

interface CommentTraversalResult {
  rawItems: RawSourceItem[];
  moreNodeCount: number;
}

export function parseRedditThreadJson(
  payload: unknown,
  sourceUrl: string,
  options: ParseRedditThreadJsonOptions = {}
): ParseRedditThreadJsonResult {
  const listings = parseListings(payload);

  if (!listings) {
    return emptyResult("invalid_payload");
  }

  const [threadListing, commentsListing] = listings;
  const threadNode = findThreadNode(threadListing.data.children);

  if (!threadNode) {
    return emptyResult("missing_thread");
  }

  const capturedAt = parseCapturedAt(options.capturedAt);
  const threadRawItem = buildThreadRawSourceItem(threadNode.data, sourceUrl, capturedAt);
  const threadFullname = redditThreadFullname(threadNode.data);
  const comments = threadFullname
    ? parseComments(commentsListing.data.children, sourceUrl, capturedAt, threadFullname)
    : { rawItems: [], moreNodeCount: 0 };

  return {
    rawItems: [threadRawItem, ...comments.rawItems],
    moreNodeCount: comments.moreNodeCount,
    stopReason: null
  };
}

function emptyResult(stopReason: "invalid_payload" | "missing_thread"): ParseRedditThreadJsonResult {
  return {
    rawItems: [],
    moreNodeCount: 0,
    stopReason
  };
}

function buildThreadRawSourceItem(
  data: Record<string, unknown>,
  sourceUrl: string,
  capturedAt: string
): RawSourceItem {
  const selectedPayload = buildSelectedPayload(data, THREAD_FIELD_KEYS);
  const sourceObjectId = redditThreadSourceObjectId(data, selectedPayload);

  return buildRawSourceItem({
    sourceKind: THREAD_SOURCE_KIND,
    sourceObjectId,
    rawSchemaVersion: THREAD_RAW_SCHEMA_VERSION,
    selectedPayload,
    sourceUrl,
    capturedAt
  });
}

function buildCommentRawSourceItem(
  data: Record<string, unknown>,
  sourceUrl: string,
  capturedAt: string,
  threadId: string
): RawSourceItem {
  const selectedPayload = buildSelectedPayload(data, COMMENT_FIELD_KEYS);
  ensureCommentThreadLinkage(selectedPayload, threadId);
  const commentFlairText = cleanJsonValue(data.comment_flair_text);

  if (selectedPayload.comment_flair === undefined && commentFlairText !== undefined) {
    selectedPayload.comment_flair = commentFlairText;
  }

  const sourceObjectId = redditCommentSourceObjectId(data, selectedPayload);

  return buildRawSourceItem({
    sourceKind: COMMENT_SOURCE_KIND,
    sourceObjectId,
    rawSchemaVersion: COMMENT_RAW_SCHEMA_VERSION,
    selectedPayload,
    sourceUrl,
    capturedAt
  });
}

function buildMoreRawSourceItem(
  data: Record<string, unknown>,
  sourceUrl: string,
  capturedAt: string,
  threadId: string
): RawSourceItem {
  const selectedPayload = {
    kind: "more",
    ...buildSelectedPayload(data, MORE_FIELD_KEYS)
  } satisfies JsonObject;
  ensureCommentThreadLinkage(selectedPayload, threadId);
  const sourceObjectId = redditMoreSourceObjectId(data, selectedPayload);

  return buildRawSourceItem({
    sourceKind: COMMENT_SOURCE_KIND,
    sourceObjectId,
    rawSchemaVersion: COMMENT_RAW_SCHEMA_VERSION,
    selectedPayload,
    sourceUrl,
    capturedAt
  });
}

function buildRawSourceItem({
  sourceKind,
  sourceObjectId,
  rawSchemaVersion,
  selectedPayload,
  sourceUrl,
  capturedAt
}: {
  sourceKind: typeof THREAD_SOURCE_KIND | typeof COMMENT_SOURCE_KIND;
  sourceObjectId: string;
  rawSchemaVersion: typeof THREAD_RAW_SCHEMA_VERSION | typeof COMMENT_RAW_SCHEMA_VERSION;
  selectedPayload: JsonObject;
  sourceUrl: string;
  capturedAt: string;
}): RawSourceItem {
  const rawPayload = {
    ...selectedPayload,
    platform: PLATFORM,
    source_kind: sourceKind,
    source_object_id: sourceObjectId,
    raw_schema_version: rawSchemaVersion,
    parser_version: PARSER_VERSION,
    source_url: sourceUrl,
    captured_at: capturedAt
  } satisfies JsonObject;

  assertJsonObject(rawPayload);

  return {
    platform: PLATFORM,
    source_kind: sourceKind,
    source_object_id: sourceObjectId,
    raw_schema_version: rawSchemaVersion,
    parser_version: PARSER_VERSION,
    raw_payload: rawPayload,
    raw_payload_hash: stableHash(rawPayload),
    captured_at: capturedAt
  };
}

function parseComments(
  children: unknown[],
  sourceUrl: string,
  capturedAt: string,
  threadId: string
): CommentTraversalResult {
  const rawItems: RawSourceItem[] = [];
  let moreNodeCount = 0;

  for (const child of children) {
    const node = parseNode(child);

    if (!node) {
      continue;
    }

    if (node.kind === "t1") {
      rawItems.push(buildCommentRawSourceItem(node.data, sourceUrl, capturedAt, threadId));

      const replies = parseListing(node.data.replies);
      if (replies) {
        const nested = parseComments(replies.data.children, sourceUrl, capturedAt, threadId);
        rawItems.push(...nested.rawItems);
        moreNodeCount += nested.moreNodeCount;
      }
      continue;
    }

    if (node.kind === "more") {
      rawItems.push(buildMoreRawSourceItem(node.data, sourceUrl, capturedAt, threadId));
      moreNodeCount += 1;
    }
  }

  return {
    rawItems,
    moreNodeCount
  };
}

function ensureCommentThreadLinkage(payload: JsonObject, threadId: string): void {
  payload.link_id = threadId;
  payload.thread_id = threadId;
}

function redditThreadFullname(data: Record<string, unknown>): string | null {
  const name = stringField(data, "name");
  if (name?.startsWith("t3_") && name.length > "t3_".length) {
    return name;
  }

  const id = stringField(data, "id");
  if (id) {
    return `t3_${id}`;
  }

  return null;
}

function parseListings(payload: unknown): [RedditListing, RedditListing] | null {
  if (!Array.isArray(payload) || payload.length < 2) {
    return null;
  }

  const threadListing = parseListing(payload[0]);
  const commentsListing = parseListing(payload[1]);

  if (!threadListing || !commentsListing) {
    return null;
  }

  return [threadListing, commentsListing];
}

function parseListing(value: unknown): RedditListing | null {
  if (!isPlainObject(value) || !isPlainObject(value.data) || !Array.isArray(value.data.children)) {
    return null;
  }

  return {
    data: {
      children: value.data.children
    }
  };
}

function findThreadNode(children: unknown[]): RedditNode | null {
  for (const child of children) {
    const node = parseNode(child);

    if (node?.kind === "t3") {
      return node;
    }
  }

  return null;
}

function parseNode(value: unknown): RedditNode | null {
  if (!isPlainObject(value) || typeof value.kind !== "string" || !isPlainObject(value.data)) {
    return null;
  }

  return {
    kind: value.kind,
    data: value.data
  };
}

function redditThreadSourceObjectId(
  data: Record<string, unknown>,
  fallbackPayload: JsonObject
): string {
  const name = stringField(data, "name");
  if (name) {
    return name;
  }

  const id = stringField(data, "id");
  if (id) {
    return `t3_${id}`;
  }

  return stableMissingId("reddit_missing_thread_id", fallbackPayload);
}

function redditCommentSourceObjectId(
  data: Record<string, unknown>,
  fallbackPayload: JsonObject
): string {
  const name = stringField(data, "name");
  if (name) {
    return name;
  }

  const id = stringField(data, "id");
  if (id) {
    return `t1_${id}`;
  }

  return stableMissingId("reddit_missing_comment_id", fallbackPayload);
}

function redditMoreSourceObjectId(
  data: Record<string, unknown>,
  fallbackPayload: JsonObject
): string {
  const id = stringField(data, "id");
  if (id) {
    return `more_${id}`;
  }

  return stableMissingId("more_missing_id", fallbackPayload);
}

function buildSelectedPayload(
  data: Record<string, unknown>,
  fieldKeys: readonly string[]
): JsonObject {
  const payload: JsonObject = {};

  for (const key of fieldKeys) {
    const value = cleanJsonValue(data[key]);

    if (value !== undefined) {
      payload[key] = value;
    }
  }

  return payload;
}

function cleanJsonValue(value: unknown): JsonValue | undefined {
  if (value === null) {
    return null;
  }

  switch (typeof value) {
    case "string":
    case "boolean":
      return value;
    case "number":
      return Number.isFinite(value) ? value : null;
    case "object":
      return cleanJsonObjectOrArray(value);
    default:
      return undefined;
  }
}

function cleanJsonObjectOrArray(value: object): JsonValue | undefined {
  if (Array.isArray(value)) {
    const output: JsonValue[] = [];

    for (const item of value) {
      const cleanedItem = cleanJsonValue(item);

      if (cleanedItem !== undefined) {
        output.push(cleanedItem);
      }
    }

    return output;
  }

  if (!isPlainObject(value)) {
    return undefined;
  }

  const output: JsonObject = {};

  for (const [key, nestedValue] of Object.entries(value)) {
    const cleanedValue = cleanJsonValue(nestedValue);

    if (cleanedValue !== undefined) {
      output[key] = cleanedValue;
    }
  }

  return output;
}

function parseCapturedAt(value: string | undefined): string {
  const parsedDate = value ? new Date(value) : new Date();

  if (Number.isNaN(parsedDate.getTime())) {
    return new Date().toISOString();
  }

  return parsedDate.toISOString();
}

function stringField(data: Record<string, unknown>, key: string): string | null {
  const value = data[key];

  if (typeof value !== "string") {
    return null;
  }

  const normalizedValue = value.trim();
  return normalizedValue.length > 0 ? normalizedValue : null;
}

function stableMissingId(prefix: string, value: JsonValue): string {
  return `${prefix}_${stableDigest64(value)}`;
}

function stableHash(value: JsonValue): string {
  return `fnv1a64:${stableDigest64(value)}`;
}

function stableDigest64(value: JsonValue): string {
  const canonicalValue = stableStringify(value);
  let hash = 0xcbf29ce484222325n;
  const prime = 0x100000001b3n;

  for (let index = 0; index < canonicalValue.length; index += 1) {
    hash ^= BigInt(canonicalValue.charCodeAt(index));
    hash = BigInt.asUintN(64, hash * prime);
  }

  return hash.toString(16).padStart(16, "0");
}

function stableStringify(value: JsonValue): string {
  if (value === null) {
    return "null";
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }

  switch (typeof value) {
    case "string":
    case "number":
    case "boolean":
      return JSON.stringify(value);
    case "object":
      return `{${Object.entries(value)
        .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
        .map(([key, nestedValue]) => `${JSON.stringify(key)}:${stableStringify(nestedValue)}`)
        .join(",")}}`;
  }

  throw new TypeError("unsupported_json_value");
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}
