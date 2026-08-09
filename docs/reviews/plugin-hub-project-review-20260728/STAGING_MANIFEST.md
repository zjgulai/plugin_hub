# Plugin Hub 2026-07-28 精确暂存与 2026-08-09 合并后对账清单

状态：Commit A-E 及后续修复已形成精确 feature head `9b29af0242a2dec872e5000822bf257821326335`。PR #3 的精确 head CI run `30785038279` 三个 job 均为 success，PR 的 CodeRabbit check 亦为 success；PR 经独立 Ready 与 merge 授权后，以 merge commit `ff6d55b27b6021530e295e7c5bc4286df603e1bb` 合入 `main`。merge tree 与 feature tree 相同，main push CI run `31304748784` 三个 job 全部 success；源分支按 owner 要求保留。未执行 deploy、生产数据库操作、migration、backup、Store、provider 或 live capture。

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

实际提交信息：`docs(review): add project retrospective and execution plan`

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

## Commit D — trusted extension credential boundary（`513dbc1`，已完成）

建议提交信息：`fix(extension): enforce trusted credential boundaries`

```text
apps/extension/extension-targets.json
apps/extension/extension-versions.json
apps/extension/src/background/service-worker.ts
apps/extension/src/content/content-script-runtime.tsx
apps/extension/src/content/ui/ContentCommandBar.tsx
apps/extension/src/lib/settings.ts
apps/extension/src/popup/Popup.tsx
apps/extension/src/types/messages.ts
apps/extension/tests/content-command-bar-render.test.tsx
apps/extension/tests/manifest.test.ts
apps/extension/tests/popup.test.tsx
apps/extension/tests/service-worker.test.ts
apps/extension/tests/settings.test.ts
scripts/verify-extension-package.mjs
```

该提交把 credential-bearing API 目标所有权收回 service worker：先校验 sender 和可信存储目标，再读取 key；来源站点仅保留在 `content_scripts.matches`，从 `host_permissions` 移除。三目标统一 bump 到 `0.2.2`，但不包含 Store upload/submission。

## Commit E — close T00-07 review evidence（本文件所在提交，已完成）

建议提交信息：`docs(review): close extension security gate`

```text
README.md
docs/reviews/plugin-hub-project-review-20260728/STAGING_MANIFEST.md
docs/reviews/plugin-hub-project-review-20260728/index.html
docs/workflows/workflow-split-extension-browser-e2e-runbook-review.md
```

本提交只更新当前设计、手册和复审证据；Graphify 图谱仍是 Commit C 的架构基线，不把它描述为包含 T00-07 增量的 fresh graph。

## Commit F — reconcile post-merge evidence and remaining plan（本地文档提交）

建议提交信息：`docs(review): reconcile post-merge evidence and remaining plan`

```text
docs/reviews/plugin-hub-project-review-20260728/STAGING_MANIFEST.md
docs/reviews/plugin-hub-project-review-20260728/index.html
```

本提交只对账 PR #3 的精确 source head、Ready/merge、main CI 与剩余独立门禁。`.kiro/plan/*` 只作为 owner 本地连续性记录更新，不进入 Commit F；未跟踪 Graphify 本地状态、旧草稿、输出和 browser harness 继续排除。

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
3. `[已完成]` Commit C 已按本清单逐文件提交，对应 `c8a7b93`。
4. `[已完成]` T00-07 修复可信 API origin/sender、Popup key readiness 和 closed Shadow DOM 纵深防御；新增 sender/target/key race 回归，三包统一为 `0.2.2`。
5. `[已完成]` 完整 377 项本地门禁、lint/typecheck/build/package/verify 通过；末次独立审查 helper exit 143，人工复核无新增 actionable finding，按 `COMMENT` 留痕。
6. `[已完成]` Owner 逐文件授权 Commit D/E；两次暂存均与清单精确一致，未使用广泛暂存，未动其他本地资产。
7. `[已完成]` 精确 push feature head `9b29af0`；PR run `30785038279` 的 API、Web and Extension、Deployment Config 均为 success，CodeRabbit check 亦为 success。
8. `[已完成]` Reviewer/owner 接受延后项后把 PR #3 从 Draft 转 Ready；Ready 未被当作 merge 授权。
9. `[已完成]` Owner 授权精确头 `9b29af0` 使用 merge commit 合并、不删分支、不部署；结果为 `ff6d55b`。
10. `[已完成]` 合并后只读核验 parents、tree identity、PR MERGED、remote refs 与 main run `31304748784` 三 job success。
11. `[本门禁完成]` 从 `ff6d55b` 建隔离分支，更新 HTML/manifest 与 owner 本地 `.kiro` 状态，执行文档和测试校验并创建 Commit F；不 push 或建 PR。
12. `[待下一门禁]` 精确 push Commit F 所在分支并创建 docs-only Draft PR，等待 fresh CI 后停止；不 merge。
13. `[保持分离]` docs PR merge、deploy、生产只读 freshness、生产 migration、Store、branch cleanup 均需新的明确授权和各自 evidence packet。
