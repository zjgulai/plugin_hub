import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Popup } from "../src/popup/Popup";
import {
  API_BASE_URL_STORAGE_KEY,
  API_KEY_STORAGE_KEY,
  PENDING_UPLOAD_STORAGE_KEY
} from "../src/lib/settings";

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("Popup settings readiness", () => {
  let rootElement: HTMLDivElement;
  let root: Root;
  let resolveApiKey: (value: Record<string, string>) => void;
  let rejectApiKey: (reason?: unknown) => void;
  let storedPendingUpload: unknown;

  beforeEach(() => {
    storedPendingUpload = undefined;
    const apiKeyPromise = new Promise<Record<string, string>>((resolve, reject) => {
      resolveApiKey = resolve;
      rejectApiKey = reject;
    });

    vi.stubGlobal("chrome", {
      storage: {
        local: {
          get: vi.fn((key: string) => {
            if (key === API_BASE_URL_STORAGE_KEY) {
              return Promise.resolve({
                [key]: "https://plugin.lute-tlz-dddd.top"
              });
            }
            if (key === API_KEY_STORAGE_KEY) {
              return apiKeyPromise;
            }
            return Promise.resolve({});
          }),
          set: vi.fn(async () => undefined)
        },
        session: {
          get: vi.fn(async () => ({
            [PENDING_UPLOAD_STORAGE_KEY]: storedPendingUpload
          })),
          set: vi.fn(async () => undefined),
          remove: vi.fn(async () => undefined)
        }
      },
      runtime: {
        sendMessage: vi.fn()
      },
      tabs: {
        query: vi.fn(),
        sendMessage: vi.fn()
      }
    });

    rootElement = document.createElement("div");
    document.body.append(rootElement);
    root = createRoot(rootElement);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    rootElement.remove();
    vi.unstubAllGlobals();
  });

  it("keeps submission disabled until the stored API key has finished restoring", async () => {
    await act(async () => {
      root.render(<Popup />);
    });

    const submitButton = rootElement.querySelector<HTMLButtonElement>("button[type='submit']");
    const apiKeyInput = rootElement.querySelector<HTMLInputElement>("#api-key");

    expect(submitButton?.disabled).toBe(true);
    expect(submitButton?.textContent).toBe("正在恢复设置…");
    expect(apiKeyInput?.disabled).toBe(true);

    await act(async () => {
      resolveApiKey({ [API_KEY_STORAGE_KEY]: "k".repeat(32) });
      await Promise.resolve();
    });

    expect(apiKeyInput?.value).toBe("k".repeat(32));
    expect(apiKeyInput?.disabled).toBe(false);
    expect(submitButton?.disabled).toBe(false);
    expect(submitButton?.textContent).toBe("采集并回传");
    expect(chrome.storage.local.set).not.toHaveBeenCalled();
  });

  it("fails closed after a key restore error but allows explicit manual recovery", async () => {
    await act(async () => {
      root.render(<Popup />);
    });

    await act(async () => {
      rejectApiKey(new Error("api_key_restore_failed"));
      await Promise.resolve();
    });

    const submitButton = rootElement.querySelector<HTMLButtonElement>("button[type='submit']");
    const apiKeyInput = rootElement.querySelector<HTMLInputElement>("#api-key");

    expect(rootElement.textContent).toContain("api_key_restore_failed");
    expect(apiKeyInput?.disabled).toBe(false);
    expect(submitButton?.disabled).toBe(true);
    expect(submitButton?.textContent).toBe("请输入 API Key");

    await act(async () => {
      if (apiKeyInput) {
        const setNativeValue = Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype,
          "value"
        )?.set;
        setNativeValue?.call(apiKeyInput, "m".repeat(32));
        apiKeyInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    expect(apiKeyInput?.value).toBe("m".repeat(32));
    expect(submitButton?.disabled).toBe(false);
  });

  it("rejects an empty or whitespace-only API key before persisting or capturing", async () => {
    await act(async () => {
      root.render(<Popup />);
    });

    await act(async () => {
      resolveApiKey({});
      await Promise.resolve();
    });

    const form = rootElement.querySelector<HTMLFormElement>("form");
    const submitButton = rootElement.querySelector<HTMLButtonElement>("button[type='submit']");
    const apiKeyInput = rootElement.querySelector<HTMLInputElement>("#api-key");

    expect(apiKeyInput?.value).toBe("");
    expect(submitButton?.disabled).toBe(true);
    expect(submitButton?.textContent).toBe("请输入 API Key");

    await act(async () => {
      if (apiKeyInput) {
        const setNativeValue = Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype,
          "value"
        )?.set;
        setNativeValue?.call(apiKeyInput, "   ");
        apiKeyInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    expect(submitButton?.disabled).toBe(true);

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await Promise.resolve();
    });

    expect(chrome.storage.local.set).not.toHaveBeenCalled();
    expect(chrome.tabs.query).not.toHaveBeenCalled();
    expect(chrome.runtime.sendMessage).not.toHaveBeenCalled();
  });

  it("allows only one in-flight submission before React renders a busy state", async () => {
    let releaseFirstSave: () => void = () => undefined;
    const firstSave = new Promise<void>((resolve) => {
      releaseFirstSave = resolve;
    });
    const pendingUpload = {
      apiBaseUrl: "https://plugin.lute-tlz-dddd.top",
      capture: {
        payload: { platform: "amazon", items: [] },
        summary: { stop_reason: "completed" }
      }
    };

    vi.mocked(chrome.storage.local.set).mockImplementationOnce(() => firstSave);
    storedPendingUpload = pendingUpload;
    vi.mocked(chrome.runtime.sendMessage).mockResolvedValue({
      collection_run_id: "run-1",
      raw_item_count: 0,
      voc_unit_count: 0
    });

    await act(async () => {
      root.render(<Popup />);
    });
    await act(async () => {
      resolveApiKey({ [API_KEY_STORAGE_KEY]: "k".repeat(32) });
      await Promise.resolve();
    });

    const form = rootElement.querySelector<HTMLFormElement>("form");

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await Promise.resolve();
    });

    expect(chrome.storage.local.set).toHaveBeenCalledTimes(1);

    await act(async () => {
      releaseFirstSave();
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(chrome.runtime.sendMessage).toHaveBeenCalledTimes(1);
  });
});
