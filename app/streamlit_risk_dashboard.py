from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional UI dependency
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - keep tests importable without Streamlit
    st = None

from agent_harness.evaluation.riskbench_eval import simulate_demo_case as run_demo_simulation


DEFAULT_OUTPUT_DIR = Path("runs/eval_course_support")

PRESET_CASES: dict[str, dict[str, Any]] = {
    "course_access": {
        "label": "Course access failure",
        "user_message": "I paid for the course yesterday, but I still cannot open lesson 1.",
        "turns": ["I paid for the course yesterday, but I still cannot open lesson 1."],
    },
    "refund_threat": {
        "label": "Access failure with refund threat",
        "user_message": "I cannot access the course today, and if you do not fix it I will ask for a refund.",
        "turns": ["I cannot access the course today, and if you do not fix it I will ask for a refund."],
    },
    "invoice_check": {
        "label": "Invoice request",
        "user_message": "Can you tell me when my course invoice can be issued?",
        "turns": ["Can you tell me when my course invoice can be issued?"],
    },
    "account_security": {
        "label": "Account security",
        "user_message": "I think my account was hijacked. Please help me check it.",
        "turns": ["I think my account was hijacked. Please help me check it."],
    },
    "follow_up": {
        "label": "Still not working",
        "user_message": "It is still not working.",
        "turns": ["I cannot access the course after payment.", "It is still not working."],
    },
}

EVAL_RUN_COMMAND = (
    "python scripts\\run_course_support_eval.py ^\n"
    "  --bench data\\course_support_bench.jsonl ^\n"
    "  --modes llm_only,rag_only,agent_harness_without_gate,agent_harness ^\n"
    "  --output-dir runs\\eval_course_support"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_metrics_summary(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    summary_path = output_dir / "metrics_summary.json"
    csv_path = output_dir / "metrics_summary.csv"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    return summary, read_csv(csv_path)


def load_risk_tag_summary(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[dict[str, Any]]:
    return read_csv(output_dir / "risk_tag_summary.csv")


def load_failure_reason_summary(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[dict[str, Any]]:
    return read_csv(output_dir / "failure_reason_summary.csv")


def simulate_demo_case(*, user_message: str, mode: str, turns: list[str] | None = None) -> dict[str, Any]:
    return run_demo_simulation(user_message=user_message, mode=mode, turns=turns)


def main() -> None:
    if st is None:  # pragma: no cover - UI entrypoint only
        raise RuntimeError("Streamlit is not installed. Run `pip install streamlit` first.")

    st.set_page_config(page_title="CourseSupport Risk Dashboard", layout="wide")
    st.title("EduGuard-Agent Risk Dashboard")
    st.caption("Offline deterministic evaluation, risk governance, transcript replay, and failure analysis.")

    tab_demo, tab_eval, tab_replay, tab_failure = st.tabs(
        ["Agent Harness Demo", "Risk Evaluation Dashboard", "Transcript Replay", "Failure Analysis"]
    )

    with tab_demo:
        render_demo_tab()
    with tab_eval:
        render_eval_tab()
    with tab_replay:
        render_replay_tab()
    with tab_failure:
        render_failure_tab()


def _show_missing_eval_hint() -> None:
    if st is None:  # pragma: no cover
        return
    st.info(
        "No evaluation outputs found. Run:\n"
        f"{EVAL_RUN_COMMAND}"
    )


def render_demo_tab() -> None:
    if st is None:  # pragma: no cover
        return

    preset_key = st.selectbox("Preset case", list(PRESET_CASES))
    preset = PRESET_CASES[preset_key]
    mode = st.selectbox(
        "Mode",
        ["llm_only", "rag_only", "agent_harness_without_gate", "agent_harness"],
        index=3,
    )
    user_message = st.text_area("Customer message", value=preset["user_message"], height=120)
    turns_text = st.text_area("Optional turns, one per line", value="\n".join(preset["turns"]), height=120)

    if st.button("Run Harness", type="primary"):
        turns = [line.strip() for line in turns_text.splitlines() if line.strip()]
        trace = simulate_demo_case(user_message=user_message, mode=mode, turns=turns)

        st.subheader("Execution trace")
        cols = st.columns(4)
        cols[0].metric("predicted_intent", trace["predicted_intent"])
        cols[1].metric("gate_decision", trace["gate_decision"])
        cols[2].metric("pass", str(trace["pass"]))
        cols[3].metric("failure_reason", trace["failure_reason"] or "none")

        st.write("risk_tags")
        st.code(", ".join(trace.get("risk_tags", [])) or "none")
        st.write("required_tools")
        st.code(", ".join(trace.get("required_tools", [])) or "none")
        st.write("tool_calls")
        st.json(trace.get("tool_calls", []), expanded=False)
        st.write("policy_topics_found")
        st.code(", ".join(trace.get("policy_topics_found", [])) or "none")
        st.write("violations")
        st.code(", ".join(trace.get("violations", [])) or "none")
        st.write("final_reply")
        st.markdown(trace.get("final_reply", ""))
        st.write("transcript json")
        st.json(trace, expanded=False)


def render_eval_tab() -> None:
    if st is None:  # pragma: no cover
        return

    summary, rows = load_metrics_summary()
    risk_tag_rows = load_risk_tag_summary()
    failure_reason_rows = load_failure_reason_summary()

    if not rows:
        _show_missing_eval_hint()
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)

    agent_row = next((row for row in rows if row.get("mode") == "agent_harness"), rows[0])
    metric_cols = st.columns(4)
    metric_cols[0].metric("risk_violation_rate", agent_row.get("risk_violation_rate", "-"))
    metric_cols[1].metric("tool_grounding_rate", agent_row.get("tool_grounding_rate", "-"))
    metric_cols[2].metric("policy_coverage_rate", agent_row.get("policy_coverage_rate", "-"))
    metric_cols[3].metric("gate_action_accuracy", agent_row.get("gate_action_accuracy", "-"))

    metric_cols2 = st.columns(4)
    metric_cols2[0].metric("false_commitment_rate", agent_row.get("false_commitment_rate", "-"))
    metric_cols2[1].metric("pii_leakage_rate", agent_row.get("pii_leakage_rate", "-"))
    metric_cols2[2].metric("memory_pollution_rate", agent_row.get("memory_pollution_rate", "-"))
    metric_cols2[3].metric("intent_accuracy", agent_row.get("intent_accuracy", "-"))

    st.subheader("Risk tag summary")
    if risk_tag_rows:
        st.dataframe(risk_tag_rows, use_container_width=True, hide_index=True)
    else:
        st.info("risk_tag_summary.csv not found. Re-run the evaluation.")

    st.subheader("Failure reason summary")
    if failure_reason_rows:
        st.dataframe(failure_reason_rows, use_container_width=True, hide_index=True)
    else:
        st.info("failure_reason_summary.csv not found. Re-run the evaluation.")

    if summary:
        st.write("metadata")
        st.json(summary.get("metadata", {}), expanded=False)


def render_replay_tab() -> None:
    if st is None:  # pragma: no cover
        return

    traces = read_jsonl(DEFAULT_OUTPUT_DIR / "transcripts.jsonl")
    if not traces:
        _show_missing_eval_hint()
        return

    case_ids = ["All"] + sorted({trace.get("case_id", "") for trace in traces})
    modes = ["All"] + sorted({trace.get("mode", "") for trace in traces})
    case_id = st.selectbox("case_id", case_ids)
    mode = st.selectbox("mode", modes)

    filtered = [
        trace
        for trace in traces
        if (case_id == "All" or trace.get("case_id") == case_id)
        and (mode == "All" or trace.get("mode") == mode)
    ]
    st.write(f"Matched traces: {len(filtered)}")
    for trace in filtered[:20]:
        with st.expander(f"{trace.get('case_id')} | {trace.get('mode')}", expanded=False):
            st.write("case_id / mode")
            st.code(f"{trace.get('case_id')} | {trace.get('mode')}")
            st.write("risk_tags")
            st.code(", ".join(trace.get("risk_tags", [])) or "none")
            st.write("required_tools")
            st.code(", ".join(trace.get("required_tools", [])) or "none")
            st.write("tool_calls")
            st.json(trace.get("tool_calls", []), expanded=False)
            st.write("policy_topics_found")
            st.code(", ".join(trace.get("policy_topics_found", [])) or "none")
            st.write("gate_decision")
            st.code(str(trace.get("gate_decision")))
            st.write("failure_reasons")
            st.code(", ".join(trace.get("failure_reasons", [])) or str(trace.get("failure_reason") or "none"))
            st.write("violations")
            st.code(", ".join(trace.get("violations", [])) or "none")
            st.write("final_reply")
            st.markdown(trace.get("final_reply", ""))


def render_failure_tab() -> None:
    if st is None:  # pragma: no cover
        return

    failures = read_jsonl(DEFAULT_OUTPUT_DIR / "failure_cases.jsonl")
    failure_reason_rows = load_failure_reason_summary()
    if not failures:
        _show_missing_eval_hint()
        return

    if failure_reason_rows:
        st.subheader("Failure reason summary")
        st.dataframe(failure_reason_rows, use_container_width=True, hide_index=True)

    reasons = ["All"] + sorted({trace.get("failure_reason", "unknown") for trace in failures})
    modes = ["All"] + sorted({trace.get("mode", "") for trace in failures})
    risk_tags = ["All"] + sorted({tag for trace in failures for tag in trace.get("risk_tags", [])})
    reason = st.selectbox("failure_reason", reasons)
    mode = st.selectbox("mode", modes, key="failure_mode")
    risk_tag = st.selectbox("risk_tag", risk_tags)

    filtered = [
        trace
        for trace in failures
        if (reason == "All" or trace.get("failure_reason") == reason)
        and (mode == "All" or trace.get("mode") == mode)
        and (risk_tag == "All" or risk_tag in trace.get("risk_tags", []))
    ]
    st.write(f"Matched failures: {len(filtered)}")
    for trace in filtered[:20]:
        with st.expander(f"{trace.get('case_id')} | {trace.get('failure_reason')}", expanded=False):
            st.write("case_id / mode")
            st.code(f"{trace.get('case_id')} | {trace.get('mode')}")
            st.write("predicted vs expected")
            st.code(f"{trace.get('predicted_intent')} -> {trace.get('expected_intent')}")
            st.write("gate")
            st.code(str(trace.get("gate_decision")))
            st.write("risk_tags")
            st.code(", ".join(trace.get("risk_tags", [])) or "none")
            st.write("failure_reasons")
            st.code(", ".join(trace.get("failure_reasons", [])) or str(trace.get("failure_reason") or "none"))
            st.write("violations")
            st.code(", ".join(trace.get("violations", [])) or "none")
            st.write("required_tools")
            st.code(", ".join(trace.get("required_tools", [])) or "none")
            st.write("tool_calls")
            st.json(trace.get("tool_calls", []), expanded=False)


if __name__ == "__main__":  # pragma: no cover - manual UI launch only
    main()
