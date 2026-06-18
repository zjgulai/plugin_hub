export interface CaptureCurrentPageInput {
  url: string;
  capturedAt?: string;
  documentRoot?: ParentNode;
  fetchText?: (url: string) => Promise<string>;
  fetchJson?: (url: string) => Promise<unknown>;
  parseHtml?: (html: string) => ParentNode;
}
