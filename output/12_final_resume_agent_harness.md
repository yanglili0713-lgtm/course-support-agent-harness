# Final Resume Content

## Fit Verdict

strong fit for LLM application / RAG / Agent engineering internship roles.

Reason: the project has a justified Agent scenario, runnable code, online DeepSeek validation, public-data ingestion, tool grounding, Gate repair, transcript replay, and regression tests. It should still be described as a local runnable prototype, not a production system.

## Resume Version

### 基于 Agent Harness 的课程平台售后客服智能体系统　　独立开发　　2026.06-至今

**背景：** 面向在线课程平台售后场景中“课程访问失败、退款威胁、发票查询、账号安全、人工工单”等高风险问题，构建本地可运行的客服 Agent Harness 原型。项目重点不是让模型直接聊天，而是将路由决策、RAG 证据、工具权限、风险 Gate、记忆管理与 Transcript 复盘工程化，避免模型在未查证订单、未调用工具或缺少政策依据时做出业务承诺。

- **多 Agent 控制平面：** 设计 Router / Monitor / Resolver 三类 Agent 分工，Router 负责意图识别，Monitor 校验高风险路由与证据缺口，Resolver 只基于已验证工具结果生成客服回复；全流程写入 `transcript.jsonl`，可复盘 raw route、final intent、RAG evidence、工具调用、Gate 决策和最终回复。

- **RAG + Skills 风险约束：** 将退款、访问恢复、身份校验、发票、账号安全等政策维护为 JSONL 知识库，通过本地 hash embedding、metadata filter、去重和 policy-topic coverage 检查装配证据；用 deterministic Playbook Skill 固化每类 intent 的风险等级、必需工具和必需政策主题，避免模型自行决定售后流程。

- **轻量 MCP 工具网关：** 实现 MCP-like Gateway，封装 `customer_lookup`、`order_lookup`、`access_reset`、`refund_policy_check`、`escalation_ticket` 等工具，并按 Agent 白名单限制调用；Gate 会拦截工具失败、越权调用、原始订单号/邮箱泄露、无工具支撑的发票开具承诺、未调用退款校验却判断退款资格等风险。

- **真实 bad case 修复：** 在线 DeepSeek 演示中发现多类模型高置信但不安全的输出：将“课程打不开但威胁退款”误路由为退款、无 `invoice_create` 工具却承诺开具发票、虚构或改写工单编号、把 `access_reset` 过度表述为“问题已解决”；通过 Monitor 路由纠偏、工具 grounding Gate、受控 Replan 和回归测试逐项修复。

- **多层记忆与上下文治理：** 实现 Working / Episodic / Semantic / Procedural 四层记忆，Working Memory 保留近期原文，旧对话压缩到 Semantic Memory；修复用户后续只说“还是进不去”时上下文丢失，以及历史 access issue 记忆污染发票轮回复的问题，保证显式 intent 优先于历史关键词。

- **公开数据摄取与安全边界：** 补充公开客服语料摄取流程，基于 Hugging Face 公开 Bitext customer-support 数据集进行 CSV 清洗、去重、来源登记和 metadata 标注，生成增强 RAG 语料；真实用户、订单、工单数据仍使用模拟 fixture，避免隐私数据进入系统。

- **Eval 与复盘闭环：** 构建小型端到端回归评测，覆盖高置信错误路由、RAG policy coverage、PII 安全、工具成功率、工单 grounding、发票越权承诺、访问恢复过度承诺和长对话记忆压缩等场景；当前 `pytest` 23 passed，`support-eval` 3/3 passed，并支持通过 `support_report.md`、`memory_snapshot.json` 和 `transcript.jsonl` 复盘每轮决策。

## Conservative Version

### 基于 Agent Harness 的课程平台售后客服智能体系统　　独立开发　　2026.06-至今

- 构建本地可运行的课程平台售后客服 Agent Harness 原型，围绕课程访问失败、退款威胁、发票查询和人工工单等场景，设计 Router / Monitor / Resolver 多 Agent 流程，并通过 transcript 记录路由、检索、工具调用和 Gate 决策。

- 基于政策知识库实现 RAG 检索与 policy-topic coverage 检查，通过 Playbook Skill 固化各 intent 所需工具和政策证据，并用 metadata backfill 处理身份校验、访问恢复、发票等关键政策召回不全问题。

- 封装轻量 MCP-like 工具网关，对用户查询、订单查询、访问恢复、退款校验和人工工单进行白名单控制与审计，避免模型直接访问业务数据或承诺未接入的后端动作。

- 针对真实 DeepSeek 在线输出中的 bad case，补充 Gate 和回归测试，覆盖退款威胁误路由、发票越权承诺、工单编号不一致、访问恢复过度承诺、历史记忆污染当前任务等问题。

- 补充公开数据摄取流程，安全清洗 Hugging Face 公开客服数据集并登记 source URL、license 和 content hash；真实订单与用户数据仍使用模拟数据，确保项目不引入隐私风险。

## Claims To Avoid

- 不写“上线生产”“服务真实用户”“支持高并发”。
- 不写“完成 LoRA/SFT 微调”，当前只有 SFT 数据导出脚本和 vLLM 接入边界说明。
- 不写“准确率提升 X%”“成本降低 X%”，当前只有小型回归评测和指标口径。
- 不写“接入完整 MCP SDK”，当前是轻量 MCP-like Gateway，重点是工具白名单、结构化调用和审计。
- 不写“使用真实客服聊天记录”，项目只使用公开 Bitext 数据集做话术样例，业务用户与订单数据为模拟 fixture。

## Interview Proof

- Demo: `python -m agent_harness support --online --knowledge examples/support_augmented_kb.jsonl`
- Eval: `python -m agent_harness support-eval --output runs\eval\support_eval_after_data.json`
- Tests: `python -m pytest`
- Evidence files: `docs/online_validation_notes.md`, `docs/data_ingestion.md`, `runs/<session>/transcript.jsonl`, `runs/<session>/support_report.md`

