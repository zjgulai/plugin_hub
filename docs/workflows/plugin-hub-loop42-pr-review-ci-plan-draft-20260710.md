---
title: Plugin Hub Loop 42 PR Review And CI Plan
doc_type: execution_plan
module: product_engineering
topic: plugin-hub-pr-review-and-ci-gate
status: accepted
created: 2026-07-10
updated: 2026-07-10
owner: self
source: human+ai
---

# Plugin Hub Loop 42 PR 审查与 CI 计划

## 1. 目标

对 Draft PR #3 完成高风险路径人工审查，并建立可重复的 GitHub Actions 门禁，使 API、Web、Extension、插件版本和部署配置不再只依赖本地验收。

## 2. 边界

本轮允许：

- 审查 `origin/main..HEAD` 的事务、鉴权、迁移、备份、客户端密钥和部署路径；
- 新增 `.github/workflows/ci.yml`；
- 使用仓库现有 lockfile、测试、lint、typecheck、build 和 package 命令；
- 推送当前 PR 分支并只读验收 GitHub checks；
- 更新工程记录。

本轮禁止：

- merge PR；
- production deploy、数据库操作、迁移、备份执行、timer/Nginx/credential 变更；
- provider call、live capture/upload、Web Store 操作；
- 给 CI 配置 production secret 或任何 write permission。

## 3. CI 设计

### API job

- Python 3.12、uv 0.11.11；
- `uv sync --frozen --all-groups`；
- pytest、ruff、mypy、sdist/wheel build。

### Web and Extension job

- Node 22、pnpm 9.15.4；
- frozen install；
- Web/Extension test、lint、typecheck、build；
- extension version governance；
- Amazon/Reddit/Instagram package verification。

### Deployment config job

- synthetic non-secret API keys 解析 Compose；
- `zsh -n` 检查异机备份脚本；
- Python compile 检查 migration dry-run；
- `git diff --check`。

所有 reusable actions 使用完整 commit SHA，workflow 权限固定为 `contents: read`，并启用同一 PR 的并发取消。

## 4. 顺序 TODO

1. `complete` 读取 Loop38-41、PR #3、提交栈、现有脚本和 GitHub Actions 官方建议。
2. `complete` 人工审查高风险代码路径并记录 accepted/rejected finding。
3. `complete` 新增最小权限三作业 CI workflow。
4. `complete` 本地解析 workflow，运行 API/Web/Extension/版本/build/package/Compose 等价门禁。
5. `complete` 运行 Codex review 并按证据分级；CLI 版本不支持当前模型，未产生二审结论，人工审查结果保持独立。
6. `complete` 更新 Loop42 验收记录，显式暂存并提交 CI/docs。
7. `complete` 推送 PR #3，等待并检查 GitHub checks。
8. `complete` 复核 docs-only head、文件范围、checks 和 merge 边界后停止。

## 5. 验收标准

- PR 高风险路径没有未处理的 P0/P1 finding；
- workflow YAML 可解析，actions 固定 SHA 与官方 tag 对应；
- 本地等价门禁全部通过；
- GitHub API 返回三个预期 job 的完成状态；
- PR 保持 Draft，production unchanged；
- merge 和部署仍是独立授权门禁。

## 6. 当前审查记录

- accepted：Deployment job 使用 `origin/main...HEAD` 时必须完整获取 base history；已为该 job 增加 `fetch-depth: 0`。
- rejected：未接受基于理论风险的大规模迁移/仓储重构；现有事务、trigger、checksum、备份和鉴权路径已有针对性测试与生产证据。
- no finding：Web API key 仅在 server component/server action 中加载，客户端自动刷新只调用 `router.refresh()`，没有把 key 作为 prop 或浏览器请求头下发。
- local evidence：workflow YAML、6 个 action SHA、最小权限、无 secret 引用、synthetic key、三个本地等价 job 均已通过。
- unavailable evidence：Codex CLI review 在重连后返回 `The 'gpt-5.6-sol' model requires a newer version of Codex.`，exit 1；没有 clean review 声明，也没有可接受/拒绝的模型 finding。

## 7. 远端验收结果

- implementation run `29102813050`：API、Deployment Config、Web and Extension 全部 success；
- docs-only run `29103163052`：API 22s、Deployment Config 14s、Web and Extension 1m06s，全部 success；
- PR #3 保持 Open、Draft、Mergeable；
- merge、repository settings 和 production 均未改变；
- 后续状态以 PR live checks 为事实源，不再通过追加验收文本制造递归 CI 提交。
