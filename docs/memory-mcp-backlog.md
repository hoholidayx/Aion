# 记忆 MCP 与 Skill 接口待办

2026 年 11 月 10 日复核。依据当前 AionCore、`mem0-mcp-lan` 源码和 NAS Mem0 实时 OpenAPI。涉及存储行为时，另对照本地 Mem0 SDK 和 pgvector 源码。本次为只读诊断，待办保留原编号。[MCP 工具](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py) · [NAS REST 实现参考](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/server/main.py) · [Aion 工具适配](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs)

## P0 · 正确性

### 1. 原地修正分类和元数据

- [x] **已部署并通过端到端验收。** 修复前，MCP 和 AionCore 只接收 ID 和正文，正文相同时提前返回，回读校验要求元数据原样保留。NAS 的 PUT 已接受独立 `metadata`，SDK 在已有元数据上做顶层合并，保留 ID 和 `created_at`，并追加更新记录。[修复前的 MCP 更新](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L420) · [Mem0 SDK 更新](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L2066)
- **修改与验收。** 允许省略 `text`，接受 `category`、`importance`、`metadata` 的部分更新，至少指定一项变更。分类是同一分区内的元数据，归属仍由受信任的身份绑定确定。复用新增的分类、敏感值及保留字段校验。只发送本次提供的字段，回读核对本次变更和不可变的 ID、归属、创建时间。将 `rp.taste` 改为 `rp.habit` 后，正文、ID、`created_at` 和原有历史保留，分类筛选随之变化。现有历史只记录正文前后值，分类差异审计和并发条件更新需单独验证。
- **2026 年 11 月 11 日验收。** MCP 19 项测试通过，覆盖改分类、原字段与历史保留、新旧分类查询、重复请求、越权和回读失败。AionCore 全仓 9,454 项通过、53 项跳过。[Aion 会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
- **2026 年 11 月 11 日部署验收。** NAS MCP 部署 `c362e42`，本机 Web 部署 AionCore `e0d7996a`。使用同一发布二进制启动隔离 Aion 会话，由测试模型发起分类更新，实际请求经过 NAS MCP 和 Mem0。核对了原 ID、正文、创建时间、归属、原有历史、新旧分类查询及重复提交。测试分区的记录已通过 MCP 删除，Mem0 保留正常审计历史。两端健康检查通过。

### 2. 显式过期与查看过期记录

- [x] **已部署并通过端到端验收。** 2026 年 11 月 11 日，本项验收范围调整为 Mem0 原生的 `YYYY-MM-DD` 到期能力。记录在到期日当天仍可见，次日 UTC 零点起隐藏。[Mem0 到期判断](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L455)
- **修改与验收。** 新增使用可选 `expirationDate` 透传到上游 `expiration_date`，日期校验包含实际日历合法性。省略时长期有效。搜索和列表用 `includeExpired` 对接原生 `show_expired`，保留身份与范围过滤。用可控时钟验收到期日当天可见、次日默认隐藏、显式查看过期记录，以及非法日期和跨分区拒绝。AionCore schema 和 Skill 同步支持这两个参数。
- **2026 年 11 月 11 日验收。** MCP 21 项测试通过。AionCore 全仓 9,455 项通过、53 项跳过，会话集成测试验证 `includeExpired` 透传。[Aion 会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
- **2026 年 11 月 11 日部署验收。** NAS MCP 部署 `7f999b6`，本机 Web 部署 AionCore `69977162`。用发布二进制启动隔离 Aion 会话，由固定模型响应触发工具调用，实际经过 NAS MCP 和 Mem0。当天到期与无到期日的记录默认可见，前一日到期的记录仅在显式查看过期记录时出现在搜索和列表中。验证了非法日期拒绝、按 ID 读取隐藏过期记录和跨助手隔离。测试分区记录已删除，Mem0 保留审计历史。两端健康检查通过。

### 3. 按记录时间过滤

- [x] **已部署并通过端到端验收。** 修复前，MCP 将 `created_at`、`updated_at` 保留为系统字段，pgvector 的通用范围操作按数值转换，NAS 列表也没有时间过滤入口。[修复前的 MCP 过滤器](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L200) · [修复前的 pgvector 范围比较](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/vector_stores/pgvector.py#L36)
- **实现。** `memory_list` 和 `memory_search` 接收可选 `since`（包含）、`until`（排除）和 `timeField`，默认按 `created_at`，可选 `updated_at`。日期按 UTC 零点，带时区的时间戳转换到 UTC，旧无时区的 ISO 时间按 UTC 解释。缺失或无效时间只在按该字段筛选时排除。列表和搜索在候选限额前过滤，带时间范围的语义搜索在范围内按向量距离精确排序，避免 HNSW 漏掉窄时间范围里的记录。列表保留 1,000 条上限与截断提示，分页由 #7 跟进。[Aion 工具参数](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L111)
- **2026 年 11 月 11 日验收。** Mem0 REST 参数与 pgvector 回归 163 项通过，MCP 23 项通过，AionCore 全仓 9,455 项通过、53 项跳过。用隔离的 PostgreSQL 17 和真实 pgvector 验证 REST 列表、语义及关键词查询。预置 1,105 条范围外记录，核对起止边界、跨时区同一时刻、单端范围、旧记录的更新时间、无效时间、过期选项和身份过滤。测试数据库已随容器清理。[Aion 会话参数透传回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
- **2026 年 11 月 11 日部署验收。** 依次部署 NAS Mem0 `02b4b6ad`、MCP `4090959` 和本机 Web 的 AionCore `a8c4aa7c`。以同一发布二进制启动隔离会话并挂载新版 Memory Triage Skill，固定模型响应触发工具调用，实际经过 NAS MCP、Mem0 和配置的嵌入服务。六个用例通过，覆盖创建时间列表与搜索、更新时间、过期可见性、跨助手隔离和省略时间条件。另验证了空范围拒绝。八条测试记忆已删除，两组测试分区为空，服务健康检查通过。[Mem0 变更](https://github.com/hoholidayx/mem0/commit/02b4b6ad) · [MCP 变更](https://github.com/hoholidayx/mem0-mcp-lan/commit/4090959) · [AionCore 变更](https://github.com/hoholidayx/AionCore/commit/a8c4aa7c)

### 4. 共享密钥的身份头诊断

- [x] **已部署并通过端到端验收。** 修复前，服务密钥有效时，MCP 对分区头缺失、重复或无效统一返回 `invalid_memory_scope`。实机只读握手中，同一服务密钥缺两个头或仅带用户头返回 `400`，带齐返回 `200`。AionCore 专用客户端会从会话的登录用户和助手定义派生两个身份头。[修复前的 MCP 鉴权](https://github.com/hoholidayx/mem0-mcp-lan/blob/4090959/src/mem0_mcp/app.py#L98) · [Aion 客户端](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L203)
- **实现。** MCP 在凭据有效时为 HTTP `400` 的 `invalid_memory_scope` 增加 `issues`，只返回固定头名和 `missing`、`duplicate`、`invalid`、`unexpected` 原因。AionCore 复用现有 HTTP 状态，区分握手拒绝、鉴权失败和访问拒绝。诊断使用固定响应和文案，避免回显头值、凭据和上游正文。Aion 专用工具继续使用共享密钥和自动分区，仅发送 Bearer 的客户端使用固定分区的角色凭据。
- **2026 年 11 月 11 日本地验收。** MCP `ab5c19a` 的 23 项测试通过，覆盖每个头分别缺失、同时缺失、重复、非法、角色凭据兼容和 HTTP `401`、`403`。AionCore `f91e2538` 全仓 9,455 项通过、53 项跳过。会话回归验证了助手分区、握手错误脱敏和发出写请求后连接失败仍返回 `write_unconfirmed`。
- **2026 年 11 月 11 日部署验收。** NAS MCP 部署 `ab5c19a`，本机 Web 部署 AionCore `f91e2538`。NAS 实测共享密钥带齐身份头和角色凭据仅带 Bearer 都可握手，缺失、重复、非法和多余身份头返回对应诊断，错误凭据及受限来源分别返回 `401`、`403`。使用正式发布二进制启动隔离 Aion 会话，两个助手各自只读到本分区的测试记忆，真实握手 `400` 和 `401` 分别返回固定诊断。两条测试记忆已删除，两组测试分区为空，服务健康检查通过。[会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)

## P1 · 可用性

- [x] **5. 自定义分类默认 importance，已实现并通过本地验收。** 新增有分类的记忆时，依次使用工具字段、`metadata.importance`、内置分类默认值或自定义分类兜底 `0.5`。分类可自定义，业务可通过新增或更新显式给出 `0` 到 `1` 的分数。未分类的新记忆只写入调用方指定的分数，更新省略两处 `importance` 时保留原值。Memory Triage Skill 与 MCP、AionCore 的工具 schema 均说明了该规则。MCP 24 项测试通过，覆盖 `work.pref` 写入回读、显式 `0`、元数据改分和编辑分类保留原分数。[Aion 工具参数](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L93)
  - **2026 年 11 月 11 日验证。** MCP `464fa97` 与 AionCore `4451f640` 已本地提交。AionCore 全仓 9,455 项通过、53 项跳过。
- [ ] **6. 参数校验缺少字段诊断，成立。** MCP 的 Pydantic 校验和 Aion 的前置白名单都可能先返回通用错误。返回有限长度、脱敏的字段路径和稳定的错误类型或安全文案，避免回显参数值、原始 `msg`、`ctx` 和任意长字段名。验收短字段拼错可定位，敏感输入不出现在返回和日志。`path` 与 `skill_path` 的例子走 Aion Skill HTTP/CLI，由 #9 覆盖。[MCP 参数校验](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/app.py#L165) · [Aion 参数白名单](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L103)
- [ ] **7. `memory_list` 缺分类和元数据过滤，成立。** 当前公开参数仅支持 `scope`，NAS 列表接口没有元数据过滤或游标。复用 search 的过滤白名单和身份约束，给 list 增加 `categories`、`filters`、`includeExpired`，在上游限额前过滤，并提供确定性排序与分页。验收无需 query 即可列 `work.todo`，大量记录跨页不漏不重。分页能力上线前，继续明确返回截断状态。[MCP 列表](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L336) · [Mem0 列表 REST](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/server/main.py#L470)
- [ ] **8. 删除预览缺少范围选择，部分成立。** `query` 预览采用默认 `all`，可返回同一角色下其他分类和凭据绑定的会话记录。它受用户和角色隔离约束，本身只读。只在预览模式支持 `categories` 与 `scope`，按 ID 和批量模式拒绝这些参数。验收限定分类和范围后候选符合条件，Aion 仍仅访问长期记忆，单条删除继续确认并回读。[MCP 删除预览](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L450) · [Aion 删除确认](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L264)

## P2 · 接口一致性与效率

- [ ] **9. Skill CLI 路径参数不一致，成立。** `config skills import` 和 `scan` 分别将 JSON 传给各自的 REST 请求结构，必填 `skill_path` 和 `folder_path`。给两种请求增加 `path` 兼容别名，保留旧字段和路径校验，同步能力发现及帮助。验收两条命令均接受 `path` 和各自旧字段，重复或冲突输入明确拒绝。[Skill 请求类型](../AionCore/crates/aionui-api-types/src/skill.rs#L61) · [CLI 路由](../AionCore/crates/aionui-app/src/commands/cmd_config.rs#L328)
- [ ] **10. MCP 无可调相关度阈值，成立。** NAS 已有上游 `threshold`，它筛的是混合评分前的语义分。新增 `minScore` 时定义为返回结果 `score` 的下限，接受 0 到 1，省略时沿用当前行为。验收低于阈值被排除、等于阈值仍返回、非法值拒绝。与 rerank 对照时注明分数来自哪个阶段。[MCP 搜索](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L316) · [Mem0 评分](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/utils/scoring.py#L60)
- [ ] **11. 跨分类写入需要多次 MCP 调用，成立。** 当前一个 `facts` 批次共享元数据，上游 REST 也是请求级元数据。增加与 `text`、`facts` 互斥的 `items`，每项可单独传 `text`、`category` 和 `importance`，最多 25 项。先校验整批，再按有效元数据分组请求上游。按输入索引返回 ID 和逐项结果，区分失败、未尝试和写入未确认。验收一条 MCP 调用写入 `work.pref` 和 `rp.master`，相同正文的不同分类可分别保存，部分成功或超时可定位后再重试。[MCP 新增](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L365) · [Mem0 新增请求](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/server/main.py#L205)

改工具参数时，同步 MCP schema、AionCore 的专用工具 schema 与白名单、`memory-triage` 和测试。#3 与 #7 共用上游列表能力，#10 与路线图的 rerank 对照共同验收。

## 完成记录与下游反馈

- [ ] 逐条处理并验收 #1 至 #11 后，在本文追加完成记录。沿用原编号，注明实际处理结果、验证方式与证据、对应提交或部署版本，以及仍适用的限制。
- [ ] 整批验收完成后，在交付回复中主动提醒用户，并交付一份可直接转发给下游需求方的独立反馈文档。按 #1 至 #11 对照原诉求，逐条写明结论、实际变化、使用方式和验收结果。
