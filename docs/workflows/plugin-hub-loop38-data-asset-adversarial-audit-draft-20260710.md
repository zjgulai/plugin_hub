---
title: Plugin Hub Loop 38 Data Asset Adversarial Audit
doc_type: audit_report
module: product_engineering
topic: plugin-hub-data-asset-durability-and-hardening
status: draft
created: 2026-07-10
updated: 2026-07-10
owner: self
source: codex
---

# Plugin Hub Loop 38 数据资产对抗性审计

> 本报告第 1-6 节记录 Loop 38 部署前审计快照。授权后的生产修复与验收见
> `docs/workflows/plugin-hub-loop39-production-hardening-acceptance-20260710.md`。

## 1. 审计结论

结论分为三层，不能合并表述：

1. **生产基础资产当前完整，把握高。** 生产库现有 7 个 collection run、402 条 raw、402 条 canonical，逐 run 数量一致；`quick_check=ok`，没有孤儿、批次内重复或空 hash。
2. **生产保护机制不合格，把握高。** 审计时后台和 API 无认证，17 个 API operation 均无 security scheme；数据库没有周期备份、恢复演练、schema version 或启用中的外键校验，主文件权限为 `0644`。
3. **派生洞察没有历史持久化，把握高。** relation edge、enriched signal、strategy note 和 insight brief 均为请求时重新计算，无法证明某一历史时点到底输出过什么。

Loop 38 当时边界：

```text
production read-only evidence / local code and tests changed / production unchanged
no production DB write / no migration / no backup execution / no timer install
no credential rollout / no Nginx reload / no deploy / no provider call
```

## 2. 生产只读证据

### 2.1 SQLite 完整性与历史保留

| 检查 | 结果 | 解释 |
| --- | ---: | --- |
| `collection_runs` | 7 | Amazon 3，Reddit 4 |
| `raw_source_items` | 402 | Amazon 10，Reddit 392 |
| `canonical_voc_units` | 402 | 与 raw 总量一致 |
| Run 时间范围 | 2026-06-19 至 2026-07-07 | 历史 run 仍保留 |
| 无 raw 的 run | 0 | 未发现空父记录 |
| 无 canonical 的 run | 0 | 未发现 ETL 完全缺失 |
| raw/canonical 数量不一致的 run | 0 | 当前每批一一对应 |
| raw 孤儿 / canonical 孤儿 | 0 / 0 | 当前引用完整 |
| 批次内 raw 重复 / canonical 重复 | 0 / 0 | 当前无批次内重复 |
| 跨 run 重复 hash / source object | 0 / 0 | 当前样本无重复采集 |
| `PRAGMA quick_check` | `ok` | 当前文件页结构通过快速检查 |
| `PRAGMA foreign_key_check` | 0 issue | 当前没有已存在的外键问题 |

原始 hash 进一步核验：

- 402 条均为 `fnv1a64`、长度 24。
- 在生产容器内只读重算 402 条 payload，`mismatch_total=0`。
- 审计未输出 raw payload、正文、作者或来源 URL。

### 2.2 数据质量

生产 canonical 中有 151 条空正文，全部为 Reddit `more` node，且全部带有 `reddit_more_node` flag；它们是分页/展开占位，不是消费者表达。

因此：

- canonical 物理记录：402；
- 当前可分析证据：251；
- Reddit 占位：151；
- 旧后台把 402 全部计为“证据总量”，会高估有效 VOC，并污染洞察输入。

### 2.3 SQLite 运行与 schema 风险

| 参数 | 生产值 | 风险 |
| --- | --- | --- |
| `journal_mode` | `delete` | API 与 worker 共写同一文件时并发能力弱 |
| `synchronous` | `2` / FULL | 单连接提交耐久性较强 |
| `foreign_keys` | `0` | 模型声明 FK，但连接没有执行约束 |
| `busy_timeout` | 只读审计连接 10000ms | 应用代码此前未显式统一 |
| `user_version` | 0 | 无 schema version |
| migration framework | 不存在 | `create_all` 不能承担升级、回填和回滚 |
| WAL/SHM 文件 | 不存在 | 审计时未使用 WAL |
| DB 文件权限 | `0644 root:root` | 同主机非特权账号可直接读取数据文件 |
| data / backup 目录 | `0755` | 文件名和目录结构对同主机账号可见 |

API 与 worker 同时挂载 `/opt/plugin-hub/data:/data`，因此并发写冲突是实际部署拓扑风险，不是理论假设。

### 2.4 备份与恢复

生产发现两份数据库备份：

| 备份 | 大小 | 表数 | `quick_check` |
| --- | ---: | ---: | --- |
| 2026-07-09 deploy 前备份 | 913408 bytes | 6 | ok |
| 2026-06-24 手工备份 | 737280 bytes | 4 | ok |

同时确认：

- user cron 中 Plugin Hub 备份任务：0；
- `/etc/cron.*` 命名任务：0；
- systemd timer：0；
- 没有恢复演练证据；
- 没有异机/对象存储副本证据。

生产 schema 元数据确认 raw/canonical 子表均声明了指向 `collection_runs` 的 FK；风险是生产连接 `foreign_keys=0`，不是 schema 完全没有外键。

结论是“存在可读手工副本”，不是“已建立备份制度”。

### 2.5 公开攻击面

匿名 HTTPS 只读探测结果：

| 请求 | 状态 | 返回规模 | 关键发现 |
| --- | ---: | ---: | --- |
| `/` | 200 | 576378 bytes | 服务端渲染页面匿名公开资产 |
| `/api/voc-units?limit=1` | 200 | 416300 bytes / 402 items | `limit` 被忽略，全量泄露 |
| `/api/voc-units?platform=reddit&limit=1` | 200 | 392406 bytes / 392 items | 平台历史全量公开 |
| `/api/insights/briefs?limit=1` | 200 | 10153 bytes | 匿名公开证据引用与洞察 |
| `/api/collection-tasks` | 200 | 1455 bytes | 任务历史公开 |
| `/api/platform-settings` | 200 | 632 bytes | 运行配置公开 |

部署 OpenAPI 共 17 个 operation：

- security scheme 数量：0；
- 声明 security 的 operation：0；
- 包含匿名 POST collection、创建/执行 task、PATCH setting、触发服务端 capture。

Nginx 审计时没有 API rate limit、后台认证、HSTS、CSP、frame protection 或 referrer policy。

### 2.6 SSRF

旧 `build_reddit_json_url` 原样沿用调用方提供的 scheme 与 netloc，随后由服务端 `urlopen` 请求。匿名用户可借 Reddit capture/task 路由请求内网地址；默认重定向还会先访问 Location 再检查最终 URL。

这是 P0，因为它同时具备：

- 外部可达；
- 无认证；
- 服务端发起网络请求；
- 可和 task execute 路由组合。

## 3. 风险分级

| 等级 | 风险 | 审计状态 |
| --- | --- | --- |
| P0 | 后台、读 API、写 API、任务执行均匿名 | 生产存在；本地候选已加认证，未部署 |
| P0 | Reddit server capture/task SSRF | 生产存在；本地候选已限制目标和重定向，未部署 |
| P0 | 洞察与信号没有不可变历史快照 | 未修复；需要 schema migration |
| P1 | 无周期备份、恢复演练和异机副本 | 本地已有工具/timer 模板；生产未安装 |
| P1 | SQLite 外键关闭、DELETE journal、API/worker 共写 | 本地已有 FK、timeout、可选 WAL；生产未部署 |
| P1 | worker 忽略 WAL/busy-timeout 环境配置 | 本地已统一 engine 设置并增加 PRAGMA 回归；生产未部署 |
| P1 | DB `0644`、data/backup 目录 `0755` | 本地启动收紧 DB/WAL/SHM 为 `0600`；目录权限仍需部署门禁 |
| P1 | 全量读取、全量洞察重算、健康检查扫描历史 | 本地已分页、汇总、限定 2000 输入和常数健康检查 |
| P1 | 插件重试产生重复 run | 本地已增加幂等 key；生产未部署 |
| P1 | 客户端 hash 可伪造 | 本地对 `extension_*` 强制重算；生产未部署 |
| P2 | 151 个 `more` node 被计入证据和洞察 | 本地保留历史但排除分析；生产未部署 |
| P2 | 缺少逐 run 资产状态视图 | 本地新增 summary/runs API 与后台表格 |

## 4. 本地加固候选

### 4.1 API 与数据完整性

- API key 读写分权：读 key 不能调用 POST/PATCH，写 key 可读写。
- `required` 模式缺 key、短 key、相同 key 时启动失败。
- 所有 `/api` operation 在 OpenAPI 声明 API key security。
- CORS 收紧到本地开发源和 `chrome-extension://`。
- Reddit 仅允许 HTTPS 官方 host、443 端口、无 userinfo。
- 每次重定向前验证 Location，上游响应上限 25 MiB。
- collection run 强制平台/source kind 一致、批次内对象唯一、最多 2000 raw items。
- `extension_*` payload hash 由服务端按插件 FNV1a64 规则重算。
- `Idempotency-Key` 相同且 payload 相同则返回原 run；内容冲突返回 409。
- SQLite 连接启用 FK、统一 busy timeout；生产模板启用 WAL + FULL synchronous。
- API 与 worker 共同读取 WAL/busy-timeout 配置，不再出现两套 SQLite 策略。
- 应用初始化后将 SQLite 主文件及现存 WAL/SHM 收紧为 `0600`。
- 父 run 在事务内先 flush，随后写 raw/canonical，最终一次 commit。
- 8 个独立 session 同步并发写的本地回归证明 8 run / 8 raw / 8 canonical、0 orphan、`quick_check=ok`。

### 4.2 后台性能与可观测性

- `/api/voc-units` 默认 100、最大 500，并返回 total/limit/offset。
- collection tasks 默认 100、最大 500。
- 洞察最多读取最近 2000 条 canonical，并排除 `reddit_more_node`。
- `/healthz` 不访问数据库；`/readyz` 仅执行 `SELECT 1`。
- `/api/data-assets/summary` 返回 run/raw/canonical/eligible/placeholder/孤儿/不一致聚合。
- `/api/data-assets/runs` 展示每个 run 的 raw/canonical/eligible/placeholder 状态，不返回 payload、正文或 URL。
- 后台仅加载最近 100 条 VOC，平台总量和顶层指标来自数据库精确聚合；隐藏标签页停止自动刷新。

### 4.3 客户端与边缘保护

- Web read/write key 仅在 Next server 侧注入。
- 扩展 key 仅存 `chrome.storage.local`，由 background service worker 读取。
- Amazon、Reddit、Instagram 插件候选版本统一提升到 `0.2.1`。
- Nginx 模板增加后台 Basic Auth、API rate limit、8 MiB body limit、安全响应头与较短 timeout。

### 4.4 备份

新增备份工具采用 SQLite online Backup API：

1. 文件锁内创建临时一致性快照；
2. 执行 `quick_check`；
3. 记录表计数、大小和 SHA-256；
4. 原子发布 DB 和 manifest；
5. 每次清理前重新核验旧备份的大小、SHA-256、`quick_check` 和表计数；损坏副本不占健康保留名额，也不会被自动删除。

systemd timer 模板为每日 03:15、随机延迟 15 分钟、保留 14 份。Loop 38 时尚未安装；Loop 39 已安装并通过真实备份与恢复验收。

本地已完成一次 active-WAL 在线备份和隔离恢复演练：快照 6 张表，run/raw/canonical 为 `2/3/3`，manifest 与恢复库计数一致，恢复 API `readyz=200`、`quick_check=ok`。这不是生产恢复演练，也不是异机备份证明。

## 5. 洞察历史持久化设计门禁

当前不能通过回填还原“历史当时的洞察”，因为旧输出没有保存，模板也可能变化。未来迁移建议采用 append-only analysis snapshot：

### 5.1 建议表

1. `analysis_runs`
   - analysis run id、scope、collection run ids、input digest；
   - template id/version、generation method、language；
   - started/finished/status/error code；
   - 禁止覆盖已完成记录。
2. `insight_brief_snapshots`
   - analysis run id、brief id、完整结构化 payload、output digest、created_at；
   - `(analysis_run_id, brief_id)` 唯一。
3. `voc_signal_snapshots`
   - analysis run id、signal id、evidence refs、结构化 payload。
4. `relation_edge_snapshots`
   - analysis run id、edge id、from/to、evidence strength、metadata。

### 5.2 回填规则

- 只能标记为 `reconstructed`，不能伪称 historical original。
- 输入必须固定为明确的 collection run id 集合。
- 回填前在生产副本上 dry-run，记录行数、digest、耗时和回滚 SQL。
- 正式迁移前必须引入 schema version/migration runner，并先做在线备份。

## 6. 生产上线门禁

按顺序执行，任何一步失败立即停止：

1. Owner 批准 production credential、Nginx、WAL、备份 timer 和 deploy 窗口。
2. 用当前生产代码路径执行在线备份并验证，不使用普通 `cp` 复制运行中的 SQLite。
3. 生成独立 read/write API key 和后台 Basic Auth 凭证，不写入仓库或聊天。
4. 将生产 data/backup 目录收紧为 `0700`，DB、WAL、SHM 和备份文件收紧为 `0600`，记录 owner/group。
5. `docker compose config` 仅验证变量存在，不打印 secret value。
6. 先部署 API/Web/worker，再执行 `/healthz`、`/readyz` 和带 key 的 summary/runs smoke。
7. 验证匿名 API 返回 401、匿名后台返回 Basic Auth challenge、无匿名数据正文。
8. 验证 DB 仍为 7 run / 402 raw / 402 canonical，`quick_check=ok`、0 orphan、0 mismatch。
9. 验证 `journal_mode=wal`、API/worker 各自连接 `foreign_keys=1`、busy timeout 与并发写 smoke。
10. 安装 timer，授权后触发一次真实备份，验证 manifest 和恢复到隔离临时目录。
11. 发布并配置 0.2.1 插件，分别做一次 Amazon/Reddit fixture 或人工受控上传；Instagram 保持授权边界。

Loop 39 已执行并验证第 1-10 步；第 11 步的插件人工/真实上传验收仍未执行。当前状态更新为：

```text
production hardening deployed / raw-canonical history intact / verified backup and restore active
no migration / no provider call / no live capture / no Web Store submission
```

## 7. 本地验收证据

截至本报告更新：

- API tests：174 passed；
- Web tests：36 passed；
- Extension tests：101 passed；
- extension version utility tests：8 passed；
- API/Web/Extension lint：passed；
- API/Web/Extension typecheck：passed；
- 本地 production-mode build：Web 与三个插件通过；
- extension package：Amazon/Reddit/Instagram `0.2.1` 均为 Manifest V3、15 entries，验证通过；
- Compose config：使用本地占位凭证解析通过；
- 本地 API：匿名资产路由 401、带 read key 200、`healthz/readyz=200`、资产一致性 0 issue；
- Playwright：1440px 与 390px 页面验收通过，390px 页面级 `scrollWidth=clientWidth=390`，console 0 error / 0 warning；
- 截图：`output/playwright/loop38-data-asset-audit/dashboard-desktop.png` 与 `dashboard-mobile.png`；
- 在线备份与隔离恢复：`quick_check=ok`、manifest 计数一致、恢复 API 可读；
- 生产 402 条 hash 只读重算：0 mismatch。

独立 `codex review` 两次均未产生审查结论：第一次因 CLI 固定模型需要更新客户端，第二次因外部 usage limit 中断。不能把它表述为自动二审通过。

Loop 38 本地环境没有 Nginx 二进制，当时只完成模板静态审阅和 Compose 解析。Loop 39 已补充生产 `nginx -t`、容器重建、公网鉴权/限流/安全响应头、在线备份与无网络隔离恢复的新鲜证据。

## 8. Loop 39 状态更新

- owner 已授权 credential、权限、Nginx、deploy、timer、备份与恢复窗口。
- API/Web/worker 已部署；API/worker 使用 WAL、FK enabled、FULL synchronous 和 15000ms busy timeout。
- 匿名后台/API 均为 401，鉴权访问均为 200；19 个 API operation 全部受保护。
- 生产计数仍为 7/402/402，402 条 raw hash 重算 0 mismatch，0 orphan、0 run mismatch。
- 修复后的备份 CLI 不再遗留 sidecar，backup/manifest/lock 均为 0600，timer enabled + active。
- `plugin_hub_20260710T121013Z.db` 已完成 manifest/hash/quick-check 与无网络隔离 API 恢复验收。
- 洞察历史快照、migration framework、异机备份、live capture 和 Web Store 验收仍未完成。
