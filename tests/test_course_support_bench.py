import json
from pathlib import Path


def test_course_support_bench_schema_and_coverage():
    path = Path("data/course_support_bench.jsonl")
    assert path.exists()

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 50
    memory_rows = [row for row in rows if row["case_id"].startswith("memory_")]
    assert len(memory_rows) >= 8

    intents = {row["expected_intent"] for row in rows}
    assert "access_issue" in intents
    assert "refund_request" in intents
    assert "invoice_request" in intents
    assert "account_security" in intents

    risk_tags = {tag for row in rows for tag in row.get("risk_tags", [])}
    assert "tool_required" in risk_tags
    assert "refund_commitment" in risk_tags
    assert "pii_safety" in risk_tags
    assert "memory_pollution" in risk_tags
    assert "context_carryover" in risk_tags
    assert "intent_switch" in risk_tags

    for row in rows:
        assert row["case_id"]
        assert row["user_message"]
        assert row["expected_intent"]
        assert isinstance(row.get("risk_tags", []), list)
        if "tool_required" in row.get("risk_tags", []):
            assert row.get("required_tools")
        if row.get("expected_gate_action") in {"block", "replan", "escalate"}:
            assert row.get("forbidden_claims") or row.get("required_tools") or row.get("required_policy_topics")
