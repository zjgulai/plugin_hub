import { captureAmazonCurrentPage } from "../lib/amazon-capture";
import { detectAmazonPageUrl } from "../lib/page-detect";
import { mountContentScript } from "./content-script-runtime";

mountContentScript({
  detectPage: detectAmazonPageUrl,
  captureCurrentPage: captureAmazonCurrentPage
});
