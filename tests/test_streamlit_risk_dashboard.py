from pathlib import Path

from app.streamlit_risk_dashboard import load_metrics_summary, read_csv, read_jsonl, simulate_demo_case


def test_dashboard_helpers_handle_missing_files():
    assert read_jsonl(Path("runs/does_not_exist/transcripts.jsonl")) == []
    assert read_csv(Path("runs/does_not_exist/metrics_summary.csv")) == []
    summary, rows = load_metrics_summary(Path("runs/does_not_exist"))
    assert summary is None
    assert rows == []


def test_demo_simulation_returns_decision_fields():
    trace = simulate_demo_case(
        user_message="我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
        mode="agent_harness",
        turns=[
            "我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
        ],
    )

    assert {"gate_decision", "final_reply", "violations"}.issubset(trace)
    assert trace["gate_decision"] in {"allow", "block", "replan", "escalate", "halt"}
    assert isinstance(trace["violations"], list)
