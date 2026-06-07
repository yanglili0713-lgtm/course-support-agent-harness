from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

class _Missing:
    pass


MISSING = _Missing()


class FieldInfo:
    """Tiny stdlib replacement for the small subset of pydantic Field we use.

    The project originally used pydantic for convenience. For demos in fresh
    conda environments, dependency installation can be the weakest link, so the
    core schema layer keeps only the features this project actually needs:
    defaults, default_factory, and JSON-like dumping.
    """

    def __init__(self, default: Any = MISSING, default_factory: Any = None, **_: Any) -> None:
        self.default = default
        self.default_factory = default_factory


def Field(default: Any = MISSING, default_factory: Any = None, **kwargs: Any) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory, **kwargs)


class BaseModel:
    """Minimal BaseModel-compatible class used by the Harness schemas."""

    def __init__(self, **kwargs: Any) -> None:
        fields = _model_fields(type(self))
        for name in fields:
            if name in kwargs:
                value = kwargs.pop(name)
            else:
                value = _default_for(type(self), name)
            setattr(self, name, value)
        for name, value in kwargs.items():
            setattr(self, name, value)

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {name: _dump_value(getattr(self, name)) for name in _model_fields(type(self))}

    def dict(self) -> dict[str, Any]:
        return self.model_dump()


def _model_fields(cls: type) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        fields.update(getattr(base, "__annotations__", {}))
    return fields


def _default_for(cls: type, name: str) -> Any:
    raw = getattr(cls, name, MISSING)
    if isinstance(raw, FieldInfo):
        if raw.default_factory:
            return raw.default_factory()
        if raw.default is not MISSING:
            return raw.default
        raise TypeError(f"Missing required field: {name}")
    if raw is not MISSING:
        return raw
    raise TypeError(f"Missing required field: {name}")


def _dump_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, tuple):
        return [_dump_value(item) for item in value]
    if isinstance(value, set):
        return sorted(_dump_value(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _dump_value(item) for key, item in value.items()}
    return value

def utc_now() -> str:
    """Return an ISO timestamp that is stable for transcript sorting."""

    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Create short, readable ids for artifacts that humans inspect."""

    return f"{prefix}_{uuid4().hex[:12]}"


def dump_model(model: BaseModel) -> dict[str, Any]:
    """Pydantic v2/v1 compatible dump helper used by storage code."""

    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


class HarnessState(str, Enum):
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    CONSOLIDATE = "CONSOLIDATE"
    DONE = "DONE"
    HALT = "HALT"


class GateAction(str, Enum):
    PASS = "PASS"
    REPLAN = "REPLAN"
    HALT = "HALT"


class MemoryLayer(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class ModelConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    timeout_seconds: float = 30.0


class SessionConfig(BaseModel):
    topic: str = "rag"
    difficulty: str = "mid"
    rounds: int = Field(default=3, ge=1, le=20)
    profile_path: Path = Path("examples/resume_profile.yaml")
    knowledge_path: Path = Path("examples/knowledge_base.jsonl")
    run_root: Path = Path("runs")
    offline: bool = True
    max_replans: int = Field(default=1, ge=0, le=5)
    model: ModelConfig = Field(default_factory=ModelConfig)


class PlanStep(BaseModel):
    round_index: int
    topic: str
    dimension: str
    difficulty: str
    learning_goal: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionPlan(BaseModel):
    session_id: str = Field(default_factory=lambda: new_id("session"))
    candidate_name: str = "candidate"
    steps: list[PlanStep]


class GateDecision(BaseModel):
    action: GateAction
    reason: str
    audit: dict[str, Any] = Field(default_factory=dict)


class TranscriptEvent(BaseModel):
    session_id: str
    state: HarnessState
    actor: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now)


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem"))
    layer: MemoryLayer
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 1.0
    created_at: str = Field(default_factory=utc_now)


class RetrievalQuery(BaseModel):
    text: str
    topic: str | None = None
    difficulty: str | None = None
    top_k: int = Field(default=4, ge=1, le=20)


class RetrievedChunk(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float


class ToolSpec(BaseModel):
    name: str
    description: str
    allowed_agents: set[str] = Field(default_factory=set)


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tool"))
    agent: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    call_id: str
    name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
