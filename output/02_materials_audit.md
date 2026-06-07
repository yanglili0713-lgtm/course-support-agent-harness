# Materials Audit

## Materials Summary

当前材料来自本地项目 `D:\study\work`，核心是课程平台售后客服 Agent Harness 原型。项目包含可运行 CLI、业务知识库、mock MCP 工具、RAG 检索、Skills playbook、多层记忆、端到端测试、评测脚本和事故复盘文档。

## Strong Evidence

- 可运行入口：`python -m agent_harness support`。
- 端到端测试：`python -m pytest`，当前 12 个测试通过。
- 业务 Runner：`agent_harness/control_plane/support_runner.py`。
- 多 Agent：`agent_harness/sub_agents/support_agents.py`。
- MCP 工具链：`agent_harness/mcp/support_gateway.py`。
- RAG 知识库：`examples/support_policy_kb.jsonl`。
- Skills playbook：`agent_harness/skills/support_playbooks.py`。
- 事故复盘：`docs/incident_log.md`。
- 证据合同：`docs/evidence_contract.md`。

## Medium Evidence

- SFT 数据导出：`scripts/export_support_sft.py`，能导出 chat-style JSONL，但没有实际训练日志和模型 checkpoint。
- vLLM 接入说明：`docs/model_ops.md`，有接口边界设计，但没有实际服务压测或部署记录。

## Weak / Missing Evidence

- 无真实线上用户、流量、客服业务接入记录。
- 无大规模评测集，当前是小型业务回归集。
- 无真实模型微调训练日志、loss 曲线、checkpoint、推理对比。
- 无明确性能指标，如 QPS、延迟、成本下降比例。

## Ownership Risks

- 可以写“独立实现本地原型 / 负责核心模块设计与实现”。
- 不建议写“上线生产”“服务真实业务”“提升 X%”“完成模型微调部署”。

## Best Resume Sources

- `docs/incident_log.md` 中四个问题最适合回答“你遇到过什么挑战”。
- `docs/evidence_contract.md` 决定简历措辞边界。
- `runs/<support_session>/transcript.jsonl` 可证明链路可复盘。

