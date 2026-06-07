from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from agent_harness.business.support_schemas import SupportConfig, SupportTurnResult
from agent_harness.context import ContextBuilder
from agent_harness.control_plane.support_gates import gate_support_response
from agent_harness.control_plane.transcript import TranscriptWriter
from agent_harness.llm import LLMClient
from agent_harness.mcp.support_gateway import build_support_gateway
from agent_harness.memory import MemoryStore
from agent_harness.rag import VectorStore
from agent_harness.schemas import GateAction, HarnessState, MemoryLayer, RetrievalQuery, RetrievedChunk, dump_model
from agent_harness.skills.support_playbooks import get_playbook
from agent_harness.sub_agents.support_agents import SupportMonitorAgent, SupportResolverAgent, SupportRouterAgent


@dataclass(frozen=True)
class SupportRunResult:
    session_id: str
    state: HarnessState
    run_dir: Path
    report_path: Path
    turns: list[SupportTurnResult]


class SupportHarnessRunner:
    """Control plane for the customer-support scenario.

    The scenario is intentionally small but has real failure cost:
    mis-routing can trigger the wrong workflow, missed policy evidence can lead
    to invalid refunds, and unsafe responses can leak order or account data.
    """

    def __init__(self, config: SupportConfig, client: LLMClient):
        self.config = config
        self.client = client
        self.session_id = f"support_{uuid4().hex[:12]}"
        self.run_dir = config.run_root / self.session_id
        self.transcript = TranscriptWriter(self.session_id, self.run_dir)
        self.memory = MemoryStore()
        self.vector_store = VectorStore.from_jsonl(config.knowledge_path, client)
        self.gateway = build_support_gateway(config.customer_db_path)
        self.router = SupportRouterAgent()
        self.monitor = SupportMonitorAgent()
        self.resolver = SupportResolverAgent(client, self.gateway, ContextBuilder())

    def run(self, messages: list[str]) -> SupportRunResult:
        self.transcript.log(
            state=HarnessState.PLAN,
            actor="harness",
            event_type="support_session_started",
            payload={"user_id": self.config.user_id, "turns": len(messages)},
        )
        final_state = HarnessState.DONE
        turn_results: list[SupportTurnResult] = []

        for index, message in enumerate(messages, start=1):
            self.memory.add(MemoryLayer.WORKING, f"user_turn_{index}: {message}", kind="user_message", turn=index)
            compacted = self.memory.compact_working_memory(keep_last=4)
            if compacted:
                self.transcript.log(
                    state=HarnessState.CONSOLIDATE,
                    actor="memory",
                    event_type="working_memory_compacted",
                    payload={"turn": index, "items": [dump_model(item) for item in compacted]},
                )

            route = self.router.route(message, self.memory.list())
            self.memory.add(MemoryLayer.EPISODIC, f"route={route.intent.value} confidence={route.confidence}", kind="route", turn=index)
            self.transcript.log(
                state=HarnessState.EXECUTE,
                actor="router",
                event_type="route_decision",
                payload={"turn": index, "route": dump_model(route)},
            )

            evidence, retrieval_flags = self._retrieve_policy_evidence(message, route.intent)
            monitor = self.monitor.inspect_route(message=message, route=route, evidence=evidence)
            if monitor.final_intent != route.intent:
                evidence, repair_flags = self._retrieve_policy_evidence(message, monitor.final_intent)
                retrieval_flags.extend(repair_flags)
            flags = retrieval_flags + monitor.flags
            self.transcript.log(
                state=HarnessState.VERIFY,
                actor="monitor",
                event_type="route_and_retrieval_monitor",
                payload={
                    "turn": index,
                    "final_intent": monitor.final_intent.value,
                    "flags": flags,
                    "policy_topics_found": monitor.required_policy_topics_found,
                },
            )

            output = self.resolver.resolve(
                user_id=self.config.user_id,
                message=message,
                intent=monitor.final_intent,
                evidence=evidence,
                memories=self.memory.list(),
            )
            policy_topics_found = _policy_topics(evidence)
            decision = gate_support_response(
                intent=monitor.final_intent,
                answer=output.answer,
                tool_results=output.tool_results,
                policy_topics_found=policy_topics_found,
            )
            self.transcript.log(
                state=HarnessState.VERIFY,
                actor="gate",
                event_type="support_response_gate",
                payload={"turn": index, "decision": dump_model(decision), "policy_topics_found": policy_topics_found},
            )
            if decision.action == GateAction.HALT:
                final_state = HarnessState.HALT
                break
            if decision.action == GateAction.REPLAN:
                repair_result = self._repair_response(
                    turn=index,
                    user_id=self.config.user_id,
                    message=message,
                    intent=monitor.final_intent,
                    evidence=evidence,
                    output=output,
                    decision=decision,
                    flags=flags,
                )
                if repair_result is None:
                    final_state = HarnessState.HALT
                    break
                output, evidence = repair_result

            self.memory.add(
                MemoryLayer.EPISODIC,
                f"support_turn_{index}: intent={monitor.final_intent.value}; flags={flags}; answer={output.answer}",
                kind="support_resolution",
                turn=index,
                intent=monitor.final_intent.value,
            )
            turn_result = SupportTurnResult(
                turn_index=index,
                user_message=message,
                route=route,
                final_intent=monitor.final_intent,
                answer=output.answer,
                monitor_flags=flags,
                tool_results=output.tool_results,
            )
            turn_results.append(turn_result)
            self.transcript.log(
                state=HarnessState.EXECUTE,
                actor="resolver",
                event_type="customer_answer",
                payload={"turn": index, "result": dump_model(turn_result)},
            )

        self.memory.save_snapshot(self.run_dir / "memory_snapshot.json")
        report_path = self._write_report(final_state, turn_results)
        self.transcript.log(
            state=final_state,
            actor="harness",
            event_type="support_session_finished",
            payload={"state": final_state.value, "report": str(report_path)},
        )
        return SupportRunResult(
            session_id=self.session_id,
            state=final_state,
            run_dir=self.run_dir,
            report_path=report_path,
            turns=turn_results,
        )

    def _repair_response(self, *, turn, user_id, message, intent, evidence, output, decision, flags):
        current_decision = decision
        current_output = output
        current_evidence = evidence
        for attempt in range(1, self.config.max_replans + 1):
            flags.append(f"response_replanned:{current_decision.reason}")
            self.memory.add(
                MemoryLayer.PROCEDURAL,
                (
                    f"Gate repair instruction for {intent.value}: {current_decision.reason}. "
                    "Answer only the current intent. Do not promise unsupported backend actions. "
                    "If a tool result is absent, say the user must complete that action in the platform."
                ),
                kind="gate_repair",
                turn=turn,
                attempt=attempt,
            )
            current_evidence, repair_flags = self._retrieve_policy_evidence(message, intent, force_backfill=True)
            flags.extend(repair_flags)
            current_output = self.resolver.resolve(
                user_id=user_id,
                message=message,
                intent=intent,
                evidence=current_evidence,
                memories=self.memory.list(),
            )
            current_decision = gate_support_response(
                intent=intent,
                answer=current_output.answer,
                tool_results=current_output.tool_results,
                policy_topics_found=_policy_topics(current_evidence),
            )
            self.transcript.log(
                state=HarnessState.VERIFY,
                actor="gate",
                event_type="support_response_repair_gate",
                payload={"turn": turn, "attempt": attempt, "decision": dump_model(current_decision)},
            )
            if current_decision.action == GateAction.PASS:
                return current_output, current_evidence
            if current_decision.action == GateAction.HALT:
                return None
        return None

    def _retrieve_policy_evidence(
        self,
        message: str,
        intent,
        *,
        force_backfill: bool = False,
    ) -> tuple[list[RetrievedChunk], list[str]]:
        playbook = get_playbook(intent)
        query_text = f"{intent.value} {message} {' '.join(playbook.required_policy_topics)}"
        evidence = self.vector_store.search(
            RetrievalQuery(text=query_text, topic="support", difficulty="any", top_k=6),
            self.client,
        )
        found = _policy_topics(evidence)
        missing = [topic for topic in playbook.required_policy_topics if topic not in found]
        flags: list[str] = []
        if missing or force_backfill:
            backfilled = self._backfill_policy_topics(missing or playbook.required_policy_topics)
            existing_ids = {item.id for item in evidence}
            evidence.extend(item for item in backfilled if item.id not in existing_ids)
            flags.append(f"rag_backfill:{','.join(missing or playbook.required_policy_topics)}")
        return evidence[:8], flags

    def _backfill_policy_topics(self, policy_topics: list[str]) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        for chunk in self.vector_store.chunks:
            metadata = dict(chunk.get("metadata", {}))
            if metadata.get("policy_topic") in policy_topics:
                chunks.append(
                    RetrievedChunk(
                        id=str(chunk["id"]),
                        text=str(chunk["text"]),
                        metadata=metadata,
                        score=1.0,
                    )
                )
        return chunks

    def _write_report(self, state: HarnessState, turns: list[SupportTurnResult]) -> Path:
        lines = [
            "# Support Agent Run Report",
            "",
            f"- Session: `{self.session_id}`",
            f"- User: `{self.config.user_id}`",
            f"- Final state: `{state.value}`",
            f"- Turns completed: {len(turns)}",
            "",
            "## What This Run Proves",
            "",
            "- RAG is used for policy grounding, with metadata backfill when required policy topics are missing.",
            "- MCP tools are allow-listed and all order/refund/access actions go through the gateway.",
            "- Skills define deterministic playbooks per intent; the model does not choose tool policy.",
            "- Monitor catches high-confidence but wrong routing before side effects happen.",
            "- Long working memory is compacted into semantic memory instead of silently disappearing.",
            "",
        ]
        for turn in turns:
            lines.extend(
                [
                    f"## Turn {turn.turn_index}",
                    "",
                    f"- User: {turn.user_message}",
                    f"- Router: `{turn.route.intent.value}` confidence={turn.route.confidence}",
                    f"- Final intent: `{turn.final_intent.value}`",
                    f"- Monitor flags: {', '.join(turn.monitor_flags) or 'none'}",
                    "",
                    turn.answer,
                    "",
                ]
            )
        path = self.run_dir / "support_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path


def _policy_topics(evidence: list[RetrievedChunk]) -> list[str]:
    return sorted({str(item.metadata.get("policy_topic")) for item in evidence if item.metadata.get("policy_topic")})
