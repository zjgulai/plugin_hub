import { captureAmazonCurrentPage, inferMarketplace } from "./amazon-capture";
import type { CaptureCurrentPageInput } from "./capture-types";
import {
  type RuntimeExtensionTarget,
  normalizeRuntimeExtensionTarget,
  targetSupportsPlatform
} from "./extension-target";
import { detectPage } from "./page-detect";
import { buildRedditJsonUrl, captureRedditCurrentPage } from "./reddit-capture";
import type { CaptureCurrentPageSuccess } from "../types/messages";

export type { CaptureCurrentPageInput } from "./capture-types";
export { buildRedditJsonUrl, inferMarketplace };

export async function captureCurrentPage(
  input: CaptureCurrentPageInput & { target?: RuntimeExtensionTarget }
): Promise<CaptureCurrentPageSuccess> {
  const target = normalizeRuntimeExtensionTarget(input.target);
  const detectedPage = detectPage(input.url);

  if (detectedPage.platform === "unknown") {
    throw new Error("unsupported_page");
  }

  if (!targetSupportsPlatform(target, detectedPage.platform)) {
    throw new Error("unsupported_page");
  }

  if (detectedPage.platform === "amazon") {
    return captureAmazonCurrentPage(input);
  }

  if (detectedPage.platform === "reddit") {
    return captureRedditCurrentPage(input);
  }

  throw new Error("instagram_capture_requires_authorized_backend");
}
