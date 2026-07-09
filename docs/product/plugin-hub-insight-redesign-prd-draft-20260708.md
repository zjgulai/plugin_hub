---
title: Plugin Hub 洞察重构产品方案
doc_type: prd
module: product
topic: plugin-hub-insight-redesign
status: draft
created: 2026-07-08
updated: 2026-07-08
owner: self
source: human+ai
---

# Plugin Hub 洞察重构产品方案

## 1. 背景

当前洞察链路已经具备基础数据资产：

- 插件能在 Amazon / Reddit 页面完成采集、预览、回传与本地导出。
- 后端已经把 raw item 转成 `canonical_voc_unit`，并派生 `relation_edges` 与 `enriched_voc_signal`。
- VOC Hub 已经能展示 evidence workbench、质量标记、策略信号与采集状态。
- 当前 `strategy_note` 仍主要是 deterministic keyword v1 聚合，输出更像技术分组摘要，缺少跨境电商运营判断、商业优先级和可执行行动。

用户方向已经明确：

- 洞察角色偏向“跨境电商运营顾问”，不是普通 VOC 摘要员。
- 第一阶段聚焦 Reddit 与 Amazon，把模板做深。
- 默认输出语言为中文。

## 2. 目标

把洞察从“关键词分组 + 泛化建议”升级为“证据驱动的跨境电商经营诊断”。

核心目标：

- 让插件侧在 30 秒内给出可判断的经营结论，而不是长报告。
- 让 VOC Hub 承载完整证据链、诊断矩阵、行动计划和模板管理。
- 每条结论都必须能回溯到 VOC 证据、采集范围、质量标记和置信原因。
- Reddit 与 Amazon 采用同一数据契约，但使用平台专属诊断模板。
- 保持旧 `strategy_note` 接口兼容，新增更专业的 `InsightBrief` 契约。

## 3. 设计原则

### 3.1 洞察角色

默认角色为跨境电商运营顾问，输出应关注：

- 转化阻力：信任、价格、物流、支付、评价、售后、页面表达。
- 产品机会：功能缺口、包装、耐用性、尺寸、兼容性、质量稳定性。
- Listing 优化：标题、五点、A+、FAQ、图片信息层级、关键词语言。
- 内容与社群：Reddit 切入角度、话题表达、反感点、可参与语境。
- 广告素材：用户原话、痛点前置、场景化卖点、异议处理。
- 运营优先级：先处理什么、为什么、预计影响哪类指标。

### 3.2 证据纪律

洞察不得脱离证据输出。每条建议至少包含：

- `evidence_count`
- `evidence_examples`
- `source_platform`
- `source_object`
- `evidence_strength`
- `confidence_reason`
- `data_gaps`

当证据不足时，输出必须降级为“待验证假设”，不能包装成确定结论。

### 3.3 输出语言

默认输出为中文，保留平台对象、字段名、ASIN、Reddit subreddit、thread id、rating、URL 等英文原文。

支持后续扩展：

- `zh-CN`: 默认中文运营顾问输出。
- `en-US`: 面向英文团队或客户的英文报告。

## 4. 用户场景

### 4.1 Reddit 场景

运营人员打开某个 Reddit thread、subreddit 话题或 Shopify/DTC 相关讨论，希望快速判断：

- 这类问题是否代表真实购买阻力。
- 用户在讨论什么痛点、疑虑和替代方案。
- 能否转化为内容选题、FAQ、广告角度或产品改进。
- 当前样本是否足以支撑行动。

Reddit 输出重点不是“总结帖子”，而是判断社区语境和商业可用性。

### 4.2 Amazon 场景

运营人员打开 Amazon 商品页或评论页，希望判断：

- 差评集中在产品质量、预期落差、包装物流、尺寸兼容，还是使用门槛。
- 好评中的真实卖点能否进入 Listing、图片、A+、广告文案。
- 当前页面承诺是否与评论体验不匹配。
- 哪些问题应先进入 Listing/FAQ 修正，哪些应进入产品/供应链改进。

Amazon 输出重点不是“评论情绪分析”，而是 Listing 与运营动作。

## 5. 产品形态

### 5.1 插件侧：`VOC 经营简报`

插件侧只承载短结论，避免把抽屉变成长报告。

信息结构：

1. `经营结论`
   - 一句话说明当前 VOC 对业务的主要含义。
   - 示例：`当前样本更像信任与转化阻力，而非流量问题；优先检查页面信任元素、支付/结账路径与评论资产。`

2. `三条关键信号`
   - 每条包含信号类型、业务含义、证据数、置信等级。

3. `下一步动作`
   - 只给 1 个优先动作 + 1 个备选动作。
   - 强制说明建议作用于 Listing、产品、客服、广告、内容还是采集补样。

4. `证据与缺口`
   - 展示证据数量、来源类型、覆盖边界、质量标记。
   - 低可信时明确提示“需要补样”或“只可作为假设”。

5. `打开 VOC Hub`
   - 进入完整报告和证据工作台。

插件侧不做：

- 大段长文报告。
- 多模板编辑。
- 深层证据筛选。
- 批量导出完整报告。

### 5.2 VOC Hub：`VOC 经营诊断`

VOC Hub 承载完整分析。

一级信息架构：

- `总览`: 经营结论、机会/风险评级、样本覆盖、置信等级。
- `信号矩阵`: 痛点、卖点、阻力、场景、竞品、内容角度、Listing 机会。
- `证据链`: VOC unit、source object、原文、quality flags、relation edges。
- `运营诊断`: 平台模板给出的具体判断。
- `行动计划`: 按优先级拆成 Listing、产品、广告、内容、客服、采集补样。
- `模板设置`: 平台模板、行业 Profile、输出语言、证据阈值。

## 6. 洞察分类体系

### 6.1 通用信号类型

| Signal type | 中文名 | 业务含义 |
| --- | --- | --- |
| `conversion_blocker` | 转化阻力 | 用户想买但被信任、价格、支付、物流、页面信息阻断 |
| `trust_gap` | 信任缺口 | 评论、资质、品牌、退换货、社证不足 |
| `listing_mismatch` | Listing 承诺落差 | 页面表达与实际体验或用户预期不一致 |
| `product_quality_issue` | 产品质量问题 | 耐用性、材料、尺寸、兼容、故障、包装等 |
| `positive_purchase_driver` | 正向购买驱动 | 好评中可复用的核心卖点 |
| `usage_scenario` | 使用场景 | 明确的使用人群、场合、任务、约束 |
| `customer_language` | 用户语言 | 可进入标题、五点、FAQ、广告的原话表达 |
| `competitive_angle` | 竞品角度 | 替代方案、竞品弱点、对比语境 |
| `content_opportunity` | 内容机会 | Reddit、FAQ、教程、测评、短视频选题 |
| `sampling_gap` | 采样缺口 | 当前证据不足，需要补采或扩大范围 |

### 6.2 业务优先级

`priority` 使用 `P0 / P1 / P2`：

- `P0`: 影响转化或产品体验，证据强，建议立即处理。
- `P1`: 有明确机会或风险，建议进入本周运营迭代。
- `P2`: 证据弱或影响间接，作为观察项或补样方向。

### 6.3 置信等级

`confidence_level` 使用 `high / medium / low / hypothesis`：

- `high`: 多条独立证据支撑，质量标记少，平台显式字段强。
- `medium`: 有多条证据，但样本集中或存在部分质量标记。
- `low`: 证据数量少、来源单一或存在明显采集缺口。
- `hypothesis`: 只能形成假设，需要补采或人工复核。

## 7. 平台模板

### 7.1 Reddit 模板：`reddit_community_commerce_v1`

适用范围：

- Reddit thread
- subreddit 话题页
- DTC / Shopify / Amazon seller / niche community 讨论

核心诊断维度：

| 维度 | 输出问题 | 推荐动作 |
| --- | --- | --- |
| `context_fit` | 这段讨论是否与购买、使用或运营决策相关 | 低相关时只做素材观察，不进入强策略 |
| `pain_or_objection` | 用户真正卡在哪里 | 转为 FAQ、内容解释、页面信任元素 |
| `trust_and_social_proof` | 是否存在信任、评价、品牌、站点可信度疑虑 | 补评论、案例、退换货、支付安全、品牌背书 |
| `community_language` | 用户如何描述问题 | 提取为广告/内容/FAQ 原话库 |
| `content_entry` | 品牌如何参与讨论更自然 | 输出 Reddit 内容角度与禁忌表达 |
| `sampling_gap` | thread 是否足够代表群体问题 | 提醒补 subreddit、相邻 thread 或竞品样本 |

默认报告结构：

1. `社区语境判断`
2. `购买/转化阻力`
3. `可复用用户语言`
4. `内容与社群切入`
5. `下一步运营动作`
6. `证据缺口`

Reddit 模板必须保留：

- thread 与 comment 的父子关系。
- subreddit、flair、score、depth、deleted/removed/locked 状态。
- `.json` 或 DOM fallback 的采集方式。
- `more node` 与评论树缺口。

### 7.2 Amazon 模板：`amazon_review_listing_ops_v1`

适用范围：

- Amazon product detail
- review page
- star-filtered reviews
- sorted reviews

核心诊断维度：

| 维度 | 输出问题 | 推荐动作 |
| --- | --- | --- |
| `negative_driver` | 差评由什么驱动 | 产品、包装、说明、FAQ 或客服路径 |
| `positive_driver` | 好评真正买单点是什么 | 标题、五点、A+、图片、广告素材强化 |
| `listing_mismatch` | Listing 承诺与评论体验是否冲突 | 修正文案、图示、规格、使用前提 |
| `variant_issue` | 问题是否集中在特定变体 | 变体拆分、尺码表、兼容提示、供应链复核 |
| `review_quality` | 样本是否有足够显式信号 | 补采 verified、recent、critical、media reviews |
| `conversion_action` | 哪个动作最可能改善转化 | 输出优先级与作用页面位置 |

默认报告结构：

1. `评论经营诊断`
2. `差评根因与风险`
3. `好评卖点与语言资产`
4. `Listing 优化建议`
5. `产品/包装/客服改进`
6. `补采与复核建议`

Amazon 模板必须保留：

- rating、verified、helpful、variant、marketplace、review date。
- star filter、sort、observed page、stop reason、coverage confidence。
- ASIN、parent ASIN、brand、variant context 关系边。

## 8. 数据契约

新增核心对象为 `InsightBrief`。旧 `StrategyNote` 保留并通过 adapter 从 `InsightBrief.action_plan` 派生简版。

### 8.1 `InsightBrief`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `brief_id` | string | yes | 稳定 id，例如 `brief_reddit_thread_<id>` |
| `template_id` | string | yes | `reddit_community_commerce_v1` 或 `amazon_review_listing_ops_v1` |
| `template_version` | string | yes | 模板版本 |
| `language` | string | yes | 默认 `zh-CN` |
| `advisor_profile` | string | yes | 默认 `cross_border_ecommerce_ops` |
| `scope` | `InsightScope` | yes | 本次分析范围 |
| `headline` | string | yes | 经营结论一句话 |
| `executive_findings` | `ExecutiveFinding[]` | yes | 关键结论，建议 3 条 |
| `business_signals` | `BusinessSignal[]` | yes | 结构化信号 |
| `action_plan` | `ActionRecommendation[]` | yes | 运营行动 |
| `evidence_refs` | `EvidenceReference[]` | yes | 证据引用索引 |
| `confidence` | `BriefConfidence` | yes | 总体置信 |
| `data_gaps` | `DataGap[]` | yes | 采集或推断缺口 |
| `created_at` | string | yes | ISO timestamp |

### 8.2 `InsightScope`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `platform` | string | `amazon` 或 `reddit` |
| `source_object_type` | string | `asin`、`review_page`、`reddit_thread`、`subreddit_topic` |
| `source_object_id` | string | ASIN、thread id、subreddit 等 |
| `source_url` | string | 原始 URL |
| `collection_run_ids` | string[] | 关联 run |
| `coverage_scope` | string | 采集范围 |
| `coverage_confidence` | string | 覆盖置信 |

### 8.3 `ExecutiveFinding`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `finding_id` | string | 稳定 id |
| `title` | string | 中文短标题 |
| `business_meaning` | string | 运营含义 |
| `priority` | string | `P0 / P1 / P2` |
| `confidence_level` | string | `high / medium / low / hypothesis` |
| `evidence_ref_ids` | string[] | 支撑证据 |

### 8.4 `BusinessSignal`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `signal_id` | string | 可追踪 id |
| `signal_type` | string | 见 6.1 |
| `topic` | string | 主题 |
| `aspect` | string | 产品、Listing、物流、信任、价格等 |
| `customer_language` | string[] | 可复用用户原话 |
| `business_impact` | string | 对转化、内容、广告、产品的影响 |
| `severity` | string | `high / medium / low` |
| `priority` | string | `P0 / P1 / P2` |
| `evidence_strength` | string | `high / medium / low` |
| `confidence_reason` | string | 为什么可信或不可信 |
| `evidence_ref_ids` | string[] | 支撑证据 |
| `quality_flags` | string[] | 低可信标记 |

### 8.5 `ActionRecommendation`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `action_id` | string | 稳定 id |
| `action_type` | string | `listing / product / packaging / faq / ads / content / customer_support / sampling` |
| `title` | string | 行动标题 |
| `recommendation` | string | 具体建议 |
| `why_now` | string | 为什么当前应处理 |
| `expected_metric` | string | 可能影响的指标，如 CVR、CTR、退货率、客诉 |
| `owner_role` | string | Listing、产品、客服、内容、广告、运营 |
| `priority` | string | `P0 / P1 / P2` |
| `effort` | string | `low / medium / high` |
| `evidence_ref_ids` | string[] | 支撑证据 |

### 8.6 `EvidenceReference`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `evidence_ref_id` | string | 引用 id |
| `voc_unit_id` | string | Canonical VOC id |
| `platform` | string | Amazon / Reddit |
| `source_kind` | string | review、thread、comment 等 |
| `source_object_id` | string | ASIN、thread id、comment id |
| `quote` | string | 合规长度内的证据摘录 |
| `normalized_quote` | string | 可选中文解释或标准化表达 |
| `rating` | number | Amazon 可用 |
| `relation_edge_ids` | string[] | 关系边 |
| `quality_flags` | string[] | 质量标记 |
| `source_url` | string | 原始链接 |

### 8.7 `BriefConfidence`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `level` | string | `high / medium / low / hypothesis` |
| `reason` | string | 总体置信原因 |
| `evidence_count` | number | 使用证据数 |
| `source_diversity` | string | 来源多样性 |
| `coverage_notes` | string[] | 采集覆盖说明 |

### 8.8 `DataGap`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `gap_type` | string | `low_sample / missing_comments / low_relevance / missing_negative_reviews / missing_recent_reviews / blocked_source` |
| `description` | string | 缺口说明 |
| `recommended_collection` | string | 推荐补采动作 |
| `blocks_confidence` | boolean | 是否阻断强结论 |

## 9. API 方案

### 9.1 新增接口

`GET /api/insights/briefs`

查询参数：

- `platform`: `amazon | reddit`
- `source_object_type`: 可选
- `source_object_id`: 可选
- `language`: 默认 `zh-CN`
- `template_id`: 可选，默认按平台选择
- `limit`: 默认 20

返回：

```json
{
  "items": [
    {
      "brief_id": "brief_reddit_thread_1umbsm4",
      "template_id": "reddit_community_commerce_v1",
      "language": "zh-CN",
      "headline": "当前样本更像信任与转化阻力，而非流量问题。",
      "executive_findings": [],
      "business_signals": [],
      "action_plan": [],
      "evidence_refs": [],
      "confidence": {
        "level": "medium",
        "reason": "有多条相关 VOC，但评论树覆盖仍有缺口。",
        "evidence_count": 8,
        "source_diversity": "single_thread",
        "coverage_notes": []
      },
      "data_gaps": []
    }
  ]
}
```

### 9.2 兼容接口

保留：

- `GET /api/insights/strategy-notes`
- `GET /api/insights/voc-signals`

兼容策略：

- `strategy-notes` 继续返回旧字段，避免 Web/Extension 直接断裂。
- 新 UI 优先读取 `InsightBrief`。
- 旧 `strategy_note.recommendation` 可以由 `ActionRecommendation.recommendation` 摘要派生。
- 旧 `evidence_examples` 可以由 `EvidenceReference` 派生。

### 9.3 推断方法标记

每个 brief 必须记录生成方式：

- `deterministic_template_v1`: 本地规则与模板生成。
- `llm_assisted_v1`: 后续可选 AI provider 润色或归纳。
- `manual_reviewed_v1`: 人工复核后发布。

第一阶段建议使用 `deterministic_template_v1`，先把模板深度、证据链和 UI 做稳，再接入 provider。

## 10. UI 信息架构

### 10.1 插件 `洞察` tab

模块顺序：

1. `VOC 经营简报`
   - headline
   - confidence badge
   - evidence count

2. `关键信号`
   - 最多 3 条
   - 每条显示 signal type、priority、business impact

3. `建议动作`
   - 1 条主动作
   - 1 条备选动作
   - 显示 owner role 与 expected metric

4. `证据与缺口`
   - evidence count
   - coverage notes
   - data gaps

5. `打开 VOC Hub`
   - 完整诊断入口

### 10.2 VOC Hub Insight 页面

推荐新增或重构为 `InsightsWorkbench`：

- 左侧筛选：平台、对象、模板、置信、优先级、行动类型。
- 顶部总览：headline、样本覆盖、置信、最近生成时间。
- 主区 tabs：
  - `诊断总览`
  - `信号矩阵`
  - `证据链`
  - `行动计划`
  - `模板设置`
- 右侧详情：
  - 当前 signal 的证据列表
  - 原文 quote
  - relation edges
  - quality flags
  - recommended action

移动端：

- 默认只展示总览、P0 动作和证据缺口。
- 信号矩阵和证据链进入二级页面或抽屉。

## 11. 开发执行 TODO

### Phase 0: 设计与 fixture

- `complete_when`: Reddit / Amazon 各 2 组 fixture 可以覆盖正向、负向、低可信和补样缺口。
- 新增 fixture：
  - Reddit thread: 转化阻力 + 社区语言。
  - Reddit thread: 低相关或样本不足。
  - Amazon reviews: 差评质量问题 + Listing mismatch。
  - Amazon reviews: 好评卖点 + 广告语言。
- 输出 fixture expected brief JSON。

### Phase 1: 后端契约与规则引擎

- 新增 schema：`InsightBrief`、`ExecutiveFinding`、`BusinessSignal`、`ActionRecommendation`、`EvidenceReference`、`BriefConfidence`、`DataGap`。
- 新增 template registry：
  - `reddit_community_commerce_v1`
  - `amazon_review_listing_ops_v1`
- 新增 deterministic builder：
  - 从 `VocSignalBundle` 生成 `InsightBrief`。
  - 统一生成 confidence 与 data gaps。
  - 控制 evidence quote 长度与证据引用。
- 新增 `GET /api/insights/briefs`。
- 保持旧 `strategy-notes` 测试通过。

### Phase 2: Web API 与 VOC Hub

- 扩展 Web API parser，读取 `InsightBrief`。
- 新增 `InsightsWorkbench` 或重构现有 Strategy Signals 区。
- 建立总览、信号矩阵、证据链、行动计划四个视图。
- 支持 `platform=reddit|amazon`、`confidence`、`priority`、`action_type` 筛选。

### Phase 3: 插件洞察 tab

- `AI 洞察` 按钮改为读取 `InsightBrief`。
- 洞察 tab 展示 `VOC 经营简报`。
- 控制抽屉内只展示短结论、三条信号、主动作和证据缺口。
- API 不可用时复用现有恢复建议，并显示当前 API base URL。

### Phase 4: 测试与验收

- 后端 contract/service/route tests：
  - Reddit brief shape。
  - Amazon brief shape。
  - low-confidence data gaps。
  - strategy-notes compatibility。
- Web tests：
  - API parser。
  - Insight workbench render。
  - mobile no-overflow smoke。
- Extension tests：
  - brief render。
  - API recovery。
  - Reddit/Amazon insight tab state。
- 本地验收：
  - API ruff/mypy/pytest。
  - Web vitest/typecheck/build。
  - Extension vitest/typecheck/build/package verifier。

### Phase 5: 可选 AI provider 层

第一阶段先不接 provider。后续接入时必须满足：

- provider 调用可关闭。
- 请求 payload 不包含 secret。
- 输出必须保留 evidence refs。
- LLM 只能润色、归纳、排序，不能创造未在 evidence 中出现的事实。
- 每次 provider 调用记录 `provider_call=true`、模板版本、输入范围与输出版本。

## 12. 验收标准

文案质量验收：

- 输出默认中文。
- 每份 brief 至少包含 1 条 headline、3 条以内 executive findings、结构化 business signals、行动计划和证据缺口。
- 建议必须指向 Listing、产品、广告、内容、客服或补采动作之一。
- 不出现没有证据支撑的确定性结论。

数据契约验收：

- Reddit 和 Amazon brief 使用同一顶层契约。
- 每条 signal 和 action 都能通过 `evidence_ref_ids` 回溯。
- 低可信或低样本必须进入 `data_gaps`。
- `strategy-notes` 兼容接口仍可用。

UI 验收：

- 插件抽屉不被长报告撑爆。
- 插件 375px 宽度无文本重叠和页面级横向溢出。
- VOC Hub 能按平台、优先级、置信和行动类型筛选。
- 证据链与行动计划可以互相跳转。

边界验收：

- 本阶段可先做到本地 deterministic brief。
- 不要求 provider 调用。
- 不要求生产部署。
- 不要求 Amazon / Reddit 全量采集。

## 13. 未定问题

需要产品侧确认：

- 第一版是否把 Shopify/DTC 店铺经营问题作为 Reddit 垂直 profile，还是保持通用 Reddit commerce profile。
- 插件侧是否只展示 3 条信号，还是允许用户展开查看更多。
- VOC Hub Insight 页面是独立页面，还是嵌入当前首页 Strategy Signals 区。
- `InsightBrief` 是否需要持久化表，还是先保持从 canonical VOC 动态生成。
- 是否需要导出 Markdown / PDF 报告。

## 14. 推荐下一步

建议下一批进入开发闭环：

1. 先实现后端 `InsightBrief` 契约、模板 registry 和 deterministic builder。
2. 用 Reddit/Amazon fixture 写 contract tests，确保输出中文、证据可回溯、低可信可降级。
3. 再接 Web/Extension UI，避免先做界面后发现数据结构不够。
4. 完成本地测试与视觉验收后，再讨论是否接入 AI provider 润色层。

本文件为产品与工程执行草案，尚未代表生产发布、provider 调用或外部平台授权。
