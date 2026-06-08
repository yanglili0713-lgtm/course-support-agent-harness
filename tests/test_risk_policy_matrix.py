from pathlib import Path

from agent_harness.evaluation.risk_policy_loader import (
    load_risk_policy,
    load_tool_permissions,
    validate_risk_policy,
    validate_tool_permissions,
)


def test_risk_policy_matrix_loads_and_validates():
    policy = load_risk_policy(Path("configs/risk_policy.yaml"))
    errors = validate_risk_policy(policy)

    assert errors == []
    for intent in [
        "access_issue",
        "refund_request",
        "invoice_request",
        "account_security",
        "human_escalation",
    ]:
        entry = policy[intent]
        assert entry["required_tools"]
        assert entry["required_policy_topics"]
        assert entry["forbidden_claims"]
        assert entry["default_action"] in {"allow", "block", "replan", "escalate", "halt"}


def test_tool_permissions_loads_and_respects_agent_boundaries():
    permissions = load_tool_permissions(Path("configs/tool_permissions.yaml"))
    errors = validate_tool_permissions(permissions)

    assert errors == []
    assert permissions["router"]["allowed_tools"] == []
    assert "customer_lookup" in permissions["resolver"]["allowed_tools"]
    assert "order_lookup" in permissions["resolver"]["allowed_tools"]
    assert "access_reset" in permissions["resolver"]["allowed_tools"]
