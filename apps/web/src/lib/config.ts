import type { VocPlatform } from "./api";

export type DashboardConfig = {
  apiBaseUrl: string;
  siteEnv: string;
  refreshSeconds: number;
  enabledPlatforms: VocPlatform[];
  amazonPageLimit: number;
  lowConfidenceThreshold: number;
};

type EnvSource = Record<string, string | undefined>;

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_SITE_ENV = "local";
const DEFAULT_REFRESH_SECONDS = 30;
const DEFAULT_ENABLED_PLATFORMS: VocPlatform[] = ["amazon", "reddit"];
const DEFAULT_AMAZON_PAGE_LIMIT = 3;
const DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.7;

export function loadDashboardConfig(env: EnvSource = process.env): DashboardConfig {
  return {
    apiBaseUrl: stringValue(env.PLUGIN_HUB_API_URL, DEFAULT_API_BASE_URL),
    siteEnv: stringValue(env.PLUGIN_HUB_SITE_ENV, DEFAULT_SITE_ENV),
    refreshSeconds: positiveInteger(env.PLUGIN_HUB_REFRESH_SECONDS, DEFAULT_REFRESH_SECONDS),
    enabledPlatforms: platformList(env.PLUGIN_HUB_ENABLED_PLATFORMS),
    amazonPageLimit: positiveInteger(
      env.PLUGIN_HUB_AMAZON_PAGE_LIMIT,
      DEFAULT_AMAZON_PAGE_LIMIT
    ),
    lowConfidenceThreshold: boundedNumber(
      env.PLUGIN_HUB_LOW_CONFIDENCE_THRESHOLD,
      DEFAULT_LOW_CONFIDENCE_THRESHOLD
    )
  };
}

function stringValue(value: string | undefined, fallback: string): string {
  const normalized = value?.trim();
  return normalized ? normalized : fallback;
}

function positiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function boundedNumber(value: string | undefined, fallback: number): number {
  const parsed = Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1 ? parsed : fallback;
}

function platformList(value: string | undefined): VocPlatform[] {
  const parsed = (value ?? "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item): item is VocPlatform => item === "amazon" || item === "reddit");

  if (parsed.length === 0) {
    return DEFAULT_ENABLED_PLATFORMS;
  }

  return Array.from(new Set(parsed));
}
