import type { ApiFetcher } from "./api";

export const API_KEY_HEADER_NAME = "X-Plugin-Hub-Api-Key";

type EnvSource = Record<string, string | undefined>;

export type ApiAccessKeys = {
  readKey: string | undefined;
  writeKey: string | undefined;
};

export function loadApiAccessKeys(env: EnvSource = process.env): ApiAccessKeys {
  const writeKey = normalizedKey(env.PLUGIN_HUB_API_WRITE_KEY);
  return {
    readKey: normalizedKey(env.PLUGIN_HUB_API_READ_KEY) ?? writeKey,
    writeKey
  };
}

export function apiFetcherWithKey(
  apiKey: string | undefined,
  fetcher: ApiFetcher = async (url, init) => fetch(url, init)
): ApiFetcher {
  return async (url, init) => {
    const headers = new Headers(init?.headers);
    if (apiKey) {
      headers.set(API_KEY_HEADER_NAME, apiKey);
    }
    return fetcher(url, { ...init, headers });
  };
}

function normalizedKey(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}
