from __future__ import annotations

import json
from pathlib import Path

from agent_harness.schemas import MemoryItem, MemoryLayer, dump_model


class MemoryStore:
    """Four-layer memory with explicit consolidation.

    Working memory is short-lived session context. Episodic memory records round
    events. Semantic memory stores stable facts learned from repeated evidence.
    Procedural memory stores reusable rules about how the agent should behave.
    """

    def __init__(self) -> None:
        self._items: dict[MemoryLayer, list[MemoryItem]] = {layer: [] for layer in MemoryLayer}

    def add(self, layer: MemoryLayer, content: str, **metadata: object) -> MemoryItem:
        item = MemoryItem(layer=layer, content=content, metadata=dict(metadata))
        self._items[layer].append(item)
        return item

    def list(self, layer: MemoryLayer | None = None) -> list[MemoryItem]:
        if layer:
            return list(self._items[layer])
        output: list[MemoryItem] = []
        for items in self._items.values():
            output.extend(items)
        return output

    def recent(self, layer: MemoryLayer, limit: int = 5) -> list[MemoryItem]:
        return self._items[layer][-limit:]

    def consolidate(self) -> list[MemoryItem]:
        """Promote repeated observations into stable memory layers.

        The rule is intentionally simple and auditable: after each round, the
        newest episodic score becomes semantic performance evidence, and a low
        score adds one procedural improvement rule.
        """

        promoted: list[MemoryItem] = []
        for event in self.recent(MemoryLayer.EPISODIC, limit=3):
            if event.metadata.get("kind") != "grading":
                continue
            score = int(event.metadata.get("score", 0))
            promoted.append(
                self.add(
                    MemoryLayer.SEMANTIC,
                    f"Candidate performance signal: {event.content}",
                    source_event=event.id,
                    score=score,
                )
            )
            if score < 75:
                promoted.append(
                    self.add(
                        MemoryLayer.PROCEDURAL,
                        "When grading identifies weak evidence, ask the next question to require metrics, failure mode, and tradeoff.",
                        source_event=event.id,
                    )
                )
        return promoted

    def compact_working_memory(self, *, keep_last: int = 4) -> list[MemoryItem]:
        """Compress old working memory into semantic summaries.

        This mirrors production long-dialog handling: recent turns stay verbatim
        for local coherence; older turns become compact facts so routing and
        safety checks do not forget the user's unresolved issue.
        """

        working = self._items[MemoryLayer.WORKING]
        if len(working) <= keep_last:
            return []
        old_items = working[:-keep_last]
        self._items[MemoryLayer.WORKING] = working[-keep_last:]
        summary = " | ".join(item.content for item in old_items)
        return [
            self.add(
                MemoryLayer.SEMANTIC,
                f"Compacted conversation memory: {summary}",
                kind="memory_compaction",
                source_count=len(old_items),
            )
        ]

    def save_snapshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {layer.value: [dump_model(item) for item in items] for layer, items in self._items.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
