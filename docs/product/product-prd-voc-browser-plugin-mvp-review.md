---
title: VOC 浏览器插件 MVP 产品需求文档
doc_type: prd
module: product
topic: voc-browser-plugin-mvp
status: review
created: 2026-06-05
updated: 2026-06-05
owner: self
source: human+ai
---

# VOC 浏览器插件 MVP 产品需求文档

## 1. 产品定位

面向中小型跨境电商品牌和商家的 Chrome 浏览器插件，用于在 Amazon 与 Reddit 场景中采集 VOC 原始证据，回传到私有服务器，经 schema 化 ETL 后生成可自定义的 AI 洞察与策略输出。

第一版产品不是通用爬虫平台，也不是通用 AI sidebar。它的核心价值是让垂直商家把分散在平台页面上的用户声音转成可保存、可追踪、可复盘、可自定义分析的品牌 VOC 数据资产。

## 2. 目标用户

P0 用户为已有明确品类、品牌或竞品方向的中小跨境电商商家，包括：

- 品牌创始人或运营负责人
- 产品经理或选品负责人
- Listing、内容、广告运营人员
- 小团队里的 VOC / 市场调研负责人

典型业务场景：

- 新品开发前，采集竞品 Amazon 评论和 Reddit 讨论，识别痛点、期望、功能缺口。
- Listing 优化前，提取好评卖点、差评抱怨、关键词表达和使用场景。
- 广告或内容策略前，找出用户真实语言、争议点、购买阻力和高频价值感知。
- 品类持续监控中，定期回传核心 ASIN 与 Reddit 话题的 VOC 变化。

## 3. 问题定义

当前市场工具的主要缺口不是“完全不能采集”，而是采集、保存、分析和决策链路被拆散：

- 数据采集字段不能按垂直商家需求自定义。
- 提取结果常停留在本地导出或临时页面，不能稳定回传并沉淀到私有数据仓。
- 分析维度、prompt、skills、标签体系和策略方向不能由商家按品类调整。
- 不同平台的数据结构差异被弱化，导致 Reddit 评论树和 Amazon review 强信号无法可信融合。
- 采集覆盖率、分页状态、访问受限和字段缺失没有被记录，后续 AI 洞察容易把低可信数据当成事实。

## 4. 第一版范围

P0 平台只包含：

- Amazon
- Reddit

暂缓平台：

- TikTok
- 独立站
- Shopify 店铺页
- Seller Central 深度接入
- Browse AI 式云端 robot
- 大规模代理池或托管 actor

P0 闭环：

```text
浏览器页面
→ Chrome 插件采集
→ 私有服务器回传
→ schema 化 ETL
→ 品牌 VOC hub
→ AI 洞察
→ AI 策略输出
```

## 5. 竞品与采集方式判断

已参考的产品类型分为四类：

| 类型 | 代表产品 | 主要能力 | 对本产品的启发 |
| --- | --- | --- | --- |
| 电商 VOC / AI sidebar | Proboost Vocpro、Shulex Copilot、VOC 类插件、VocoVoca | 评论提取、AI 总结、选品或运营辅助 | 证明商家愿意在浏览器内完成 VOC 分析，但自定义 schema、私有回传和分析链路仍是差异点 |
| Amazon 运营工具 | Helium 10、Seller Assistant | 选品、利润、竞品、Listing 辅助 | 不直接竞争全套运营工具，优先切 VOC 深度 |
| 通用采集工具 | Browse AI、Thunderbit、Web Scraper | 训练 robot、字段抽取、监控、API/webhook | 吸收任务化采集、监控、回传、字段映射，不复制泛用 robot 平台 |
| 托管 scraper / actor | Apify 等 | 代理、重试、托管执行、数据集导出 | 作为 P1/P2 扩展，不作为 P0 主路径 |

使用频率判断：

- Amazon 核心 ASIN/竞品 VOC：中小商家可能按周或按关键运营动作采集。
- Reddit 品类/话题 VOC：新品调研、趋势监控、内容策略前更可能按项目制采集。
- 插件触发采集：P0 应支持手动触发和任务记录；自动定时监控放入 P1。

以上频率为基于业务流程的推断，不是已验证的用户行为数据。

## 6. 采集策略

确认采用任务化混合采集。

### 6.1 Amazon

P0 主入口为插件端页面采集：

- 商品页
- 评论页
- 星级过滤后的评论页
- 排序后的评论页

Amazon 多页采集不能设计成简单的固定 `pageNumber` 循环。每次采集必须生成 `collection_run`，并记录：

- `asin`
- `parent_asin`
- `marketplace`
- `source_url`
- `requested_page`
- `observed_page`
- `sort_by`
- `filter_by_star`
- `verified_filter`
- `media_filter`
- `variant_context`
- `page_hash`
- `duplicate_ratio`
- `stop_reason`
- `coverage_scope`
- `coverage_confidence`
- `parser_version`

默认采集段：

- `recent_all`
- `critical_1_2_star`
- `positive_4_5_star`
- `media_reviews`
- `verified_only`

默认停止条件：

- 没有下一页
- 达到页数、条数或时间预算
- 页面 hash 重复
- 重复评论比例过高
- 访问受限
- 验证码
- 空 DOM
- 用户主动停止

P0 不承诺 Amazon 全量评论，只承诺已采集范围可审计。

### 6.2 Reddit

P0 主入口为插件端 `.json` 采集：

- 用户打开 Reddit thread URL。
- 插件请求同 URL 的 `.json?raw_json=1` 结构。
- `.json` 失败时使用 DOM fallback。

Reddit thread JSON 需要拆分为：

- `raw_reddit_thread_v1`
- `raw_reddit_comment_v1`

关键要求：

- 保留 `t3_` post 与 `t1_` comment 的对象类型。
- 保留 `thread_id`、`comment_id`、`link_id`、`parent_id`。
- 保留评论树 `depth`、`permalink`、`subreddit`、`flair`。
- 识别 `more` node，不把未展开评论当作不存在。
- 标记 deleted、removed、locked、archived 等状态。
- 不把 comment 脱离 thread 单独解释。

P0 可不展开全部 `more` node，但必须记录缺口。

## 7. Collection Method Audit

PRD、开发计划和验收必须以 `collection-method-audit` 为前置 gate。没有通过审计的采集路径不进入 P0 承诺。

### 7.1 审计目标

每种采集入口必须回答：

- primary 入口是什么
- fallback 入口是什么
- future-scale 入口是什么
- 字段完整率如何
- 覆盖率边界是什么
- 访问受限时如何标记
- 哪些字段会影响后续 AI 洞察可信度

### 7.2 Amazon 样本审计

必须覆盖：

- 普通商品评论页多页翻页
- 1/2 星差评过滤
- 4/5 星好评过滤
- 最近排序
- Top review 排序
- verified purchase
- 带图/视频评论
- variant 商品评论混合或切换
- 更多评论入口缺失
- 访问受限、验证码或空页

### 7.3 Reddit 样本审计

必须覆盖：

- 普通 self post 与评论树
- 深层 replies
- deleted / removed 评论
- `more` node
- link / image / video 类型帖子
- locked / archived thread

### 7.4 P0 通过标准

采集入口进入 P0 需要满足：

- raw 字段能保真保存。
- canonical 字段能稳定映射。
- 字段缺失能被质量标记表达。
- 采集覆盖率能被解释。
- 停止原因能被追踪。
- 低可信数据不会被当成强证据输出。

## 8. Schema 融合策略

确认采用融合模型 A：

```text
raw_source_item
→ canonical_voc_unit
→ platform_extension
→ relation_edges
→ enriched_voc_signal
→ insight
→ strategy_note
```

### 8.1 raw_source_item

raw 层按平台保真，不做强行统一：

- `raw_amazon_review_v1`
- `raw_reddit_thread_v1`
- `raw_reddit_comment_v1`

raw 层保存：

- 原始字段
- 原始 URL
- 原始采集时间
- raw schema version
- parser version
- collection run id
- raw payload hash

### 8.2 canonical_voc_unit

统一 VOC 核心字段：

- `voc_unit_id`
- `platform`
- `source_kind`
- `source_object_id`
- `collection_run_id`
- `source_url`
- `created_at`
- `captured_at`
- `author_display`
- `author_type`
- `title`
- `body`
- `language`
- `media_refs`
- `commercial_object_type`
- `brand`
- `product_title`
- `asin`
- `parent_asin`
- `marketplace`
- `category`
- `thread_id`
- `parent_id`
- `depth`
- `reply_role`
- `quality_flags`
- `coverage_confidence`

### 8.3 platform_extension

Amazon 扩展字段：

- `rating`
- `verified_purchase`
- `helpful_vote`
- `review_position`
- `review_page`
- `sort_by`
- `filter_by_star`
- `variant_context`
- `reviewer_profile_url`

Reddit 扩展字段：

- `subreddit`
- `subreddit_name_prefixed`
- `post_flair`
- `comment_flair`
- `score`
- `upvote_ratio`
- `num_comments`
- `is_submitter`
- `locked`
- `archived`
- `stickied`
- `controversiality`
- `more_node_count`

### 8.4 relation_edges

关系边用于保留结构上下文：

- Amazon review → ASIN
- Amazon ASIN → parent ASIN
- Amazon review → variant context
- Reddit comment → Reddit thread
- Reddit comment → parent comment
- Reddit thread → subreddit
- VOC unit → brand mention
- VOC unit → product feature
- VOC unit → competitor

### 8.5 enriched_voc_signal

AI 增强字段：

- `sentiment`
- `sentiment_confidence`
- `topic`
- `aspect`
- `pain_point`
- `severity`
- `purchase_intent`
- `usage_scenario`
- `feature_request`
- `quality_issue`
- `comparison_target`
- `strategy_relevance`
- `evidence_strength`

Amazon 的 rating、verified、helpful 是强显式信号。Reddit 的情绪、购买意图和产品相关性更多依赖 AI 推断，因此必须记录推断置信度。

## 9. AI 洞察与策略输出

P0 输出不追求复杂自动化，而追求可解释、可复盘。

默认 insight 模板：

- 高频痛点
- 产品缺陷
- 好评卖点
- 使用场景
- 用户语言
- 竞品弱点
- 需求机会
- 购买阻力
- 内容关键词
- Listing 优化建议
- 广告创意方向

默认 strategy_note 模板：

- Listing 标题/五点/描述优化方向
- 产品功能或包装改进方向
- FAQ 与售前解释方向
- 广告素材与文案方向
- Reddit 社群内容切入方向

默认模板必须可用；高级用户可以修改 schema 映射、prompt、skills、标签和策略输出方向。

## 10. P0 功能清单

### 10.1 Chrome 插件

- 识别当前页面平台。
- 识别 Amazon ASIN / Reddit thread。
- 触发采集任务。
- 展示采集进度。
- 展示已采集条数、页数、停止原因。
- 展示字段完整率和低可信状态。
- 将采集结果回传到私有服务器。

### 10.2 后端

- 接收 collection run。
- 保存 raw payload。
- 执行 schema 校验。
- 生成 canonical VOC unit。
- 保存平台扩展字段。
- 生成关系边。
- 执行去重。
- 标记质量问题。
- 触发 AI 分析任务。

### 10.3 VOC Hub

- 按品牌、ASIN、竞品、平台、话题查看 VOC。
- 查看 raw 证据与 canonical 映射。
- 查看采集覆盖率和质量标记。
- 查看 AI 洞察。
- 查看策略输出。
- 支持用户调整分析模板。

## 11. 非目标

P0 不做：

- 全平台通用 scraper。
- Amazon 全量评论承诺。
- Reddit 全量评论树展开承诺。
- 自动绕过验证码或风控。
- 云端代理池。
- Seller Central 深度 API 集成。
- TikTok 和独立站采集。
- 任意网页可视化 robot 训练。
- 完整 BI dashboard。
- 自动执行广告投放或 Listing 发布。

## 12. 技术原则

推荐技术栈：

- Chrome Extension：Manifest V3、TypeScript
- 前端：React 19、Next.js 15、Tailwind CSS
- 后端：Python 3.12+、FastAPI、Pydantic V2
- 数据库：PostgreSQL
- ORM：SQLAlchemy 2.0
- 包管理：pnpm、uv
- 测试：Vitest、pytest

架构原则：

- content script 只负责页面上下文采集和用户交互。
- service worker 负责受控网络请求与消息调度。
- 后端不信任插件 payload，必须重新校验 schema。
- raw 数据不可丢弃。
- AI 输出必须能追溯到 VOC 证据。
- 采集失败和字段缺失必须显式表达。

## 13. 风险与约束

### 13.1 Amazon 访问风险

Amazon 评论入口、排序、过滤和多页能力可能随账号、市场、访问状态变化。P0 设计不承诺全量，只承诺可解释覆盖。

### 13.2 Reddit more node 风险

Reddit `.json` 可能返回 `more` node。P0 可不完整展开，但必须记录未展开节点数量和字段损失。

### 13.3 合规风险

产品不设计自动绕过验证码、登录限制、访问限制或平台风控。用户安装插件并触发采集时，必须能看到采集范围、回传目标和数据用途。

### 13.4 AI 误判风险

AI 洞察不能脱离证据输出。每个 insight 和 strategy_note 必须能回溯到 VOC unit，并保留证据强度与置信度。

## 14. 成功指标

P0 成功标准：

- 用户能在 Amazon 评论页完成一次多页采集并看到停止原因。
- 用户能在 Reddit thread 完成 `.json` 采集并保留 comment tree 上下文。
- raw 数据、canonical VOC、平台扩展字段和关系边能同时保存。
- Amazon 与 Reddit 的 VOC 能在同一分析模板下产出洞察。
- 每条 AI 洞察能追溯到原始 VOC 证据。
- 用户能修改至少一种分析模板或策略输出方向。
- 采集结果能稳定回传到私有服务器。

## 15. 发布与迭代

### 15.1 P0

- Amazon + Reddit 手动采集。
- collection-method-audit。
- schema 化 ETL。
- 私有服务器回传。
- 默认 AI insight 和 strategy_note 模板。
- 高级用户可修改分析模板。

### 15.2 P1

- 定时监控。
- Reddit `more` node 深度展开。
- Amazon 采集模板自定义。
- 托管 actor 或第三方 API fallback。
- 更完整的 VOC Hub 视图。

### 15.3 P2

- TikTok。
- 独立站和 Shopify。
- Seller Central 数据融合。
- 团队权限。
- 多品牌工作区。
- 更复杂的策略工作流。

## 16. 参考依据

- [Amazon Customer Feedback API](https://developer-docs.amazon.com/sp-api/docs/customer-feedback-api)
- [Amazon Reviews 2023 dataset](https://huggingface.co/datasets/krusagis/Amazon-Reviews-2023)
- [About Amazon customer reviews](https://www.aboutamazon.com/news/retail/amazon-customer-reviews-star-ratings)
- [Reddit API Overview](https://developers.reddit.com/docs/capabilities/server/reddit-api)
- [Reddit Comment model](https://developers.reddit.com/docs/api/redditapi/models/classes/Comment)
- [Chrome extension network requests](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests)
- [Chrome extension permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions)
- [Browse AI](https://www.browse.ai/)
- [Thunderbit Web Scraper](https://thunderbit.com/web-scraper-chrome-extension)
- [Web Scraper](https://webscraper.io/)
- [Apify Reddit Scraper](https://apify.com/prodiger/reddit-scraper)
- [Canopy Amazon Reviews API](https://www.canopyapi.co/amazon-reviews-api)

## 17. 自检结论

- 当前 PRD 聚焦 P0，不把 TikTok、独立站和 Seller Central 放入第一版。
- Amazon 不承诺全量评论，避免采集边界与平台实际访问状态矛盾。
- Reddit 保留 thread/comment 关系，不把评论树压平成无上下文文本。
- raw、canonical、extension、relation、enriched 五层职责清晰。
- AI 输出必须回溯证据，避免把低可信采集结果包装成确定结论。
