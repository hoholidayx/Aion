# 记忆 MCP 与 Skill 接口待办

2026 年 11 月 10 日复核。依据当前 AionCore、`mem0-mcp-lan` 源码和 NAS Mem0 实时 OpenAPI。涉及存储行为时，另对照本地 Mem0 SDK 和 pgvector 源码。本次为只读诊断，待办保留原编号。[MCP 工具](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py) · [NAS REST 实现参考](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/server/main.py) · [Aion 工具适配](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs)

## P0 · 正确性

### 1. 原地修正分类和元数据

- [x] **已部署并通过端到端验收。** 修复前，MCP 和 AionCore 只接收 ID 和正文，正文相同时提前返回，回读校验要求元数据原样保留。NAS 的 PUT 已接受独立 `metadata`，SDK 在已有元数据上做顶层合并，保留 ID 和 `created_at`，并追加更新记录。[修复前的 MCP 更新](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L420) · [Mem0 SDK 更新](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L2066)
- **修改与验收。** 允许省略 `text`，接受 `category`、`importance`、`metadata` 的部分更新，至少指定一项变更。分类是同一分区内的元数据，归属仍由受信任的身份绑定确定。复用新增的分类、敏感值及保留字段校验。只发送本次提供的字段，回读核对本次变更和不可变的 ID、归属、创建时间。将 `rp.taste` 改为 `rp.habit` 后，正文、ID、`created_at` 和原有历史保留，分类筛选随之变化。现有历史只记录正文前后值，分类差异审计和并发条件更新需单独验证。
- **2026 年 11 月 11 日验收。** MCP 19 项测试通过，覆盖改分类、原字段与历史保留、新旧分类查询、重复请求、越权和回读失败。AionCore 全仓 9,454 项通过、53 项跳过。[Aion 会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
- **2026 年 11 月 11 日部署验收。** NAS MCP 部署 `c362e42`，本机 Web 部署 AionCore `e0d7996a`。使用同一发布二进制启动隔离 Aion 会话，由测试模型发起分类更新，实际请求经过 NAS MCP 和 Mem0。核对了原 ID、正文、创建时间、归属、原有历史、新旧分类查询及重复提交。测试分区的记录已通过 MCP 删除，Mem0 保留正常审计历史。两端健康检查通过。

### 2. 显式过期与查看过期记录

- [ ] **成立，原生能力有粒度限制。** MCP 的新增没有过期参数，公开查询也没有 `includeExpired`。NAS 的 `expiration_date` 只接受 `YYYY-MM-DD`，记录在到期日当天仍可见，按 UTC 日期判断过期。现有内部 `show_expired` 可用于读取过期记录。[MCP 可见性](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L143) · [Mem0 到期判断](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L455)
- **修改与验收。** 可先开放显式日期和 `includeExpired`，默认继续隐藏过期记录，未设置时继续长期有效。精确 TTL 需要新增 UTC 时间戳语义，支持 `expiresIn` 或带时区的 `expiresAt`，在检索和列表限额前过滤，并和按 ID 读取保持一致。用可控时钟验证 59 秒仍可见、满 60 秒默认隐藏、`list(includeExpired=true)` 仍能看到且跨分区不可见。只完成日期级方案时，60 秒验收继续保留。
- **下一步方案。** 以 60 秒验收为目标，在 Mem0 REST 和 SDK 增加独立的精确到期字段，存储层按 UTC 绝对时间比较。旧 `expiration_date` 继续以到期日次日 UTC 零点为边界。MCP 将互斥的正整数 `expiresIn` 和带时区的 `expiresAt` 转成同一上游字段，将显式 `includeExpired` 传到 `show_expired`。当前 SDK 先取限量候选再过滤，需让 pgvector 在取候选时就排除过期记录。验收增加「过期记录多于候选上限时仍能返回未过期记录」，并同步 AionCore schema 和 Skill。[当前列表候选获取](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L1337) · [当前搜索候选获取](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/memory/main.py#L1655)

### 3. 按记录时间过滤

- [ ] **成立。** MCP 将 `created_at`、`updated_at` 保留为系统字段，范围操作仅接受数值。当前 pgvector 的通用范围操作也按数值转换，直接放开 ISO 时间字符串会失败。NAS 的列表接口只提供身份、条数和过期选项，当前上限为 1,000 条。[MCP 过滤器](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L200) · [pgvector 范围比较](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/mem0/vector_stores/pgvector.py#L36)
- **修改与验收。** 增加只读的 `since`、`until` 和创建时间或更新时间选项，明确时区、旧时间戳的解释，以及起始包含、结束排除的边界。按类型将范围过滤下推到限额前，与 #7 复用列表过滤和分页。「上周记了什么」以创建时间为准，和事实发生时间分开。验收 `since: "2026-11-01"`、等于边界、跨时区、更新旧记录和超过 1,000 条的结果。

### 4. 共享密钥的身份头诊断

- [ ] **报错缺少细节成立，Aion 专用客户端未注入头的判断未复现。** AionCore 从会话的登录用户和助手定义派生两个身份头。服务密钥有效时，MCP 对分区头缺失、重复或无效统一返回 `invalid_memory_scope`。实机只读握手中，同一服务密钥缺两个头或仅带用户头返回 `400`，带齐返回 `200`。Aion 集成测试也覆盖两个助手各自的身份头。[Aion 客户端](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L184) · [Aion 集成测试](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343) · [MCP 鉴权](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/app.py#L70)
- **修改与验收。** 保留 Aion 的单服务密钥与自动分区。复现部署问题时先区分 Aion 专用记忆工具、通用 MCP 注册和直连脚本。诊断返回缺失或无效的头名与原因，避免回显头值、凭据或正文，Aion 侧保留安全的连接错误信息。使用 NAS `profiles.<role>` 的独立客户端可以仅发送绑定角色的 Bearer，继续作为兼容路径。验收覆盖共享密钥带齐头成功、缺每个头分别可定位、角色凭据无头成功。只有专用路径仍出现失败时，按 P0 部署问题追踪。

## P1 · 可用性

- [ ] **5. 自定义分类默认 importance，成立。** 目前仅内置分类有默认值。复用新增时的元数据归一化，工具字段和元数据中的显式值优先，其次按分类精确配置、最长前缀、兜底的顺序选择。保留显式 `0`。验收 `work.pref` 省略 `importance` 后回读仍有值，显式值优先，内置分类保持原默认。[新增与默认值](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L365)
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
