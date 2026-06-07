from __future__ import annotations

import re

from agent_harness.business.support_schemas import SupportIntent
from agent_harness.schemas import GateAction, GateDecision
from agent_harness.skills.support_playbooks import get_playbook


RAW_ORDER_PATTERN = re.compile(r"ord_[a-zA-Z0-9_]+", flags=re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}")

# Keep Chinese safety phrases as unicode escapes so Windows console/codepage
# issues cannot corrupt the source file. These mean:
# 我将为您开具 / 帮您开具 / 为您开具 / 帮您办理 / 立即开具 / 直接开具
# / 安排开具 / 会为您安排开具
INVOICE_PROMISE_PATTERN = re.compile(
    r"(\u6211\u5c06\u4e3a\u60a8\u5f00\u5177|"
    r"\u5e2e\u60a8\u5f00\u5177|"
    r"\u4e3a\u60a8\u5f00\u5177|"
    r"\u5e2e\u60a8\u529e\u7406|"
    r"\u7acb\u5373\u5f00\u5177|"
    r"\u76f4\u63a5\u5f00\u5177|"
    r"\u5b89\u6392\u5f00\u5177|"
    r"\u4f1a\u4e3a\u60a8\u5b89\u6392\u5f00\u5177)"
)

# 发票抬头 / 纳税识别号 / 税号. The current Harness has no invoice_create
# tool, so the chat agent must not collect invoice application data in chat.
INVOICE_DATA_COLLECTION_PATTERN = re.compile(
    r"(\u53d1\u7968\u62ac\u5934|"
    r"\u7eb3\u7a0e\u8bc6\u522b\u53f7|"
    r"\u7a0e\u53f7)"
)

# 已创建...工单 / 工单编号. A support answer can mention this only when the
# escalation_ticket tool actually succeeded.
TICKET_PROMISE_PATTERN = re.compile(r"(\u5df2.*\u5de5\u5355|\u5de5\u5355\u7f16\u53f7)")

# 符合条件 / 可进入退款审核 / 可退款 / 可以退款. These are eligibility
# claims and must be grounded by the refund_policy_check tool.
REFUND_ELIGIBILITY_PATTERN = re.compile(
    r"(\u7b26\u5408\u6761\u4ef6|"
    r"\u53ef\u8fdb\u5165\u9000\u6b3e\u5ba1\u6838|"
    r"\u53ef\u9000\u6b3e|"
    r"\u53ef\u4ee5\u9000\u6b3e)"
)

# 现在可以重新打开 / 已恢复正常 / 已经解决. access_reset means the token
# was refreshed, not that the user's device/session is guaranteed fixed.
ACCESS_RESOLVED_OVERCLAIM_PATTERN = re.compile(
    r"(\u73b0\u5728\u60a8\u53ef\u4ee5\u91cd\u65b0\u6253\u5f00|"
    r"\u73b0\u5728\u53ef\u4ee5\u91cd\u65b0\u6253\u5f00|"
    r"\u5df2\u6062\u590d\u6b63\u5e38|"
    r"\u95ee\u9898\u5df2\u89e3\u51b3)"
)


def gate_support_response(
    *,
    intent: SupportIntent,
    answer: str,
    tool_results: list[dict],
    policy_topics_found: list[str],
) -> GateDecision:
    """Final safety gate before customer-facing text is accepted."""

    if not answer.strip():
        return GateDecision(action=GateAction.REPLAN, reason="empty customer answer")
    if RAW_ORDER_PATTERN.search(answer) or EMAIL_PATTERN.search(answer):
        return GateDecision(action=GateAction.HALT, reason="PII or raw internal id leaked")
    if intent == SupportIntent.INVOICE_REQUEST and INVOICE_PROMISE_PATTERN.search(answer):
        return GateDecision(
            action=GateAction.REPLAN,
            reason="unsupported invoice action promise",
            audit={"rule": "invoice_create_tool_absent"},
        )
    if intent == SupportIntent.INVOICE_REQUEST and INVOICE_DATA_COLLECTION_PATTERN.search(answer):
        return GateDecision(
            action=GateAction.REPLAN,
            reason="unsupported invoice data collection",
            audit={"rule": "invoice_create_tool_absent"},
        )
    ticket_ids = _successful_ticket_ids(tool_results)
    if TICKET_PROMISE_PATTERN.search(answer) and not ticket_ids:
        return GateDecision(
            action=GateAction.REPLAN,
            reason="unsupported ticket promise",
            audit={"rule": "escalation_ticket_tool_absent"},
        )
    if "\u5de5\u5355\u7f16\u53f7" in answer and ticket_ids and not any(ticket_id in answer for ticket_id in ticket_ids):
        return GateDecision(
            action=GateAction.REPLAN,
            reason="ticket id not grounded in tool result",
            audit={"ticket_ids": ticket_ids},
        )
    if REFUND_ELIGIBILITY_PATTERN.search(answer) and not _has_successful_tool(tool_results, "refund_policy_check"):
        return GateDecision(
            action=GateAction.REPLAN,
            reason="unsupported refund eligibility claim",
            audit={"rule": "refund_policy_check_tool_absent"},
        )
    if intent == SupportIntent.ACCESS_ISSUE and ACCESS_RESOLVED_OVERCLAIM_PATTERN.search(answer):
        return GateDecision(
            action=GateAction.REPLAN,
            reason="access reset overclaimed as resolved",
            audit={"rule": "access_reset_is_not_end_user_verification"},
        )

    failed_tools = [item for item in tool_results if not item.get("success", False)]
    if failed_tools:
        return GateDecision(action=GateAction.HALT, reason="required MCP tool failed", audit={"failed_tools": failed_tools})

    playbook = get_playbook(intent)
    missing_topics = [topic for topic in playbook.required_policy_topics if topic not in policy_topics_found]
    if missing_topics:
        return GateDecision(
            action=GateAction.REPLAN,
            reason="RAG recall missed required policy topics",
            audit={"missing_policy_topics": missing_topics},
        )
    return GateDecision(action=GateAction.PASS, reason="support response passed gate")


def _successful_ticket_ids(tool_results: list[dict]) -> list[str]:
    ticket_ids: list[str] = []
    for item in tool_results:
        if item.get("success") and item.get("name") == "escalation_ticket":
            ticket_id = item.get("data", {}).get("ticket_id")
            if ticket_id:
                ticket_ids.append(str(ticket_id))
    return ticket_ids


def _has_successful_tool(tool_results: list[dict], name: str) -> bool:
    return any(item.get("success") and item.get("name") == name for item in tool_results)
