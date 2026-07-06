---
title: Plugin Hub Loop Engineering Execution Plan
doc_type: workflow
module: product_engineering
topic: plugin-hub-loop-engineering
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Loop Engineering Execution Plan

## 1. 目标摘要

本计划把 loop engineering 抽象为五个工程组件：

```text
目标 -> 状态 -> 动作 -> 评价 -> 记忆/反馈 -> 下一轮目标
```

当前仓库没有发现独立的 `loop engineering` 定义。本计划采用项目现有口径：`VOC browser plugin loop`、`Detect -> Raw -> Schema -> Canonical -> Insight -> Strategy`、`collection-method-audit`、分平台能力门控、证据等级分层。

## 2. 当前证据边界

| 证据层 | 当前可支持的表达 | 当前边界 |
| --- | --- | --- |
| 本地代码与测试 | API/Web/Extension 具备可验证的本地 MVP 骨架 | 聚合命令会受 pnpm 非交互依赖确认影响，需分层复判 |
| fixture/local | Instagram parser、Graph skeleton、preflight、配置审计可本地验证 | fixture/local 只证明契约与解析链路 |
| public/read-only | 2026-07-01 已完成 public GET-only smoke，生产公开入口和部分 API 可读 | 只支持被 GET 观测到的生产状态；不能证明本地未上线接口或字段已部署 |
| authorized live | 需要平台账号、权限、明确授权和记录 | Meta live read、production write、provider call 均需独立批准 |

## 3. Loop 五组件定义

### 3.1 目标

目标用于锁定每一轮闭环的业务价值和证据等级。Plugin Hub 的 loop 目标分四层：

| 目标层 | 目标 | 完成判据 |
| --- | --- | --- |
| P0 体验闭环 | 用户在 Amazon/Reddit 页面完成可信 VOC 采集、回传、复核 | 页面内 UI 展示对象、coverage、stop reason、回传结果；VOC Hub 可复核 |
| P0 运营闭环 | 运营人员在 VOC Hub 判断证据健康、待补采、低覆盖、平台授权状态 | 第一屏展示 API、最新采集、队列、低置信度、平台 gate |
| P1 数据资产闭环 | raw/canonical/platform_extension 进入可复用信号层 | `relation_edges` 与 `enriched_voc_signal` 有 schema、测试、回溯证据 |
| P2 商业策略闭环 | VOC 转成选品、Listing、广告、本地化策略 | strategy output 可回溯到 VOC unit，并保留 evidence strength |

### 3.2 状态

状态是每轮 loop 的输入。状态必须可读、可比较、可升级证据等级。

| 状态域 | 当前来源 | 必须保留的字段 |
| --- | --- | --- |
| ProductState | PRD、UI plan、value analysis | P0/P1/P2 范围、用户场景、非目标 |
| CaptureState | `/api/capture-capabilities`、extension package、collection tasks | platform、capture_method、mode、status、live_read_enabled、writes_canonical_voc |
| EvidenceState | collection runs、raw items、canonical VOC、quality flags | raw count、voc count、coverage_scope、coverage_confidence、stop_reason |
| UIState | Extension command bar、VOC Hub、screenshots | viewport、overflow、primary CTA、drawer tabs、task queue visibility |
| GovernanceState | platform settings、audit events、runbooks | changed_fields、updated_by、gate、authorization context |
| DeliveryState | tests、lint、typecheck、build、public smoke | command、scope、result、evidence_grade |

### 3.3 动作

动作是状态到目标的最小可验证变更。每个动作都要有目标、输入状态、输出状态、评价门槛。

| 动作类型 | 示例 | 输出 |
| --- | --- | --- |
| Inspect | 读取 PRD、runbook、代码、dashboard、API | `findings.md` 记录事实与边界 |
| Design | 写 workflow、schema、UI task spec | draft/review 文档 |
| Implement | 改 UI、API、ETL、worker、tests | 小范围代码变更 |
| Verify | 跑 targeted test、browser smoke、read-only probe | 命令证据与截图/JSON |
| Promote | 更新计划状态、准备 commit/PR/部署 | 只在证据等级支持时推进 |
| Gate | Meta 授权、production write、provider call | 缺授权时保持 blocked |

### 3.4 评价

评价用于判断动作是否进入下一轮。评价按证据层级分开。

| 评价项 | 最低通过条件 | 升级条件 |
| --- | --- | --- |
| 本地正确性 | API/Web/Extension targeted tests 通过 | full test/lint/typecheck/build 通过 |
| 体验可用性 | desktop/mobile 无主要布局阻断 | 真实 Chrome 插件页面截图通过 |
| 数据可信度 | `coverage_confidence`、`stop_reason`、`quality_flags` 可解释 | 多平台样本复核通过 |
| 运营可管理性 | 队列、配置、授权状态可见 | 操作路径包含复核、补采、导出、策略生成 |
| 合规边界 | credential/live-read/write gate 分层 | 授权记录齐全后进入 read-only/live 层 |
| 商业价值 | 输出可映射到选品、Listing、广告、本地化 | 指标与业务结果形成复盘样本 |

### 3.5 记忆/反馈

记忆只保存可复用、可追溯、可执行的反馈，不把瞬时状态升级为长期真相。

| 记忆载体 | 用法 |
| --- | --- |
| `.kiro/plan/task_plan.md` | 当前 loop 的目标、阶段、状态 |
| `.kiro/plan/progress.md` | 每轮动作、命令、结果、阻塞 |
| `.kiro/plan/findings.md` | 事实、决策、证据边界 |
| `docs/workflows/*` | 可复用执行计划、runbook、gate |
| `drafts/analysis/*` | 产品/战略分析与阶段性方案 |
| `~/.codex/evolution/inbox/candidates.jsonl` | 仅在真实失败、用户纠正、测试断点时记录候选经验 |

## 4. 当前未完成任务映射

| Lane | 当前状态 | Loop 目标 | 下一动作 | 评价门槛 |
| --- | --- | --- | --- | --- |
| L1 Extension UX | Command Bar 已有 pipeline，但 drawer 分层、恢复路径、移动布局仍待强化 | 页面内完成采集、复核、回传、补采的最短路径 | 拆分 drawer tabs：计划、Raw、Schema、洞察、回传；建立异常恢复模型 | Extension render tests + 375px/desktop screenshot |
| L2 VOC Hub Ops | 平台工作区、指标条、证据表已实现；Evidence Workbench 操作链仍浅 | 管理者 5 秒内看清健康、队列、低覆盖、授权 | 强化 EvidenceFilterBar、TaskQueuePanel、低置信度复核动作 | Web tests + mobile/desktop smoke |
| L3 Evidence Model | raw/canonical/platform_extension 已有；relation_edges/enriched_voc_signal 已有本地派生层 | VOC 从证据进入可分析信号层 | 如需审计历史，补持久化表、迁移、回填 runbook | API tests + migration/backfill dry-run |
| L4 Platform Gates | Instagram fixture/Graph/preflight 已有；授权 evidence labels 已落到 API/Web contract；live read 需外部授权 | 平台扩展在合规门控下推进 | 等待确认授权数据源与权限；未授权前只做 dry preflight/readiness | readiness endpoint + authorization context + evidence labels |
| L5 Production Governance | 部署计划历史显示完成；当前生产状态需新鲜 read-only 证据 | 发布/回滚/证据索引可重复 | 建 production read-only checklist 与 evidence index | quoted curl + screenshot + no mutation |
| L6 Business Strategy | strategy-notes 为关键词模板；行业策略深度有限 | 输出可服务选品、Listing、广告、本地化 | 建跨境电商标签体系与策略模板 | evidence-backed strategy note tests |
| L7 Team/Permission | 团队权限、多品牌空间还在 P2 | 公司级协作与审计 | 先定义 workspace/account/role contract | PRD + schema proposal |

## 5. 执行计划

### Loop 0：计划启动与状态基线

**目标：** 建立本轮 loop 工作记忆和执行计划。

**状态输入：**

- `.kiro/plan/*` 仍是部署闭环，部署阶段已完成。
- PRD、UI plan、Meta execution register、value analysis 已存在。
- 工作树已有大量 tracked/untracked 变更，后续实现动作必须先做 checkpoint。

**动作：**

1. 建立本 workflow。
2. 更新 `.kiro/plan/task_plan.md`、`progress.md`、`findings.md`。
3. 输出当前 loop 的第一轮 backlog。

**评价：**

- 文档有 frontmatter。
- `.kiro/plan` 指向当前 loop。
- 无业务代码改动。

### Loop 1：UX 证据闭环

**目标：** 让页面内插件与 VOC Hub 都能解释“本次采集可信度”。

**动作队列：**

1. Extension：建立 drawer tabs 与 `ErrorRecoveryBanner` 规格。
2. Extension：把 Reddit server capture 入口从 footer 级动作提升为恢复路径。
3. Web：把 Evidence Workbench 放在运营工作流主区域。
4. Web：增加低覆盖/quality flag 复核动作。

**评价：**

- Extension tests 覆盖 collapsed/expanded/recovery。
- Web tests 覆盖 filters/task queue/quality badge。
- 375px 与桌面截图无横向溢出。

**2026-07-01 执行进展：**

- 已完成：Extension drawer 增加 `计划` / `Raw` / `Schema` / `洞察` / `回传` 五段 loop tabs。
- 已完成：Extension 增加恢复建议横幅，覆盖 Reddit Raw 0 服务端补采、Instagram 授权门禁、local/API error。
- 已完成：VOC Hub Evidence Workbench 增加行级 `复核` / `详情` 与 `来源` 动作。
- 已完成：VOC detail drawer 增加基于 `lowConfidenceThreshold` 和 `quality_flags` 的复核建议。
- 已验证：Extension render test、Extension TypeScript、Web TypeScript、diff check。
- 已验证：本地 Playwright visual smoke，覆盖 Extension Reddit Raw 0 desktop/375px、VOC Hub Evidence Workbench desktop/375px、VOC detail drawer 375px 内部滚动。
- 截图证据：`output/playwright/loop1-visual/`。
- 边界：本轮只支持 local visual-smoke 结论，不支持真实 Chrome 插件加载、live Reddit capture、production read-only、provider call 或平台 credential readiness。

### Loop 2：数据资产闭环

**目标：** 从 raw/canonical 扩展到可分析信号。

**动作队列：**

1. 定义 `relation_edges` 最小 schema：Amazon review -> ASIN、Reddit comment -> parent/thread。
2. 定义 `enriched_voc_signal` 最小 schema：topic、aspect、pain_point、severity、evidence_strength。
3. 用 Amazon/Reddit fixture 建 sample mapping。
4. 把 strategy note 从关键词模板升级为 signal-backed 模板。

**评价：**

- API tests 证明 signal 可由 fixture 生成。
- 每条 strategy note 能回溯到 VOC units。
- 低覆盖或推断型信号带 evidence_strength。

**2026-07-01 执行进展：**

- 已完成：新增 `RelationEdge`、`EnrichedVocSignal`、`VocSignalBundle` schema。
- 已完成：新增 `build_voc_signal_bundle` 与 `generate_relation_edges`，从 canonical VOC 派生 Amazon、Reddit、Instagram 的结构关系边。
- 已完成：新增 `GET /api/insights/voc-signals`，支持按 platform 过滤。
- 已完成：`/api/insights/strategy-notes` 改为从 enriched VOC signal 汇总证据，保留原 endpoint。
- 已验证：ruff、mypy、targeted API tests、full API pytest、diff check。
- 边界：当前是可重建的本地派生资产；未新增 DB 表/迁移，未做 AI provider call，未做 live capture 或 production read-only。
- 下一决策：如需要审计与历史回放，执行 Loop 2.1 持久化；否则进入 Loop 3 平台授权闭环。

### Loop 3：平台授权闭环

**目标：** 让 Instagram/Facebook 扩展保持授权优先、fixture 可测、live read 分层。

**动作队列：**

1. 确认目标平台：Instagram 或 Facebook。
2. 确认账号、权限、App Review、数据范围。
3. 完成 backend-only credential 配置 runbook。
4. 只在授权后执行 live read-only gate。

**评价：**

- `/api/capture-capabilities` 显示正确状态。
- preflight ready 后才允许 worker 触达 Graph fetcher。
- task context 保存 sanitized URL，无 token。

**2026-07-01 执行进展：**

- 已完成：`/api/capture-capabilities` 增加 `evidence_grade`、`next_required_action`、`side_effect_boundary`。
- 已完成：`/api/capture-authorizations/instagram-graph-live-read/preflight` 增加同样的证据边界字段。
- 已完成：Web API client 类型、解析和测试要求这些字段，防止 VOC Hub 丢失门禁解释。
- 已完成：Instagram Graph authorization runbook 增加 readiness/preflight 字段解释。
- 已验证：API full pytest、API focused Graph/worker tests、Web API tests、Web/Extension package tests、ruff、mypy、TypeScript、diff check。
- 边界：未配置 Meta token，未调用 Meta Graph live endpoint，未执行 authorized live read-only，未执行 live write 或 production VOC write。
- 下一轮：Loop 4 production evidence governance。

### Loop 4：生产与证据治理闭环

**目标：** 生产入口、数据、证据和回滚路径可重复核验。

**动作队列：**

1. 建 public read-only smoke checklist。
2. 建 evidence index：截图、JSON、curl、browser harness 输出。
3. 建 migration/DB upgrade runbook。
4. 建 release checkpoint 与 rollback checklist。

**评价：**

- public read-only 与 local/fixture 结果分开记录。
- production mutation 需要独立授权。
- 证据路径可追踪，临时产物有保留策略。

**2026-07-01 执行进展：**

- 已完成：生产 public GET-only smoke，证据目录为 `output/production-readonly/20260701T024920Z/`。
- 已完成：新增 `docs/workflows/plugin-hub-production-evidence-governance-runbook-draft-20260701.md`。
- 已完成：runbook 记录证据等级、可支持/禁止表达、repeatable smoke checklist、evidence index、DB upgrade boundary。
- 已观测 200：`/`、`/api/capture-capabilities`、`/api/voc-units?platform=amazon`、`/api/voc-units?platform=reddit`、`/api/insights/strategy-notes?platform=amazon`。
- 已观测 404：`/api/insights/voc-signals?platform=amazon`，说明本地 Loop 2 signal endpoint 尚不能被称为生产已部署能力。
- 已观测：生产 `/api/capture-capabilities` 未携带 Loop 3 evidence-label 字段，说明本地 Loop 3 字段尚不能被称为生产已部署能力。
- 边界：本轮是 L3 production read-only 证据；未做部署、provider call、live platform capture、production write 或 DB migration。
- 下一轮：Loop 5 release/version alignment，处理本地能力与生产行为漂移。

### Loop 5：Release / Version Alignment 闭环

**目标：** 把本地 Loop 2/3 能力与生产可观测状态对齐，形成可审查的 release candidate 边界。

**状态输入：**

- 生产 Loop 4 smoke：`/api/insights/voc-signals?platform=amazon` 返回 404。
- 生产 Loop 4 smoke：`/api/capture-capabilities` 未观测到 Loop 3 evidence-label 字段。
- 本地代码：已实现 `voc-signals` route、capability evidence labels、Web API parser。
- 工作树：仍是 API/Web/Extension/deploy/docs/output 混合 dirty tree。

**动作：**

1. 运行 Loop 2/3 scoped API/Web release-candidate validation。
2. 生成本地只读 contract probe。
3. 建立 release/version alignment runbook。
4. 将 release candidate 与生产后验收 smoke 分开。

**评价：**

- API ruff、API scoped tests、API mypy、Web API tests、Web TypeScript 均通过。
- 本地 contract probe 记录在 `output/release-alignment/20260701T031215Z/local_contract_probe.json`。
- 生产差异仍以 Loop 4 L3 smoke 为准。

**2026-07-01 执行进展：**

- 已完成：新增 `docs/workflows/plugin-hub-release-version-alignment-runbook-draft-20260701.md`。
- 已完成：本地 probe 观测 `/api/insights/voc-signals?platform=amazon` 为 200，响应 shape 为 `enriched_voc_signals` + `relation_edges`。
- 已完成：本地 probe 观测 `/api/capture-capabilities` 为 200，4 个 capability item 均带 evidence-label 字段。
- 已验证：API scoped ruff、41 个 API tests、API mypy、27 个 Web API tests、Web TypeScript。
- 边界：本轮只支持 local release-candidate alignment；生产观测升级需要经过批准部署和新的 L3 production read-only smoke。
- 下一轮：Loop 6 path selection，在 approved release packaging 与 evidence-model persistence proposal 之间选择。

### Loop 6：Path Selection 闭环

**目标：** 在 release packaging 与 evidence-model persistence 之间选择下一轮路径。

**状态输入：**

- 本地 Loop 2/3 capability 已通过 scoped validation 与 local contract probe。
- 生产 Loop 4 smoke 仍显示 `voc-signals` route 和 capability evidence-label 字段未对齐。
- 当前实现没有新增持久化 relation/signal 表。
- 工作树仍然包含 API/Web/Extension/deploy/docs/output 多域混合变更。
- 当前对话未提供 production deploy approval。

**动作：**

1. 读取 package/build scripts 与 Tencent Lighthouse compose。
2. 对比 release packaging preparation 与 evidence-model persistence proposal。
3. 新增 `docs/workflows/plugin-hub-loop6-path-selection-decision-draft-20260701.md`。
4. 将 Loop 7 定义为 release packaging preparation，明确 no production deploy。

**评价：**

- 决策能直接解决当前最大价值缺口：本地能力尚未成为生产可观测能力。
- 决策没有引入 DB mutation、provider call、live capture 或 deploy。
- 下一轮动作可执行：file inventory、full local gates、build/package proof、DB backup plan、post-release smoke plan。

**2026-07-01 执行进展：**

- 已完成：选择 release packaging preparation without production deployment。
- 已完成：defer evidence-model persistence，直到 leadership 要求审计历史、production 已观测 Loop 2/3 capability，或 DB migration window 获批。
- 已完成：新增 Loop 6 decision record。
- 边界：Loop 6 是 decision-record evidence；未跑新 build/test gate，未执行 deploy、remote mutation、production DB operation、provider call、live capture。
- 下一轮：Loop 7 release packaging preparation, no production deploy。

### Loop 7：Release Packaging Preparation 闭环

**目标：** 生成本地 release packaging evidence，但不执行 production deploy。

**状态输入：**

- Loop 6 已选择 release packaging preparation。
- 工作树包含 API/Web/Extension/deploy/docs/output 多域变更。
- 当前对话未提供 production deploy approval。

**动作：**

1. 生成 dirty-tree release inventory。
2. 运行 API/Web/Extension full local gates。
3. 运行 API/Web/Extension build/package proof。
4. 运行 Tencent Lighthouse Docker Compose config check。
5. 新增 `docs/workflows/plugin-hub-loop7-release-packaging-readiness-draft-20260701.md`。

**评价：**

- API pytest 137 passed，API ruff/mypy passed。
- Web vitest 29 passed，Web lint/typecheck/build passed。
- Extension vitest 93 passed，Extension lint/typecheck/build/package/verify passed。
- Docker Compose config passed。
- Dirty-tree inventory 显示 direct candidate 只有 14 个文件，但 API/Web/Extension/deploy 仍有大量 needs-review 项。

**2026-07-01 执行进展：**

- 已完成：`output/release-packaging/20260701T110015Z/release_file_inventory.json` 与 `.tsv`。
- 已完成：API/Web/Extension full local gates。
- 已完成：API wheel/sdist、Web `.next` build、Extension 三目标 dist 和 zip package。
- 已完成：新增 Loop 7 readiness runbook。
- 边界：本轮是 L1 local runtime/build-package evidence；未执行 deploy、remote mutation、production DB backup execution、DB migration、provider call、live capture、Chrome Web Store submission。
- 下一轮：Loop 8 release branch/file-inventory decision, no production deploy。

### Loop 8：Release Branch / File Inventory Decision 闭环

**目标：** 对 Loop 7 的 101 个 dirty entries 做 include / split / exclude 决策，先形成发布范围，不做 git staging。

**状态输入：**

- Loop 7 本地 gates 和 build/package proof 全部通过。
- 直接 Loop 2/3 candidate 为 14 个文件。
- 实际 dirty tree 包含 API/Web/Extension/deploy/docs/output 多域变更。
- API route registration、platform settings、Web parser/UI、Extension packaging 和 deploy 文件存在耦合。

**动作：**

1. 读取 `output/release-packaging/20260701T110015Z/release_file_inventory.json`。
2. 补读关键 API/Web diff，确认 narrow 14-file candidate 依赖不完整。
3. 生成 file-level decision matrix。
4. 新增 `docs/workflows/plugin-hub-loop8-release-branch-inventory-decision-draft-20260701.md`。

**评价：**

- 101 个 inventory rows 均已决策。
- 选择 broad app release candidate。
- 本地 evidence、`.kiro` planning state、business analysis drafts、diagnostic tooling 从 app source release 中拆出。

**2026-07-01 执行进展：**

- 已完成：`output/release-branch-decision/20260701T110851Z/release_branch_file_decision.json`。
- 已完成：`output/release-branch-decision/20260701T110851Z/release_branch_file_decision.tsv`。
- 决策结果：82 broad app source/test、3 extension packaging、4 release infra、6 release docs、1 workspace hygiene 纳入候选；2 business analysis、1 diagnostic tooling、1 local planning state 拆出；1 local evidence 从 source release 排除。
- 边界：本轮是 L1 local file-inventory decision；未执行 git stage、branch、commit、push、PR、deploy、production DB operation、provider call、live capture。
- 下一轮：Loop 9 release approval packet before any git staging。

## 6. 第一轮 Backlog

| 优先级 | 任务 | 目标组件 | 状态组件 | 动作组件 | 评价组件 | 反馈位置 |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | 建立 loop 工作计划 | 目标 | 当前计划状态 | 写 workflow + `.kiro/plan` | 文件存在、frontmatter 合规 | progress/findings |
| P0 | 做工作树 checkpoint 方案 | 状态 | git status 大量变更 | 按业务域列出可提交/暂存边界 | 用户确认后执行 | task_plan |
| P0 | Extension recovery spec | 目标/动作 | UI plan + command bar 当前实现 | 设计 drawer/recovery 数据模型 | render test spec | docs/workflows |
| P0 | VOC Hub Evidence Workbench spec | 目标/动作 | page.tsx + VocEvidenceTable | 设计 filters/actions/queue states | Web test spec | docs/workflows |
| P1 | signal schema proposal | 状态/动作 | PRD relation_edges/enriched fields | 写 schema proposal | API fixture plan | docs/workflows |
| P1 | production read-only checklist | 评价 | deploy plan + memory boundary | 已写 smoke checklist 和治理 runbook | public GET-only smoke completed | docs/workflows + output/production-readonly |

## 7. 执行约束

- 保持 Amazon、Reddit、Instagram 证据 lane 分开。
- 本地测试、fixture、public read-only、authorized live side effect 分开记录。
- 任何 Meta credential、provider call、production write 都需要显式授权。
- 不把 dashboard online、API reachable、fixture pass 叙述为真实平台采集完成。
- 新平台先过 contract/schema/UI/readiness，再进入 live-read。
- 每轮最多推进一个主目标，避免 UI、ETL、部署、授权同时混合。
- 每轮结束必须写 progress，并把新发现写入 findings。

## 8. Loop 运行模板

```text
Loop N
目标：
状态：
动作：
评价：
记忆/反馈：
下一轮：
```

每轮完成后更新：

- `.kiro/plan/progress.md`
- `.kiro/plan/findings.md`
- 相关 `docs/workflows/*` 或 `drafts/analysis/*`
