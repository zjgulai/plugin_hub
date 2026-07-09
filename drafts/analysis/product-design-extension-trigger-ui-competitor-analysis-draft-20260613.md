---
title: 插件自动触发与页面展示竞品分析草稿
doc_type: analysis
module: product-design
topic: extension-trigger-ui
status: draft
created: 2026-06-13
updated: 2026-06-13
owner: self
source: human+ai
---

# 插件自动触发与页面展示竞品分析草稿

## 结论

当前项目的核心差距不是采集能力，而是入口形态。现有插件已经有 Amazon/Reddit 页面识别、Amazon 多页评论采集、Reddit `.json` 主入口与 DOM fallback，但用户仍必须打开 popup 手动触发。竞品把入口直接注入商品页或内容页，形成“打开页面即识别、即分析、即下载/回传”的低摩擦工作流。

产品设计方向应改为：

- Amazon 商品页自动触发：打开 `/dp/{ASIN}` 或 `/gp/product/{ASIN}` 后，内容脚本自动注入页面级 VOC 操作台。
- Reddit thread 自动触发：打开 `/r/{subreddit}/comments/{threadId}/...` 后，注入 Reddit 版 VOC 操作台。
- 免登录默认可用：允许当前页识别、采集预览、schema 映射预览、导出本地 JSON/CSV、回传到用户已配置的私有服务器。
- 登录只用于：云端工作区、历史 run、团队协作、托管 AI 额度、跨设备配置同步。
- UI 不做单纯“评论下载器”，而做“Schema-first VOC Command Bar”：突出采集状态、覆盖率、schema 映射、回传目标和 AI insight 入口。

## 竞品矩阵

| 产品 | 入口触发 | 页面展示 | 免登录/登录 | 核心卖点 | 可借鉴 | 应避免 |
| --- | --- | --- | --- | --- | --- | --- |
| VOC.AI / Shulex ChatGPT for Amazon | 打开 Amazon listing 页后出现 Review Analysis / Download / Listing Optimization 入口 | 商品页标题附近或图片下方的横向按钮组，强调一键分析 | Chrome Web Store 文案强调可直接试用，完整洞察通常导向账号体系 | Amazon 评论分析、Listing 优化、Review download、消费者洞察 | 入口必须贴近商品主体，按钮命名直接对应运营任务 | 过度偏 Amazon，难以解释跨平台 raw VOC 融合 |
| Shulex Copilot Sidebar | 在多电商站点侧边栏常驻/触发 | 浏览器侧边栏 + 页面内按钮 | 文案强调无需 ChatGPT 账号 | AI assistant、运营建议、报告自动化 | 对“随时可问”的 AI 侧边栏有启发 | 侧边栏容易与我们的 schema/ETL 采集主流程混淆 |
| VocoVoca Amazon Reviews Extractor | 打开 Amazon 相关页面后提供导出动作 | 简洁横条，核心是 Amazon 评论一键导出 | 截图中突出 Free 与展开入口 | 批量导入 ASIN、一键导出 Excel，字段包括 title/content/author/date/images/videos/rating/helpful | 低门槛、轻 CTA、免费入口 | 只强调导出，缺少结构化回传和策略分析差异 |
| VOCO | Amazon/Facebook/Reddit/Wayfair 等平台页面采集 | 页面中横向操作区，Amazon 场景有用户画像分析/评论下载分段按钮 | 截图有登录/注册，但下载/分析入口先展示 | 覆盖 Amazon、Facebook、Reddit、Wayfair；支持 Excel 导出和 GPT 多维分析 | 多平台定位与我们的 Amazon + Reddit 方向接近 | 如果只做平台列表，容易牺牲字段一致性与融合模型稳定性 |
| Proboost Vocpro | 多平台评论解析插件 | 以 VoC 智能分析为主，触发细节公开资料较少 | Chrome Web Store 可安装，完整能力可能导向服务体系 | 支持 Amazon、TikTok、YouTube、Walmart、Instagram、eBay、AliExpress；用户画像、购买动机、痛点、改进方向 | 卖点语言接近“业务决策”，不是单纯采集 | 平台过多会稀释 P0，当前应守住 Amazon + Reddit |
| Octoparse VOC | 浏览 review 页面、输入产品 URL/关键词、上传 review 文件 | 更像工具型入口，强调报告生成 | 未见页面注入细节证据 | Product research、竞品分析、情感分析、Customer Q&A highlights | “URL/关键词/文件”三入口可作为后台补充 | 不适合作为浏览器插件首屏主路径 |
| Browse AI | 用户训练 robot 后定时抽取与监控 | 点选式训练、结果表、监控任务 | 面向 SaaS 工作区 | No-code 抽取、监控、API/Webhook、定时任务、动态页面动作 | 采集配置、字段选择、监控与回传链路值得借鉴 | 不是垂直 VOC 产品，缺少 Amazon/Reddit 语义层 |

## 当前项目状态判断

当前扩展已具备自动触发的基础条件：

- `manifest.config.ts` 已配置 Amazon 和 Reddit 的 `content_scripts.matches`。
- `page-detect.ts` 已能识别 Amazon product detail、Amazon reviews、Reddit thread。
- `capture.ts` 已支持 Amazon product detail embedded reviews、Amazon reviews 多页 link walk、Reddit `.json?raw_json=1` 与 DOM fallback。

缺口集中在页面 UI：

- `content-script.ts` 只派发 `plugin-hub-page-detected` 事件并监听 popup 消息。
- 没有 Shadow DOM 容器。
- 没有页面级 command bar/drawer。
- 没有游客态采集预览。
- 没有把 schema/coverage/回传状态展示给用户。

## 设计原则

### 1. 页面级入口优先，popup 降级为设置入口

插件 popup 适合配置 API 地址、查看版本、设置默认行为，不适合作为主采集入口。主入口必须在 Amazon/Reddit 页面内自动出现。

### 2. 免登录不是“全功能免费”

免登录应覆盖公开页面上的即时价值：

- 识别当前页面对象：ASIN、marketplace、subreddit、threadId。
- 采集当前页或有限页预算。
- 预览 raw item 与 canonical VOC units。
- 展示 coverage confidence、stop reason、字段缺失。
- 导出本地 JSON/CSV。
- 回传到用户自定义私有服务器。

登录应绑定长期价值：

- 云端保存 run 历史。
- 团队工作区。
- 托管 AI 分析额度。
- 自定义 skills/prompt 模板云同步。
- 跨设备配置。

### 3. Amazon 与 Reddit 必须用同一个认知模型展示

UI 不应分别做成“Amazon 下载器”和“Reddit 下载器”。两者都应进入同一个 VOC pipeline：

```text
Page Detected -> Raw Capture -> Schema Mapping -> Canonical VOC -> AI Insight -> Strategy Output -> Save/Export
```

Amazon 的主对象是 ASIN/review；Reddit 的主对象是 thread/comment。展示层允许平台差异，但流程、状态、字段映射和回传目标必须一致。

### 4. 不复制竞品的大横幅堆按钮

附件里的横幅证明了市场教育已经存在，但也暴露了三个问题：

- 按钮多但状态弱：用户不知道采集了多少、覆盖率如何、是否可回传。
- 登录/注册过早：容易打断第一次体验。
- 缺少 schema 透明度：用户难以判断后续 AI 洞察基于哪些字段。

我们的差异化应放在“采集可信度 + schema 可解释 + 私有回传 + prompt/skill 可配置”。

## 推荐 UI 结构

### 折叠态：VOC Command Bar

位置：

- Amazon：商品标题区域下方或 buying box 上方，避免遮挡主图和购买按钮。
- Reddit：thread 标题下方、评论区上方。

内容：

- 左侧：Plugin Hub 标识、平台 badge、Guest mode 状态。
- 中间：检测对象。
  - Amazon：ASIN、marketplace、rating/review count、entry kind。
  - Reddit：subreddit、threadId、comment estimate、source mode `.json`/DOM。
- 右侧主操作：
  - `采集预览`
  - `采集并回传`
  - `AI 洞察`
  - `展开`

### 展开态：VOC Drawer

Tabs：

- `采集计划`：页预算、采集范围、字段覆盖、停止条件。
- `Raw VOC`：原始 item 预览、平台字段。
- `Schema 映射`：raw -> canonical 字段映射、缺失字段、置信度。
- `AI 洞察`：默认模板输出，允许高级用户修改 skill/prompt。
- `回传`：API base URL、run id、上传状态、失败重试。

### 首次体验

首屏文案应避免“先注册”。推荐：

```text
Guest mode 可用：先采集当前页面并预览 schema。登录仅用于云端历史与团队协作。
```

## 技术实现建议

### 内容脚本

- 保留当前 `content-script.ts` 的消息监听。
- 增加页面 UI bootstrap：
  - `detectPage(window.location.href)` 返回 Amazon/Reddit 时挂载。
  - 使用 Shadow DOM 隔离样式，减少与 Amazon/Reddit CSS 冲突。
  - 使用 `MutationObserver` 或轻量 URL polling 处理 Reddit 新版页面内导航。
  - 将折叠状态、API base URL、默认页预算写入 `chrome.storage.local`。

### UI 架构

- 新增 `apps/extension/src/content/ui/ContentApp.tsx`。
- 复用现有 React 依赖，不引入新 UI 框架。
- popup 保留为设置页，但主 CTA 从“采集并回传”调整为“打开页面内操作台/配置 API”。

### 数据链路

- `采集预览` 调用现有 `captureCurrentPage`，不上传。
- `采集并回传` 先采集，再复用 `UPLOAD_COLLECTION_MESSAGE_TYPE`。
- `AI 洞察` 在 MVP 可展示本地 mock 或后端策略 notes；正式版调用后端 insight endpoint。
- 所有状态显示 `raw_item_count`、`voc_unit_count`、`coverage_confidence`、`stop_reason`。

## Product Design 简报草稿

设计对象：

- Chrome extension 的页面内 VOC 操作台，不是官网 dashboard，也不是 popup 优化。

目标行为：

- 用户打开 Amazon 商品链接或 Reddit thread 链接后，插件自动识别页面并展示可折叠 UI。
- 用户无需登录即可完成当前页采集预览、schema 映射查看、本地导出、私有服务器回传。
- 登录仅作为高级工作区入口。

视觉来源：

- 参考附件中 VOC.AI、VocoVoca、VOCO 的 Amazon 页面注入式横条。
- 遵循当前项目监控台的稳重、数据资产化风格：高对比边框、低饱和背景、green/teal/rust 状态色。

交互等级：

- 需要完整交互方案：折叠/展开、平台切换状态、采集进度、上传状态、错误态、schema tab、guest/login 分界。

下一步：

- 先生成 3 个视觉方向，再选择其中一个进入代码实现。

## 调研来源

- Chrome Web Store: ChatGPT for Amazon with GPT4 Shulex Copilot, https://chromewebstore.google.com/detail/chatgpt-for-amazon-with-g/fchbhcjlkcdchcaklpkdofllfoimelgb
- Chrome Web Store: Shulex Copilot ChatGPT E-commerce Sidebar, https://chromewebstore.google.com/detail/shulex-copilotchatgpt-e-c/imbdabdbipefiieekabpncjcambojjdg
- Chrome Web Store: VocoVoca Amazon Reviews Extractor, https://chromewebstore.google.com/detail/vocovoca-amazon-reviews-e/mbjnhblbmoijhjlbmojpobddlebheoai
- Chrome Web Store: VOCO E-commerce social media platform user review download analysis, https://chromewebstore.google.com/detail/voco-e-commerce-social-me/bclaoecbblljmoaanbbhcdadmhcejhdm
- Chrome Web Store: Proboost Vocpro, https://chromewebstore.google.com/detail/proboost-vocpro/nmjpnkhpmlfolhkaigjbjfhboekmmblj
- Chrome Web Store: Octoparse VOC, https://chromewebstore.google.com/detail/octoparse-voc-ai-review-r/dcejniggmfiedegekbcindccneeegeoi
- Browse AI, https://www.browse.ai/
- Chrome for Developers: Manifest content scripts, https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts
- Chrome for Developers: Content scripts, https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts
