from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agent_harness.config_loader import load_mapping
from agent_harness.context import ContextBuilder
from agent_harness.control_plane.gates import extract_score, gate_grade, gate_question
from agent_harness.control_plane.transcript import TranscriptWriter
from agent_harness.llm import LLMClient
from agent_harness.mcp.gateway import build_default_gateway
from agent_harness.memory import MemoryStore
from agent_harness.rag import VectorStore
from agent_harness.schemas import GateAction, HarnessState, MemoryLayer, RetrievalQuery, SessionConfig, dump_model
from agent_harness.skills import build_session_plan
from agent_harness.sub_agents import ExaminerAgent, GraderAgent


AnswerProvider = Callable[[str, int], str]


@dataclass(frozen=True)
class RunResult:
    session_id: str
    state: HarnessState
    run_dir: Path
    final_report_path: Path


class HarnessRunner:
    """PLAN-EXECUTE-VERIFY runner.

    This class is the control plane. It owns transitions, gates, memory writes,
    tool boundaries, transcripts, and final artifacts. Sub-agents never decide
    whether the workflow should continue.
    """

    def __init__(self, config: SessionConfig, client: LLMClient):
        self.config = config
        self.client = client
        self.profile = _load_yaml(config.profile_path)
        self.plan = build_session_plan(config, self.profile)
        self.run_dir = config.run_root / self.plan.session_id
        self.transcript = TranscriptWriter(self.plan.session_id, self.run_dir)
        self.memory = MemoryStore()
        self.context_builder = ContextBuilder()
        self.gateway = build_default_gateway(self.profile)
        self.vector_store = VectorStore.from_jsonl(config.knowledge_path, client)
        self.examiner = ExaminerAgent(client, self.gateway, self.context_builder)
        self.grader = GraderAgent(client, self.gateway, self.context_builder)

    def run(self, answer_provider: AnswerProvider) -> RunResult:
        self.transcript.log(
            state=HarnessState.PLAN,
            actor="harness",
            event_type="session_plan",
            payload={"plan": dump_model(self.plan), "profile": self.profile},
        )
        final_state = HarnessState.DONE
        round_reports: list[dict] = []

        for step in self.plan.steps:
            evidence = self.vector_store.search(
                RetrievalQuery(
                    text=f"{step.topic} {step.dimension} {step.learning_goal}",
                    topic=step.topic,
                    difficulty=step.difficulty,
                    top_k=4,
                ),
                self.client,
            )
            self.transcript.log(
                state=HarnessState.EXECUTE,
                actor="rag",
                event_type="retrieval",
                payload={"round": step.round_index, "evidence": [dump_model(item) for item in evidence]},
            )

            question_output = self._generate_question_with_gate(step, evidence)
            if question_output is None:
                final_state = HarnessState.HALT
                break
            question, question_audit = question_output
            answer = answer_provider(question, step.round_index)
            self.memory.add(
                MemoryLayer.WORKING,
                f"Round {step.round_index} answer draft: {answer}",
                round=step.round_index,
                kind="answer",
            )
            self.transcript.log(
                state=HarnessState.EXECUTE,
                actor="candidate",
                event_type="answer",
                payload={"round": step.round_index, "answer": answer},
            )

            grade_output = self._grade_with_gate(step, question, answer, evidence)
            if grade_output is None:
                final_state = HarnessState.HALT
                break
            grade, grade_audit = grade_output
            score = extract_score(grade) or 0
            self.memory.add(
                MemoryLayer.EPISODIC,
                f"Round {step.round_index}: score={score}; grade={grade}",
                round=step.round_index,
                kind="grading",
                score=score,
            )
            promoted = self.memory.consolidate()
            self.transcript.log(
                state=HarnessState.CONSOLIDATE,
                actor="memory",
                event_type="memory_consolidated",
                payload={"round": step.round_index, "promoted": [dump_model(item) for item in promoted]},
            )
            round_reports.append(
                {
                    "round": step.round_index,
                    "question": question,
                    "answer": answer,
                    "grade": grade,
                    "score": score,
                    "question_audit": question_audit,
                    "grade_audit": grade_audit,
                }
            )

        self.memory.save_snapshot(self.run_dir / "memory_snapshot.json")
        report_path = self._write_final_report(final_state, round_reports)
        self.transcript.log(
            state=final_state,
            actor="harness",
            event_type="session_finished",
            payload={"final_report": str(report_path), "state": final_state.value},
        )
        return RunResult(
            session_id=self.plan.session_id,
            state=final_state,
            run_dir=self.run_dir,
            final_report_path=report_path,
        )

    def _generate_question_with_gate(self, step, evidence) -> tuple[str, dict] | None:
        last_audit: dict = {}
        for attempt in range(self.config.max_replans + 1):
            output = self.examiner.generate_question(
                step=step,
                memories=self.memory.list(),
                evidence=evidence,
            )
            decision = gate_question(output.content, tool_audit=output.tool_audit, round_index=step.round_index)
            last_audit = {"attempt": attempt, "gate": dump_model(decision), "context": output.context_audit}
            self.transcript.log(
                state=HarnessState.VERIFY,
                actor="gate",
                event_type="question_gate",
                payload={"round": step.round_index, **last_audit},
            )
            if decision.action == GateAction.PASS:
                self.transcript.log(
                    state=HarnessState.EXECUTE,
                    actor="examiner",
                    event_type="question",
                    payload={"round": step.round_index, "question": output.content, "audit": last_audit},
                )
                return output.content, last_audit
            if decision.action == GateAction.HALT:
                return None
        self.transcript.log(
            state=HarnessState.HALT,
            actor="harness",
            event_type="replan_exhausted",
            payload={"round": step.round_index, "last_audit": last_audit},
        )
        return None

    def _grade_with_gate(self, step, question: str, answer: str, evidence) -> tuple[str, dict] | None:
        last_audit: dict = {}
        for attempt in range(self.config.max_replans + 1):
            output = self.grader.grade_answer(
                step=step,
                question=question,
                answer=answer,
                memories=self.memory.list(),
                evidence=evidence,
            )
            decision = gate_grade(output.content, tool_audit=output.tool_audit, round_index=step.round_index)
            last_audit = {"attempt": attempt, "gate": dump_model(decision), "context": output.context_audit}
            self.transcript.log(
                state=HarnessState.VERIFY,
                actor="gate",
                event_type="grade_gate",
                payload={"round": step.round_index, **last_audit},
            )
            if decision.action == GateAction.PASS:
                self.transcript.log(
                    state=HarnessState.EXECUTE,
                    actor="grader",
                    event_type="grade",
                    payload={"round": step.round_index, "grade": output.content, "audit": last_audit},
                )
                return output.content, last_audit
            if decision.action == GateAction.HALT:
                return None
        self.transcript.log(
            state=HarnessState.HALT,
            actor="harness",
            event_type="replan_exhausted",
            payload={"round": step.round_index, "last_audit": last_audit},
        )
        return None

    def _write_final_report(self, final_state: HarnessState, rounds: list[dict]) -> Path:
        lines = [
            f"# Agent Harness Final Report",
            "",
            f"- Session: `{self.plan.session_id}`",
            f"- Candidate: {self.plan.candidate_name}",
            f"- Final state: `{final_state.value}`",
            f"- Rounds completed: {len(rounds)}",
            "",
        ]
        for item in rounds:
            lines.extend(
                [
                    f"## Round {item['round']} - Score {item['score']}",
                    "",
                    f"**Question**: {item['question']}",
                    "",
                    f"**Answer**: {item['answer']}",
                    "",
                    "```text",
                    item["grade"],
                    "```",
                    "",
                ]
            )
        path = self.run_dir / "final_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path


def _load_yaml(path: Path) -> dict:
    return load_mapping(path)
