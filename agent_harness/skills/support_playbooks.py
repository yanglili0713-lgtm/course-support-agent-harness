from __future__ import annotations

from agent_harness.business.support_schemas import Playbook, RiskLevel, SupportIntent


PLAYBOOKS: dict[SupportIntent, Playbook] = {
    SupportIntent.REFUND_REQUEST: Playbook(
        intent=SupportIntent.REFUND_REQUEST,
        name="Paid-course refund triage",
        risk=RiskLevel.HIGH,
        required_tools=["customer_lookup", "order_lookup", "refund_policy_check"],
        required_policy_topics=["refund", "identity"],
        requires_identity_check=True,
        response_contract="Explain eligibility, do not promise refund until policy and order state pass.",
    ),
    SupportIntent.ACCESS_ISSUE: Playbook(
        intent=SupportIntent.ACCESS_ISSUE,
        name="Course access recovery",
        risk=RiskLevel.MEDIUM,
        required_tools=["customer_lookup", "order_lookup", "access_reset"],
        required_policy_topics=["access", "identity"],
        requires_identity_check=True,
        response_contract="Recover access or create escalation; never expose another user's course/order data.",
    ),
    SupportIntent.INVOICE_REQUEST: Playbook(
        intent=SupportIntent.INVOICE_REQUEST,
        name="Invoice guidance",
        risk=RiskLevel.MEDIUM,
        required_tools=["customer_lookup", "order_lookup"],
        required_policy_topics=["invoice", "identity"],
        requires_identity_check=True,
        response_contract="Tell user the invoice state and next step, with masked order id only.",
    ),
    SupportIntent.ACCOUNT_SECURITY: Playbook(
        intent=SupportIntent.ACCOUNT_SECURITY,
        name="Account security escalation",
        risk=RiskLevel.HIGH,
        required_tools=["customer_lookup", "escalation_ticket"],
        required_policy_topics=["security", "identity"],
        requires_identity_check=True,
        response_contract="Do not change sensitive data; create security escalation and give safe next step.",
    ),
    SupportIntent.ESCALATE: Playbook(
        intent=SupportIntent.ESCALATE,
        name="Human escalation",
        risk=RiskLevel.LOW,
        required_tools=["escalation_ticket"],
        required_policy_topics=["escalation"],
        requires_identity_check=False,
        response_contract="Summarize issue and create a human-review ticket.",
    ),
}


def get_playbook(intent: SupportIntent) -> Playbook:
    return PLAYBOOKS[intent]


def all_playbooks() -> list[Playbook]:
    return list(PLAYBOOKS.values())

