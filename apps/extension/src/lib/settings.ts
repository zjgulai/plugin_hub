export const API_BASE_URL_STORAGE_KEY = "pluginHubApiBaseUrl";
export const DEFAULT_API_BASE_URL = "http://localhost:8000";

export async function loadApiBaseUrl(): Promise<string> {
  const result = await chrome.storage.local.get(API_BASE_URL_STORAGE_KEY);
  const value = result[API_BASE_URL_STORAGE_KEY];
  return typeof value === "string" && value.trim() ? normalizeApiBaseUrl(value) : DEFAULT_API_BASE_URL;
}

export async function saveApiBaseUrl(value: string): Promise<string> {
  const normalized = normalizeApiBaseUrl(value);
  await chrome.storage.local.set({ [API_BASE_URL_STORAGE_KEY]: normalized });
  return normalized;
}

export function normalizeApiBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/+$/, "");
  if (!normalized) {
    return DEFAULT_API_BASE_URL;
  }

  assertHttpUrl(normalized);
  return normalized;
}

function assertHttpUrl(value: string): void {
  let parsedUrl: URL;

  try {
    parsedUrl = new URL(value);
  } catch {
    throw new TypeError("api_base_url_invalid");
  }

  if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
    throw new TypeError("api_base_url_must_be_http");
  }
}
