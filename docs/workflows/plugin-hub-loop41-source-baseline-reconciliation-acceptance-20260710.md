---
title: Plugin Hub Loop 41 Source Baseline Reconciliation Acceptance
doc_type: acceptance_report
module: product_engineering
topic: plugin-hub-source-baseline-and-release-reconciliation
status: accepted
created: 2026-07-10
updated: 2026-07-10
owner: self
source: human+ai
---

# Plugin Hub Loop 41 源码基线与发布对账验收

## 1. 结论

Loop38-40 已部署能力现已收口为可审阅的 Git 源码基线。后端、客户端、部署恢复资产分别形成原子提交并推送到独立分支，Draft PR #3 已创建。

本轮没有部署、生产数据库操作、凭据变更、provider call、live capture/upload、Web Store 操作或 merge。

## 2. Git 基线

- 基线：`origin/main@fe7395b9f6ca03a0f4d198d3027c4696445c3782`。
- 分支：`codex/data-asset-durability-audit-20260710`。
- Draft PR：`https://github.com/zjgulai/plugin_hub/pull/3`。
- 后端提交：`489387d feat(api): harden and preserve data assets`。
- 客户端提交：`1b07e65 feat(clients): secure asset operations and plugin versions`。
- 部署恢复提交：`4b4469b ops: add verified backup and hardened deployment assets`。
- 治理文档提交：`0aa0972 docs: record data asset production acceptance`。

逐文件边界见 `plugin-hub-loop41-source-baseline-file-manifest-20260710.tsv`。当前 146 个工作区路径全部被 manifest 分类；历史 `output/`、`.kiro/plan`、旧草稿、旧 release packet 和 Chrome 诊断工具未进入应用提交。

## 3. 本地测试

### API

- pytest：178 passed；
- ruff：passed；
- mypy：passed；
- sdist/wheel build：passed。

### Web

- Vitest：36 passed；
- ESLint：passed；
- Next typegen + TypeScript：passed；
- production build：passed。

Next.js 仍提示父目录存在另一个 lockfile，导致 workspace root 自动推断警告；该警告没有阻断 typecheck/build，本轮未删除用户父目录文件，也未扩大范围调整 Next 配置。

### Extension

- Vitest：101 passed；
- ESLint：passed；
- TypeScript：passed；
- Amazon/Reddit/Instagram 三目标 build/package/verify：passed；
- version governance：8 passed；
- 三个插件 registry 与生成 manifest 均为 `0.2.1`，每个 ZIP 15 entries。

### Migration 与 Backup

隔离 fixture 写入 Amazon/Reddit 各一个 collection run，核心计数为 `2/2/2`。随后：

- 显式应用 `0001_analysis_snapshots`；
- 创建 2 个 snapshot run、7 个 artifacts；
- 第二次同输入创建返回 replay；
- UPDATE trigger 生效，非空 rollback 被阻止；
- core counts 前后保持 `2/2/2`；
- `quick_check=ok`，FK issue 为 0；
- 生成 1 个 verified DB 和 1 个 manifest，sidecar 为 0。

Compose config、`zsh -n`、Python compile、`git diff --check` 和高信号 secret scan 均通过。本机缺少 `systemd-analyze`，因此没有把本地 systemd parser 结果计入验收；timer 的真实运行证据来自 Loop39/40 生产验收与本轮只读复核。

## 4. 生产只读对账

- active release：`plugin-hub-20260710T125458Z-insight-snapshots`；
- API image：`sha256:ee3133a50c42b9154b046f3e0f0711275dbcc872ad989a8a66a9b48dfd8b1d8b`，running + healthy；
- Web image：`sha256:90002099a80bec10764fc1d618bbf51dbb3fac3915a5229ce2aecc39b85e937c`，running + healthy；
- worker 使用同一 API image，running；
- backup timer：enabled + active；
- 最新生产 manifest：`plugin_hub_20260710T130106Z.manifest.json`；
- 本机 LaunchAgent 最近 exit code 为 0，最新 age archive 为 `plugin_hub_20260710T130106Z.tar.age`；
- 公共首页返回 200；匿名 data-assets/snapshots API 均返回 401。

受控 runtime hash 对账：

- 本地与 active release：36 checked，0 missing，0 mismatch；
- 本地与运行 API/Web 容器：28 checked，0 mismatch。

这证明当前 runtime 源码已进入本分支提交范围；它不等同于重新部署，也不改变生产状态。

## 5. 被否决的中间证据

- 首次 fixture 命令因 `uv --directory` 改变工作目录而找不到相对脚本路径；改用绝对路径后继续。
- 空数据库不满足双平台 snapshot dry-run 前置条件；改为按正式 collection API 生成最小双平台 fixture 后通过完整断言。
- 一次 secret scan 因工具路径未解析而没有实际执行；该次零命中结论作废，使用绝对工具路径后重新扫描。
- 两次没有远端分支证据的 push 过程未计入完成状态；最终非交互 verbose push 返回 exit 0，并由远端 branch/PR 事实确认。

## 6. 验收边界

当前状态：

```text
reviewable source baseline / Draft PR #3 / production unchanged
no merge / no redeploy / no DB operation / no provider call / no live capture
```

下一道门禁是 Draft PR 审查、CI 和原子提交范围复核。merge 与任何再次部署仍需单独授权。

PR #3 当前为 Open、Draft、Mergeable，GitHub 未返回 status checks。没有 status checks 只能说明仓库当前未上报 CI 结果，不能替代本地验证或人工审查。
