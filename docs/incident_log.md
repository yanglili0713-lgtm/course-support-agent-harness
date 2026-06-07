# Incident Log

这个文件记录项目开发中实际暴露并修复的问题。简历和面试中只使用这里能被代码、测试或运行产物支撑的内容。

## INC-001 高置信错误路由：退款威胁掩盖访问故障

- **现象**：用户说“课程打不开，再不解决就退款”，Router 因退款关键词给出 `refund_request`，置信度 0.89。
- **失败代价**：如果直接进入退款流程，会绕过访问恢复，可能触发错误售后路径。
- **定位方式**：Transcript 中同时记录 `route_decision` 和 `route_and_retrieval_monitor`，可以看到 raw route 与 final intent 不一致。
- **修复**：Monitor 检查 `access_signal && refund_signal && high_confidence_refund`，命中后改为 `access_issue`。
- **证据**：`tests/test_support_scenario.py::test_support_monitor_corrects_high_confidence_refund_threat_route`。
- **运行标记**：`route_corrected:refund_threat_to_access_issue`。

## INC-002 RAG 政策召回不全：缺失身份校验证据

- **现象**：向量检索可能召回退款或访问政策，但遗漏身份校验政策。
- **失败代价**：Agent 可能在未验证身份时处理订单、退款、发票或访问恢复。
- **定位方式**：Skills playbook 声明每个 intent 的 required policy topics；Gate 检查 transcript 中的 `policy_topics_found`。
- **修复**：当 required topic 缺失时，Harness 执行 metadata backfill，按 `policy_topic` 精准补证据。
- **证据**：`agent_harness/control_plane/support_runner.py::_retrieve_policy_evidence` 与 support eval 的 `policy_coverage_rate`。

## INC-003 长对话记忆丢失：用户后续只说“还是不行”

- **现象**：多轮客服中，用户后续消息依赖前文；如果只保留最近一句，Router 不知道“还是不行”指课程访问失败。
- **失败代价**：错误升级或错误路由，用户需要重复说明问题。
- **修复**：Working Memory 保留最近 4 条原文，旧 working memory 压缩为 Semantic Memory。
- **证据**：`MemoryStore.compact_working_memory` 和 `test_working_memory_compaction_preserves_old_context_as_semantic_memory`。

## INC-004 历史记忆污染当前任务：发票轮被 access 记忆带偏

- **现象**：CLI smoke test 中，第三轮用户询问发票，但上下文里有前两轮 `access_issue`，mock 回复错误地继续说“刷新课程访问权限”。
- **失败代价**：Agent 没有响应当前明确任务，多轮客服体验变差。
- **修复**：Resolver prompt 中显式写入 `Intent: <intent>`，模型适配层优先匹配显式 Intent，而不是扫描整段历史关键词。
- **证据**：`test_explicit_intent_wins_over_old_memory_terms`。

## INC-005 真实 API 输出越权承诺：无发票工具却承诺开具

- **现象**：DeepSeek 在线演示中，第三轮发票咨询被正确路由为 `invoice_request`，但模型回复“我将为您开具 / 帮您办理”，而当前 Harness 只实现了订单查询工具，没有 `invoice_create` 工具。
- **失败代价**：客服 Agent 对未接入的后端能力做了承诺，真实业务中会导致用户预期错误和工单追责问题。
- **定位方式**：对比 `tool_results` 可以看到只调用了 `customer_lookup` 和 `order_lookup`，没有任何发票开具工具结果支撑该承诺。
- **修复**：在 Resolver prompt 中加入“不能承诺未由工具结果支撑的动作”；在 Gate 中加入 invoice promise pattern，命中“我将为您开具/帮您办理”等表述时触发 REPLAN，并写入 procedural repair memory。
- **证据**：`support_response_gate` / `support_response_repair_gate` transcript 事件，以及 `test_invoice_gate_replans_unsupported_invoice_promise`。

## INC-006 重复访问失败时承诺已建工单但未调用工单工具

- **现象**：DeepSeek 在线演示第二轮用户说“还是进不去”，模型回复“已创建人工复核工单”，但原 ACCESS_ISSUE playbook 只调用 `access_reset`，没有调用 `escalation_ticket`。
- **失败代价**：客服对用户承诺了一个并不存在的工单，真实业务中会造成追责和用户等待落空。
- **修复**：Resolver 在访问恢复场景中检测“还是/仍然/进不去/无法进入”等重复失败信号，除 `access_reset` 外同步调用 `escalation_ticket`。
- **证据**：`test_repeated_access_failure_creates_escalation_ticket`。
