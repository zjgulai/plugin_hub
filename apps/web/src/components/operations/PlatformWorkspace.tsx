import type {
  CaptureCapability,
  CollectionTask,
  PlatformSetting,
  PlatformSettingAuditEvent,
  VocPlatform,
  VocUnit
} from "../../lib/api";
import type { DashboardConfig } from "../../lib/config";
import { PlatformSettingSubmitButton } from "./PlatformSettingSubmitButton";

type PlatformWorkspaceProps = {
  units: VocUnit[];
  platformUnitCounts: Record<VocPlatform, number> | null;
  tasks: CollectionTask[];
  capabilities: CaptureCapability[];
  platformSettings: PlatformSetting[];
  platformSettingAuditEvents: PlatformSettingAuditEvent[];
  platformSettingsError: string | null;
  platformSettingAuditError: string | null;
  platformSettingsStatus: PlatformSettingsStatus | null;
  config: DashboardConfig;
  updatePlatformSettingAction: (formData: FormData) => Promise<void>;
};

type PlatformStage = "active" | "gated" | "planned" | "deferred";
type PlatformTone = "amazon" | "reddit" | "instagram" | "facebook" | "neutral";
type PlatformSettingsStatus = {
  tone: "success" | "error";
  title: string;
  detail: string;
  platform: VocPlatform | null;
};

type ActivePlatformDefinition = {
  platform: VocPlatform;
  title: string;
  subtitle: string;
  packageName: string;
  primaryObject: string;
  capturePath: string;
};

type PlannedPlatformDefinition = {
  platform: "facebook" | "tiktok" | "shopify";
  title: string;
  stage: PlatformStage;
  dataSource: string;
  blocker: string;
  plannedConfig: string[];
};

const ACTIVE_PLATFORMS: ActivePlatformDefinition[] = [
  {
    platform: "amazon",
    title: "Amazon Reviews",
    subtitle: "评论页翻页、覆盖率和 extension package 状态",
    packageName: "plugin-hub-amazon-voc",
    primaryObject: "ASIN / marketplace",
    capturePath: "extension_dom_next_link_walk"
  },
  {
    platform: "reddit",
    title: "Reddit Threads",
    subtitle: ".json proxy、OAuth readiness 和补采队列",
    packageName: "plugin-hub-reddit-voc",
    primaryObject: "thread / subreddit",
    capturePath: "server_reddit_json_proxy"
  },
  {
    platform: "instagram",
    title: "Instagram Media",
    subtitle: "Graph live-read gate、fixture path 和授权上下文",
    packageName: "plugin-hub-instagram-voc",
    primaryObject: "media_id / shortcode",
    capturePath: "server_instagram_graph_comments"
  }
];

const PLANNED_PLATFORMS: PlannedPlatformDefinition[] = [
  {
    platform: "facebook",
    title: "Facebook Page Comments",
    stage: "planned",
    dataSource: "Page post comments through approved Graph permissions",
    blocker: "Page ownership, App Review and read-only authorization path",
    plannedConfig: ["page_id", "graph_api_version", "comment_limit", "permission_checklist"]
  },
  {
    platform: "tiktok",
    title: "TikTok Comments",
    stage: "deferred",
    dataSource: "Public comment access requires separate platform review",
    blocker: "Compliance and official data-access path not selected",
    plannedConfig: ["video_url", "creator_handle", "comment_limit", "access_policy"]
  },
  {
    platform: "shopify",
    title: "Shopify Storefront Reviews",
    stage: "deferred",
    dataSource: "Storefront review app exports or authorized merchant API",
    blocker: "Review provider and merchant authorization model not fixed",
    plannedConfig: ["store_domain", "review_provider", "import_mode", "sync_window"]
  }
];

export function PlatformWorkspace({
  units,
  platformUnitCounts,
  tasks,
  capabilities,
  platformSettings,
  platformSettingAuditEvents,
  platformSettingsError,
  platformSettingAuditError,
  platformSettingsStatus,
  config,
  updatePlatformSettingAction
}: PlatformWorkspaceProps) {
  const settingsByPlatform = new Map(
    platformSettings.map((setting) => [setting.platform, setting])
  );
  const activeCards = ACTIVE_PLATFORMS.map((definition) =>
    buildPlatformCard(
      definition,
      units,
      platformUnitCounts,
      tasks,
      capabilities,
      settingsByPlatform.get(definition.platform),
      platformSettingAuditEvents.filter((event) => event.platform === definition.platform),
      config
    )
  );

  return (
    <section className="platformWorkspace" aria-label="平台插件运营工作台">
      <div className="platformWorkspace__header">
        <div>
          <p className="panelKicker">Platform Operations</p>
          <h2>平台插件监控</h2>
        </div>
        <p>
          每个平台保留独立采集路径、配置状态和授权边界，统一写入 Canonical VOC。
        </p>
      </div>
      {platformSettingsStatus ? (
        <div
          className={`platformSettingsNotice platformSettingsNotice--${platformSettingsStatus.tone}`}
          role={platformSettingsStatus.tone === "error" ? "alert" : "status"}
          aria-live={platformSettingsStatus.tone === "error" ? "assertive" : "polite"}
        >
          <strong>{platformSettingsStatus.title}</strong>
          <span>{platformSettingsStatus.detail}</span>
        </div>
      ) : null}
      {platformSettingsError ? (
        <div className="platformSettingsNotice platformSettingsNotice--error" role="alert">
          <strong>配置接口未连接</strong>
          <span>{platformSettingsError}</span>
        </div>
      ) : null}
      {platformSettingAuditError ? (
        <div className="platformSettingsNotice platformSettingsNotice--error" role="alert">
          <strong>审计接口未连接</strong>
          <span>{platformSettingAuditError}</span>
        </div>
      ) : null}

      <nav className="platformNav" aria-label="平台插件导航">
        {activeCards.map((card) => (
          <a
            href={`#platform-${card.platform}`}
            key={card.platform}
            className={`platformNavItem platformNavItem--${card.tone}`}
          >
            <span>{card.title}</span>
            <strong>{card.stageLabel}</strong>
          </a>
        ))}
        {PLANNED_PLATFORMS.map((platform) => (
          <a
            href={`#platform-${platform.platform}`}
            key={platform.platform}
            className={`platformNavItem platformNavItem--${platform.platform === "facebook" ? "facebook" : "neutral"}`}
          >
            <span>{platform.title}</span>
            <strong>{stageLabel(platform.stage)}</strong>
          </a>
        ))}
      </nav>

      <div className="platformConsoleGrid">
        {activeCards.map((card) => {
          const recentlySaved =
            platformSettingsStatus?.tone === "success" &&
            platformSettingsStatus.platform === card.platform;

          return (
            <article
              id={`platform-${card.platform}`}
              key={card.platform}
              className={`platformConsole platformConsole--${card.tone}${
                recentlySaved ? " platformConsole--saved" : ""
              }`}
            >
              <div className="platformConsole__header">
                <div>
                  <div className="platformConsole__statusRow">
                    <span className={`platformStatus platformStatus--${card.stage}`}>
                      {card.stageLabel}
                    </span>
                    {recentlySaved ? <span className="platformSavedPill">just saved</span> : null}
                  </div>
                  <h3>{card.title}</h3>
                  <p>{card.subtitle}</p>
                </div>
                <strong>{card.packageName}</strong>
              </div>

              <div className="platformMetricGrid">
                <PlatformMetric label="VOC Units" value={card.unitCount} detail={card.unitDetail} />
                <PlatformMetric label="Queue" value={card.queueCount} detail={card.queueDetail} />
                <PlatformMetric label="Quality" value={card.qualityCount} detail={card.qualityDetail} />
                <PlatformMetric label="Freshness" value={card.latestLabel} detail="latest captured" />
              </div>

              <div className="platformConsole__body">
                <section className="platformSubpanel">
                  <h4>采集监控</h4>
                  <dl className="platformFactList">
                    <FactRow label="Primary Object" value={card.primaryObject} />
                    <FactRow label="Capture Path" value={card.capturePath} />
                    <FactRow label="Capability" value={card.capabilityLabel} />
                    <FactRow label="Package" value={card.packageName} />
                    <FactRow label="Recent Object" value={card.recentObject} />
                  </dl>
                  <p className={`platformCapabilityNote platformCapabilityNote--${card.capabilityTone}`}>
                    {card.capabilityNote}
                  </p>
                </section>

                <section className="platformSubpanel">
                  <h4>配置项</h4>
                  <PlatformSettingForm
                    card={card}
                    config={config}
                    action={updatePlatformSettingAction}
                  />
                </section>

                <section className="platformSubpanel">
                  <h4>配置审计</h4>
                  <PlatformAuditList events={card.auditEvents} />
                </section>

                <section className="platformSubpanel platformSubpanel--queue">
                  <h4>任务状态</h4>
                  {card.visibleTasks.length === 0 ? (
                    <PlatformEmptyState
                      title="暂无待处理任务"
                      detail="当前队列没有 pending、running 或 retry_scheduled 任务。"
                    />
                  ) : (
                    <ul className="platformTaskList">
                      {card.visibleTasks.map((task) => (
                        <li key={task.collection_task_id}>
                          <span className={`taskStatus taskStatus--${task.status}`}>
                            {task.status}
                          </span>
                          <strong>{taskObjectLabel(task)}</strong>
                          <small>{task.requested_capture_method}</small>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            </article>
          );
        })}
      </div>

      <section className="platformRoadmap" aria-label="PRD 平台规划">
        <div className="sectionMiniHeading">
          <p className="panelKicker">Roadmap</p>
          <h2>PRD 平台预设计</h2>
        </div>
        <div className="roadmapGrid">
          {PLANNED_PLATFORMS.map((platform) => (
            <article
              id={`platform-${platform.platform}`}
              key={platform.platform}
              className={`roadmapCard roadmapCard--${platform.platform}`}
            >
              <div className="roadmapCard__header">
                <span className={`platformStatus platformStatus--${platform.stage}`}>
                  {stageLabel(platform.stage)}
                </span>
                <h3>{platform.title}</h3>
              </div>
              <dl className="platformFactList">
                <FactRow label="Data Source" value={platform.dataSource} />
                <FactRow label="Gate" value={platform.blocker} />
              </dl>
              <ul className="roadmapConfigList">
                {platform.plannedConfig.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function buildPlatformCard(
  definition: ActivePlatformDefinition,
  units: VocUnit[],
  platformUnitCounts: Record<VocPlatform, number> | null,
  tasks: CollectionTask[],
  capabilities: CaptureCapability[],
  setting: PlatformSetting | undefined,
  auditEvents: PlatformSettingAuditEvent[],
  config: DashboardConfig
) {
  const platformUnits = units.filter((unit) => unit.platform === definition.platform);
  const platformTasks = tasks.filter((task) => task.platform === definition.platform);
  const lowConfidenceCount = platformUnits.filter(
    (unit) => unit.coverage_confidence < config.lowConfidenceThreshold
  ).length;
  const flaggedCount = platformUnits.filter((unit) => unit.quality_flags.length > 0).length;
  const capability = primaryCapability(definition.platform, capabilities);
  const latestCapturedAt = latestDate(platformUnits.map((unit) => unit.captured_at));
  const enabled = setting?.enabled ?? config.enabledPlatforms.includes(definition.platform);
  const gated = definition.platform === "instagram" && capability?.status !== "ready";
  const stage: PlatformStage = enabled ? (gated ? "gated" : "active") : "deferred";
  const capabilityLabel = capability ? capabilityStatusLabel(capability) : "not reported";
  const capabilityTone = capabilityToneFor(capability);

  return {
    ...definition,
    tone: definition.platform as PlatformTone,
    setting,
    auditEvents: auditEvents.slice(0, 3),
    stage,
    stageLabel: stageLabel(stage),
    unitCount: platformUnitCounts?.[definition.platform] ?? platformUnits.length,
    unitDetail: uniqueObjectDetail(definition.platform, platformUnits),
    queueCount: platformTasks.filter((task) => task.status !== "completed").length,
    queueDetail: queueDetail(platformTasks),
    qualityCount: lowConfidenceCount + flaggedCount,
    qualityDetail:
      lowConfidenceCount + flaggedCount === 0
        ? "no review items"
        : `${lowConfidenceCount} low / ${flaggedCount} flagged`,
    latestLabel: latestCapturedAt ? freshnessLabel(latestCapturedAt) : "none",
    capabilityLabel,
    capabilityTone,
    capabilityNote: capabilityNoteFor(definition.platform, capabilityLabel, capability),
    recentObject: recentObjectLabel(definition.platform, platformUnits),
    visibleTasks: platformTasks.slice(0, 3)
  };
}

function PlatformMetric({
  label,
  value,
  detail
}: {
  label: string;
  value: number | string;
  detail: string;
}) {
  return (
    <div className="platformMetric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function PlatformAuditList({ events }: { events: PlatformSettingAuditEvent[] }) {
  if (events.length === 0) {
    return (
      <PlatformEmptyState
        title="暂无配置变更"
        detail="保存配置后，这里会显示变更字段、操作者和时间。"
      />
    );
  }

  return (
    <ul className="platformAuditList">
      {events.map((event) => (
        <li key={event.id}>
          <div className="platformAuditList__header">
            <strong>{event.changed_fields.join(", ")}</strong>
            <span>{event.changed_by}</span>
          </div>
          <AuditChangeList event={event} />
          <time dateTime={event.created_at}>{formatCompactDate(event.created_at)}</time>
        </li>
      ))}
    </ul>
  );
}

function AuditChangeList({ event }: { event: PlatformSettingAuditEvent }) {
  return (
    <dl className="platformAuditChanges" aria-label="配置变更详情">
      {event.changed_fields.map((field) => (
        <div key={field} className="platformAuditChange">
          <dt>{auditFieldLabel(field)}</dt>
          <dd>
            <span>{formatAuditValue(auditValue(event, field, "previous"))}</span>
            <strong>→</strong>
            <span>{formatAuditValue(auditValue(event, field, "new"))}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function PlatformEmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="platformEmptyState">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

function auditValue(
  event: PlatformSettingAuditEvent,
  field: string,
  side: "previous" | "new"
): unknown {
  if (field === "enabled") {
    return side === "previous" ? event.previous_enabled : event.new_enabled;
  }
  if (field.startsWith("config.")) {
    const key = field.slice("config.".length);
    return side === "previous" ? event.previous_config[key] : event.new_config[key];
  }
  return undefined;
}

function auditFieldLabel(field: string): string {
  if (field === "enabled") {
    return "Enabled";
  }
  if (field.startsWith("config.")) {
    return field.slice("config.".length).replaceAll("_", " ");
  }
  return field.replaceAll("_", " ");
}

function formatAuditValue(value: unknown): string {
  if (value === undefined || value === null) {
    return "unset";
  }
  if (typeof value === "boolean") {
    return value ? "enabled" : "disabled";
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return truncateAuditValue(trimmed.length > 0 ? trimmed : "empty");
  }
  if (Array.isArray(value)) {
    return truncateAuditValue(value.map((item) => String(item)).join(", "));
  }
  if (typeof value === "object") {
    return truncateAuditValue(JSON.stringify(value));
  }
  return "unsupported";
}

function truncateAuditValue(value: string): string {
  return value.length > 72 ? `${value.slice(0, 69)}...` : value;
}

function PlatformSettingForm({
  card,
  config,
  action
}: {
  card: ReturnType<typeof buildPlatformCard>;
  config: DashboardConfig;
  action: (formData: FormData) => Promise<void>;
}) {
  const values = platformSettingValues(card, config);

  return (
    <form
      action={action}
      className="platformSettingsForm"
      aria-label={`${card.title} 配置表单`}
    >
      <input type="hidden" name="platform" value={card.platform} />
      <label className="platformConfigField platformConfigField--toggle">
        <span>Enabled</span>
        <input name="enabled" type="checkbox" defaultChecked={values.enabled} />
        <strong>{values.enabled ? "enabled" : "disabled"}</strong>
      </label>
      {card.platform === "amazon" ? (
        <>
          <NumberField
            label="Page Budget"
            name="page_limit"
            min={1}
            max={20}
            defaultValue={values.pageLimit}
          />
          <TextField
            label="Markets"
            name="marketplaces"
            autoComplete="off"
            spellCheck={false}
            defaultValue={values.marketplaces.join(", ")}
          />
        </>
      ) : null}
      {card.platform === "reddit" ? (
        <>
          <label className="platformConfigField platformConfigField--toggle">
            <span>JSON Proxy</span>
            <input
              name="json_proxy_enabled"
              type="checkbox"
              defaultChecked={values.jsonProxyEnabled}
            />
            <strong>{values.jsonProxyEnabled ? "enabled" : "disabled"}</strong>
          </label>
          <NumberField
            label="Max Depth"
            name="max_comment_depth"
            min={0}
            max={10}
            defaultValue={values.maxCommentDepth}
          />
        </>
      ) : null}
      {card.platform === "instagram" ? (
        <>
          <label className="platformConfigField platformConfigField--toggle">
            <span>Fixture Mode</span>
            <input
              name="fixture_mode_enabled"
              type="checkbox"
              defaultChecked={values.fixtureModeEnabled}
            />
            <strong>{values.fixtureModeEnabled ? "enabled" : "disabled"}</strong>
          </label>
          <TextField
            label="Graph Version"
            name="graph_api_version"
            autoComplete="off"
            spellCheck={false}
            defaultValue={values.graphApiVersion}
          />
          <NumberField
            label="Comment Limit"
            name="comment_limit"
            min={1}
            max={100}
            defaultValue={values.commentLimit}
          />
        </>
      ) : null}
      <label className="platformConfigField platformConfigField--wide">
        <span>Notes</span>
        <textarea
          name="notes"
          rows={2}
          maxLength={240}
          autoComplete="off"
          defaultValue={values.notes}
        />
      </label>
      <PlatformConfigSummary card={card} values={values} />
      <div className="platformSettingsForm__footer">
        <small>
          {values.source} · {values.updatedBy} · {values.updatedAt}
        </small>
        <PlatformSettingSubmitButton label={`保存 ${card.title} 配置`} />
      </div>
    </form>
  );
}

function PlatformConfigSummary({
  card,
  values
}: {
  card: ReturnType<typeof buildPlatformCard>;
  values: ReturnType<typeof platformSettingValues>;
}) {
  return (
    <dl className="platformConfigSummary" aria-label={`${card.title} 当前配置摘要`}>
      <SummaryItem label="状态" value={values.enabled ? "enabled" : "disabled"} />
      {card.platform === "amazon" ? (
        <>
          <SummaryItem label="页预算" value={String(values.pageLimit)} />
          <SummaryItem label="市场" value={values.marketplaces.join(", ")} />
        </>
      ) : null}
      {card.platform === "reddit" ? (
        <>
          <SummaryItem label="JSON Proxy" value={values.jsonProxyEnabled ? "enabled" : "disabled"} />
          <SummaryItem label="深度" value={String(values.maxCommentDepth)} />
        </>
      ) : null}
      {card.platform === "instagram" ? (
        <>
          <SummaryItem
            label="Fixture"
            value={values.fixtureModeEnabled ? "enabled" : "disabled"}
          />
          <SummaryItem label="Graph" value={values.graphApiVersion} />
          <SummaryItem label="评论上限" value={String(values.commentLimit)} />
        </>
      ) : null}
    </dl>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function NumberField({
  label,
  name,
  min,
  max,
  defaultValue
}: {
  label: string;
  name: string;
  min: number;
  max: number;
  defaultValue: number;
}) {
  return (
    <label className="platformConfigField">
      <span>{label}</span>
      <input
        name={name}
        type="number"
        inputMode="numeric"
        autoComplete="off"
        min={min}
        max={max}
        defaultValue={defaultValue}
      />
    </label>
  );
}

function TextField({
  label,
  name,
  autoComplete = "off",
  spellCheck,
  defaultValue
}: {
  label: string;
  name: string;
  autoComplete?: string;
  spellCheck?: boolean;
  defaultValue: string;
}) {
  return (
    <label className="platformConfigField">
      <span>{label}</span>
      <input
        name={name}
        type="text"
        autoComplete={autoComplete}
        spellCheck={spellCheck}
        defaultValue={defaultValue}
      />
    </label>
  );
}

function platformSettingValues(
  card: ReturnType<typeof buildPlatformCard>,
  config: DashboardConfig
) {
  const settingConfig = card.setting?.config ?? {};
  return {
    enabled: card.setting?.enabled ?? config.enabledPlatforms.includes(card.platform),
    pageLimit: numberConfig(settingConfig.page_limit, config.amazonPageLimit),
    marketplaces: stringListConfig(settingConfig.marketplaces, [
      "US",
      "UK",
      "DE",
      "CA",
      "AU",
      "JP"
    ]),
    jsonProxyEnabled: booleanConfig(settingConfig.json_proxy_enabled, true),
    maxCommentDepth: numberConfig(settingConfig.max_comment_depth, 8),
    fixtureModeEnabled: booleanConfig(settingConfig.fixture_mode_enabled, true),
    graphApiVersion: stringConfig(settingConfig.graph_api_version, "v25.0"),
    commentLimit: numberConfig(settingConfig.comment_limit, 50),
    notes: stringConfig(settingConfig.notes, ""),
    source: card.setting?.source ?? "runtime",
    updatedBy: card.setting?.updated_by ?? "dashboard-runtime",
    updatedAt: card.setting ? formatCompactDate(card.setting.updated_at) : "not stored"
  };
}

function numberConfig(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function booleanConfig(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function stringConfig(value: unknown, fallback: string): string {
  return typeof value === "string" ? value : fallback;
}

function stringListConfig(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) {
    return fallback;
  }

  const strings = value.filter((item): item is string => typeof item === "string");
  return strings.length > 0 ? strings : fallback;
}

function primaryCapability(
  platform: VocPlatform,
  capabilities: CaptureCapability[]
): CaptureCapability | undefined {
  if (platform === "instagram") {
    return capabilities.find(
      (capability) =>
        capability.platform === "instagram" &&
        capability.capture_method === "server_instagram_graph_comments"
    );
  }
  if (platform === "reddit") {
    return capabilities.find(
      (capability) =>
        capability.platform === "reddit" &&
        capability.capture_method === "server_reddit_json_proxy"
    );
  }
  return capabilities.find(
    (capability) =>
      capability.platform === "amazon" &&
      capability.capture_method === "extension_dom_next_link_walk"
  );
}

function capabilityStatusLabel(capability: CaptureCapability): string {
  if (capability.status === "ready") {
    return "ready";
  }
  if (capability.status === "fixture_only") {
    return "fixture only";
  }
  if (capability.status === "credential_missing") {
    return "credential missing";
  }
  if (capability.status === "live_read_blocked") {
    return "live read blocked";
  }
  if (capability.status === "task_authorization_required") {
    return "task authorization required";
  }
  return "authorization required";
}

function capabilityToneFor(capability: CaptureCapability | undefined): "ready" | "blocked" | "quiet" {
  if (!capability) {
    return "quiet";
  }
  return capability.status === "ready" || capability.status === "fixture_only" ? "ready" : "blocked";
}

function capabilityNoteFor(
  platform: VocPlatform,
  capabilityLabel: string,
  capability: CaptureCapability | undefined
): string {
  if (!capability) {
    return "当前 API 未返回该平台的采集能力状态，配置保存不会代表采集链路已可执行。";
  }
  if (platform === "instagram" && capability.status !== "ready") {
    return `能力状态为 ${capabilityLabel}，需要先满足授权和 live-read gate 后再进入真实采集。`;
  }
  if (capability.status === "fixture_only") {
    return "当前仅代表本地 fixture 路径可用，不等同于外部平台真实读取。";
  }
  if (capability.status === "ready") {
    return "采集能力已就绪，配置变更会影响后续任务的默认执行参数。";
  }
  return `能力状态为 ${capabilityLabel}，请先处理授权或凭据边界。`;
}

function stageLabel(stage: PlatformStage): string {
  if (stage === "active") {
    return "active";
  }
  if (stage === "gated") {
    return "gated";
  }
  if (stage === "planned") {
    return "planned";
  }
  return "deferred";
}

function uniqueObjectDetail(platform: VocPlatform, units: VocUnit[]): string {
  if (platform === "amazon") {
    return `${uniqueCount(units.map((unit) => unit.asin))} ASIN`;
  }
  if (platform === "reddit") {
    return `${uniqueCount(units.map((unit) => unit.thread_id))} thread`;
  }
  return `${uniqueCount(units.map((unit) => extensionString(unit.platform_extension.media_id)))} media`;
}

function recentObjectLabel(platform: VocPlatform, units: VocUnit[]): string {
  const latest = [...units].sort(
    (left, right) =>
      new Date(right.captured_at).getTime() - new Date(left.captured_at).getTime()
  )[0];
  if (!latest) {
    return "-";
  }
  if (platform === "amazon") {
    return latest.asin ?? latest.source_object_id;
  }
  if (platform === "reddit") {
    return latest.thread_id ?? latest.source_object_id;
  }
  return extensionString(latest.platform_extension.media_id) ?? latest.source_object_id;
}

function queueDetail(tasks: CollectionTask[]): string {
  const pending = tasks.filter(
    (task) =>
      task.status === "pending" ||
      task.status === "running" ||
      task.status === "retry_scheduled"
  ).length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  return `${pending} open / ${completed} done`;
}

function taskObjectLabel(task: CollectionTask): string {
  const mediaId = contextString(task.context.media_id);
  if (task.platform === "instagram" && mediaId) {
    return mediaId;
  }
  const threadId = contextString(task.context.thread_id);
  if (task.platform === "reddit" && threadId) {
    return threadId;
  }
  const asin = contextString(task.context.asin);
  if (task.platform === "amazon" && asin) {
    return asin;
  }
  return task.collection_task_id;
}

function uniqueCount(values: Array<string | null | undefined>): number {
  return new Set(values.filter((value): value is string => Boolean(value))).size;
}

function contextString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function extensionString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function latestDate(values: string[]): string | null {
  const timestamps = values
    .map((value) => new Date(value).getTime())
    .filter((value) => Number.isFinite(value));

  if (timestamps.length === 0) {
    return null;
  }

  return new Date(Math.max(...timestamps)).toISOString();
}

function freshnessLabel(value: string): string {
  const elapsedMs = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) {
    return "captured";
  }

  const elapsedHours = Math.floor(elapsedMs / 1000 / 60 / 60);
  if (elapsedHours < 1) {
    return "1h";
  }
  if (elapsedHours < 24) {
    return `${elapsedHours}h`;
  }
  return `${Math.floor(elapsedHours / 24)}d`;
}

function formatCompactDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime()) || date.getTime() === 0) {
    return "default";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}
