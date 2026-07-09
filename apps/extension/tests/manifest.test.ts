import { describe, expect, it } from "vitest";

import { buildManifest } from "../manifest.config";

describe("extension manifest", () => {
  const amazonManifest = buildManifest("amazon");
  const redditManifest = buildManifest("reddit");
  const instagramManifest = buildManifest("instagram");

  it("declares install and toolbar icons", () => {
    expect(amazonManifest.icons).toEqual({
      "16": "icons/amazon/icon-16.png",
      "32": "icons/amazon/icon-32.png",
      "48": "icons/amazon/icon-48.png",
      "128": "icons/amazon/icon-128.png"
    });
    expect(redditManifest.icons).toEqual({
      "16": "icons/reddit/icon-16.png",
      "32": "icons/reddit/icon-32.png",
      "48": "icons/reddit/icon-48.png",
      "128": "icons/reddit/icon-128.png"
    });
    expect(instagramManifest.icons).toEqual({
      "16": "icons/instagram/icon-16.png",
      "32": "icons/instagram/icon-32.png",
      "48": "icons/instagram/icon-48.png",
      "128": "icons/instagram/icon-128.png"
    });
    expect(redditManifest.icons).not.toEqual(amazonManifest.icons);
    expect(instagramManifest.icons).not.toEqual(amazonManifest.icons);
    expect(instagramManifest.icons).not.toEqual(redditManifest.icons);
    expect(amazonManifest.action?.default_icon).toEqual(amazonManifest.icons);
    expect(redditManifest.action?.default_icon).toEqual(redditManifest.icons);
    expect(instagramManifest.action?.default_icon).toEqual(instagramManifest.icons);
  });

  it("allows local API hosts without pinning a single port", () => {
    for (const manifest of [amazonManifest, redditManifest, instagramManifest]) {
      expect(manifest.host_permissions).toContain("http://localhost/*");
      expect(manifest.host_permissions).toContain("http://127.0.0.1/*");
      expect(manifest.host_permissions).not.toContain("http://localhost:8000/*");
    }
  });

  it("allows the production Plugin Hub API host", () => {
    for (const manifest of [amazonManifest, redditManifest, instagramManifest]) {
      expect(manifest.host_permissions).toContain("https://plugin.lute-tlz-dddd.top/*");
    }
  });

  it("keeps permissions scoped to the implemented browser APIs", () => {
    expect(amazonManifest.permissions).toEqual(["activeTab", "storage"]);
    expect(redditManifest.permissions).toEqual(["activeTab", "storage"]);
    expect(instagramManifest.permissions).toEqual(["activeTab", "storage"]);
  });

  it("builds an Amazon-only extension manifest", () => {
    expect(amazonManifest.name).toBe("Plugin Hub Amazon VOC Collector");
    expect(amazonManifest.host_permissions).toContain("https://www.amazon.com/*");
    expect(amazonManifest.host_permissions).not.toContain("https://www.reddit.com/*");
    expect(amazonManifest.host_permissions).not.toContain("https://www.instagram.com/*");
    expect(amazonManifest.content_scripts?.[0]?.matches).toContain("https://www.amazon.com/*");
    expect(amazonManifest.content_scripts?.[0]?.matches).not.toContain("https://www.reddit.com/*");
    expect(amazonManifest.content_scripts?.[0]?.matches).not.toContain("https://www.instagram.com/*");
  });

  it("builds a Reddit-only extension manifest", () => {
    expect(redditManifest.name).toBe("Plugin Hub Reddit VOC Collector");
    expect(redditManifest.host_permissions).toContain("https://www.reddit.com/*");
    expect(redditManifest.host_permissions).not.toContain("https://www.amazon.com/*");
    expect(redditManifest.host_permissions).not.toContain("https://www.instagram.com/*");
    expect(redditManifest.content_scripts?.[0]?.matches).toContain("https://www.reddit.com/*");
    expect(redditManifest.content_scripts?.[0]?.matches).not.toContain("https://www.amazon.com/*");
    expect(redditManifest.content_scripts?.[0]?.matches).not.toContain("https://www.instagram.com/*");
  });

  it("builds an Instagram-only extension manifest", () => {
    expect(instagramManifest.name).toBe("Plugin Hub Instagram VOC Collector");
    expect(instagramManifest.host_permissions).toContain("https://www.instagram.com/*");
    expect(instagramManifest.host_permissions).not.toContain("https://www.amazon.com/*");
    expect(instagramManifest.host_permissions).not.toContain("https://www.reddit.com/*");
    expect(instagramManifest.content_scripts?.[0]?.matches).toContain("https://www.instagram.com/*");
    expect(instagramManifest.content_scripts?.[0]?.matches).not.toContain("https://www.amazon.com/*");
    expect(instagramManifest.content_scripts?.[0]?.matches).not.toContain("https://www.reddit.com/*");
  });
});
