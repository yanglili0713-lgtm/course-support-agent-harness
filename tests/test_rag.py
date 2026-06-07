import json

from agent_harness.llm import MockLLMClient
from agent_harness.rag import VectorStore
from agent_harness.schemas import RetrievalQuery


def test_rag_filters_dedupes_and_prefers_matching_difficulty(tmp_path):
    path = tmp_path / "kb.jsonl"
    rows = [
        {"id": "a", "text": "rag metadata filter vector search", "metadata": {"topic": "rag", "difficulty": "mid"}},
        {"id": "b", "text": "rag metadata filter vector search", "metadata": {"topic": "rag", "difficulty": "mid"}},
        {"id": "c", "text": "rag hard reranker", "metadata": {"topic": "rag", "difficulty": "hard"}},
        {"id": "d", "text": "agent memory", "metadata": {"topic": "agent", "difficulty": "mid"}},
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    client = MockLLMClient()
    store = VectorStore.from_jsonl(path, client)

    results = store.search(RetrievalQuery(text="rag filter", topic="rag", difficulty="mid", top_k=5), client)

    assert len({item.text for item in results}) == len(results)
    assert all(item.metadata["topic"] == "rag" for item in results)
    assert results[0].metadata["difficulty"] == "mid"
