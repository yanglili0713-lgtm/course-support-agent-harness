from __future__ import annotations

import json
from pathlib import Path

from agent_harness.schemas import HarnessState, TranscriptEvent, dump_model


class TranscriptWriter:
    """Append-only JSONL transcript for replay and debugging."""

    def __init__(self, session_id: str, run_dir: Path):
        self.session_id = session_id
        self.run_dir = run_dir
        self.path = run_dir / "transcript.jsonl"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def log(self, *, state: HarnessState, actor: str, event_type: str, payload: dict) -> TranscriptEvent:
        event = TranscriptEvent(
            session_id=self.session_id,
            state=state,
            actor=actor,
            event_type=event_type,
            payload=payload,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dump_model(event), ensure_ascii=False) + "\n")
        return event

