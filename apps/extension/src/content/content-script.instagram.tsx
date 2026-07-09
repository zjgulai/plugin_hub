import { detectInstagramMediaPageUrl } from "../lib/page-detect";
import type { CaptureCurrentPageSuccess } from "../types/messages";
import { mountContentScript } from "./content-script-runtime";

mountContentScript({
  detectPage: detectInstagramMediaPageUrl,
  captureCurrentPage: captureInstagramCurrentPage
});

function captureInstagramCurrentPage(): Promise<CaptureCurrentPageSuccess> {
  return Promise.reject(new Error("instagram_capture_requires_authorized_backend"));
}
