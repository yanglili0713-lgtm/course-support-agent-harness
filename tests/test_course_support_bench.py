import json
from pathlib import Path


def test_course_support_bench_schema_and_coverage():
    path = Path("data/course_support_bench.jsonl")
    assert path.exists()

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 100
    assert len({row["case_id"] for row in rows}) == len(rows)

    memory_rows = [row for row in rows if row["case_id"].startswith("memory_")]
    assert len(memory_rows) >= 10

    intents = {row["expected_intent"] for row in rows}
    assert "access_issue" in intents
    assert "refund_request" in intents
    assert "invoice_request" in intents
    assert "account_security" in intents
    assert "human_escalation" in intents

    risk_tags = {tag for row in rows for tag in row.get("risk_tags", [])}
    expected_tags = {
        "access_issue",
        "refund_threat",
        "refund_commitment",
        "invoice",
        "unsupported_business_action",
        "account_security",
        "escalation",
        "ticket_grounding",
        "pii_safety",
        "raw_id_leak",
        "no_tool_grounding",
        "tool_required",
        "memory_pollution",
        "context_carryover",
        "intent_switch",
        "tool_failure",
        "policy_conflict",
        "order_not_found",
        "unsafe_commitment_under_failure",
    }
    assert expected_tags.issubset(risk_tags)

    for row in rows:
        assert row["case_id"]
        assert row["user_message"]
        assert row["turns"]
        assert row["expected_intent"]
        assert row["expected_gate_action"] in {"allow", "block", "replan", "escalate", "halt"}
        assert isinstance(row.get("risk_tags", []), list)
        if "tool_required" in row.get("risk_tags", []):
            assert row.get("required_tools")
        if row.get("expected_gate_action") in {"block", "replan", "escalate"}:
            assert row.get("forbidden_claims") or row.get("required_tools") or row.get("required_policy_topics")
