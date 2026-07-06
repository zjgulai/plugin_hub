export interface CaptureRuntimeSettings {
  amazonPageLimit?: number;
  platformSettingEnabled?: boolean;
  platformSettingSource?: string;
  platformSettingUpdatedAt?: string;
}

export interface CaptureCurrentPageInput {
  url: string;
  capturedAt?: string;
  documentRoot?: ParentNode;
  fetchText?: (url: string) => Promise<string>;
  fetchJson?: (url: string) => Promise<unknown>;
  parseHtml?: (html: string) => ParentNode;
  runtimeSettings?: CaptureRuntimeSettings;
}
