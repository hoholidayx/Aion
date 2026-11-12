# Aion 记忆优化待办

2026 年 11 月 12 日更新。以下任务按依赖顺序排列。

接口缺口、诊断和分类问题单独记录在 [记忆 MCP 与 Skill 接口待办](memory-mcp-backlog.md)。

## 当前能力

- 登录 WebUI 后，AionRS 助手可以通过 AionCore 使用 Mem0 的查询、写入、更新和单条删除工具。AionCore 与 MCP 配置同一份服务密钥，AionCore 从登录用户和助手定义自动确定长期记忆分区。助手仍独立启用，单条删除沿用用户确认。需要沿用旧分区时，配置不含凭据的分区映射。[配置与分区](../AionCore/ARCHITECTURE.md#assistant-long-term-memory) · [工具接入](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/mem0.rs)
- `memory-common` 已定义何时查、记和改。挂载后由主对话模型在轮内按需调用。MCP 用 `infer=false` 写入已经提取的事实，检索结果按现有分数排序。[通用记忆 Skill](https://github.com/hoholidayx/mem0-mcp-lan/blob/bcdbab1c9e251d292529e89d986d39e58e77e0b2/skills/memory-common/SKILL.md) · [MCP 工具实现](https://github.com/hoholidayx/mem0-mcp-lan/blob/25578407aeb9e3bf549fe7fc558bc4384e5b5ad7/src/mem0_mcp/tools.py)

## 1. 自动 recall 和检索追踪

- [ ] 在 AionCore 的正常发消息路径接入轮前决策，沿用已有 Mem0 绑定和轮次生命周期。用户明确要求回忆时直接查。当前上下文已足够时跳过。其余有记忆信号的请求交给决策模型，输出 `skip` 或带短查询和可选分类的 `search`。复用已有供应商与模型配置，首版可选 OpenAI，输出由 Aion 校验。
- [ ] 在主模型首次请求前注入少量相关记录，作为本轮临时参考上下文。引擎负责请求侧注入，AionCore 负责决策和鉴权。保留记录的时间信息，用户当前的明确纠正优先。无匹配、超时或出错时继续正常回复。[AionCore 轮次入口](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/agent.rs) · [引擎请求构造](../aionrs/crates/aion-agent/src/engine.rs)
- [ ] 增加助手级自动 recall 开关，初期默认关闭。追踪跳过、触发、候选数量、入选和耗时，常规日志只记诊断字段。用少量案例覆盖显式回忆、模糊引用、无需回忆、跨助手隔离和 MCP 超时。验收时分别看误触发、漏触发、候选缺失和首字延迟。

## 2. 候选召回与 rerank

- [ ] 用相同查询和候选做重排前后对照。候选里缺正确记录时，优先检查查询改写、别名、分类与时间过滤，以及事实有没有写入。候选包含正确记录但它排得低时，再验证重排收益。
- [ ] 让手动查询和自动 recall 共用 MCP 的检索排序。先按身份和可见范围过滤，再对扩大的候选集重排，最后裁剪输出。初始试验可取 20 条候选、注入最多 3–5 条。重排失败时回退现有排序。
- [ ] 验证部署链路。当前 NAS 的 HTTP `/search` schema 没有 `rerank` 参数。若采用 Mem0 OSS 的 reranker，需要接通 HTTP 参数并保留返回顺序，避免 MCP 再按原分数排序。验收记录候选覆盖、重排后命中和额外延迟。[Mem0 搜索文档](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-operations/search.mdx)

## 3. 自动记忆与可追溯写入

- [ ] 在成功轮次结束后异步读取新增原文，先运行只产候选模式。沿用 `memory-common` 的长期价值、新颖性、事实依据和安全规则。决策模型返回 `skip` 或候选事实、分类与来源证据。外部模型输入和写入前分别做安全校验，自动 recall 和自动写可共用模型配置，各自维护独立的提示词、输出约束和超时。
- [ ] 按同一助手分区查重，由 AionCore 校验后复用 MCP 执行 `skip`、`add` 或 `update`。先开放高置信、有原文依据的新增，再开放明确的纠正和更新。启用自动写的助手由后台负责自动结算，skill 继续处理用户显式请求和按需查询。删除仍使用现有确认，项目记忆维持当前过期策略。
- [ ] 复用现有轮次 ID 定位原文，记录事实时间、来源轮次和关联记忆 ID。当前更新接口保留元数据，先核对现有历史能否表达更新来源。需要支持压缩和会话结束补结算时，沿用同一结算游标。只在需要跨重启恢复或协调并发时引入对应状态。对相同事实做幂等，遇到 `write_unconfirmed` 先核对服务端实际状态再重试。[轮次 ID 与完成分支](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/agent.rs)
- [ ] 增加独立于自动 recall 的助手级自动写开关，初期默认关闭。人工抽查无依据写入、重复写入、错误覆盖和遗漏，覆盖被取消的轮次、更新冲突和重试。通过后逐步开放自动新增和自动更新。

## 相关待办：按模型配置上下文窗口与最大输出

当前「设置 → 模型供应商 → 配置模型」缺少这两个字段。AionRS 可从 TOML 读取 `[compact].context_window`，Aion Web 会清除独立 AionRS 的 `max_tokens` 覆盖。[模型设置](../AionUi/packages/desktop/src/renderer/pages/settings/components/AddModelModal.tsx) · [Web 运行时](../AionCore/crates/aionui-ai-agent/src/manager/aionrs/agent.rs)

- [ ] 复用现有按模型配置，为上下文窗口和单次最大输出提供独立的可选字段。空值沿用当前自动策略。AionCore 将上下文窗口传给 AionRS 的上下文预算和压缩逻辑，将最大输出交给现有的供应商协议适配。[模型配置类型](../AionCore/crates/aionui-api-types/src/provider.rs) · [上下文压缩配置](../aionrs/crates/aion-config/src/compact.rs)
- [ ] 验收保存和回读、清空恢复默认、旧配置兼容，以及不同供应商下同名模型的隔离。检查实际对话的上下文窗口和压缩阈值，以及上游请求中的输出限制字段。
