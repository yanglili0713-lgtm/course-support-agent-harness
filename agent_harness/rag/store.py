from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from agent_harness.llm import LLMClient
from agent_harness.schemas import RetrievalQuery, RetrievedChunk


class VectorStore:
    """Small JSONL vector store backed by local cosine similarity.

    The project avoids heavy native dependencies in v1. The important Harness
    behavior is the retrieval pipeline: embed -> vector search -> metadata
    filter -> dedupe -> difficulty rerank.
    """

    def __init__(self, chunks: list[dict], embeddings: list[list[float]]):
        self.chunks = chunks
        self.embeddings = embeddings

    @classmethod
    def from_jsonl(cls, path: Path, client: LLMClient) -> "VectorStore":
        chunks = list(_read_jsonl(path))
        texts = [chunk["text"] for chunk in chunks]
        embeddings = client.embed(texts)
        return cls(chunks=chunks, embeddings=embeddings)

    def search(self, query: RetrievalQuery, client: LLMClient) -> list[RetrievedChunk]:
        query_vector = client.embed([query.text])[0]
        if not self.embeddings:
            return []

        scores = [_cosine_score(vector, query_vector) for vector in self.embeddings]
        candidates: list[RetrievedChunk] = []
        ranked_indexes = sorted(range(len(scores)), key=lambda item: scores[item], reverse=True)
        for index in ranked_indexes:
            chunk = self.chunks[index]
            metadata = dict(chunk.get("metadata", {}))
            if query.topic and metadata.get("topic") != query.topic:
                continue
            if query.difficulty and metadata.get("difficulty") not in {query.difficulty, "any"}:
                continue
            candidates.append(
                RetrievedChunk(
                    id=str(chunk["id"]),
                    text=str(chunk["text"]),
                    metadata=metadata,
                    score=float(scores[index]),
                )
            )

        deduped = _dedupe(candidates)
        reranked = sorted(
            deduped,
            key=lambda item: (_difficulty_bonus(item, query.difficulty), item.score),
            reverse=True,
        )
        return reranked[: query.top_k]


def _read_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _cosine_score(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _dedupe(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    output: list[RetrievedChunk] = []
    for chunk in chunks:
        key = chunk.text.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(chunk)
    return output


def _difficulty_bonus(chunk: RetrievedChunk, difficulty: str | None) -> int:
    if not difficulty:
        return 0
    return 1 if chunk.metadata.get("difficulty") == difficulty else 0
