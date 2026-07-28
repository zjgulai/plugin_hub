import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE_URL_STORAGE_KEY,
  API_KEY_STORAGE_KEY
} from "../src/lib/settings";
import { GET_PLATFORM_SETTING_MESSAGE_TYPE } from "../src/types/messages";

type RuntimeMessageListener = (
  message: unknown,
  sender: chrome.runtime.MessageSender,
  sendResponse: (response: unknown) => void
) => boolean | undefined;

const EXTENSION_ID = "plugin-hub-test-extension";
const API_KEY = "k".repeat(32);
const PLATFORM_SETTING_RESPONSE = {
  platform: "amazon",
  enabled: true,
  config: {},
  updated_at: "2026-07-28T00:00:00Z",
  updated_by: "test",
  source: "test"
};

describe("background service worker credential boundary", () => {
  let listener: RuntimeMessageListener;
  let storageGet: ReturnType<typeof vi.fn>;
  let fetcher: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.resetModules();
    storageGet = vi.fn(async (key: string) => {
      if (key === API_BASE_URL_STORAGE_KEY) {
        return { [key]: "https://plugin.lute-tlz-dddd.top" };
      }
      if (key === API_KEY_STORAGE_KEY) {
        return { [key]: API_KEY };
      }
      return {};
    });
    fetcher = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => PLATFORM_SETTING_RESPONSE
    }));

    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("chrome", {
      storage: {
        local: {
          get: storageGet
        }
      },
      runtime: {
        id: EXTENSION_ID,
        onMessage: {
          addListener: vi.fn((registeredListener: RuntimeMessageListener) => {
            listener = registeredListener;
          })
        }
      }
    });

    await import("../src/background/service-worker");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ignores a legacy message target and uses the trusted stored API origin", async () => {
    const response = await invokeAsync({
      type: GET_PLATFORM_SETTING_MESSAGE_TYPE,
      platform: "amazon",
      apiBaseUrl: "https://www.amazon.com"
    });

    expect(response).toEqual(PLATFORM_SETTING_RESPONSE);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith(
      "https://plugin.lute-tlz-dddd.top/api/platform-settings/amazon",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Plugin-Hub-Api-Key": API_KEY
        })
      })
    );
    expect(fetcher).not.toHaveBeenCalledWith(
      expect.stringContaining("amazon.com"),
      expect.anything()
    );
  });

  it("rejects a poisoned stored source-site target before reading the API key", async () => {
    storageGet.mockImplementation(async (key: string) => {
      if (key === API_BASE_URL_STORAGE_KEY) {
        return { [key]: "https://www.amazon.com" };
      }
      if (key === API_KEY_STORAGE_KEY) {
        return { [key]: API_KEY };
      }
      return {};
    });

    await expect(invokeAsync(validMessage())).resolves.toEqual({
      error: "api_base_url_untrusted"
    });
    expect(storageGet).toHaveBeenCalledTimes(1);
    expect(storageGet).toHaveBeenCalledWith(API_BASE_URL_STORAGE_KEY);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("rejects an unrelated sender before reading settings or credentials", () => {
    let response: unknown;
    const keepChannelOpen = listener(
      validMessage(),
      {
        id: EXTENSION_ID,
        url: "https://evil.example/attack",
        tab: { id: 9, url: "https://evil.example/attack" } as chrome.tabs.Tab
      },
      (value) => {
        response = value;
      }
    );

    expect(keepChannelOpen).toBe(false);
    expect(response).toEqual({ error: "runtime_message_sender_untrusted" });
    expect(storageGet).not.toHaveBeenCalled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("accepts a content-script sender only on the packaged target's source origins", async () => {
    const response = await invokeAsync(validMessage(), {
      id: EXTENSION_ID,
      url: "https://www.amazon.com/dp/B08MHGST8X",
      tab: {
        id: 11,
        url: "https://www.amazon.com/dp/B08MHGST8X"
      } as chrome.tabs.Tab
    });

    expect(response).toEqual(PLATFORM_SETTING_RESPONSE);
    expect(fetcher).toHaveBeenCalledWith(
      "https://plugin.lute-tlz-dddd.top/api/platform-settings/amazon",
      expect.anything()
    );
  });

  function invokeAsync(
    message: unknown,
    sender: chrome.runtime.MessageSender = {
      id: EXTENSION_ID,
      url: `chrome-extension://${EXTENSION_ID}/popup/index.html`
    }
  ): Promise<unknown> {
    return new Promise((resolve) => {
      const keepChannelOpen = listener(
        message,
        sender,
        resolve
      );
      expect(keepChannelOpen).toBe(true);
    });
  }
});

function validMessage() {
  return {
    type: GET_PLATFORM_SETTING_MESSAGE_TYPE,
    platform: "amazon"
  };
}
