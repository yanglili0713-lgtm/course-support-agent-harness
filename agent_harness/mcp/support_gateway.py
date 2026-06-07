from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_harness.config_loader import load_mapping
from agent_harness.mcp.gateway import MCPGateway
from agent_harness.schemas import ToolSpec


def build_support_gateway(customer_db_path: Path) -> MCPGateway:
    """Build mock MCP tools for a support desk.

    These tools are deliberately tiny, but they model the real backend concerns:
    identity checks, scoped customer data, side-effect tools, and audit-friendly
    return values. The resolver must call tools through this gateway instead of
    directly reading the customer database.
    """

    db = _load_db(customer_db_path)
    tickets: list[dict[str, Any]] = []
    gateway = MCPGateway()

    gateway.register(
        ToolSpec(
            name="customer_lookup",
            description="Look up the current customer's masked profile.",
            allowed_agents={"resolver", "monitor"},
        ),
        lambda args: _customer_lookup(db, str(args["user_id"])),
    )
    gateway.register(
        ToolSpec(
            name="order_lookup",
            description="Look up current user's course order state.",
            allowed_agents={"resolver", "monitor"},
        ),
        lambda args: _order_lookup(db, str(args["user_id"]), args.get("course_id")),
    )
    gateway.register(
        ToolSpec(
            name="refund_policy_check",
            description="Check whether an order is eligible for refund.",
            allowed_agents={"resolver"},
        ),
        lambda args: _refund_policy_check(db, str(args["user_id"]), str(args["order_id"])),
    )
    gateway.register(
        ToolSpec(
            name="access_reset",
            description="Reset course access for an active paid order.",
            allowed_agents={"resolver"},
        ),
        lambda args: _access_reset(db, str(args["user_id"]), str(args["order_id"])),
    )
    gateway.register(
        ToolSpec(
            name="escalation_ticket",
            description="Create a human-review ticket.",
            allowed_agents={"resolver", "monitor"},
        ),
        lambda args: _create_ticket(tickets, args),
    )
    return gateway


def _load_db(path: Path) -> dict[str, Any]:
    return load_mapping(path)


def _customer_lookup(db: dict[str, Any], user_id: str) -> dict[str, Any]:
    user = db["users"].get(user_id)
    if not user:
        return {"found": False}
    return {
        "found": True,
        "user_id": user_id,
        "email_masked": user["email_masked"],
        "verified": bool(user.get("verified", False)),
        "risk_flags": user.get("risk_flags", []),
    }


def _order_lookup(db: dict[str, Any], user_id: str, course_id: str | None = None) -> dict[str, Any]:
    orders = [
        order
        for order in db["orders"]
        if order["user_id"] == user_id and (course_id is None or order["course_id"] == course_id)
    ]
    return {"orders": [_mask_order(order) for order in orders]}


def _refund_policy_check(db: dict[str, Any], user_id: str, order_id: str) -> dict[str, Any]:
    order = _find_order(db, user_id, order_id)
    if not order:
        return {"eligible": False, "reason": "order not found for current user"}
    if order["days_since_purchase"] > 7:
        return {"eligible": False, "reason": "outside 7-day refund window", "order_id": _mask_id(order_id)}
    if order["progress_percent"] > 20:
        return {"eligible": False, "reason": "course progress exceeds 20%", "order_id": _mask_id(order_id)}
    return {"eligible": True, "reason": "inside refund policy", "order_id": _mask_id(order_id)}


def _access_reset(db: dict[str, Any], user_id: str, order_id: str) -> dict[str, Any]:
    order = _find_order(db, user_id, order_id)
    if not order:
        return {"success": False, "reason": "order not found for current user"}
    if order["status"] != "paid":
        return {"success": False, "reason": "order is not paid"}
    return {"success": True, "reason": "access token refreshed", "order_id": _mask_id(order_id)}


def _create_ticket(tickets: list[dict[str, Any]], args: dict[str, Any]) -> dict[str, Any]:
    ticket = {
        "ticket_id": f"T{len(tickets) + 1:04d}",
        "user_id": args.get("user_id"),
        "intent": args.get("intent", "unknown"),
        "summary": args.get("summary", ""),
    }
    tickets.append(ticket)
    return ticket


def _find_order(db: dict[str, Any], user_id: str, order_id: str) -> dict[str, Any] | None:
    for order in db["orders"]:
        if order["user_id"] == user_id and order["order_id"] == order_id:
            return order
    return None


def _mask_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": _mask_id(order["order_id"]),
        "raw_order_id": order["order_id"],
        "course_id": order["course_id"],
        "course_name": order["course_name"],
        "status": order["status"],
        "days_since_purchase": order["days_since_purchase"],
        "progress_percent": order["progress_percent"],
        "invoice_state": order["invoice_state"],
    }


def _mask_id(value: str) -> str:
    return f"{value[:3]}***{value[-2:]}"
