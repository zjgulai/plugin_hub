import type { Platform } from "../types/contracts";
import targetRegistry from "../../extension-targets.json";

type ExtensionTargetRegistry = {
  targets: ExtensionTarget[];
  targetConfigs: Record<ExtensionTarget, ExtensionTargetConfig>;
};

type ExtensionTargetConfig = {
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
  packageSlug: string;
  defaultApiBaseUrl: string;
  hostPermissions: string[];
  contentMatches: string[];
  verify: {
    requiredHost: string;
    forbiddenHosts: string[];
    requiredApiHostPermissions: string[];
  };
};

export type ExtensionTarget = keyof typeof targetRegistry.targetConfigs;
export type RuntimeExtensionTarget = ExtensionTarget | "all";

const registry = targetRegistry as ExtensionTargetRegistry;

export const EXTENSION_TARGETS = registry.targets;
export const EXTENSION_TARGET_CONFIGS = registry.targetConfigs;

export const AMAZON_HOST_MATCHES = EXTENSION_TARGET_CONFIGS.amazon.contentMatches;
export const REDDIT_HOST_MATCHES = EXTENSION_TARGET_CONFIGS.reddit.contentMatches;

const EXTENSION_TARGET_SET = new Set<string>(EXTENSION_TARGETS);

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
  return typeof value === "string" && EXTENSION_TARGET_SET.has(value);
}

export function targetSupportsPlatform(
  target: RuntimeExtensionTarget,
  platform: Platform
): boolean {
  return target === "all" || extensionTargetConfig(target).platform === platform;
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
