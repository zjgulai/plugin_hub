---
title: Plugin Hub Loop 42 PR Review And CI Acceptance
doc_type: acceptance_report
module: product_engineering
topic: plugin-hub-pr-review-and-ci-gate
status: accepted
created: 2026-07-10
updated: 2026-07-10
owner: self
source: human+ai
---

# Plugin Hub Loop 42 PR 审查与 CI 验收

## 1. 结论

Draft PR #3 已建立服务器侧 CI 门禁。API、Web/Extension、Deployment Config 三个 job 在首个实现提交 `6652e1a` 上全部通过。

人工审查未发现未处理的 P0/P1 业务代码问题；接受并修复了一个 CI 浅克隆问题。Codex CLI 二审因本机 CLI 版本不支持配置模型而没有产生结论，不能表述为二审通过。

本轮没有 merge、生产部署、数据库操作、migration、backup、timer、Nginx、credential、provider、live capture/upload 或 Web Store 操作。

## 2. 实际改动

- 新增 `.github/workflows/ci.yml`；
- workflow 只授予 `contents: read`；
- checkout、setup-node、pnpm setup、setup-uv 均固定到官方 tag 对应的完整 commit SHA；
- CI 不引用 `secrets.*`，Compose 使用两个 32 字符 synthetic key；
- 同一 PR 的旧运行会通过 concurrency 自动取消；
- workflow 仅在 pull request 和 `main` push 上运行，不包含 deploy job。

## 3. 审查结果

### Accepted

Deployment Config 需要执行 `git diff --check origin/main...HEAD`，但 checkout 默认浅克隆不保证存在 base history。该 job 已增加 `fetch-depth: 0`，GitHub 首轮运行证明 base diff 可执行。

### No Accepted Runtime Finding

- collection run、raw、canonical 仍由同一 repository transaction 提交；
- API read/write key 使用 constant-time compare，全部 `/api` router 受保护；
- snapshot migration 具有 checksum、unknown-version refusal、append-only trigger 和非空 rollback 阻断；
- backup 保持 temp snapshot、完整性验证、atomic rename、manifest/hash/count 和 verified-only retention；
- Web key 仅在 server component/server action 加载，客户端只触发 `router.refresh()`；
- Extension key 保存在 `chrome.storage.local`，由 background request path 注入；
- Reddit/Amazon/Instagram source URL 使用明确 HTTPS host allowlist。

### Rejected Scope Expansion

没有证据支持在本轮引入新数据库、迁移框架、credential service、发布自动化或业务抽象。

### Unavailable Second Review

`codex review --uncommitted` 在 transport retry 后返回：

```text
The 'gpt-5.6-sol' model requires a newer version of Codex.
```

命令 exit 1，没有模型 finding，也没有 clean review 结论。人工审查和自动化门禁是本轮可接受证据。

## 4. 本地等价验证

### API

- frozen dependency sync：passed；
- pytest：178 passed；
- ruff：passed；
- mypy：passed；
- sdist/wheel build：passed。

### Web And Extension

- frozen pnpm install：passed；
- Web：36 tests；
- Extension：101 tests；
- ESLint、typecheck、Web/三插件 build：passed；
- extension version governance：8 tests；
- Amazon/Reddit/Instagram registry、manifest 和 package 均为 `0.2.1`；
- 三个 package verify 均为 15 entries。

### Deployment Config

- Compose config：passed；
- `zsh -n`：passed；
- migration dry-run Python compile：passed；
- base branch 与 worktree diff check：passed；
- workflow YAML、完整 SHA、最小权限、无 secret 引用和 synthetic key 长度：passed。

## 5. GitHub Actions 验收

实现 run：`https://github.com/zjgulai/plugin_hub/actions/runs/29102813050`

| Job | 结果 | 时长 |
| --- | --- | ---: |
| API | success | 24s |
| Deployment Config | success | 17s |
| Web and Extension | success | 1m14s |

run event 为 `pull_request`，head 为 `6652e1a53fda2c8bcb8f64c8911653a541dc5ab4`。最终 docs-only closeout head 仍需重复通过同一 workflow，最终状态以 PR checks 为准。

## 6. 仓库治理边界

- PR #3 在实现 run 后仍为 Open、Draft、Mergeable；
- rulesets 只读查询返回空列表；
- branch protection API 未返回可确认配置；
- 本轮没有修改 repository settings 或 required checks。

将 CI job 设为 required checks 会改变仓库合并策略，需要单独授权。

## 7. 最终边界

```text
CI implemented / first pull_request run green / PR remains Draft
production unchanged / no merge / no deploy / no database operation
```
