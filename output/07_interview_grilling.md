# Interview Grilling

## Round 1: Truth Boundary

1. 你这个项目是否上线？有没有真实用户和流量？
   - 重要性：防止把本地原型说成生产系统。
   - 证据：只能回答本地可运行原型和离线回归验证。

2. 你是否真的用了标准 MCP SDK？
   - 重要性：轻量 MCP-like gateway 和真实 MCP server 不同。
   - 证据：`mcp/support_gateway.py`，安全说法是“轻量 MCP 网关/工具白名单”。

3. 你是否真的微调了模型？
   - 重要性：SFT 导出不等于训练完成。
   - 证据：目前只有 `scripts/export_support_sft.py`，不能写“完成微调”。

## Round 2: Technical Depth

1. Router 为什么会错？你怎么发现它错？
   - 看点：raw route、final intent、Monitor flags、transcript。

2. RAG 召回不全怎么定位？
   - 看点：required policy topics、policy coverage、metadata backfill。

3. 工具调用怎么避免越权？
   - 看点：ToolSpec allowed_agents、Gateway call、Gate tool failure。

4. 多轮记忆怎么压缩？压缩后怎么避免丢关键任务？
   - 看点：Working 保留最近原文，Semantic 保存旧摘要。

5. 历史记忆污染当前任务怎么解决？
   - 看点：显式 Intent 优先，测试覆盖发票轮不被 access 记忆带偏。

## Round 3: Scenario Questions

1. 如果用户未验证身份但要求退款，你的 Agent 怎么处理？
2. 如果 RAG 没召回 identity policy，但召回了 refund policy，会发生什么？
3. 如果 access_reset 工具失败，模型会不会继续说“已恢复”？
4. 如果用户让客服查看别人订单，工具层如何隔离用户？
5. 如果 Monitor 修正错了，怎么复盘和回滚规则？

## Round 4: Risk Summary

- 能回答：Harness 分层、Monitor 修路由、MCP 白名单、RAG coverage、记忆压缩。
- 需谨慎：MCP 标准生态、SFT、vLLM、指标提升。
- 不能写：上线生产、真实用户规模、准确率提升百分比、完成模型微调。

