# Evidence Contract

按 `llm-intern-skill` 的规则，强简历表述必须有证据。当前项目证据边界如下。

| Resume Claim | Level | Evidence | Status | Safer Wording | Interview Proof |
| --- | --- | --- | --- | --- | --- |
| 构建课程平台售后客服 Agent Harness 原型 | C1 | `agent_harness/control_plane/support_runner.py`, CLI `python -m agent_harness support` | 可以写 | 构建本地可运行客服 Agent Harness 原型 | 现场跑 CLI，展示 report |
| 设计 Router / Monitor / Resolver 多 Agent 链路 | C1 | `agent_harness/sub_agents/support_agents.py` | 可以写 | 设计并实现 Router/Monitor/Resolver 分工 | 展示类职责和 transcript |
| 用 RAG 做政策证据检索并修复召回不全 | C2 | `support_policy_kb.jsonl`, `_retrieve_policy_evidence`, eval metrics | 可以写 | 实现 policy-topic coverage 检查与 metadata backfill | 展示 `policy_coverage_rate` 和 backfill flag |
| 实现 MCP 工具白名单和订单/退款/访问工具链 | C1 | `mcp/support_gateway.py`, tool audit in transcript | 可以写 | 封装轻量 MCP Gateway，统一工具权限与审计 | 演示越权调用会失败 |
| 解决高置信错误路由问题 | C2 | `incident_log.md`, monitor flag, test | 可以写 | 基于 Monitor 纠正 refund threat 到 access issue 的错误路由 | 展示 raw route 与 final intent |
| 设计四层记忆并处理长对话 | C2 | `memory/store.py`, compaction test | 可以写 | 实现 working/episodic/semantic/procedural 与 working memory compaction | 展示 memory snapshot |
| 做了模型微调 | C0 | 只有 SFT 导出脚本，没有训练日志/checkpoint | 不能写成已完成微调 | 支持从 transcript 导出 SFT 数据，预留 vLLM 接入 | 展示 `scripts/export_support_sft.py` |
| 上线生产/支持真实用户 | C0 | 无部署、流量、用户日志 | 不能写 | 本地可运行原型 / 离线回归验证 | 不写上线 |
| 提升准确率/降低成本 X% | C0 | 无 baseline 对照和规模化样本 | 不能写具体百分比 | 构建指标口径并在小型评测集验证 | 展示 support eval JSON |

