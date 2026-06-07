from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from agent_harness.business.support_schemas import SupportConfig
from agent_harness.control_plane.support_runner import SupportHarnessRunner
from agent_harness.llm import build_client, load_model_config


PRESET_CASES = {
    "课程打不开": [
        "我昨天买的 RAG 实战课今天打不开了。",
    ],
    "课程打不开但威胁退款": [
        "我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
    ],
    "查询发票": [
        "帮我看下 RAG 实战课的发票什么时候能开。",
    ],
    "账号安全问题": [
        "我的账号好像被别人改过信息，课程订单也不确定是不是我的。",
    ],
    "还是进不去": [
        "我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
        "刚才还是进不去，你们是不是把我的账号弄错了？",
    ],
}


def main() -> None:
    st.set_page_config(page_title="Course Support Agent Harness", layout="wide")
    st.title("课程售后客服 Agent Harness Demo")
    st.caption(
        "本页只做展示层：调用现有 Harness 主流程，展示 Router/Monitor/Resolver、RAG、MCP-like 工具、Risk Gate、Memory 和 Transcript。"
    )

    with st.sidebar:
        st.header("Run Config")
        preset_name = st.selectbox("Preset case", list(PRESET_CASES))
        offline = st.toggle("Offline mock mode", value=True)
        user_id = st.text_input("Synthetic user id", value="u_1001")
        knowledge_path = st.text_input("Knowledge JSONL", value="examples/support_augmented_kb.jsonl")
        customer_db_path = st.text_input("Synthetic customer DB", value="examples/support_customers.yaml")
        st.info("Online mode uses your local .env. No real user/order data is used.")

    default_messages = "\n".join(PRESET_CASES[preset_name])
    messages_text = st.text_area(
        "Customer messages, one turn per line",
        value=default_messages,
        height=150,
    )
    messages = [line.strip() for line in messages_text.splitlines() if line.strip()]

    if st.button("Run Harness", type="primary", disabled=not messages):
        run_demo(
            messages=messages,
            user_id=user_id,
            knowledge_path=Path(knowledge_path),
            customer_db_path=Path(customer_db_path),
            offline=offline,
        )


def run_demo(
    *,
    messages: list[str],
    user_id: str,
    knowledge_path: Path,
    customer_db_path: Path,
    offline: bool,
) -> None:
    config = SupportConfig(
        user_id=user_id,
        knowledge_path=knowledge_path,
        customer_db_path=customer_db_path,
        offline=offline,
    )
    client = build_client(load_model_config(), offline=offline)
    runner = SupportHarnessRunner(config, client)

    with st.spinner("Running Agent Harness..."):
        result = runner.run(messages)

    transcript_path = result.run_dir / "transcript.jsonl"
    memory_path = result.run_dir / "memory_snapshot.json"
    events = read_jsonl(transcript_path)
    memory = read_json(memory_path)
    evidence_by_turn = collect_evidence(runner, result.turns)

    st.success(f"Finished: {result.state.value}")
    st.write(f"Run dir: `{result.run_dir}`")

    if result.turns:
        st.subheader("Final Response")
        st.markdown(result.turns[-1].answer)

    overview_tab, rag_tab, tools_tab, gate_tab, memory_tab, transcript_tab = st.tabs(
        ["Decision Flow", "RAG Evidence", "Tool Calls", "Risk Gate", "Memory", "Transcript JSON"]
    )

    with overview_tab:
        render_decision_flow(result.turns)

    with rag_tab:
        render_rag_evidence(evidence_by_turn)

    with tools_tab:
        render_tool_calls(result.turns)

    with gate_tab:
        render_gate_events(events)

    with memory_tab:
        render_memory(memory)

    with transcript_tab:
        st.json(events, expanded=False)


def render_decision_flow(turns: list[Any]) -> None:
    for turn in turns:
        with st.container(border=True):
            st.markdown(f"**Turn {turn.turn_index}**")
            st.write(turn.user_message)
            cols = st.columns(4)
            cols[0].metric("Raw route", turn.route.intent.value)
            cols[1].metric("Confidence", f"{turn.route.confidence:.2f}")
            cols[2].metric("Final intent", turn.final_intent.value)
            cols[3].metric("Tools", str(len(turn.tool_results)))
            if turn.monitor_flags:
                st.write("Monitor flags")
                st.code("\n".join(turn.monitor_flags))
            st.write("Resolver answer")
            st.markdown(turn.answer)


def render_rag_evidence(evidence_by_turn: dict[int, list[dict[str, Any]]]) -> None:
    for turn_index, rows in evidence_by_turn.items():
        with st.expander(f"Turn {turn_index} evidence", expanded=True):
            for row in rows:
                metadata = row["metadata"]
                st.markdown(
                    f"**{metadata.get('policy_topic', 'unknown')}** | "
                    f"id=`{row['id']}` | score={row['score']:.4f}"
                )
                st.write(row["text"])


def render_tool_calls(turns: list[Any]) -> None:
    for turn in turns:
        with st.expander(f"Turn {turn.turn_index} tool calls", expanded=True):
            st.json(turn.tool_results, expanded=False)


def render_gate_events(events: list[dict[str, Any]]) -> None:
    gate_events = [event for event in events if event.get("actor") == "gate"]
    for event in gate_events:
        payload = event.get("payload", {})
        decision = payload.get("decision", {})
        with st.container(border=True):
            st.markdown(f"**{event.get('event_type')}**")
            cols = st.columns(3)
            cols[0].metric("Turn", str(payload.get("turn", "-")))
            cols[1].metric("Action", decision.get("action", "-"))
            cols[2].metric("Reason", decision.get("reason", "-"))
            st.write("Policy topics found")
            st.code(", ".join(payload.get("policy_topics_found", [])) or "none")
            if decision.get("audit"):
                st.json(decision["audit"], expanded=False)


def render_memory(memory: dict[str, Any]) -> None:
    for layer in ["working", "episodic", "semantic", "procedural"]:
        items = memory.get(layer, [])
        with st.expander(f"{layer} memory ({len(items)})", expanded=layer in {"working", "semantic"}):
            if not items:
                st.write("empty")
                continue
            for item in items[-8:]:
                st.markdown(f"- `{item.get('id')}` {item.get('content')}")


def collect_evidence(runner: SupportHarnessRunner, turns: list[Any]) -> dict[int, list[dict[str, Any]]]:
    evidence_by_turn: dict[int, list[dict[str, Any]]] = {}
    for turn in turns:
        evidence, _ = runner._retrieve_policy_evidence(turn.user_message, turn.final_intent)
        evidence_by_turn[turn.turn_index] = [
            {
                "id": item.id,
                "text": item.text,
                "metadata": item.metadata,
                "score": item.score,
            }
            for item in evidence
        ]
    return evidence_by_turn


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
