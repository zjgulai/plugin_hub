import { detectRedditThreadPageUrl } from "../lib/page-detect";
import { captureRedditCurrentPage } from "../lib/reddit-capture";
import { mountContentScript } from "./content-script-runtime";

mountContentScript({
  detectPage: detectRedditThreadPageUrl,
  captureCurrentPage: captureRedditCurrentPage
});
