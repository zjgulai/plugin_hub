---
title: Amazon 与 Reddit 双插件真实浏览器 E2E 验收 Runbook
doc_type: workflow
module: workflows
topic: split-extension-browser-e2e
status: review
created: 2026-06-18
updated: 2026-06-18
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
| Reddit negative isolation | Amazon page with no Reddit bar | pending |
| Shared backend | Two platform-filtered API responses | pending |

## 自动化阻塞记录

2026-06-18 当前桌面环境里，以下自动化路径已验证不可用：

- AppleScript 可读 tab/title，但 `execute javascript` 被 Chrome 拒绝。
- Google Chrome / Playwright Chromium 进程存活，但 `--remote-debugging-port` 不开放 CDP。
- Playwright headful persistent context 空白页也超时。
- Playwright headless 不加载 MV3 extension service worker。
- Computer Use 读取 Google Chrome 状态超时。

因此，在该环境恢复可交互 Chrome 控制能力之前，本 runbook 需要人工执行，或迁移到支持 headful Chrome extension 自动化的 CI/本地机器执行。
