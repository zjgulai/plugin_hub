import { describe, expect, it } from "vitest";

import { buildManifest } from "../manifest.config";

describe("extension manifest", () => {
  const amazonManifest = buildManifest("amazon");
  const redditManifest = buildManifest("reddit");

  it("declares install and toolbar icons", () => {
    expect(amazonManifest.icons).toEqual({
      "16": "icons/icon-16.png",
      "32": "icons/icon-32.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    });
    expect(redditManifest.icons).toEqual(amazonManifest.icons);
    expect(amazonManifest.action?.default_icon).toEqual(amazonManifest.icons);
    expect(redditManifest.action?.default_icon).toEqual(redditManifest.icons);
  });

  it("allows local API hosts without pinning a single port", () => {
    for (const manifest of [amazonManifest, redditManifest]) {
      expect(manifest.host_permissions).toContain("http://localhost/*");
      expect(manifest.host_permissions).toContain("http://127.0.0.1/*");
      expect(manifest.host_permissions).not.toContain("http://localhost:8000/*");
    }
  });

  it("keeps permissions scoped to the implemented browser APIs", () => {
    expect(amazonManifest.permissions).toEqual(["activeTab", "storage"]);
    expect(redditManifest.permissions).toEqual(["activeTab", "storage"]);
  });

  it("builds an Amazon-only extension manifest", () => {
    expect(amazonManifest.name).toBe("Plugin Hub Amazon VOC Collector");
    expect(amazonManifest.host_permissions).toContain("https://www.amazon.com/*");
    expect(amazonManifest.host_permissions).not.toContain("https://www.reddit.com/*");
    expect(amazonManifest.content_scripts?.[0]?.matches).toContain("https://www.amazon.com/*");
    expect(amazonManifest.content_scripts?.[0]?.matches).not.toContain("https://www.reddit.com/*");
  });

  it("builds a Reddit-only extension manifest", () => {
    expect(redditManifest.name).toBe("Plugin Hub Reddit VOC Collector");
    expect(redditManifest.host_permissions).toContain("https://www.reddit.com/*");
    expect(redditManifest.host_permissions).not.toContain("https://www.amazon.com/*");
    expect(redditManifest.content_scripts?.[0]?.matches).toContain("https://www.reddit.com/*");
    expect(redditManifest.content_scripts?.[0]?.matches).not.toContain("https://www.amazon.com/*");
  });
});
