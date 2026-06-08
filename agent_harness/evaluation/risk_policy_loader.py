from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback keeps project dependency-light
    yaml = None


ALLOWED_ACTIONS = {"allow", "block", "replan", "escalate", "halt"}
REQUIRED_INTENTS = {
    "access_issue",
    "refund_request",
    "invoice_request",
    "account_security",
    "human_escalation",
}
REQUIRED_POLICY_KEYS = {
    "required_tools",
    "required_policy_topics",
    "forbidden_claims",
    "on_missing_tool",
    "on_missing_policy",
    "on_forbidden_claim",
    "default_action",
}


def load_risk_policy(path: Path) -> dict[str, Any]:
    return _load_structured_mapping(path)


def load_tool_permissions(path: Path) -> dict[str, Any]:
    return _load_structured_mapping(path)


def validate_risk_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(policy, dict):
        return ["risk policy must be a mapping"]

    missing_intents = sorted(REQUIRED_INTENTS - set(policy))
    if missing_intents:
        errors.append(f"missing intents: {', '.join(missing_intents)}")

    for intent, entry in policy.items():
        if not isinstance(entry, dict):
            errors.append(f"{intent}: policy entry must be a mapping")
            continue
        missing_keys = sorted(REQUIRED_POLICY_KEYS - set(entry))
        if missing_keys:
            errors.append(f"{intent}: missing keys: {', '.join(missing_keys)}")
        for key in ("required_tools", "required_policy_topics", "forbidden_claims"):
            _validate_string_list(errors, intent, key, entry.get(key))
        for key in ("on_missing_tool", "on_missing_policy", "on_forbidden_claim", "default_action"):
            _validate_action(errors, intent, key, entry.get(key))
    return errors


def validate_tool_permissions(permissions: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(permissions, dict):
        return ["tool permissions must be a mapping"]

    for agent in ("router", "monitor", "resolver"):
        entry = permissions.get(agent)
        if not isinstance(entry, dict):
            errors.append(f"{agent}: permission entry must be a mapping")
            continue
        allowed_tools = entry.get("allowed_tools")
        if not isinstance(allowed_tools, list) or any(not isinstance(item, str) or not item for item in allowed_tools):
            errors.append(f"{agent}: allowed_tools must be a list of strings")

    router_tools = permissions.get("router", {}).get("allowed_tools", [])
    if router_tools:
        errors.append("router must not be allowed to call tools")

    resolver_tools = set(permissions.get("resolver", {}).get("allowed_tools", []))
    required_resolver_tools = {
        "customer_lookup",
        "order_lookup",
        "access_reset",
        "refund_policy_check",
        "escalation_ticket",
    }
    if not required_resolver_tools.issubset(resolver_tools):
        missing = sorted(required_resolver_tools - resolver_tools)
        errors.append(f"resolver missing business tools: {', '.join(missing)}")
    return errors


def _load_structured_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data: Any
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def _validate_string_list(errors: list[str], intent: str, key: str, value: Any) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{intent}: {key} must be a list of strings")


def _validate_action(errors: list[str], intent: str, key: str, value: Any) -> None:
    if value not in ALLOWED_ACTIONS:
        errors.append(f"{intent}: {key} must be one of {sorted(ALLOWED_ACTIONS)}")
