import type { CollectionRunPayload, JsonObject, JsonValue } from "../../types/contracts";

export function buildPayloadJson(payload: CollectionRunPayload): string {
  return `${JSON.stringify(payload, null, 2)}\n`;
}

export function buildRawItemsCsv(payload: CollectionRunPayload): string {
  const headers = [
    "platform",
    "source_kind",
    "source_object_id",
    "captured_at",
    "raw_schema_version",
    "parser_version",
    "title",
    "body",
    "rating",
    "source_url"
  ];
  const rows = payload.raw_items.map((item) => {
    const rawPayload = item.raw_payload;
    return [
      item.platform,
      item.source_kind,
      item.source_object_id,
      item.captured_at,
      item.raw_schema_version,
      item.parser_version,
      textField(rawPayload, ["title", "review_title"]),
      textField(rawPayload, ["body", "selftext", "review_text"]),
      textField(rawPayload, ["rating"]),
      textField(rawPayload, ["url", "source_url"])
    ];
  });

  return `${[headers, ...rows].map((row) => row.map(escapeCsvCell).join(",")).join("\n")}\n`;
}

export function buildExportFilename(payload: CollectionRunPayload, extension: "csv" | "json"): string {
  const sourceId = sourceIdFromPayload(payload);
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `plugin-hub-${payload.run.platform}-${sourceId}-${timestamp}.${extension}`;
}

export function downloadTextFile(filename: string, mimeType: string, content: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function sourceIdFromPayload(payload: CollectionRunPayload): string {
  const coverageScope = payload.run.coverage_scope;
  const rawSourceId =
    stringValue(coverageScope.asin) ??
    stringValue(coverageScope.thread_id) ??
    stringValue(payload.raw_items[0]?.source_object_id) ??
    "capture";

  return rawSourceId.replace(/[^a-zA-Z0-9_-]/g, "-").slice(0, 64);
}

function textField(rawPayload: JsonObject, fieldNames: string[]): string {
  for (const fieldName of fieldNames) {
    const value = stringValue(rawPayload[fieldName]);
    if (value) {
      return value;
    }
  }

  return "";
}

function stringValue(value: JsonValue | undefined): string | null {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function escapeCsvCell(value: string): string {
  if (!/[",\n\r]/.test(value)) {
    return value;
  }

  return `"${value.replace(/"/g, '""')}"`;
}
