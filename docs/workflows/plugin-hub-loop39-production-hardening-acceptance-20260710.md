---
title: Plugin Hub Loop 39 Production Hardening Acceptance
doc_type: acceptance_report
module: product_engineering
topic: plugin-hub-production-data-asset-hardening
status: accepted
created: 2026-07-10
updated: 2026-07-10
owner: self
source: codex
---

# Plugin Hub Loop 39 生产加固验收

## 1. 结论

经 owner 明确授权，Loop 38 的认证、SQLite、备份、Nginx 和权限加固已部署到生产并完成恢复演练。

当前已验证：

- 生产保留 7 个 collection run、402 条 raw、402 条 canonical；0 orphan、0 run count mismatch。
- 402 条 raw payload 的 FNV1a64 hash 全部重算匹配。
- API 与 worker 均使用 WAL、FK enabled、FULL synchronous、15000ms busy timeout。
- 19 个 `/api` operation 全部声明并执行 API key 保护。
- 匿名后台与匿名 API 均返回 401；Basic Auth 后台与 read-key API 均返回 200。
- Nginx rate limit 在 30 次受控突发中返回 21 个 401 和 9 个 429，3 秒后鉴权请求恢复 200。
- 每日 systemd 备份 timer 已启用；修复后备份通过 hash、manifest、权限、完整性与无网络隔离 API 恢复验收。
- Amazon、Reddit、Instagram 版本登记均为 0.2.1。

## 2. 授权与边界

本轮已授权并执行：

- production read/write API key 与后台 Basic Auth 凭据生成和部署；
- data/backup/runtime 文件权限收紧；
- API、Web、worker 部署；
- Nginx 配置变更、重建与公网验收；
- 在线备份、systemd timer 安装、真实触发与隔离恢复；
- 备份 sidecar 缺陷修复后的 API/worker 更新。

本轮未执行：

- database schema migration 或历史洞察回填；
- provider call、平台 live capture 或真实插件上传；
- Chrome Web Store 提交或 manual Chrome acceptance；
- 生产 raw payload 导出；
- Git stage、commit、push 或 merge。

## 3. 生产变更

### 3.1 凭据与权限

- 凭据值未输出到日志、仓库或报告。
- 本机 Keychain service：
  - `plugin-hub-production-api-read` / account `plugin-hub`；
  - `plugin-hub-production-api-write` / account `plugin-hub`；
  - `plugin-hub-production-dashboard-basic` / account `pluginhub`。
- `/opt/plugin-hub/runtime/plugin-hub.env`：root-owned，0600。
- `/opt/ai-video/deploy/lighthouse/plugin-hub.htpasswd`：0640，挂载为 Nginx read-only 文件。
- `/opt/plugin-hub/data` 与 `/opt/plugin-hub/backups`：0700。
- production DB、备份、manifest 与 backup lock：0600。

### 3.2 Release 与容器

- 当前 release：`/opt/plugin-hub/releases/plugin-hub-20260710T120927Z-backupfix`。
- API/worker image：`sha256:c43d8f4ba2285dea344f62e5634b14044a5a3e4ec589df50e34f549279f3bad2`。
- Web image：`sha256:90002099a80bec10764fc1d618bbf51dbb3fac3915a5229ce2aecc39b85e937c`。
- API/Web healthy，worker running；API 和 worker 近期日志无 `ERROR`/`Traceback`。
- Web 在备份修复更新中未重建。

回滚资产：

- 基线目录：`/opt/plugin-hub/backups/loop39-production-hardening-20260710T1115Z`。
- 应用候选前回滚 tags：`plugin-hub-api:rollback-loop39-20260710T1115Z`、`plugin-hub-web:rollback-loop39-20260710T1115Z`。
- 备份修复前 API 回滚 tag：`plugin-hub-api:rollback-loop39-backupfix`。

### 3.3 Nginx

- 后台 `/` 使用 Basic Auth。
- `/api/` 保留 API key 认证，并启用 10 r/s、burst 20 的 Nginx rate limit。
- 请求体上限 8 MiB，连接/读写 timeout 收紧。
- HSTS、CSP、nosniff、DENY、Referrer-Policy 与 Permissions-Policy 已启用。
- `nginx -t`、Compose config、htpasswd mount 与容器重建均通过。
- 共享入口回归：主站、video、voc、skills 四个站点均返回 200。

## 4. 数据完整性验收

生产应用连接证据：

| 检查 | 结果 |
| --- | --- |
| collection runs / raw / canonical | 7 / 402 / 402 |
| run count mismatch | 0 |
| raw orphan / canonical orphan | 0 / 0 |
| `PRAGMA quick_check` | ok |
| `PRAGMA foreign_key_check` | 0 issue |
| raw hash recomputation | 402 checked / 0 mismatch |
| journal mode | WAL |
| foreign keys | 1 |
| synchronous | 2 / FULL |
| busy timeout | 15000ms |
| runnable collection tasks | 0 |

三类核心资产仍按一个 repository transaction 写入。部署未删除、改写或回填任何历史 raw/canonical 记录。

## 5. 备份与恢复

### 5.1 首次生产演练

- 部署前在线备份：`plugin_hub_20260710T111428Z.db`，913408 bytes。
- manifest SHA-256 与文件一致，`quick_check=ok`，计数 7/402/402。
- 关闭后的备份复制件完成 SQLite 只读恢复检查。

### 5.2 Sidecar 缺陷与修复

定时备份首次运行后发现校验连接会遗留 `.tmp-shm/.tmp-wal` 和最终 backup sidecar，部分初始模式为 0644。备份目录 0700 阻止了同主机普通账号访问，但该行为会累积文件且不满足资产治理要求。

修复内容：

- backup verification 使用 `mode=ro&immutable=1`；
- 临时 DB 及 `-wal/-shm` 在 `finally` 中清理；
- backup lock 立即 `fchmod(0600)`；
- backup directory 强制 0700；
- retention 删除备份时同时清理关联 sidecar；
- WAL fixture 测试断言无 `.tmp/-wal/-shm` 且目录/文件权限正确。

修复后生产备份：`plugin_hub_20260710T121013Z.db`，913408 bytes。

- backup/manifest/hash/count/quick check 全部一致；
- backup 目录 sidecar 数量 0，非 0600 文件数量 0；
- 无网络隔离 API 恢复返回 200，计数 7/402/402，0 mismatch、0 orphan；
- 恢复库 `quick_check=ok`、0 FK issue、journal mode WAL；
- 临时恢复容器和复制件已删除。

systemd timer：

- `plugin-hub-db-backup.timer` enabled + active；
- 每日 03:15，随机延迟 15 分钟，保留 14 个已验证备份；
- 本轮最终观测的下一次触发为 2026-07-11 03:21:37 CST。

## 6. 测试证据

- API：174 passed；ruff passed；mypy passed；package build passed。
- 备份定向测试：2 passed，包含 WAL/sidecar/permission 回归。
- candidate backup smoke：3 个预期文件、0 sidecar、0 bad mode、目录 0700。
- production DB：7/402/402、402 hash checked、0 mismatch、0 orphan、0 FK issue。
- OpenAPI：19 protected operations、0 unprotected operation。
- 公网：匿名后台/API 401，鉴权后台/API 200，安全响应头全部存在。
- Nginx：配置有效，受控 rate-limit probe 产生 429，恢复后 200。
- 共享站点：4/4 返回 200。

## 7. 被否决的中间证据

- 第一次 Nginx 脚本因 root 临时文件清理权限失败，自动回滚并验证旧入口恢复 200；修正后重新执行成功。
- 第一次 timer 安装验收以普通用户 `stat` 0700 目录内文件而失败，单元自动回滚；改用 `sudo stat` 后成功。
- 第一次隔离恢复深度断言漏传 `docker exec -i`，只证明了 `/readyz`；该证据被否决，重新运行后输出完整 API/SQLite 断言。
- 一次最终 PRAGMA 断言误用了原生 SQLite 连接的默认 5000ms timeout；改用应用 `build_engine` 后 API/worker 均实测 15000ms。

## 8. 剩余风险

- 本节是 Loop 39 收尾时点状态；Loop 40 已增加显式 migration、append-only insight snapshots 和本机 age 加密异机副本，见独立验收报告。
- 2026-07-10 之前的洞察仍没有历史快照，不能通过当前重算进行伪回填。
- 当前异机目标是这台 Mac，不是对象存储或跨地域灾备。
- API key 为共享 read/write 两级，不是按插件独立身份、轮换窗口或逐 actor 审计。
- 插件 0.2.1 尚未完成 manual Chrome、live capture/upload 或 Web Store 验收。

最终状态：

```text
production hardening deployed / raw-canonical history intact / verified backup and restore active
no migration / no derived-insight history / no provider call / no live capture / no Web Store submission
```
