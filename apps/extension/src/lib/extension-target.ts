import type { Platform } from "../types/contracts";

export const EXTENSION_TARGETS = ["amazon", "reddit"] as const;

export type ExtensionTarget = (typeof EXTENSION_TARGETS)[number];
export type RuntimeExtensionTarget = ExtensionTarget | "all";

export const AMAZON_HOST_MATCHES = [
  "https://amazon.com/*",
  "https://www.amazon.com/*",
  "https://smile.amazon.com/*",
  "https://amazon.co.uk/*",
  "https://www.amazon.co.uk/*",
  "https://amazon.de/*",
  "https://www.amazon.de/*",
  "https://amazon.ca/*",
  "https://www.amazon.ca/*",
  "https://amazon.com.au/*",
  "https://www.amazon.com.au/*",
  "https://amazon.co.jp/*",
  "https://www.amazon.co.jp/*"
] as const;

export const REDDIT_HOST_MATCHES = [
  "https://reddit.com/*",
  "https://www.reddit.com/*",
  "https://old.reddit.com/*"
] as const;

export const LOCAL_API_HOST_PERMISSIONS = [
  "http://localhost/*",
  "http://127.0.0.1/*"
] as const;

export const EXTENSION_TARGET_CONFIGS = {
  amazon: {
    target: "amazon",
    platform: "amazon",
    name: "Plugin Hub Amazon VOC Collector",
    shortName: "Amazon VOC",
    description: "Collects Amazon review VOC evidence for Plugin Hub.",
    defaultTitle: "Plugin Hub Amazon VOC Collector",
    popupTitle: "Plugin Hub Amazon VOC Collector",
    commandBarSubtitle: "Amazon review evidence collector",
    supportedSourceText: "Amazon",
    idleStatusText: "打开 Amazon 商品页或评论页后开始采集。",
    hostPermissions: [...AMAZON_HOST_MATCHES, ...LOCAL_API_HOST_PERMISSIONS],
    contentMatches: AMAZON_HOST_MATCHES
  },
  reddit: {
    target: "reddit",
    platform: "reddit",
    name: "Plugin Hub Reddit VOC Collector",
    shortName: "Reddit VOC",
    description: "Collects Reddit thread VOC evidence for Plugin Hub.",
    defaultTitle: "Plugin Hub Reddit VOC Collector",
    popupTitle: "Plugin Hub Reddit VOC Collector",
    commandBarSubtitle: "Reddit thread evidence collector",
    supportedSourceText: "Reddit",
    idleStatusText: "打开 Reddit thread 后开始采集。",
    hostPermissions: [...REDDIT_HOST_MATCHES, ...LOCAL_API_HOST_PERMISSIONS],
    contentMatches: REDDIT_HOST_MATCHES
  }
} as const satisfies Record<
  ExtensionTarget,
  {
    target: ExtensionTarget;
    platform: Platform;
    name: string;
    shortName: string;
    description: string;
    defaultTitle: string;
    popupTitle: string;
    commandBarSubtitle: string;
    supportedSourceText: string;
    idleStatusText: string;
    hostPermissions: readonly string[];
    contentMatches: readonly string[];
  }
>;

declare const __PLUGIN_HUB_EXTENSION_TARGET__: string | undefined;

export const CURRENT_EXTENSION_TARGET = normalizeExtensionTarget(readDefinedExtensionTarget());

export function normalizeExtensionTarget(
  value: unknown,
  fallback: ExtensionTarget = "amazon"
): ExtensionTarget {
  return isExtensionTarget(value) ? value : fallback;
}

export function normalizeRuntimeExtensionTarget(
  value: unknown,
  fallback: RuntimeExtensionTarget = "all"
): RuntimeExtensionTarget {
  if (value === "all") {
    return "all";
  }
  return isExtensionTarget(value) ? value : fallback;
}

export function isExtensionTarget(value: unknown): value is ExtensionTarget {
  return value === "amazon" || value === "reddit";
}

export function targetSupportsPlatform(
  target: RuntimeExtensionTarget,
  platform: Platform
): boolean {
  return target === "all" || target === platform;
}

export function extensionTargetConfig(target: ExtensionTarget) {
  return EXTENSION_TARGET_CONFIGS[target];
}

function readDefinedExtensionTarget(): unknown {
  if (typeof __PLUGIN_HUB_EXTENSION_TARGET__ === "undefined") {
    return undefined;
  }

  return __PLUGIN_HUB_EXTENSION_TARGET__;
}
