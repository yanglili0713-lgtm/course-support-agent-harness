from __future__ import annotations

import hashlib
from dataclasses import dataclass

from agent_harness.schemas import MemoryItem, PlanStep, RetrievedChunk


@dataclass(frozen=True)
class BuiltContext:
    text: str
    prefix_hash: str
    cache_hit: bool
    token_estimate: int


class PrefixCache:
    """Harness-level prefix cache bookkeeping.

    Real provider-side KV cache is not directly controlled here. We record the
    stable prefix hash so runs can reuse and audit prompt prefixes consistently.
    """

    def __init__(self) -> None:
        self._hashes: set[str] = set()

    def mark(self, prefix: str) -> tuple[str, bool]:
        digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
        hit = digest in self._hashes
        self._hashes.add(digest)
        return digest, hit


class ContextBuilder:
    def __init__(self) -> None:
        self.prefix_cache = PrefixCache()

    def build(
        self,
        *,
        agent_role: str,
        step: PlanStep,
        memories: list[MemoryItem],
        evidence: list[RetrievedChunk],
        task_input: str,
        output_schema: str,
    ) -> BuiltContext:
        """Build the seven-part context used by all sub-agents."""

        stable_prefix = "\n\n".join(
            [
                "# 1. System Policy\nHarness owns control flow. LLM only generates text. Follow the requested output schema.",
                f"# 2. Session Plan\nRound {step.round_index}: {step.topic} / {step.dimension} / {step.difficulty}. Goal: {step.learning_goal}",
                "# 3. Memory\n" + _format_memories(memories),
                "# 4. RAG Evidence\n" + _format_evidence(evidence),
            ]
        )
        prefix_hash, cache_hit = self.prefix_cache.mark(stable_prefix)
        volatile_suffix = "\n\n".join(
            [
                f"# 5. Agent Role\n{agent_role}",
                f"# 6. Task Input\n{task_input}",
                f"# 7. Output Schema\n{output_schema}",
            ]
        )
        text = f"{stable_prefix}\n\n{volatile_suffix}"
        return BuiltContext(
            text=compress_context(text),
            prefix_hash=prefix_hash,
            cache_hit=cache_hit,
            token_estimate=max(1, len(text) // 4),
        )


def compress_context(text: str, max_chars: int = 8_000) -> str:
    """Five-stage compression placeholder with deterministic behavior.

    Stages represented: trim whitespace, remove duplicate blank lines, keep
    global rules, keep latest task, and hard cap size. The implementation is
    conservative so the reference remains easy to audit.
    """

    normalized = "\n".join(line.rstrip() for line in text.splitlines())
    while "\n\n\n" in normalized:
        normalized = normalized.replace("\n\n\n", "\n\n")
    if len(normalized) <= max_chars:
        return normalized
    head = normalized[: max_chars // 2]
    tail = normalized[-max_chars // 2 :]
    return f"{head}\n\n# Compression Notice\nMiddle context compressed deterministically.\n\n{tail}"


def _format_memories(memories: list[MemoryItem]) -> str:
    if not memories:
        return "No prior memory."
    return "\n".join(f"- [{item.layer.value}] {item.content}" for item in memories[-8:])


def _format_evidence(evidence: list[RetrievedChunk]) -> str:
    if not evidence:
        return "No retrieved evidence."
    return "\n".join(
        f"- ({chunk.id}, score={chunk.score:.3f}, difficulty={chunk.metadata.get('difficulty')}) {chunk.text}"
        for chunk in evidence
    )

