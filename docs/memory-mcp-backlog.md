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

- [x] **5. 自定义分类默认 importance，已部署并通过端到端验收。** 新增有分类的记忆时，依次使用工具字段、`metadata.importance`、内置分类默认值或自定义分类兜底 `0.5`。分类可自定义，业务可通过新增或更新显式给出 `0` 到 `1` 的分数。未分类的新记忆只写入调用方指定的分数，更新省略两处 `importance` 时保留原值。Memory Triage Skill 与 MCP、AionCore 的工具 schema 均说明了该规则。MCP 24 项测试通过，覆盖 `work.pref` 写入回读、显式 `0`、元数据改分和编辑分类保留原分数。[Aion 工具参数](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L93)
  - **2026 年 11 月 11 日验证。** MCP `464fa97` 与 AionCore `4451f640` 已本地提交。AionCore 全仓 9,455 项通过、53 项跳过。
  - **2026 年 11 月 11 日部署验收。** 随 NAS MCP `7ff4f9e` 和本机 AionCore `9de065b1` 发布。隔离助手挂载新版 Memory Triage Skill 后，通过实际链路写入 `work.pref` 并回读 `0.5`，显式 `0` 覆盖元数据中的分数，编辑分类后仍保留 `0`。
- [x] **6. 参数校验缺少字段诊断，已部署并通过端到端验收。** MCP 的 `invalid_arguments` 与 AionCore 的 `invalid_memory_arguments` 增加 `issues`。MCP 最多返回五条，Aion 前置检查返回首条。诊断包含已知字段路径、数组索引和固定原因，短字段名只有唯一匹配合法字段时才返回拼写建议。参数值、未知键及 Pydantic 原始报错均省略。Skill HTTP/CLI 的路径字段由 #9 跟进。[Aion 参数校验](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L132)
  - **2026 年 11 月 11 日本地验收。** MCP `7ff4f9e` 的 25 项测试通过，覆盖字段拼写、类型、范围、字段组合及脱敏。AionCore `9de065b1` 全仓 9,456 项通过、53 项跳过。会话回归核对了 MCP 诊断透传，并确认冲突的删除参数在 MCP 请求和删除确认之前被拒绝。[会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
  - **2026 年 11 月 11 日部署验收。** 发布版 AionCore 在隔离会话中实际连接 NAS MCP 与 Mem0，覆盖 `qurey`、错误类型的 `limit` 和 `facts[1]`、越界 `scope`、删除参数冲突与五条诊断上限。测试用的字段名和值未出现在诊断和运行日志中，冲突的删除请求未触发删除确认，记录仍可读。验收后通过 MCP 删除测试记录并确认测试分区为空。两端健康检查通过。
- [x] **7. `memory_list` 缺分类和元数据过滤，已部署并通过端到端验收。** 无需 `query` 即可按 `categories` 和 `filters` 列出 `work.todo`，可组合已有的分区、时间与过期条件。PostgreSQL 先筛选，再按记忆 UUID 升序分页。`limit` 取 1 到 1,000，默认 1,000。后续页用 `nextCursor` 作为 `cursor`，保留 `truncated` 表示还有下一页。批量删除沿用原有上限和截断时拒绝执行的检查。[Aion 工具适配](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs)
  - **2026 年 11 月 11 日隔离验收。** Mem0 REST 参数和 pgvector 回归 164 项通过，MCP 26 项通过，AionCore 全仓 9,456 项通过、53 项跳过。真实 MCP 经 HTTP Mem0 连接隔离 PostgreSQL 17，预置 1,105 条排序靠前的无关记录，核对分类和元数据过滤后跨页无遗漏或重复。REST 另外验证了时间、过期和会话范围、混合类型的数值字段、跨分区及篡改游标拒绝、删除游标所指记录后继续翻页，以及默认上限的 1,000 加 105 条分页。测试数据库随容器清理。[Aion 会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
  - **2026 年 11 月 11 日部署验收。** NAS 依次部署 Mem0 `65ec8552` 和 MCP `b0b90b8`，本机 Web 发布包搭载 AionCore `68f74dfc`。以同一发布二进制启动隔离的登录会话，挂载新版 Memory Triage Skill，由固定模型响应触发真实 MCP 调用。九轮验收覆盖分类与元数据过滤后的两页、助手隔离、跨助手和改条件的游标拒绝、篡改游标拒绝、过期与时间筛选及删除游标所指记录后继续翻页。通过正式 MCP 写入七条测试记忆，验收后两组测试分区均已清空，旧 REST `GET /memories` 也验证了分区与清理结果。Mem0、MCP 和本机 Web 健康检查通过。
- [x] **8. 删除预览缺少范围选择，已部署并通过端到端验收。** `memory_delete` 的 `query` 模式支持 `categories` 和 `scope`，复用搜索并返回最多 10 条可见候选。独立 MCP 默认 `all`，有会话绑定的凭据可选 `session`。Aion 将省略的 `scope` 和 `all` 都按 `long-term` 执行，拒绝 `session`。按 ID 或批量删除时提交预览字段会返回参数错误。Memory Triage Skill 和 README 已同步。[Aion 工具适配](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs)
  - **2026 年 11 月 11 日本地验收。** MCP 27 项测试通过，验证了分类、当前会话、长期范围、其他助手和会话、过期记录，以及非法组合未请求 Mem0。AionCore 在独立检出中通过参数回归和会话集成测试，验证预览传递的分类与范围、参数冲突拦截、取消删除及批准后重新读取并删除指定 ID。[Aion 会话回归](../AionCore/crates/aionui-app/tests/assistant_follow_e2e.rs#L343)
  - **2026 年 11 月 11 日部署验收。** NAS MCP 已部署 `1881a88`，连接 Mem0 `65ec8552`。使用本机 Web 正式发布包的 AionCore `f64acb3c`（包含 `01956f60`）启动隔离登录会话并挂载新版 Memory Triage Skill。固定模型响应触发九轮真实调用，覆盖默认和显式 `all` 的分类预览、会话范围与非法参数拒绝、跨助手 ID 拒绝、取消保留、确认期间发生变更时阻止删除、批准后只删除指定 ID，以及重复删除返回 `memory_not_found`。独立 MCP 用同一发布镜像和绑定会话的测试凭据验证了长期与当前会话范围、其他助手与会话隔离、过期记录过滤，以及按 ID 和批量模式拒绝预览字段。测试记录均已清理，Mem0、MCP 和本机 Web 健康检查通过。

## P2 · 接口一致性与效率

- [x] **9. Skill CLI 路径参数不一致，已部署并通过端到端验收。** `config skills import` 和 `scan` 均接受 `path`。导入兼容 `skill_path`，扫描兼容 `folder_path`。同时提供 `path` 与旧字段会返回 HTTP 400。CLI 帮助和能力发现均推荐 `path`。[Skill 请求类型](../AionCore/crates/aionui-api-types/src/skill.rs#L61) · [CLI 能力发现](../AionCore/crates/aionui-app/src/commands/config_capabilities.rs#L79)
  - **2026 年 11 月 11 日本地验收。** AionCore `e5644822` 的 97 项相关测试通过。用本地构建的 CLI 连接隔离后端，两条命令用新旧字段均可处理含空格的路径，新旧字段并传时拒绝且导入列表未变化。两个子命令的 `--help` 已实测。
  - **2026 年 11 月 12 日部署验收。** 本机正式 Web 使用 AionCore `e5644822` 和 AionUi `a35f3ce1f`。使用发布版 CLI 连接同一二进制启动的隔离后端，验证两条命令的新旧字段、含空格的路径、混用字段拒绝及导入目录回读。两个子命令的帮助和能力发现均列出了 `path` 及对应旧字段。正式 Web 健康检查通过，隔离数据已清理。
- [x] **10. MCP 无可调相关度阈值，已部署并通过端到端验收。** `memory_search` 支持 `minScore`，取 `0` 到 `1`。MCP 合并候选后只保留混合 `score` 大于等于阈值的记录，再按原顺序裁剪。省略时使用默认搜索结果。Mem0 的语义召回门槛在混合评分前应用。AionCore 暴露并透传该字段，Memory Triage Skill 与 README 已同步。[Aion 搜索 schema](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs#L83) · [Mem0 评分](https://github.com/hoholidayx/mem0/blob/65ec8552/mem0/utils/scoring.py#L60)
  - **2026 年 11 月 12 日隔离验收。** MCP 28 项测试通过，覆盖分数边界、同分排序、跨会话范围合并、空结果和非法参数。AionCore 的两项会话集成测试通过，核对了 schema 和参数透传。临时 MCP 连接 NAS Mem0 `65ec8552`，逐次核对了上游响应与筛选后的 ID、分数和顺序。合成查询 `release checklist before production deployment` 的混合分为 `0.337079`、`0.332550`、`0.322869`、`0.225677`，阈值约 `0.281378` 时保留三条。`billing receipt invoice payment date` 的混合分为 `0.373703`、`0.343716`、`0.220663`、`0.218840`，阈值约 `0.296271` 时保留两条。两组分数用于后续重排对照，测试分区已清空。
  - **2026 年 11 月 12 日部署验收。** NAS MCP 部署 `ee86eb0`，本机 Web 部署 AionCore `6694ba2c`。使用正式二进制启动隔离登录会话，挂载新版 Memory Triage Skill，由固定模型响应触发八轮工具调用，经正式 NAS MCP 连接 Mem0。两组查询分别从四条筛到三条和两条，剩余记录的顺序与基线一致，分数均达到对应阈值。另验证 `0`、空结果、跨助手与过期隔离，以及越界值和字符串的字段诊断。两个测试分区已清空，Mem0、MCP 和 Web 健康检查通过。
- [ ] **11. 跨分类写入需要多次 MCP 调用，成立。** 当前一个 `facts` 批次共享元数据，上游 REST 也是请求级元数据。增加与 `text`、`facts` 互斥的 `items`，每项可单独传 `text`、`category` 和 `importance`，最多 25 项。先校验整批，再按有效元数据分组请求上游。按输入索引返回 ID 和逐项结果，区分失败、未尝试和写入未确认。验收一条 MCP 调用写入 `work.pref` 和 `rp.master`，相同正文的不同分类可分别保存，部分成功或超时可定位后再重试。[MCP 新增](https://github.com/hoholidayx/mem0-mcp-lan/blob/2557840/src/mem0_mcp/tools.py#L365) · [Mem0 新增请求](https://github.com/hoholidayx/mem0/blob/a6adc944c818d590cf93cfba69bfe79e49bb6c11/server/main.py#L205)

改工具参数时，同步 MCP schema、AionCore 的专用工具 schema 与白名单、`memory-triage` 和测试。#3 与 #7 共用上游列表能力。评估 rerank 时，使用 #10 记录的当前混合分作为对照，并注明阈值应用在哪个阶段。

## 完成记录与下游反馈

- [ ] 逐条处理并验收 #1 至 #11 后，在本文追加完成记录。沿用原编号，注明实际处理结果、验证方式与证据、对应提交或部署版本，以及仍适用的限制。
- [ ] 整批验收完成后，在交付回复中主动提醒用户，并交付一份可直接转发给下游需求方的独立反馈文档。按 #1 至 #11 对照原诉求，逐条写明结论、实际变化、使用方式和验收结果。
