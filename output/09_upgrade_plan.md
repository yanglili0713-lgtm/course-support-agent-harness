# Upgrade Plan

## Half-Day

- 增加 10 条客服 eval case，覆盖未验证身份、别人订单、退款超窗、access_reset 失败。
- 给 `support_eval.json` 增加 Markdown 报告导出，方便面试展示。

## 1-Day

- 增加真实 MCP stdio server 示例，保留当前 Gateway 作为 mock adapter。
- 给 RAG 增加 query/evidence 标注文件，计算 required topic recall 和 evidence precision。

## 3-Day

- 用导出的 SFT JSONL 做一次小模型 LoRA 训练实验，保存 config、loss、checkpoint、对比样例。
- 用 vLLM 起 OpenAI-compatible API，跑同一组 support eval，对比 mock/online 输出。

## 1-Week

- 加入 FastAPI 服务层和 SQLite/Postgres 持久化，把 transcript、memory、tool audit 做成可查询接口。
- 增加前端或 Streamlit AgentOps 面板，展示 route correction、policy gap、tool failure、PII gate 等指标趋势。

