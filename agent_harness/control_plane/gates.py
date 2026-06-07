from __future__ import annotations

import re

from agent_harness.schemas import GateAction, GateDecision


def gate_question(question: str, *, tool_audit: list[dict], round_index: int) -> GateDecision:
    """Verify that Examiner produced a usable question and legal tools passed."""

    failed_tools = [item for item in tool_audit if not item.get("success", False)]
    if failed_tools:
        return GateDecision(
            action=GateAction.HALT,
            reason="Examiner tool call failed or violated allow-list.",
            audit={"round": round_index, "failed_tools": failed_tools},
        )
    if len(question.strip()) < 20:
        return GateDecision(
            action=GateAction.REPLAN,
            reason="Question is too short to be useful.",
            audit={"round": round_index, "question": question},
        )
    if "?" not in question and "？" not in question:
        return GateDecision(
            action=GateAction.REPLAN,
            reason="Question does not look like a question.",
            audit={"round": round_index, "question": question},
        )
    return GateDecision(action=GateAction.PASS, reason="Question passed gate.", audit={"round": round_index})


def gate_grade(grade: str, *, tool_audit: list[dict], round_index: int) -> GateDecision:
    """Verify that Grader output contains a parseable score."""

    failed_tools = [item for item in tool_audit if not item.get("success", False)]
    if failed_tools:
        return GateDecision(
            action=GateAction.HALT,
            reason="Grader tool call failed or violated allow-list.",
            audit={"round": round_index, "failed_tools": failed_tools},
        )
    score = extract_score(grade)
    if score is None:
        return GateDecision(
            action=GateAction.REPLAN,
            reason="Grade output does not contain a score.",
            audit={"round": round_index, "grade": grade},
        )
    if not 0 <= score <= 100:
        return GateDecision(
            action=GateAction.HALT,
            reason="Grade score is outside 0-100.",
            audit={"round": round_index, "score": score},
        )
    return GateDecision(action=GateAction.PASS, reason="Grade passed gate.", audit={"round": round_index, "score": score})


def extract_score(text: str) -> int | None:
    match = re.search(r"score\s*:\s*(\d{1,3})", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{1,3})\s*/\s*100", text)
    return int(match.group(1)) if match else None

