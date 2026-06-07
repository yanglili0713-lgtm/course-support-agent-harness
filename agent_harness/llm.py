from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from agent_harness.schemas import ModelConfig


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class LLMClient(Protocol):
    """Minimal model boundary.

    Everything outside this protocol is deterministic Harness code. This keeps
    model replacement cheap and makes tests possible without network access.
    """

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class MockLLMClient:
    """Deterministic offline model used by tests and first-run demos."""

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        prompt = "\n".join(message.content for message in messages)
        prompt_lower = prompt.lower()
        if "grader" in prompt_lower or "评分" in prompt:
            return (
                "score: 82\n"
                "strengths: 能说明核心概念，并能联系项目经历。\n"
                "risks: 需要补充失败场景、指标和工程取舍。\n"
                "next_step: 用 STAR 结构补充约束、方案、验证结果。"
            )
        if "examiner" in prompt_lower or "出题" in prompt:
            digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:6]
            return (
                f"请结合你的简历项目，说明 RAG 检索链路如何从 embedding、metadata filter、"
                f"去重到难度重排保证题目质量？请给出一个失败案例和修复方案。#{digest}"
            )
        if "support resolver agent" in prompt_lower:
            if "intent: invoice_request" in prompt_lower:
                return "我已核验账号和订单状态。当前发票状态可查询；如未申请，请登录平台订单详情页提交发票申请信息。"
            if "intent: access_issue" in prompt_lower:
                return (
                    "已为你核验当前账号的付费订单，并刷新访问令牌。请退出账号后重新登录，"
                    "等待 10 分钟再尝试打开课程；如果仍无法观看，会按工具结果升级人工处理。"
                )
            if "intent: refund_request" in prompt_lower:
                return (
                    "我已根据订单状态和退款规则完成初步核验。当前是否可退款需要以系统校验结果为准，"
                    "不会在未通过身份和政策检查前直接承诺退款。"
                )
            if "intent: account_security" in prompt_lower:
                return "为保护账号安全，我不会直接修改敏感信息，已创建安全工单并建议你先重置登录密码。"
            return "已记录你的问题并创建人工复核工单，后续会由客服继续处理。"
        return "offline mock response"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [stable_embedding(text) for text in texts]


class OpenAICompatibleClient:
    """Small OpenAI-compatible adapter.

    The adapter intentionally avoids OpenAI-specific SDK types. Any service with
    /chat/completions and /embeddings can be used by changing environment vars.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        if not config.api_key:
            raise ValueError("AGENT_HARNESS_API_KEY is required unless --offline is used.")

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        payload = {
            "model": self.config.chat_model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
        }
        data = _post_json(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            payload=payload,
            api_key=self.config.api_key,
            timeout=self.config.timeout_seconds,
        )
        return data["choices"][0]["message"]["content"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        # DeepSeek's official API is OpenAI-compatible for chat, but this
        # project also needs embeddings for the local RAG vector store. When the
        # embedding model is set to local-hash, we keep chat online while using
        # deterministic local embeddings for retrieval. This is a deliberate
        # engineering fallback, not a fake DeepSeek embedding call.
        if self.config.embedding_model in {"local-hash", "local_hash", "hash"}:
            return [stable_embedding(text) for text in texts]
        data = _post_json(
            f"{self.config.base_url.rstrip('/')}/embeddings",
            payload={"model": self.config.embedding_model, "input": texts},
            api_key=self.config.api_key,
            timeout=self.config.timeout_seconds,
        )
        return [item["embedding"] for item in data["data"]]


def stable_embedding(text: str, dims: int = 64) -> list[float]:
    """Hashing embedding for deterministic local vector search.

    It is not semantically rich, but it keeps retrieval behavior stable in tests
    and mirrors the production interface closely enough to swap real embeddings.
    """

    vector = [0.0 for _ in range(dims)]
    for token in text.lower().replace("/", " ").replace("-", " ").split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dims
        sign = 1 if digest[2] % 2 == 0 else -1
        vector[index] += sign
    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def load_model_config() -> ModelConfig:
    _load_dotenv()
    return ModelConfig(
        base_url=os.getenv("AGENT_HARNESS_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("AGENT_HARNESS_API_KEY"),
        chat_model=os.getenv("AGENT_HARNESS_CHAT_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("AGENT_HARNESS_EMBEDDING_MODEL", "text-embedding-3-small"),
    )


def build_client(config: ModelConfig, *, offline: bool) -> LLMClient:
    if offline:
        return MockLLMClient()
    return OpenAICompatibleClient(config)


def _post_json(url: str, *, payload: dict, api_key: str, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
