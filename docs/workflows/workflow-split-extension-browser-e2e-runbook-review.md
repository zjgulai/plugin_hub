---
title: Amazon 与 Reddit 双插件真实浏览器 E2E 验收 Runbook
doc_type: workflow
module: workflows
topic: split-extension-browser-e2e
status: review
created: 2026-06-18
updated: 2026-06-19
owner: self
source: human+ai
---

# Amazon 与 Reddit 双插件真实浏览器 E2E 验收 Runbook

## 目标

验证 Amazon VOC 插件和 Reddit VOC 插件已经拆成两个独立 Manifest V3 扩展，同时继续共用同一个本地私有后台。

本 runbook 是真实浏览器 gate，不替代单元测试、typecheck、lint、build 和 zip package 校验。

## 边界

- `read-only`: 浏览第三方公开页面并读取页面内容。
- `local write`: 插件只向本机 `plugin_hub_api` 写入 collection run / raw item / VOC unit。
- `production unchanged`: 不部署生产服务，不写生产数据库。
- `no provider call`: 不调用 AI provider，不触发外部洞察生成。
- `no Web Store publish`: 不发布、不安装线上商店版本。

## 前置条件

1. 构建两个插件：

```bash
pnpm --filter @plugin-hub/extension build
```

2. 打包并校验两个 zip：

```bash
pnpm package:extension
pnpm verify:extension
```

3. 启动一个临时本地后台。若 `8000` 被其他项目占用，使用 `8010`：

```bash
PLUGIN_HUB_DATABASE_URL=sqlite+pysqlite:////Users/pray/project/plugin_hub/tmp/debug/split-extension-browser-e2e.db \
  uv --directory apps/api run uvicorn plugin_hub_api.main:create_app --factory --host 127.0.0.1 --port 8010
```

4. 确认后台为空：

```bash
curl -fsS 'http://127.0.0.1:8010/api/voc-units'
```

期望：

```json
{"items":[]}
```

## Chrome Profile 策略

优先使用两个隔离的 Chrome profile：

- Amazon profile: 只加载 `apps/extension/dist/amazon`
- Reddit profile: 只加载 `apps/extension/dist/reddit`

如果只能使用同一个 Chrome profile，必须一次只启用一个插件，完成一个平台后禁用再切换另一个插件。

不要在同一个验收步骤里同时启用两个插件，否则无法证明 host permission 和 content script 已经按平台隔离。

## Browser Harness 自动化层

Browser Harness 可作为本 runbook 的真实 Chrome 操作层，用于替代一部分人工点击、截图和 Network 取证。它不改变插件、后台或第三方站点访问权限。

边界：

- 默认 `read-only`: 读取当前 Chrome tab、点击插件 `采集预览`、保存截图和本地 JSON 诊断结果。
- 默认 `no local write`: 不点击 `采集并回传`，不点击 `服务端补采`。
- 可选 `local write`: 仅当显式设置 `PLUGIN_HUB_CREATE_SERVER_TASK=1` 时，才会点击 Reddit 面板里的 `服务端补采`，向本机后台创建 collection task。
- `production unchanged`: 不部署生产服务，不写生产数据库。
- `no provider call`: 不调用 AI provider。
- 不用于绕过 Reddit 或其他第三方平台的网络安全、登录或授权限制。

安装与连接检查：

```bash
browser-harness --doctor
```

期望至少满足：

- `chrome running` 为 ok。
- `daemon alive` 为 ok。
- `active browser connections` 大于 0。

Reddit blocked 诊断脚本：

```bash
PLUGIN_HUB_BROWSER_E2E_API_BASE=http://127.0.0.1:8010 \
  browser-harness < scripts/browser-harness/reddit-blocked-diagnostic.py
```

若当前 Chrome 没有打开目标 Reddit thread，可显式给 URL：

```bash
PLUGIN_HUB_REDDIT_THREAD_URL='https://www.reddit.com/r/Coffee/comments/1eka2tx/ranking_the_importance_of_your_coffee_gear/' \
PLUGIN_HUB_BROWSER_E2E_API_BASE=http://127.0.0.1:8010 \
  browser-harness < scripts/browser-harness/reddit-blocked-diagnostic.py
```

输出与证据：

- stdout 打印诊断 JSON。
- 截图默认写入 `tmp/screenshots/`。
- 诊断 JSON 默认写入 `tmp/debug/`。
- 当 Reddit `.json?raw_json=1` 返回 `403` 时，结论是 `blocked_requires_login_or_developer_token`，不是插件拆分失败。

## Reddit 后端授权采集

当 Reddit 浏览器页或 `.json?raw_json=1` 被网络安全策略拦截时，后端 collection worker 支持使用 Reddit OAuth app-only token 走 `https://oauth.reddit.com`。

环境变量：

```bash
export PLUGIN_HUB_REDDIT_CLIENT_ID='...'
export PLUGIN_HUB_REDDIT_CLIENT_SECRET='...'
export PLUGIN_HUB_REDDIT_USER_AGENT='PluginHubVOC/0.1 by your-reddit-username'
```

运行一次 pending task：

```bash
PLUGIN_HUB_DATABASE_URL=sqlite+pysqlite:////Users/pray/project/plugin_hub/tmp/debug/split-extension-browser-e2e.db \
  pnpm collection:worker:once
```

授权边界：

- `local write`: 仅写入本机后台数据库中的 collection run / raw item / VOC unit。
- `production unchanged`: 不部署生产服务，不写生产数据库。
- `no provider call`: 不调用 AI provider。
- Reddit `401/403` 会标记为 `reddit_capture_requires_authorized_access`，不会被当成普通可重试 worker error。

## Amazon 插件验收

1. 打开 `chrome://extensions/`。
2. 开启 Developer mode。
3. Load unpacked: `apps/extension/dist/amazon`。
4. 打开一个 Amazon review 页面，例如目标 ASIN 的 `product-reviews` 页面。
5. 验证页面出现 Plugin Hub 内容栏，且文案指向 Amazon VOC。
6. 将 API 地址设置为本地后台，例如：

```text
http://127.0.0.1:8010
```

7. 点击采集预览，确认 raw item 数量大于 0。
8. 点击采集并回传。
9. 查询后台：

```bash
curl -fsS 'http://127.0.0.1:8010/api/voc-units?platform=amazon'
```

通过条件：

- `items.length > 0`
- 每条 `platform` 为 `amazon`
- 至少一条记录保留 Amazon review source object id
- 页面内容栏显示已回传 run id、raw item count 和 VOC unit count

隔离负向检查：

- 在同一 profile 打开 Reddit thread 页面。
- Amazon 插件不应出现 Reddit VOC 内容栏。
- 后台不应新增 `platform=reddit` 的记录。

## Reddit 插件验收

1. 打开另一个隔离 Chrome profile。
2. 打开 `chrome://extensions/`。
3. 开启 Developer mode。
4. Load unpacked: `apps/extension/dist/reddit`。
5. 打开一个公开 Reddit thread 页面。
6. 验证页面出现 Plugin Hub 内容栏，且文案指向 Reddit VOC。
7. 将 API 地址设置为同一个本地后台：

```text
http://127.0.0.1:8010
```

8. 点击采集预览，确认 thread 或 comment raw item 数量大于 0。
9. 点击采集并回传。
10. 查询后台：

```bash
curl -fsS 'http://127.0.0.1:8010/api/voc-units?platform=reddit'
```

通过条件：

- `items.length > 0`
- 每条 `platform` 为 `reddit`
- 至少一条 `t3_` thread 或 `t1_` comment source object id 被保留
- 页面内容栏显示已回传 run id、raw item count 和 VOC unit count

隔离负向检查：

- 在同一 profile 打开 Amazon review 页面。
- Reddit 插件不应出现 Amazon VOC 内容栏。
- 后台不应新增 `platform=amazon` 的记录。

## 共享后台验收

两个插件必须写入同一个后台实例，但平台记录必须可区分：

```bash
curl -fsS 'http://127.0.0.1:8010/api/voc-units?platform=amazon'
curl -fsS 'http://127.0.0.1:8010/api/voc-units?platform=reddit'
```

通过条件：

- Amazon 查询只返回 Amazon VOC units。
- Reddit 查询只返回 Reddit VOC units。
- collection run 中的 `source_platform`、`capture_method` 和 `coverage_scope` 与实际页面一致。

## 证据模板

| Gate | Evidence | Result |
| --- | --- | --- |
| Amazon plugin loaded | Chrome extensions page screenshot | pending |
| Amazon content bar | Amazon review page screenshot | pending |
| Amazon upload | API response / run id | pending |
| Amazon negative isolation | Reddit page with no Amazon bar | pending |
| Reddit plugin loaded | Chrome extensions page screenshot | pending |
| Reddit content bar | Reddit thread screenshot | pending |
| Reddit upload | API response / run id | pending |
| Reddit blocked diagnostic | Browser Harness JSON + screenshot + Network 403 evidence | pending |
| Reddit negative isolation | Amazon page with no Reddit bar | pending |
| Shared backend | Two platform-filtered API responses | pending |

## 自动化状态记录

2026-06-18 桌面环境里，以下自动化路径曾验证不可用：

- AppleScript 可读 tab/title，但 `execute javascript` 被 Chrome 拒绝。
- Google Chrome / Playwright Chromium 进程存活，但 `--remote-debugging-port` 不开放 CDP。
- Playwright headful persistent context 空白页也超时。
- Playwright headless 不加载 MV3 extension service worker。
- Computer Use 读取 Google Chrome 状态超时。

2026-06-19 Browser Harness 已验证可用：

- 可连接真实 Chrome tab。
- 可读取页面 DOM 和插件 open shadow DOM。
- 可点击插件 `采集预览`。
- 可保存页面截图。
- 可记录 Reddit `.json?raw_json=1` 的 CDP Network response。

剩余 blocker：

- 如果 Reddit 返回 `You've been blocked by network security` 或 `.json?raw_json=1` 返回 `403`，Browser Harness 只能记录证据，不能把拦截页转成可采集内容。
- 需要使用用户可访问的登录态页面，或在后台实现 Reddit developer token / OAuth 授权采集路径。
