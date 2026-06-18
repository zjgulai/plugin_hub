import { captureCurrentPage } from "../lib/capture";
import { detectPage } from "../lib/page-detect";
import { mountContentScript } from "./content-script-runtime";

mountContentScript({
  detectPage,
  captureCurrentPage
});
