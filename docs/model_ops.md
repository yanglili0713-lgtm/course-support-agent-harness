# Model Ops：SFT 与 vLLM 接入边界

这个项目的核心不是让模型学会控制流程，而是让 Harness 控制流程，模型只学习“在给定证据和工具结果后如何生成更稳定的客服回复”。

## SFT 数据怎么来

运行一次客服场景后：

```powershell
python -m agent_harness support
python scripts/export_support_sft.py --run-dir runs/<support_session> --output datasets/support_sft.jsonl
```

导出的格式是 chat JSONL，可直接改成 LLaMA-Factory 常用格式。训练目标只包含最终客服回复，不包含路由、工具权限、Gate 决策。

## 为什么不微调路由和权限

路由、工具权限、RAG policy coverage、PII gate 都属于工程控制面。如果把这些交给微调模型，模型置信度高但错误时很难追责。项目里保留了一个真实例子：Router 高置信判成退款，Monitor 根据 access/refund 信号冲突纠正。

## vLLM 部署

训练后可用 vLLM 提供 OpenAI 兼容接口：

```powershell
python -m vllm.entrypoints.openai.api_server --model <your_model_path> --served-model-name support-sft
```

然后配置：

```text
AGENT_HARNESS_BASE_URL=http://localhost:8000/v1
AGENT_HARNESS_API_KEY=EMPTY
AGENT_HARNESS_CHAT_MODEL=support-sft
```

再运行：

```powershell
python -m agent_harness support --online
```

项目没有假设高并发能力。更合理的简历表述是：完成了 OpenAI-compatible serving 边界设计，支持将 SFT 后的模型通过 vLLM 接入 Harness。

