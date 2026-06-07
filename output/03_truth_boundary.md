# Truth Boundary

| Claim | Status | Evidence | Risk | Safe Wording |
| --- | --- | --- | --- | --- |
| 做了客服 Agent Harness 项目 | 可以写 | CLI、代码、测试、报告 | 低 | 构建本地可运行的课程平台售后客服 Agent Harness 原型 |
| 多 Agent 路由与监控 | 可以写 | Router/Monitor/Resolver 代码与测试 | 中 | 设计 Router/Monitor/Resolver 分工，解决高置信错误路由 |
| RAG 检索优化 | 谨慎写 | policy topic backfill 和 eval metrics | 中 | 针对政策召回不全实现 coverage 检查与 metadata backfill |
| MCP 标准生态 | 谨慎写 | 轻量 MCP-like gateway，不是真实 MCP SDK | 中 | 实现轻量 MCP 网关，模拟工具白名单、审计和隔离 |
| 多层记忆系统 | 可以写 | MemoryStore 与 compaction test | 中 | 实现四层记忆与 working memory 压缩 |
| 做了 SFT 微调 | 不能写 | 只有导出脚本 | 高 | 支持从 transcript 导出 SFT 数据，预留 vLLM 接入 |
| 上线生产 | 不能写 | 无上线证据 | 高 | 本地可运行原型，完成离线回归验证 |
| 提升准确率 X% | 不能写 | 无大规模 baseline | 高 | 构建小型业务回归评测与指标口径 |

