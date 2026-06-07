# DeepSeek Setup

DeepSeek 官方 API 支持 OpenAI-compatible ChatCompletions。当前项目的客服 Agent 还需要 Embedding 做 RAG 检索，因此推荐配置为：

```env
AGENT_HARNESS_BASE_URL=https://api.deepseek.com
AGENT_HARNESS_API_KEY=你的DeepSeek_API_Key
AGENT_HARNESS_CHAT_MODEL=deepseek-v4-flash
AGENT_HARNESS_EMBEDDING_MODEL=local-hash
```

说明：

- `deepseek-v4-flash`：适合 demo 和成本更低的客服场景。
- `deepseek-v4-pro`：可以用于更复杂推理，但成本更高。
- `local-hash`：让项目使用本地确定性 embedding，不调用 DeepSeek embeddings endpoint。

运行：

```powershell
python -m agent_harness support --online
```

如果要接真实 embedding 服务，可以扩展 `agent_harness/llm.py`，把 chat provider 和 embedding provider 拆开。

