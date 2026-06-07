# Targeted Resume Project Draft

## 项目经历

### 基于 Agent Harness 的课程平台售后客服智能体系统　　独立开发　　2026.06-至今

**背景：** 面向在线课程平台售后场景，针对误退款、身份校验缺失、课程访问恢复失败、订单信息泄露等高风险问题，构建本地可运行的客服 Agent Harness 原型；项目重点不在“调用大模型回复”，而在于将路由、工具权限、RAG 证据、记忆压缩、Gate 校验和复盘日志工程化。

- **多 Agent 控制平面设计：** 设计 Router / Monitor / Resolver 三类 Agent 分工，由 Router 识别用户意图，Monitor 校验高风险路由和 RAG 证据缺口，Resolver 只基于已验证工具结果生成回复；全链路事件写入 `transcript.jsonl`，支持复盘 raw route、final intent、工具调用和 Gate 决策。

- **RAG + Skills 风险约束：** 将退款、访问恢复、身份校验、发票、账号安全等政策维护为 JSONL 知识库，基于 Embedding 检索、metadata filter、去重和 policy-topic coverage 检查装配证据；通过 deterministic Playbook Skill 固化每类 intent 的风险等级、必需工具和必需政策主题，避免模型自行决定售后流程。

- **MCP 工具网关与权限隔离：** 实现轻量 MCP Gateway，封装 `customer_lookup`、`order_lookup`、`refund_policy_check`、`access_reset`、`escalation_ticket` 等工具，并按 Agent 白名单限制调用；所有工具结果进入审计日志，Gate 会拦截工具失败、越权调用和原始订单号/邮箱泄露。

- **真实 Bad Case 修复：** 在测试中发现 Router 会将“课程打不开，再不解决就退款”高置信误判为退款流程，存在错误触发售后路径风险；引入 Monitor 检查 access/refund 信号冲突，将 final intent 修正为访问恢复，并记录 `route_corrected` 事件用于复盘。

- **多层记忆与上下文污染治理：** 实现 Working / Episodic / Semantic / Procedural 四层记忆，Working Memory 保留最近多轮原文，旧消息压缩到 Semantic Memory，解决用户后续只说“还是不行”时上下文丢失；同时修复历史 `access_issue` 记忆污染发票轮回复的问题，保证显式 Intent 优先于历史关键词。

- **评测与模型边界：** 构建小型端到端回归评测，覆盖高置信错误路由、RAG policy coverage、PII 安全、工具成功率和长对话记忆压缩等场景；支持从 transcript 导出 chat-style SFT 数据，但将路由、工具权限和 Gate 决策保留在 Harness 控制面，预留 OpenAI-compatible / vLLM 接入边界。

## Conservative Version

如果投递岗位更看重真实性和可解释性，可使用更稳版本：

- 独立实现课程平台售后客服 Agent Harness 原型，围绕“课程访问失败、退款、发票、账号安全”等场景设计 Router/Monitor/Resolver 多 Agent 流程，并通过 transcript 记录路由、检索、工具调用和 Gate 结果。
- 基于政策知识库实现 RAG 检索与 policy-topic coverage 检查，通过 Playbook Skill 固化各 intent 所需工具和政策证据，补充 metadata backfill 处理召回不全问题。
- 封装轻量 MCP 工具网关，对订单查询、退款校验、访问恢复和人工工单进行白名单控制与审计，避免模型直接访问业务数据或越权执行工具。
- 实现四层记忆和 working memory 压缩，补充回归测试处理长对话丢失、历史记忆污染当前任务、高置信错误路由等 bad case。

