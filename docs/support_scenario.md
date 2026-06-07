# 真实约束业务场景：课程平台售后客服 Agent

这个项目升级后的主场景是一个小型课程平台客服 Agent。它不追求覆盖所有客服功能，而是聚焦几个有失败代价的问题：

- 误判退款意图：用户说“课程打不开，再不解决就退款”，如果直接走退款，会绕过真正的访问恢复。
- RAG 召回不全：只召回退款政策，没有召回身份校验或访问恢复政策，会导致错误承诺。
- MCP 工具越权或缺失：退款、订单、访问恢复必须走工具白名单。
- 长对话记忆丢失：用户前面说过课程打不开，后面只说“还是不行”，路由必须还能记住 unresolved access issue。
- 高置信错误路由：Router 给出 0.89 的退款置信度，但 Monitor 通过信号冲突发现它错了。

## 端到端链路

1. Router Agent 根据用户消息和记忆给出 `RouteDecision`。
2. Skills 根据 intent 选 deterministic playbook，定义风险等级、必需工具、必需政策主题。
3. RAG 检索政策证据，并按 `policy_topic` 做 targeted backfill，修复初召回不全。
4. Monitor Agent 检查高置信错误路由、RAG policy gap、低置信升级。
5. Resolver Agent 只能通过 MCP Gateway 调用订单、退款、访问恢复、升级工单工具。
6. Gate 检查 PII 泄露、工具失败、必需政策主题缺失。
7. Transcript、memory snapshot、support report 全部落盘。

## 项目里“真修过”的问题

### 问题 1：高置信错误路由

早期 Router 看到“退款”就把意图判成 `refund_request`，置信度 0.89。真实用户话术是：“课程打不开，再不解决我就退款。”  
这个失败代价是：Agent 会跳过访问恢复，直接进入退款审核，用户问题没有解决，还可能触发错误售后流程。

修复方式：

- 保留 Router 的原始决策，不把问题藏起来。
- Monitor 检查 `access_signal && refund_signal && high_confidence_refund`。
- 命中后把 final intent 改成 `access_issue`，并记录 `route_corrected:refund_threat_to_access_issue`。
- Transcript 中同时保留原 route 和 final intent，面试时可以展示定位链路。

### 问题 2：RAG 初召回不全

仅靠向量相似度时，可能召回退款政策但漏掉身份校验政策。失败代价是：Agent 在没有验证身份的情况下谈订单、发票或退款。

修复方式：

- Skills playbook 声明每个 intent 必须具备哪些 `policy_topic`。
- Monitor/Gate 检查 evidence 是否覆盖 required topics。
- 缺失时 Harness 执行 metadata backfill，按 `policy_topic` 精准补证据。
- 事件里记录 `rag_backfill:<topic>`，方便复盘召回问题。

### 问题 3：长对话记忆丢失

多轮客服里，用户后续常说“还是不行”。如果只保留最近一句，路由会失去前文的访问失败背景。

修复方式：

- Working memory 保留最近 4 条原文。
- 更早消息通过 `compact_working_memory` 固化为 Semantic Memory。
- Router 读取最近 working + semantic memory 中的 unresolved signal。

### 问题 4：历史记忆污染当前任务

在一次真实 CLI smoke test 中，第三轮用户询问发票，但上下文里仍有前两轮的 `access_issue` 记忆。mock 生成器先匹配到了历史里的 access 关键词，导致发票轮回复成“已刷新课程访问权限”。

失败代价是：多轮客服中旧问题会污染当前明确意图，用户会觉得 Agent 没听懂新诉求。

修复方式：

- Resolver prompt 中显式写入 `Intent: <intent>`。
- 模型适配层和测试都改成优先匹配显式 Intent，而不是扫描整段上下文里的历史关键词。
- 新增回归测试 `test_explicit_intent_wins_over_old_memory_terms`，保证发票轮不会再被 access memory 带偏。

## 运行

```powershell
python -m agent_harness support
```

自定义多轮消息：

```powershell
python -m agent_harness support --message "我昨天买的 RAG 实战课打不开了，再不解决我就退款" --message "还是不行"
```

运行后查看：

- `runs/<support_session>/transcript.jsonl`
- `runs/<support_session>/memory_snapshot.json`
- `runs/<support_session>/support_report.md`
