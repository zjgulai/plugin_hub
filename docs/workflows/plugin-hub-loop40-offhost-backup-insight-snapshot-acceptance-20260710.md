---
title: Plugin Hub Loop 40 Off-Host Backup And Insight Snapshot Acceptance
doc_type: acceptance_report
module: product_engineering
topic: plugin-hub-offhost-backup-and-insight-snapshots
status: accepted
created: 2026-07-10
updated: 2026-07-10
owner: self
source: codex
---

# Plugin Hub Loop 40 异机备份与洞察快照验收

## 1. 结论

经 owner 对上一轮两项独立建议的明确授权，以下闭环已完成：

1. 生产 SQLite 备份已建立到本机 Mac 的 age 加密第二主机副本，并由 LaunchAgent 每日自动拉取。
2. `0001_analysis_snapshots` 已在生产显式执行，Amazon/Reddit 当前时点基线已持久化为 append-only 洞察快照。

生产核心资产仍为 7 collection runs / 402 raw / 402 canonical。没有删除、覆盖、回填或重新解释历史 raw/canonical 证据。

## 2. 授权与边界

本轮执行：

- 安装官方 age 1.3.1；
- 生成独立 age identity，将私钥写入 macOS Keychain；
- 创建流式加密拉取脚本和每日 04:15 LaunchAgent；
- 设计并实现显式 schema migration、append-only trigger、snapshot API；
- 在生产备份副本和远端无网络候选容器内执行 migration dry-run；
- 生产迁移、API/worker 部署、Amazon/Reddit 当前时点基线 snapshot 写入；
- 迁移前/迁移后在线备份、异机复制和无网络恢复验收。

本轮未执行：

- 伪造或回填 2026-07-10 迁移前的历史洞察；
- provider call、live capture、真实插件上传或 Web Store 提交；
- raw production payload 报告输出；
- Git stage、commit、push 或 merge。

## 3. 异机加密备份

### 3.1 密钥与传输

- 工具：age 1.3.1，按官方 recipient/identity 工作流使用。
- Keychain service：`plugin-hub-offhost-backup-age-identity`，account `plugin-hub`。
- recipient 公钥文件：`~/.config/plugin-hub/offhost-backup-recipient.txt`，0600。
- 生产 DB/manifest 先在远端验证，再通过 SSH tar stream 直接加密；不保留本机长期明文副本。
- 解密验收只在 0700 临时目录进行，退出时清理。

### 3.2 自动化

- 源脚本：`scripts/pull-offhost-backup.zsh`。
- 安装脚本：`~/.local/libexec/plugin-hub/pull-offhost-backup.zsh`。
- LaunchAgent：`com.pray.plugin-hub-offhost-backup`。
- 计划：每日 04:15；加密归档保留 30 份。
- kickstart 验收：last exit code 0；重复拉取会解密验证已有归档并返回 `already_present`。

验收归档：

| 阶段 | 生产备份 | age 归档 | 结果 |
| --- | --- | --- | --- |
| 迁移前 | `plugin_hub_20260710T125630Z.db` | 同名 `.tar.age` | 7/402/402，恢复通过 |
| 迁移后 | `plugin_hub_20260710T130106Z.db` | 同名 `.tar.age` | 2 runs / 824 artifacts，恢复通过 |

迁移后 age 归档为 2243304 bytes，模式 0600；备份根目录为 0700。

## 4. Snapshot Schema 与约束

### 4.1 显式迁移

- migration version：`0001_analysis_snapshots`。
- `schema_migrations` 记录 version、SQL checksum 和 applied time。
- migration `up` 可重入；checksum drift 和未知 migration 会失败。
- `down` 只允许 snapshot tables 为空；已有快照时返回 `analysis_snapshot_rows_exist`。
- 应用 startup 不自动执行 migration，也不通过 `create_all` 偷建快照表。

### 4.2 不可变表

- `analysis_runs`：固定 platform、language、scope、collection run ids、input digest、模板契约、输出 digest 和 created_at。
- `analysis_artifact_snapshots`：固定 artifact type/key/schema、完整结构化 payload、payload digest 和 lineage。
- 四类 artifact：relation edge、enriched VOC signal、strategy note、insight brief。
- 两张表均有 UPDATE/DELETE abort trigger。

### 4.3 API

- `POST /api/insights/snapshots`：使用 write key，按当前输入创建确定性 snapshot；同输入重试返回 `replayed=true`。
- `GET /api/insights/snapshots`：使用 read/write key，分页读取 run history。
- `GET /api/insights/snapshots/{analysis_run_id}`：读取 run 与全部不可变 artifact。
- 全部 22 个 API operation 仍受 API key 保护。

## 5. Dry-Run 证据

本地解密生产副本与远端无网络候选容器得到一致结果：

| 指标 | Amazon | Reddit | 合计 |
| --- | ---: | ---: | ---: |
| source units | 10 | 392 | 402 |
| analysis units | 10 | 241 | 251 |
| artifacts | 25 | 799 | 824 |

artifact 合计：

- relation edges：561；
- enriched VOC signals：251；
- strategy notes：7；
- insight briefs：5。

两条路径均验证：

- migration status/up/down/up；
- 核心三表前后均为 7/402/402；
- `quick_check=ok`、0 FK issue；
- trigger 拒绝 UPDATE；
- 同输入第二次创建为 replay；
- 非空 rollback 被拒绝。

## 6. 生产执行与验收

### 6.1 Release

- 生产 release：`/opt/plugin-hub/releases/plugin-hub-20260710T125458Z-insight-snapshots`。
- API/worker image：`sha256:ee3133a50c42b9154b046f3e0f0711275dbcc872ad989a8a66a9b48dfd8b1d8b`。
- Web image 未变化：`sha256:90002099a80bec10764fc1d618bbf51dbb3fac3915a5229ce2aecc39b85e937c`。
- 回滚 API tag：`plugin-hub-api:rollback-loop40-pre-migration`。

### 6.2 基线快照

- Amazon：`analysis_3b2fd99365972991668ffa3134bcfedd`，3 个 collection runs、10 个分析单元、25 artifacts。
- Reddit：`analysis_a6f953055ec38384de15ffbbbe6cea02`，4 个 collection runs、241 个分析单元、799 artifacts。
- 两条记录的 language 均为 `zh-CN`，创建时间是迁移后的当前时点，不代表过去曾输出过这些洞察。

### 6.3 完整性

- 402 raw hash：0 mismatch；
- 824 artifact payload digest：0 mismatch；
- 2 run output digest：0 mismatch；
- 2 input digest/run identity：0 mismatch；
- append-only UPDATE probe：被 trigger 拒绝；
- core counts：7/402/402；
- `quick_check=ok`、0 FK issue；
- anonymous snapshot API 401，read-key 200，write-key replay 201；
- dashboard anonymous 401、Basic Auth 200；
- API/Web healthy，worker running，近期日志无 ERROR/Traceback。

### 6.4 恢复

从 `plugin_hub_20260710T130106Z.db` 启动无网络 API：

- summary 为 7/402/402，0 orphan/mismatch；
- snapshot listing 为 2；
- detail 共读取 824 artifacts；
- migration version、4 个 trigger、`quick_check` 和 FK 检查全部通过；
- 临时容器和恢复副本已删除。

## 7. 测试证据

- API：178 passed；ruff passed；mypy passed；package build passed。
- migration CLI：status/up/idempotent-up/down/status passed。
- production-copy dry-run：passed。
- remote no-network candidate dry-run：passed。
- production digest/trigger/integrity：passed。
- post-migration online backup、off-host decrypt、no-network restore：passed。
- source hash：本地、current release、运行容器一致。

## 8. 被否决的中间证据

- 首次 age key 脚本缺少换行，未写入 Keychain；临时文件由 trap 删除。
- 第二次 keygen 使用已存在的 `mktemp` 文件，age 拒绝覆盖；改用临时目录中的新路径后成功。
- live migration 脚本的一段 `docker run ... python -` 漏 `-i`，空输出未计入证据；部署后用 `docker exec -i` 补齐 schema/trigger 检查。
- 公网验收两次错误假设 `/openapi.json` 可由 Nginx 代理到 API；实际只代理 `/api/`，最终在 API 容器内部验证 OpenAPI 22/22 protected。
- 共享站点循环误用 zsh 只读变量 `status`，改名后补跑通过。

## 9. 剩余风险

- 本机 Mac 是第二主机，不是对象存储、跨地域灾备或不可删除存储。
- LaunchAgent 依赖本机开机、用户会话、SSH alias 和 Keychain 可用；当前没有失败告警。
- snapshot 仅从迁移后开始；迁移前洞察历史仍未知。
- API key 仍为共享 read/write 两级，没有 per-plugin actor identity 与轮换窗口。
- manual Chrome、live capture/upload 和 Web Store 发布仍未完成。

最终状态：

```text
off-host encrypted backup active / explicit snapshot migration applied
2 post-migration baseline runs / 824 immutable artifacts / core 7-402-402 intact
no historical backfill / no provider call / no live capture / no Web Store submission
```
