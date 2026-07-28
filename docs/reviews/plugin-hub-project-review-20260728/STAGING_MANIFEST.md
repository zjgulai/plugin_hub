# Plugin Hub 2026-07-28 精确暂存与合并清单

状态：Commit A（`3ba8e9c`）、Commit B（`b616235`）与 Graphify 边界纠偏（`7b1c659`）已在本地分支提交；Commit C 仍为候选。未执行 push、PR Ready、merge 或 deploy。

## Commit A — data asset durability and local product fixes

实际提交信息：`feat: harden data assets, snapshots, backups, and runtime configuration`

仅在 owner 复核范围后逐文件暂存：

```text
apps/api/src/plugin_hub_api/backup_cli.py
apps/api/src/plugin_hub_api/insight_snapshot_repository.py
apps/api/src/plugin_hub_api/migration_cli.py
apps/api/src/plugin_hub_api/migrations.py
apps/api/src/plugin_hub_api/repositories.py
apps/api/src/plugin_hub_api/routes/collection_runs.py
apps/api/src/plugin_hub_api/routes/collection_tasks.py
apps/api/src/plugin_hub_api/routes/data_assets.py
apps/api/src/plugin_hub_api/routes/insights.py
apps/api/src/plugin_hub_api/routes/instagram_media_captures.py
apps/api/src/plugin_hub_api/schemas.py
apps/api/src/plugin_hub_api/security.py
apps/api/src/plugin_hub_api/services/collection_task_worker.py
apps/api/src/plugin_hub_api/services/insights.py
apps/api/src/plugin_hub_api/services/instagram_capture.py
apps/api/src/plugin_hub_api/source_urls.py
apps/api/tests/test_api_security.py
apps/api/tests/test_backup_cli.py
apps/api/tests/test_collection_runs_api.py
apps/api/tests/test_collection_tasks_api.py
apps/api/tests/test_contracts.py
apps/api/tests/test_data_assets_api.py
apps/api/tests/test_database_hardening.py
apps/api/tests/test_insight_snapshots_api.py
apps/api/tests/test_insights.py
apps/api/tests/test_instagram_capture.py
apps/api/tests/test_instagram_media_capture_api.py
apps/api/tests/test_migration_dry_run_script.py
apps/api/tests/test_snapshot_migrations.py
apps/extension/src/lib/settings.ts
apps/extension/src/popup/Popup.tsx
apps/extension/tests/settings.test.ts
apps/web/app/page.tsx
apps/web/src/components/operations/PlatformWorkspace.tsx
apps/web/src/lib/api.ts
apps/web/tests/api.test.ts
apps/web/tests/config.test.ts
deploy/tencent-lighthouse/docker-compose.yml
scripts/dry-run-insight-snapshot-migration.py
scripts/pull-offhost-backup.zsh
```

暂存前复核：该提交包含数据库迁移定义和生产 compose 配置，但提交代码不等于授权生产迁移或部署。建议在 owner 复核时再按“API durability / clients / deploy config”拆成更小提交；不得为了追求提交数量而改写已验证逻辑。

## Commit B — Graphify local analysis boundary

实际提交信息：`chore(graphify): add local analysis boundary`

```text
.graphifyignore
.gitignore
```

`.gitignore` 只归属 Commit B。规则只覆盖 `*.pem` 与 `**/graphify-out/cache/`，不删除任何本地文件。

## Commit C — project retrospective and graph artifacts

建议提交信息：`docs(review): add project retrospective and execution plan`

```text
docs/reviews/plugin-hub-project-review-20260728/STAGING_MANIFEST.md
docs/reviews/plugin-hub-project-review-20260728/index.html
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/.graphify_analysis.json
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/.graphify_labels.json
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/.graphify_labels.json.sig
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/CALLFLOW.html
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/GRAPH_REPORT.md
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/GRAPH_TREE.html
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/graph.html
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/graph.json
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/manifest.json
```

## 明确排除

不得使用 `git add .`、`git add -A` 或目录级广泛暂存。以下现有本地资产全部排除：

```text
.kiro/
DDDD.pem
docs/workflows/plugin-hub-loop13-release-approval-refresh-draft-20260708.md
docs/workflows/plugin-hub-loop9-release-approval-packet-draft-20260706.md
drafts/
output/
scripts/browser-harness/
tmp/
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/cache/
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/.graphify_root
docs/reviews/plugin-hub-project-review-20260728/graphify/graphify-out/2026-07-28/
```

排除不代表这些资产可以删除；它们属于既有工作树或本地证据，需单独 inventory、owner 决策和独立变更。`.graphify_root` 保存生成机器的绝对项目路径，只用于本地 Graphify 状态，不属于可移植的复盘产物。

## Owner-gated 合并顺序

1. `[已完成]` Owner 确认 Commit A 范围，并完成 Commit A/B 的逐文件暂存与本地提交。
2. `[已完成]` 补充 `scripts/browser-harness/` Graphify 排除规则，重建图谱并确认未授权本地资产为 0。
3. `[进行中]` 逐文件暂存 Commit C，比较 `git diff --cached --name-status` 与本清单。
4. `[待执行]` Commit C 后跑完整 370 项本地门禁和 final Codex review。
5. 推送前重新读取 PR #3 head SHA；push 属外部写，需明确授权。
6. 等待新的 API、Web and Extension、Deployment Config CI；2026-07-10 的历史 green 不可复用为 fresh gate。
7. Reviewer/owner 接受范围后才把 Draft 转 Ready；Ready 不等于 merge 授权。
8. Merge 前再做 head guard、base `main`、review、fresh CI 和 mergeability 检查；merge、deploy、生产 migration、Store 分别审批。
