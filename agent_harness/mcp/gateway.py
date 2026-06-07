from __future__ import annotations

from typing import Callable

from agent_harness.schemas import ToolCall, ToolResult, ToolSpec


ToolHandler = Callable[[dict], dict]


class MCPGateway:
    """Lightweight MCP-like gateway with allow-list control.

    v1 uses in-process mock tools so the Harness can demonstrate the engineering
    contract: explicit tool specs, agent allow-lists, audit-friendly results.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def call(self, call: ToolCall) -> ToolResult:
        spec = self._specs.get(call.name)
        if not spec:
            return ToolResult(call_id=call.id, name=call.name, success=False, error="unknown tool")
        if call.agent not in spec.allowed_agents:
            return ToolResult(call_id=call.id, name=call.name, success=False, error="agent not allowed")
        try:
            data = self._handlers[call.name](call.args)
            return ToolResult(call_id=call.id, name=call.name, success=True, data=data)
        except Exception as exc:  # pragma: no cover - defensive audit path
            return ToolResult(call_id=call.id, name=call.name, success=False, error=str(exc))


def build_default_gateway(profile: dict) -> MCPGateway:
    gateway = MCPGateway()
    gateway.register(
        ToolSpec(
            name="resume_lookup",
            description="Return resume highlights for personalized questions.",
            allowed_agents={"examiner"},
        ),
        lambda args: {"highlights": profile.get("highlights", []), "projects": profile.get("projects", [])},
    )
    gateway.register(
        ToolSpec(
            name="rubric_lookup",
            description="Return grading rubric dimensions.",
            allowed_agents={"grader"},
        ),
        lambda args: {
            "rubric": [
                "concept accuracy",
                "engineering tradeoff",
                "failure analysis",
                "evidence and metrics",
            ]
        },
    )
    gateway.register(
        ToolSpec(
            name="knowledge_probe",
            description="Return topic probe hints for either sub-agent.",
            allowed_agents={"examiner", "grader"},
        ),
        lambda args: {"topic": args.get("topic", "rag"), "hint": "Check retrieval quality, grounding, and evaluation."},
    )
    return gateway
