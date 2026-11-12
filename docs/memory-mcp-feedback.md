# 记忆 MCP 与 Skill 接口改进验收反馈

2026 年 11 月 12 日，原需求 #1 至 #11 已完成部署验收。本次验收使用 NAS Mem0 `65ec8552`、MCP `13f876b`，以及包含 AionCore `8aa16fc9` 和 AionUi `a35f3ce1f` 的本机 Web 发布包。各项的部署版本与验证记录见[记忆 MCP 待办与验收记录](memory-mcp-backlog.md)。

| 编号 | 交付与使用 | 验收结果与适用边界 |
| --- | --- | --- |
| 1 · 修改分类 | `memory_update` 传 `memoryId`，再传 `category`、`importance`、`metadata` 或 `text` 中需要调整的字段。元数据按顶层键合并。 | 将 `rp.taste` 改为 `rp.habit` 后，原 ID、正文、`created_at` 和原有编辑历史保留，分类查询随之变化。历史目前记录正文前后值，分类差异审计需单独处理。 |
| 2 · 显式到期 | `memory_add` 用 `expirationDate` 指定 UTC 日期，格式为 `YYYY-MM-DD`。`memory_list` 和 `memory_search` 用 `includeExpired: true` 查看过期记录。 | 验证了到期当日仍可见、次日 UTC 零点起默认隐藏、显式查看过期数据及非法日期拒绝。沿用 Mem0 原生日期粒度。 |
| 3 · 时间过滤 | 列表和搜索接受 `since`（含起点）和 `until`（不含终点）。默认使用 `created_at`，可用 `timeField: "updated_at"` 查编辑时间。 | 验证了时间边界、时区转换、创建时间与更新时间，并核对了候选限额前的筛选。日期按 UTC 零点解析，时间戳需带时区。 |
| 4 · 分区头诊断 | Aion 从登录用户和助手自动派生 `X-Mem0-User-Id` 与 `X-Mem0-Agent-Id`。独立客户端可用绑定固定分区的角色 Bearer 发起调用。 | 实测角色 Bearer 单独握手成功。共享密钥模式对缺失、重复或无效的头返回具体字段和原因，Aion 区分握手、鉴权和访问拒绝。 |
| 5 · 自定义分类权重 | 自定义分类默认 `importance` 为 `0.5`。业务可在新增或更新时显式传 `0` 到 `1`，也可使用 `metadata.importance`。两处同时提供时工具参数优先。 | 回读验证了 `work.pref` 的默认 `0.5`、显式 `0` 覆盖以及编辑分类时保留原权重。无分类时只有显式赋值才保存权重。 |
| 6 · 参数错误诊断 | 读取 `invalid_arguments` 或 `invalid_memory_arguments` 中的 `issues`。每项给出已知字段路径、索引和原因，能唯一识别拼写时提供建议。 | 验证了拼写、类型、越界和字段冲突。MCP 最多返回五条，Aion 前置校验返回首条。参数原值和未知键不回显。 |
| 7 · 分类列表 | `memory_list` 可直接传 `categories`、`filters` 和 `scope`。按页读取时用 `nextCursor` 作为下一页的 `cursor`，并沿用筛选条件。 | 无需 `query` 即可列出 `work.todo`。验证了筛选后分页无遗漏或重复，跨助手、变更筛选条件和篡改游标均被拒绝。每页最多 1,000 条。 |
| 8 · 删除预览范围 | `memory_delete` 的 `query` 模式可传 `categories` 和 `scope`，最多返回 10 条候选。Aion 预览限定在长期分区，独立 MCP 可用绑定会话的凭据预览 `session`。 | 验证了分类和范围筛选、跨助手拒绝、取消保留记录、等待确认期间发生变化时中止、确认后仅删除指定 ID。Aion 删除仍经过用户确认。 |
| 9 · Skill CLI 路径 | `config skills import` 与 `config skills scan` 的请求均接受 `path`。导入兼容 `skill_path`，扫描兼容 `folder_path`。 | 发布版 CLI 验证了两个命令的新旧字段、含空格路径和新旧字段同时提交时的拒绝。帮助与能力发现均已同步。 |
| 10 · 召回阈值 | `memory_search` 可传 `minScore`，取 `0` 到 `1`，仅保留混合相关度大于等于阈值的候选。 | 两组真实查询分别从四条筛到三条和两条，候选顺序保留。验证了 `0`、空结果和非法值。Mem0 的语义召回门槛先于该阈值应用。 |
| 11 · 跨分类批量写入 | `memory_add` 可传 `items: [{"text":"...","category":"work.pref"},{"text":"...","category":"rp.master","importance":0.8}]`，最多 25 项。批次共用作用域与到期日。 | 25 项实测返回 25 条索引回执并保存 24 条记忆。验证了同文跨分类、非法批次零写入和跨助手隔离。部分写入与 25 秒超时均可定位到原始索引。收到 `write_unconfirmed` 时先回读再补写缺失项。 |

第 11 项的 `items` 与 `text`、`facts` 互斥。每项必填 `text`，可选 `category` 和 `importance`。同批使用相同的 `longTerm` 和 `expirationDate`。Aion 使用长期分区，独立 MCP 的会话绑定凭据可传 `longTerm: false`。回执 `results` 按原始索引给出 `stored`、`failed`、`write_unconfirmed` 或 `not_attempted`。已确认的记录带 `memoryId`。分组写入允许部分成功，去重只覆盖当前请求。
