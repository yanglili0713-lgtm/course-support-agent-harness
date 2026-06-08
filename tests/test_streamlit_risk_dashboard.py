from pathlib import Path

from app.streamlit_risk_dashboard import (
    load_failure_reason_summary,
    load_metrics_summary,
    load_risk_tag_summary,
    read_csv,
    read_jsonl,
    simulate_demo_case,
)


def test_dashboard_helpers_handle_missing_files():
    assert read_jsonl(Path("runs/does_not_exist/transcripts.jsonl")) == []
    assert read_csv(Path("runs/does_not_exist/metrics_summary.csv")) == []
    summary, rows = load_metrics_summary(Path("runs/does_not_exist"))
    assert summary is None
    assert rows == []
    assert load_risk_tag_summary(Path("runs/does_not_exist")) == []
    assert load_failure_reason_summary(Path("runs/does_not_exist")) == []


def test_dashboard_summary_helpers_read_csv_outputs(tmp_path):
    (tmp_path / "risk_tag_summary.csv").write_text(
        "risk_tag,mode,case_count,pass_rate\npii_safety,agent_harness,3,1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "failure_reason_summary.csv").write_text(
        "mode,failure_reason,count,rate\nllm_only,pii_leakage,2,0.5\n",
        encoding="utf-8",
    )

    assert load_risk_tag_summary(tmp_path)[0]["risk_tag"] == "pii_safety"
    assert load_failure_reason_summary(tmp_path)[0]["failure_reason"] == "pii_leakage"


def test_demo_simulation_returns_decision_fields():
    trace = simulate_demo_case(
        user_message="I cannot access the course today, and if you do not fix it I will ask for a refund.",
        mode="agent_harness",
        turns=[
            "I cannot access the course today, and if you do not fix it I will ask for a refund.",
        ],
    )

    assert {"gate_decision", "final_reply", "violations"}.issubset(trace)
    assert trace["gate_decision"] in {"allow", "block", "replan", "escalate", "halt"}
    assert isinstance(trace["violations"], list)
