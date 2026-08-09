---
title: Plugin Hub Loop 41 Source Baseline Reconciliation Plan
doc_type: execution_plan
module: product_engineering
topic: plugin-hub-source-baseline-and-release-reconciliation
status: completed
created: 2026-07-10
updated: 2026-08-01
owner: self
source: human+ai
---

# Plugin Hub Loop 41 源码基线与发布对账计划

## 1. 目标

把已通过生产验收的 Loop38-40 能力收口为可审阅、可测试、可重建、可回滚的 Git 源码基线，同时保留既有用户文件和历史证据，不产生新的生产副作用。

## 2. 证据边界

本轮允许：

- 本地源码、测试、部署模板与工程文档收口；
- 只读 Git/远端 release 对账；
- 本地测试、构建、迁移 dry-run、备份恢复 fixture；
- 通过明确文件清单形成原子暂存和提交；
- 本地验收通过后推送当前 `codex/` 分支并创建 Draft PR。

本轮禁止：

- 生产部署、Nginx reload、timer/LaunchAgent 变更、数据库写入或迁移；
- provider call、live capture/upload、Web Store upload/submit/publish；
- merge Draft PR；
- 读取、打印或提交任何 secret。

## 3. 变更分组

### Commit A: 数据资产后端

- SQLite 连接与事务加固、幂等和服务端 hash；
- API read/write 认证、SSRF 防护、分页和资产汇总；
- append-only insight snapshot migration/repository/API；
- 后端单元、集成、迁移、备份与完整性测试；
- `.env.example` 中不含真实值的配置契约。

### Commit B: Web 与插件客户端

- Web server-side API key 转发、资产历史工作台和分页契约；
- Extension key storage/upload recovery；
- Amazon、Reddit、Instagram 独立版本登记与版本测试。

### Commit C: 部署与恢复资产

- Compose/Nginx hardened templates；
- systemd backup service/timer；
- snapshot migration dry-run 和 age 加密异机拉取脚本。

### Commit D: 工程治理与验收文档

- README、AGENTS、生产证据治理 runbook；
- Loop38-41 审计、生产验收和源码对账文档。

跨分组文件只有在无法保持中间提交可验证时才合并到同一提交；禁止为了形式上的拆分制造不可运行的中间状态。

## 4. 明确排除

- `.kiro/plan/**`：本地会话状态，不作为应用发布源码；
- `output/**`：截图、只读 smoke 和历史验收产物；
- `drafts/analysis/**`：旧业务分析草稿；
- `scripts/browser-harness/**`：Loop37 手工 Chrome 阻断诊断；
- Loop9/13 历史 release packet：除非与当前事实对账后另行更新；
- 构建目录、ZIP、缓存和临时数据库。

## 5. 顺序 TODO

1. `complete` 生成精确 tracked/untracked 文件清单并标注 include/exclude/patch-stage。
2. `complete` 核对插件版本登记、manifest 生成和 package 校验链。
3. `complete` 审查 Loop38-40 代码差异，修复源码基线缺口，不扩大业务范围。
4. `complete` 执行 API pytest/ruff/mypy/build。
5. `complete` 执行 Web/Extension test/lint/typecheck/build。
6. `complete` 执行三插件 package/version verification。
7. `complete` 执行 snapshot migration dry-run、备份恢复 fixture 和 `git diff --check`。
8. `complete` 只读核对 active production release 的受控源码 hash、镜像/release 标识和服务状态。
9. `complete` 更新本计划与验收文档，给出事实、推断、未验证项和回滚边界。
10. `complete` 按显式文件清单逐组暂存，执行 cached diff/secret/staged gate。
11. `complete` 创建原子提交并复验完整 commit stack。
12. `complete` 推送当前分支并创建 Draft PR；停止在 merge 和再部署之前。

## 6. 验收门槛

- 全部受影响 package 的自动化测试、lint、typecheck、build 通过；
- snapshot migration 和 backup restore 在隔离 fixture 中可重入且不改写历史资产；
- 三个插件均由独立 registry 版本驱动，package manifest 与登记一致；
- staged file list 不包含排除项、secret 或未解释的 generated artifact；
- Git 提交能够从 `origin/main` 重放并构建当前能力；
- 生产只读对账无意外 drift，且本轮 `production unchanged`。

精确边界清单见 `plugin-hub-loop41-source-baseline-file-manifest-20260710.tsv`。

## 7. 2026-07-10 收口状态（历史快照）

> 本节只记录 Loop 41 收口时点，不代表 PR 当前状态。后续状态以 PR
> live checks 和 Loop 42 验收记录为准。

- 当时的 Draft PR：`https://github.com/zjgulai/plugin_hub/pull/3`；
- 当时的 PR 状态：Open、Draft、Mergeable；
- GitHub 当时未返回 status checks；
- 67 个 include 文件与 branch diff 完全一致；
- 剩余工作区仅包含 manifest 明确排除的本地计划、历史证据、旧草稿和浏览器诊断；
- `production unchanged`，merge 和再次部署仍需单独授权。
