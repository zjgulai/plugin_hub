import {
  CURRENT_EXTENSION_TARGET,
  extensionTargetConfig
} from "./extension-target";

export const API_BASE_URL_STORAGE_KEY = "pluginHubApiBaseUrl";
export const API_KEY_STORAGE_KEY = "pluginHubApiKey";
export const DEFAULT_API_BASE_URL = extensionTargetConfig(CURRENT_EXTENSION_TARGET).defaultApiBaseUrl;

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

export async function loadApiKey(): Promise<string> {
  const result = await chrome.storage.local.get(API_KEY_STORAGE_KEY);
  const value = result[API_KEY_STORAGE_KEY];
  return typeof value === "string" ? normalizeApiKey(value) : "";
}

export async function saveApiKey(value: string): Promise<string> {
  const normalized = normalizeApiKey(value);
  await chrome.storage.local.set({ [API_KEY_STORAGE_KEY]: normalized });
  return normalized;
}

export function normalizeApiKey(value: string): string {
  const normalized = value.trim();
  if (normalized && normalized.length < 32) {
    throw new TypeError("api_key_too_short");
  }
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
