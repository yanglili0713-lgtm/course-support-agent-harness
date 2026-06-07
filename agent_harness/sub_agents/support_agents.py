from __future__ import annotations

from dataclasses import dataclass, field

from agent_harness.business.support_schemas import RouteDecision, SupportIntent
from agent_harness.context import ContextBuilder
from agent_harness.llm import ChatMessage, LLMClient
from agent_harness.mcp import MCPGateway
from agent_harness.schemas import MemoryItem, RetrievedChunk, ToolCall
from agent_harness.skills.support_playbooks import get_playbook


@dataclass
class ResolverOutput:
    answer: str
    tool_results: list[dict] = field(default_factory=list)


@dataclass
class MonitorDecision:
    final_intent: SupportIntent
    flags: list[str] = field(default_factory=list)
    required_policy_topics_found: list[str] = field(default_factory=list)


class SupportRouterAgent:
    """Intent router with auditable signals.

    The first version intentionally has a realistic weakness: if a user says
    "打不开课程，再不行就退款", the refund keyword can dominate. The monitor
    layer fixes this by comparing route confidence with policy evidence and
    conversation signals instead of trusting confidence alone.
    """

    def route(self, message: str, memories: list[MemoryItem]) -> RouteDecision:
        text = message.lower()
        signals = {
            "refund_words": _count_any(text, ["退款", "退费", "refund"]),
            "access_words": _count_any(text, ["打不开", "无法进入", "看不了", "进不去", "access", "login"]),
            "invoice_words": _count_any(text, ["发票", "invoice"]),
            "security_words": _count_any(text, ["盗号", "被改", "安全", "security"]),
            "memory_access_issue": any("access_issue" in item.content for item in memories[-5:]),
        }
        if signals["security_words"]:
            return RouteDecision(intent=SupportIntent.ACCOUNT_SECURITY, confidence=0.92, reason="security keyword", signals=signals)
        if signals["refund_words"]:
            return RouteDecision(intent=SupportIntent.REFUND_REQUEST, confidence=0.89, reason="refund keyword dominated", signals=signals)
        if signals["invoice_words"]:
            return RouteDecision(intent=SupportIntent.INVOICE_REQUEST, confidence=0.86, reason="invoice keyword", signals=signals)
        if signals["access_words"] or signals["memory_access_issue"]:
            return RouteDecision(intent=SupportIntent.ACCESS_ISSUE, confidence=0.84, reason="access recovery signal", signals=signals)
        return RouteDecision(intent=SupportIntent.ESCALATE, confidence=0.55, reason="no stable business intent", signals=signals)


class SupportMonitorAgent:
    """Online monitor that checks route, retrieval and tool plan before action."""

    def inspect_route(
        self,
        *,
        message: str,
        route: RouteDecision,
        evidence: list[RetrievedChunk],
    ) -> MonitorDecision:
        flags: list[str] = []
        found_topics = sorted({str(item.metadata.get("policy_topic")) for item in evidence if item.metadata.get("policy_topic")})
        playbook = get_playbook(route.intent)
        missing = [topic for topic in playbook.required_policy_topics if topic not in found_topics]
        if missing:
            flags.append(f"rag_policy_gap:{','.join(missing)}")

        # The concrete bug fix: a high-confidence refund route can be wrong when
        # the user primarily reports access failure and only threatens refund.
        access_signal = any(word in message for word in ["打不开", "无法进入", "看不了"])
        refund_signal = any(word in message for word in ["退款", "退费"])
        if route.intent == SupportIntent.REFUND_REQUEST and route.confidence >= 0.85 and access_signal and refund_signal:
            flags.append("route_corrected:refund_threat_to_access_issue")
            return MonitorDecision(
                final_intent=SupportIntent.ACCESS_ISSUE,
                flags=flags,
                required_policy_topics_found=found_topics,
            )

        if route.confidence < 0.65:
            flags.append("low_confidence_escalation")
            return MonitorDecision(final_intent=SupportIntent.ESCALATE, flags=flags, required_policy_topics_found=found_topics)
        return MonitorDecision(final_intent=route.intent, flags=flags, required_policy_topics_found=found_topics)


class SupportResolverAgent:
    """Resolve a turn using only MCP tools allowed to the resolver."""

    def __init__(self, client: LLMClient, gateway: MCPGateway, context_builder: ContextBuilder):
        self.client = client
        self.gateway = gateway
        self.context_builder = context_builder
        self.history: list[ChatMessage] = []

    def resolve(
        self,
        *,
        user_id: str,
        message: str,
        intent: SupportIntent,
        evidence: list[RetrievedChunk],
        memories: list[MemoryItem],
    ) -> ResolverOutput:
        playbook = get_playbook(intent)
        tool_results = self._execute_playbook_tools(user_id=user_id, intent=intent, message=message)
        compact_context = self._build_compact_context(
            message=message,
            intent=intent,
            evidence=evidence,
            memories=memories,
            tool_results=tool_results,
            response_contract=playbook.response_contract,
        )
        answer = self.client.chat([ChatMessage(role="user", content=compact_context)], temperature=0.1)
        self.history.append(ChatMessage(role="user", content=compact_context))
        self.history.append(ChatMessage(role="assistant", content=answer))
        return ResolverOutput(answer=answer, tool_results=tool_results)

    def _execute_playbook_tools(self, *, user_id: str, intent: SupportIntent, message: str) -> list[dict]:
        results: list[dict] = []
        customer = self.gateway.call(ToolCall(agent="resolver", name="customer_lookup", args={"user_id": user_id}))
        results.append(customer.model_dump())
        orders = self.gateway.call(ToolCall(agent="resolver", name="order_lookup", args={"user_id": user_id}))
        results.append(orders.model_dump())
        raw_order_id = _first_raw_order_id(orders.data)

        if intent == SupportIntent.REFUND_REQUEST and raw_order_id:
            refund = self.gateway.call(
                ToolCall(agent="resolver", name="refund_policy_check", args={"user_id": user_id, "order_id": raw_order_id})
            )
            results.append(refund.model_dump())
        elif intent == SupportIntent.ACCESS_ISSUE and raw_order_id:
            reset = self.gateway.call(
                ToolCall(agent="resolver", name="access_reset", args={"user_id": user_id, "order_id": raw_order_id})
            )
            results.append(reset.model_dump())
            if _needs_access_escalation(message):
                ticket = self.gateway.call(
                    ToolCall(
                        agent="resolver",
                        name="escalation_ticket",
                        args={"user_id": user_id, "intent": intent.value, "summary": message},
                    )
                )
                results.append(ticket.model_dump())
        elif intent == SupportIntent.ACCOUNT_SECURITY:
            ticket = self.gateway.call(
                ToolCall(
                    agent="resolver",
                    name="escalation_ticket",
                    args={"user_id": user_id, "intent": intent.value, "summary": message},
                )
            )
            results.append(ticket.model_dump())
        elif intent == SupportIntent.ESCALATE:
            ticket = self.gateway.call(
                ToolCall(
                    agent="resolver",
                    name="escalation_ticket",
                    args={"user_id": user_id, "intent": intent.value, "summary": message},
                )
            )
            results.append(ticket.model_dump())
        return results

    def _build_compact_context(
        self,
        *,
        message: str,
        intent: SupportIntent,
        evidence: list[RetrievedChunk],
        memories: list[MemoryItem],
        tool_results: list[dict],
        response_contract: str,
    ) -> str:
        memory_text = "\n".join(f"- {item.content}" for item in memories[-6:]) or "- none"
        evidence_text = "\n".join(f"- {item.metadata.get('policy_topic')}: {item.text}" for item in evidence[:4])
        return (
            "Support Resolver Agent\n"
            "You answer in Chinese. Never reveal raw order ids, full email, or internal tool payloads.\n"
            "Answer the current intent only. Do not mention previous refund/access/ticket issues unless the current user message asks about them.\n"
            "Never promise an action that is not backed by a successful tool result. "
            "If you mention an escalation ticket id, copy the exact ticket_id from tool results; otherwise omit the id. "
            "For access_issue, access_reset only means the token was refreshed; do not say the user can now access or that the issue is solved. Ask them to retry after re-login. "
            "Do not state refund eligibility unless refund_policy_check succeeded in tool results. "
            "For invoice_request, there is no invoice_create tool in this Harness: if invoice_state is not_requested, "
            "tell the user to submit invoice application info in the platform order page. "
            "Do not say we will issue or arrange the invoice, and do not collect invoice title, tax number, or company details in chat.\n"
            f"Intent: {intent.value}\n"
            f"User message: {message}\n"
            f"Response contract: {response_contract}\n"
            f"Memory:\n{memory_text}\n"
            f"Policy evidence:\n{evidence_text}\n"
            f"Tool results:\n{tool_results}\n"
            "Return a concise customer-facing answer with next step."
        )


def _count_any(text: str, words: list[str]) -> int:
    return sum(1 for word in words if word in text)


def _first_raw_order_id(order_payload: dict) -> str | None:
    for order in order_payload.get("orders", []):
        if order.get("raw_order_id"):
            return str(order["raw_order_id"])
    return None


def _needs_access_escalation(message: str) -> bool:
    return any(word in message for word in ["还是", "仍然", "依然", "再次", "还不行", "进不去"])
