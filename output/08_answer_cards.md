# Answer Cards

## Q1：你这个项目最大的挑战是什么？

**Why risky:** 容易泛泛说“调 prompt”，显得没做工程。

**Dangerous answer:** 我优化了 prompt，让模型更准确。

**Passable answer:** 最大挑战是高置信错误路由。用户说“课程打不开，再不解决就退款”，Router 看到退款关键词后高置信走 refund，但真实诉求是访问恢复。

**Strong answer:** 我没有直接相信模型置信度，而是在 Monitor 层做信号一致性检查：当 refund signal 和 access signal 同时出现，且 raw route 是高置信 refund，就把 final intent 修正为 access_issue，并记录 `route_corrected`。这个问题有回归测试和 transcript 证据，可以看到 raw route 和 final intent 的差异。

**Evidence needed:** `incident_log.md`, `test_support_monitor_corrects_high_confidence_refund_threat_route`。

## Q2：RAG 召回不全怎么处理？

**Dangerous answer:** 我调大 top_k 就解决了。

**Passable answer:** 我没有只调 top_k，而是给每类 intent 定义 required policy topics。

**Strong answer:** Skills playbook 会声明 refund/access/invoice 等流程需要哪些 policy topic。RAG 初召回后，Gate/Monitor 检查 evidence 是否覆盖这些 topic。如果缺 identity 或 access，就通过 metadata backfill 精准补证据，并把 `rag_backfill` 写入 transcript。这比盲目扩大 top_k 更可控。

## Q3：MCP 在项目里到底做了什么？

**Dangerous answer:** 我接入了完整 MCP 生态。

**Passable answer:** 我实现的是轻量 MCP-like 网关，不是完整 SDK。

**Strong answer:** 我做的是工具协议层的工程约束：每个工具有 ToolSpec、allowed_agents、结构化输入输出和审计结果。Resolver 可以调用订单和访问恢复，Router 不能直接调用工具，越权会失败。这个设计是为了演示 MCP 的核心价值：工具边界和可审计，而不是声称接入了生产 MCP server。

## Q4：为什么说你的记忆系统不是简单拼历史？

**Dangerous answer:** 我把历史对话都放进 prompt。

**Passable answer:** 我把记忆分成 working、episodic、semantic、procedural。

**Strong answer:** Working 只保留最近多轮原文，避免上下文爆炸；更早的 working 会压缩成 semantic summary，保留 unresolved issue 这类路由信号；episodic 记录每轮 route 和 resolution；procedural 存可复用规则。后面我还修过一次历史记忆污染当前任务的问题，让显式 Intent 优先于旧记忆关键词。

## Q5：你做了微调吗？

**Dangerous answer:** 做了 SFT，用 vLLM 部署了。

**Passable answer:** 目前没有完成真实微调。

**Strong answer:** 这个项目里我只做了 SFT 数据导出和 vLLM 接入边界设计。我不会把它写成“完成微调”。我的设计原则是：微调只学习客服回复风格，不学习路由、工具权限和 Gate 决策，这些仍然由 Harness 控制。

