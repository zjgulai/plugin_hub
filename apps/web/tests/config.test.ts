import { describe, expect, it } from "vitest";

import { loadDashboardConfig } from "../src/lib/config";

describe("loadDashboardConfig", () => {
  it("loads dashboard parameters from environment values", () => {
    expect(
      loadDashboardConfig({
        PLUGIN_HUB_API_URL: "http://127.0.0.1:8010",
        PLUGIN_HUB_SITE_ENV: "staging",
        PLUGIN_HUB_REFRESH_SECONDS: "15",
        PLUGIN_HUB_ENABLED_PLATFORMS: "amazon,reddit,amazon",
        PLUGIN_HUB_AMAZON_PAGE_LIMIT: "5",
        PLUGIN_HUB_LOW_CONFIDENCE_THRESHOLD: "0.65"
      })
    ).toEqual({
      apiBaseUrl: "http://127.0.0.1:8010",
      siteEnv: "staging",
      refreshSeconds: 15,
      enabledPlatforms: ["amazon", "reddit"],
      amazonPageLimit: 5,
      lowConfidenceThreshold: 0.65
    });
  });

  it("uses stable defaults for invalid or missing values", () => {
    expect(
      loadDashboardConfig({
        PLUGIN_HUB_API_URL: " ",
        PLUGIN_HUB_REFRESH_SECONDS: "0",
        PLUGIN_HUB_ENABLED_PLATFORMS: "shopify,tiktok",
        PLUGIN_HUB_AMAZON_PAGE_LIMIT: "-1",
        PLUGIN_HUB_LOW_CONFIDENCE_THRESHOLD: "2"
      })
    ).toEqual({
      apiBaseUrl: "http://localhost:8000",
      siteEnv: "local",
      refreshSeconds: 30,
      enabledPlatforms: ["amazon", "reddit"],
      amazonPageLimit: 3,
      lowConfidenceThreshold: 0.7
    });
  });
});
