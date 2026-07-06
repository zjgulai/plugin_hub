import type { CaptureRuntimeSettings } from "./capture-types";
import type { PlatformSettingResult } from "../types/contracts";

export function amazonRuntimeSettingsFromPlatformSetting(
  setting: PlatformSettingResult
): CaptureRuntimeSettings | undefined {
  if (setting.platform !== "amazon") {
    return undefined;
  }
  if (!setting.enabled) {
    throw new Error("platform_disabled_by_settings");
  }

  const pageLimit = configInteger(setting.config.page_limit, {
    minimum: 1,
    maximum: 20
  });
  return {
    amazonPageLimit: pageLimit ?? undefined,
    platformSettingEnabled: setting.enabled,
    platformSettingSource: setting.source,
    platformSettingUpdatedAt: setting.updated_at
  };
}

function configInteger(
  value: unknown,
  {
    minimum,
    maximum
  }: {
    minimum: number;
    maximum: number;
  }
): number | null {
  return typeof value === "number" &&
    Number.isInteger(value) &&
    value >= minimum &&
    value <= maximum
    ? value
    : null;
}
