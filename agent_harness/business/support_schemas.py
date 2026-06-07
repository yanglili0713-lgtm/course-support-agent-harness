from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from agent_harness.schemas import BaseModel, Field, ModelConfig


class SupportIntent(str, Enum):
    REFUND_REQUEST = "refund_request"
    ACCESS_ISSUE = "access_issue"
    INVOICE_REQUEST = "invoice_request"
    ACCOUNT_SECURITY = "account_security"
    ESCALATE = "escalate"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupportConfig(BaseModel):
    """Runtime config for the customer-support business scenario."""

    user_id: str = "u_1001"
    run_root: Path = Path("runs")
    knowledge_path: Path = Path("examples/support_policy_kb.jsonl")
    customer_db_path: Path = Path("examples/support_customers.yaml")
    offline: bool = True
    max_replans: int = Field(default=2, ge=0, le=5)
    model: ModelConfig = Field(default_factory=ModelConfig)


class RouteDecision(BaseModel):
    intent: SupportIntent
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    signals: dict[str, Any] = Field(default_factory=dict)


class Playbook(BaseModel):
    intent: SupportIntent
    name: str
    risk: RiskLevel
    required_tools: list[str]
    required_policy_topics: list[str]
    requires_identity_check: bool
    response_contract: str


class SupportTurnResult(BaseModel):
    turn_index: int
    user_message: str
    route: RouteDecision
    final_intent: SupportIntent
    answer: str
    monitor_flags: list[str] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
