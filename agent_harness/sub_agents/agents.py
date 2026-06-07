from __future__ import annotations

from dataclasses import dataclass, field

from agent_harness.context import ContextBuilder
from agent_harness.llm import ChatMessage, LLMClient
from agent_harness.mcp import MCPGateway
from agent_harness.schemas import MemoryItem, PlanStep, RetrievedChunk, ToolCall, dump_model


@dataclass
class AgentOutput:
    content: str
    tool_audit: list[dict] = field(default_factory=list)
    context_audit: dict = field(default_factory=dict)


class BaseSubAgent:
    """Base class enforcing isolated history per agent instance."""

    name: str

    def __init__(self, client: LLMClient, gateway: MCPGateway, context_builder: ContextBuilder):
        self.client = client
        self.gateway = gateway
        self.context_builder = context_builder
        self.history: list[ChatMessage] = []

    def _chat(self, context: str) -> str:
        messages = [ChatMessage(role="user", content=context)]
        response = self.client.chat(messages)
        self.history.extend(messages)
        self.history.append(ChatMessage(role="assistant", content=response))
        return response


class ExaminerAgent(BaseSubAgent):
    name = "examiner"

    def generate_question(
        self,
        *,
        step: PlanStep,
        memories: list[MemoryItem],
        evidence: list[RetrievedChunk],
    ) -> AgentOutput:
        resume = self.gateway.call(ToolCall(agent=self.name, name="resume_lookup"))
        probe = self.gateway.call(ToolCall(agent=self.name, name="knowledge_probe", args={"topic": step.topic}))
        context = self.context_builder.build(
            agent_role="Examiner: generate one interview question only. Do not grade.",
            step=step,
            memories=memories,
            evidence=evidence,
            task_input=f"Use resume highlights and probe hints: {resume.data} {probe.data}",
            output_schema="A single Chinese interview question.",
        )
        content = self._chat(context.text)
        return AgentOutput(
            content=content,
            tool_audit=[dump_model(resume), dump_model(probe)],
            context_audit={"prefix_hash": context.prefix_hash, "cache_hit": context.cache_hit},
        )


class GraderAgent(BaseSubAgent):
    name = "grader"

    def grade_answer(
        self,
        *,
        step: PlanStep,
        question: str,
        answer: str,
        memories: list[MemoryItem],
        evidence: list[RetrievedChunk],
    ) -> AgentOutput:
        rubric = self.gateway.call(ToolCall(agent=self.name, name="rubric_lookup"))
        context = self.context_builder.build(
            agent_role="Grader: score the answer. Do not create new questions.",
            step=step,
            memories=memories,
            evidence=evidence,
            task_input=f"Question: {question}\nAnswer: {answer}\nRubric: {rubric.data}",
            output_schema="score: <0-100>\nstrengths: <text>\nrisks: <text>\nnext_step: <text>",
        )
        content = self._chat(context.text)
        return AgentOutput(
            content=content,
            tool_audit=[dump_model(rubric)],
            context_audit={"prefix_hash": context.prefix_hash, "cache_hit": context.cache_hit},
        )
