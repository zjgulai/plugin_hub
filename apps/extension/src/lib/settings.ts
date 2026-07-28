import {
  CURRENT_EXTENSION_TARGET,
  extensionTargetConfig
} from "./extension-target";
import type { CaptureCurrentPageSuccess } from "../types/messages";

export const API_BASE_URL_STORAGE_KEY = "pluginHubApiBaseUrl";
export const API_KEY_STORAGE_KEY = "pluginHubApiKey";
export const PENDING_UPLOAD_STORAGE_KEY = "pluginHubPendingCollectionUpload";
export const DEFAULT_API_BASE_URL = extensionTargetConfig(CURRENT_EXTENSION_TARGET).defaultApiBaseUrl;

export type PendingCollectionUpload = {
  apiBaseUrl: string;
  capture: CaptureCurrentPageSuccess;
};

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

export async function loadPendingCollectionUpload(): Promise<PendingCollectionUpload | null> {
  const result = await chrome.storage.session.get(PENDING_UPLOAD_STORAGE_KEY);
  const value = result[PENDING_UPLOAD_STORAGE_KEY];
  if (isPendingCollectionUpload(value)) {
    return value;
  }
  if (value !== undefined) {
    await chrome.storage.session.remove(PENDING_UPLOAD_STORAGE_KEY);
  }
  return null;
}

export async function savePendingCollectionUpload(
  pendingUpload: PendingCollectionUpload
): Promise<void> {
  await chrome.storage.session.set({ [PENDING_UPLOAD_STORAGE_KEY]: pendingUpload });
}

export async function clearPendingCollectionUpload(): Promise<void> {
  await chrome.storage.session.remove(PENDING_UPLOAD_STORAGE_KEY);
}

export async function resolvePendingUpload<T>(
  pendingUpload: T | null,
  capture: () => Promise<T>
): Promise<T> {
  return pendingUpload ?? capture();
}

export function retargetPendingCollectionUpload(
  pendingUpload: PendingCollectionUpload,
  apiBaseUrl: string
): PendingCollectionUpload {
  return {
    apiBaseUrl: normalizeApiBaseUrl(apiBaseUrl),
    capture: pendingUpload.capture
  };
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

function isPendingCollectionUpload(value: unknown): value is PendingCollectionUpload {
  if (!isRecord(value) || typeof value.apiBaseUrl !== "string" || !isRecord(value.capture)) {
    return false;
  }
  return isRecord(value.capture.payload) && isRecord(value.capture.summary);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
