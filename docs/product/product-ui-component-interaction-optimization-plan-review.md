---
title: Plugin Hub UI 组件设计与交互优化计划
doc_type: prd
module: product
topic: ui-component-interaction-optimization
status: review
created: 2026-06-14
updated: 2026-06-14
owner: self
source: human+ai
---

# Plugin Hub UI 组件设计与交互优化计划

## 1. 审计范围

本次审计覆盖两类 UI：

- Chrome 插件页面注入 UI：`ContentCommandBar`、pipeline 状态、采集预览、回传、本地导出、服务端补采入口。
- VOC Hub 网站 UI：运行总览、配置参数、采集模板、监控指标、补采队列、平台覆盖、策略信号、Canonical VOC 表格。

不覆盖：

- Chrome Web Store 发布页。
- 登录、团队空间、云端历史等尚未进入当前代码的能力。
- 完整 WCAG 合规结论。当前只根据截图、DOM、组件代码判断可见风险。

## 2. 审计证据

当前使用的证据：

- 网站桌面截图：`tmp/screenshots/tmp-ui-audit-web-dashboard-desktop-20260614.png`
- 网站移动截图：`tmp/screenshots/tmp-ui-audit-web-dashboard-mobile-20260614.png`
- 插件 UI 代码：`apps/extension/src/content/ui/ContentCommandBar.tsx`
- 插件样式：`apps/extension/src/content/ui/content-command-bar.css.ts`
- 网站页面代码：`apps/web/app/page.tsx`
- 网站全局样式：`apps/web/app/globals.css`
- 竞品入口与页面展示草稿：`drafts/analysis/product-design-extension-trigger-ui-competitor-analysis-draft-20260613.md`

证据限制：

- 本次未重新捕获真实 Amazon / Reddit 页面中的插件截图；插件审计主要来自当前代码结构、既有测试和之前的竞品分析草稿。
- 网站截图来自本地临时服务 `http://localhost:3001`，API 指向当前代码启动的 `http://localhost:8010`。

## 3. 当前结构判断

当前产品已经不是“popup 插件 + 普通 dashboard”的形态，而是：

```text
平台页面
-> 页面注入 VOC Command Bar
-> 当前页采集预览 / 本地导出 / 私有服务器回传 / Reddit 服务端补采
-> VOC Hub 监控采集结果、补采队列和策略信号
```

这个方向正确，因为它与竞品的页面内触发形态一致，同时保留了差异化：schema 透明、coverage 可解释、私有回传、Amazon + Reddit 融合模型。

反面论点是：继续强化 dashboard 可能比优化插件页内 UI 更快看到成果。但这会偏离用户真实触发场景。中小商家第一次价值感发生在打开 Amazon 商品页或 Reddit thread 的那一刻，不是在事后进入后台看报表。因此插件页内 UI 是 P0 优先级，网站 UI 是监控与复盘层。

## 4. 主要问题

### 4.1 插件 UI 问题

1. Command Bar 信息密度高，但缺少真正的 drawer 分层。
   当前 `expanded` 展开后只显示 pipeline 和 footer，没有 `采集计划 / Raw VOC / Schema 映射 / AI 洞察 / 回传设置` 的分区。

2. 主要操作按钮仍是文字按钮。
   `采集预览`、`采集并回传`、`AI 洞察`、`收起`、`关闭` 都是文字按钮。工具型插件更适合用图标按钮 + tooltip 承载次级动作，主 CTA 保留文字。

3. 状态模型合理，但用户无法看到关键失败恢复路径。
   已有 `ready / capturing / previewed / uploading / uploaded / error`，但 UI 没有把错误归类为：页面不支持、无 raw items、API 不可达、Reddit JSON 失败、服务端任务已提交、重试排队。

4. Amazon 与 Reddit 的对象字段展示过于压缩。
   当前 `ph-object` 五列固定展示，Amazon 的 `rating/review count` 和 Reddit 的 `.json + DOM fallback` 被放在同一层级，用户难以分辨“对象信息”和“采集方法”。

5. 服务端补采只作为 footer 按钮出现。
   Reddit fallback 是关键差异化能力，应在 `Raw VOC` 或 `回传` 分区中变成明确的恢复路径，而不是次级按钮。

### 4.2 网站 UI 问题

1. 移动端存在横向裁切。
   移动截图显示首屏 H1 与 Hero 文案向右超出可视区。根因是页面布局、标题字号和部分宽度约束未充分适配窄屏。

2. 首屏像“状态海报”，不像“操作监控台”。
   桌面截图视觉稳定，但首屏主要展示解释性文案和配置参数。高频用户更需要优先看到：采集是否正常、最近 run、待处理任务、失败原因、低置信度证据。

3. 配置参数占据过多首屏空间。
   `Runtime Config` 当前是首屏右侧大面板，但它不是日常最高频任务。应收敛为 compact config rail 或折叠面板。

4. 采集模板展示过早。
   `Capture Templates` 对新用户有解释价值，但对运营监控不是核心动作。它应移到“配置/模板”区，而不是挤占首屏。

5. 表格是数据资产核心，但位置偏后。
   `Canonical VOC Units` 是最能体现产品价值的区域，应与筛选、质量状态、AI strategy entry 更强绑定。

6. 缺少操作路径。
   当前网站主要是只读监控，没有“处理任务 / 查看 run / 复核低置信度 / 打开原始来源 / 生成策略”的连续动作。

## 5. 设计原则

### 5.1 插件 UI 原则

- 页面内自动触发优先，popup 降级为设置入口。
- Guest mode 默认可用：识别、预览、导出、私有回传不要求登录。
- 主流程必须固定为同一个 pipeline：`Detect -> Raw -> Schema -> Canonical -> Insight -> Strategy`。
- Amazon 与 Reddit 展示同一流程，但字段细节允许平台差异。
- 用户必须看见 coverage、stop reason、raw item count、schema 缺失和回传目标。

### 5.2 网站 UI 原则

- 第一屏服务于运营监控，不服务于产品介绍。
- 配置、模板、说明文案降权，采集健康度、待处理任务和证据质量升权。
- 表格不是普通列表，而是 VOC 证据工作台。
- 所有错误状态必须指向下一步动作。
- 移动端以读关键状态为主，不追求完整桌面信息密度。

### 5.3 视觉表达原则

Creative Production 侧的视觉定位应是“可信的数据采集控制台”，不是营销页，也不是 AI 聊天玩具。

- 主色：保留 green / teal / rust / amber / red 的状态体系。
- 背景：保留轻网格，但降低存在感，避免移动端显脏。
- 卡片：保留硬边框和低圆角，符合工具感。
- 图标：引入 lucide 风格图标用于采集、上传、导出、设置、关闭、刷新、补采、告警。
- 禁止：大面积渐变、装饰性光斑、过度 hero 化、过多解释性大字。

## 6. 目标组件体系

### 6.1 插件组件

| 组件 | 作用 | 当前状态 | 优化方向 |
| --- | --- | --- | --- |
| `VocCommandBar` | 页面内入口与主 CTA | 已有 | 拆成品牌区、对象区、状态区、动作区 |
| `DetectedObjectCard` | ASIN/thread 上下文 | 隐含在 `ph-object` | 平台字段分组展示，支持 compact |
| `PipelineStepper` | 采集链路进度 | 已有 | 每步增加 tooltip、错误态、可点击详情 |
| `CoverageMeter` | 覆盖率与可信度 | 已有数字 | 增加颜色阈值、stop reason、缺失字段 |
| `VocDrawer` | 展开态详情容器 | 未真正分层 | 新增 tabs |
| `CapturePlanTab` | 页预算、范围、停止条件 | 未独立 | Amazon / Reddit 差异化配置 |
| `RawVocTab` | raw item 预览 | 未独立 | 展示 raw count、source kind、more node |
| `SchemaMappingTab` | raw -> canonical | 未独立 | 展示映射字段、缺失、quality flags |
| `InsightTab` | AI 洞察入口 | 文案 notice | 默认模板 + 高级 prompt 入口 |
| `ReturnTargetTab` | API、run、task、错误恢复 | footer 承载 | 私有服务器、上传状态、补采队列 |
| `LocalExportMenu` | JSON/CSV 导出 | 已有按钮 | 合并为 download icon menu |
| `ErrorRecoveryBanner` | 错误说明与下一步 | 仅文本错误 | 按错误类型给 CTA |

### 6.2 网站组件

| 组件 | 作用 | 当前状态 | 优化方向 |
| --- | --- | --- | --- |
| `OperationsHeader` | 全局 API / freshness / env | 已有 topBar | 增加最近 run、失败数、刷新按钮 |
| `HealthStrip` | API、任务、质量、策略状态 | 分散在 metrics/monitor | 合并为第一屏横条 |
| `TaskQueuePanel` | 补采队列 | 已有 | 加筛选、claim/stale/retry 状态解释 |
| `EvidenceWorkbench` | VOC 证据工作台 | 表格在后方 | 提升为主区域，增加 filters |
| `EvidenceFilterBar` | 平台、质量、run、对象筛选 | 未有 | P0 必做 |
| `QualityReviewPanel` | 低置信度 / flags | metrics only | 展示复核清单 |
| `StrategySignalsPanel` | 策略洞察 | 已有 | 绑定 evidence count 和生成时间 |
| `CaptureTemplateSettings` | 模板配置 | 已有早展示 | 移入设置区或 secondary tab |
| `RuntimeConfigDrawer` | API 与环境配置 | 大面板 | 改为抽屉/折叠 |

## 7. 插件交互优化计划

### P0.1 响应式与信息分层

- Command Bar 默认折叠高度控制在页面可接受范围。
- 展开态改为 drawer，不再把所有内容塞在 footer。
- 宽屏：横向 command bar + 下方 drawer。
- 窄屏：顶部/底部贴边 compact bar + 全屏 drawer。

验收标准：

- Amazon 商品页、Amazon 评论页、Reddit thread 均能自动出现。
- 375px 宽度下按钮不溢出，文本不遮挡平台页面主内容。
- 折叠后仍能看到平台、对象、coverage、主 CTA。

### P0.2 操作优先级重排

主 CTA：

- `采集并回传`

次 CTA：

- `预览`
- `AI 洞察`

图标按钮：

- 导出
- 设置
- 展开/收起
- 关闭

验收标准：

- 首次用户无需理解所有功能即可完成一次采集回传。
- 导出、设置、关闭等次级动作不抢主 CTA 视觉层级。

### P0.3 Drawer tabs

新增 tabs：

- `计划`
- `Raw`
- `Schema`
- `洞察`
- `回传`

每个 tab 的最小内容：

- `计划`：平台、对象、采集方法、页预算、停止条件。
- `Raw`：raw item count、source kind、more node / empty DOM / captcha 标记。
- `Schema`：canonical 字段覆盖、缺失字段、quality flags。
- `洞察`：默认模板、提示词入口、生成状态。
- `回传`：API base URL、run id、task id、错误恢复。

验收标准：

- 用户能解释这次采集为什么可信或不可信。
- Reddit `.json` 失败后能清楚看到“提交服务端补采”的路径。

### P0.4 错误与恢复

错误类型要从裸字符串变成可理解状态：

- `unsupported_page`
- `empty_raw_items`
- `api_unreachable`
- `upload_failed`
- `reddit_json_unavailable`
- `server_task_created`
- `server_task_retry_scheduled`

每类状态必须有：

- 标题
- 原因
- 推荐动作
- 技术详情折叠区

验收标准：

- 用户不需要复制错误码给开发者，也能知道下一步是重试、导出、补采还是检查 API。

## 8. 网站交互优化计划

### P0.1 修复移动端布局

必须先修：

- `.dashboardShell` 在窄屏下改为 `width: 100%; padding-inline: 10px`。
- `h1` 使用断点字号，不使用 viewport 缩放。
- `.topBar` 在移动端改为纵向。
- `.commandGrid`、`.templateGrid`、`.opsGrid`、`.metricGrid` 全部在移动端单列。
- 长 URL、英文方法名、任务 id 必须 `overflow-wrap: anywhere`。

验收标准：

- 390px 宽度截图不出现横向裁切。
- H1、Hero 文案、配置值、模板 URL 都完整可读。

### P0.2 第一屏重构为运营工作台

第一屏顺序调整为：

1. `OperationsHeader`
2. `HealthStrip`
3. `TaskQueuePanel + EvidenceWorkbench` 首屏摘要
4. `RuntimeConfig` 折叠入口

下移：

- `Capture Templates`
- 长说明文案
- 配置详情列表

验收标准：

- 用户进入网站 5 秒内知道：API 是否正常、最近采集是否新鲜、是否有待补采、是否有低置信度证据。

### P0.3 Evidence Workbench

表格前增加 filter bar：

- 平台：All / Amazon / Reddit
- 质量：All / flagged / low confidence
- 对象：ASIN / thread id 搜索
- 时间：latest / last 24h / all

表格列优化：

- 平台
- 对象
- 原文证据
- 质量
- 覆盖率
- 来源/时间
- 操作

行操作：

- 查看 raw
- 查看 schema mapping
- 打开 source URL
- 加入策略分析

验收标准：

- 表格从“展示数据”变成“处理证据”的工作台。

### P0.4 Server Capture Queue

补采队列必须显式表达 worker 状态：

- `pending`
- `running`
- `retry_scheduled`
- `completed`
- `failed`
- `stale claim recovered`

每个任务展示：

- 平台与对象
- trigger reason
- claim / worker
- attempts
- next run
- last error

验收标准：

- 用户能判断服务端补采是还没跑、正在跑、失败重试，还是 worker stale 后已恢复。

## 9. 视觉组件规范

### 9.1 颜色

保留当前语义：

- Amazon：rust
- Reddit：teal
- success / clear：green
- warning / pending：amber
- error / failed：red
- neutral：ink / muted / line

调整：

- 移动端背景网格透明度降低 30%-50%。
- 状态色只用于边框、badge、条形进度，不做大面积底色。

### 9.2 排版

- Dashboard H1 桌面最大 42px，移动端降到 30px-32px。
- 面板标题 18px-22px。
- 表格和任务卡 12px-14px。
- 不使用负 letter spacing。

### 9.3 图标

建议引入 `lucide-react` 或扩展侧等价轻量图标：

- Capture：`ScanLine`
- Upload：`UploadCloud`
- Export：`Download`
- Insight：`Sparkles`
- Settings：`Settings`
- Close：`X`
- Expand：`PanelRightOpen`
- Retry：`RefreshCw`
- Warning：`TriangleAlert`
- Success：`CheckCircle2`

按钮规则：

- 主操作用文字按钮。
- 次级工具用图标按钮 + tooltip。
- 关闭、展开、导出、设置不再使用纯文字按钮。

## 10. 实施顺序

### 阶段 1：修复明显 UI 风险

- 修复网站移动端横向裁切。
- 重排网站首屏，让健康状态和待处理任务优先。
- 给插件 Command Bar 增加窄屏布局规则。

### 阶段 2：组件拆分

- 拆分 `ContentCommandBar.tsx` 为：
  - `VocCommandBar`
  - `PipelineStepper`
  - `CoverageMeter`
  - `VocDrawer`
  - `ErrorRecoveryBanner`
- 拆分 `apps/web/app/page.tsx` 中的大型内联组件，迁移到 `apps/web/src/components/operations/`。

### 阶段 3：Drawer 与工作台

- 插件实现 drawer tabs。
- 网站实现 `EvidenceFilterBar` 和 `EvidenceWorkbench`。
- 补采队列增加 worker/claim/stale 语义展示。

### 阶段 4：视觉资产与品牌统一

- 引入统一 icon set。
- 固化按钮、badge、panel、metric、table、task card 的 component tokens。
- 对 Amazon / Reddit 做平台色与字段模板，而不是分裂成两个产品。

## 11. 验收清单

插件 UI：

- 打开 Amazon 商品页自动出现 Command Bar。
- 打开 Reddit thread 自动出现 Command Bar。
- Guest mode 可完成预览、导出、回传。
- Reddit 采集失败时能提交服务端补采。
- API 不可达时有明确恢复动作。
- 375px 宽度无溢出。

网站 UI：

- 桌面首屏优先显示运行健康、待补采、低置信度、最近采集。
- 390px 宽度无横向裁切。
- Evidence 表格有筛选与行操作。
- Task 队列展示 pending/running/retry/failed/stale 语义。
- Runtime Config 不再占据首屏主视觉。

质量验证：

- `pnpm test`
- `pnpm lint`
- `pnpm typecheck`
- 插件 render 测试覆盖 expanded/collapsed/error/reddit server task。
- Web 增加移动端布局 smoke 或截图检查。

## 12. 推荐下一步

下一步先执行阶段 1：

1. 修复网站移动端横向裁切。
2. 优化网站首屏信息顺序。
3. 给插件 Command Bar 增加窄屏布局规则。

这三项风险最明确、收益最高，并且不会改变后端数据结构。
