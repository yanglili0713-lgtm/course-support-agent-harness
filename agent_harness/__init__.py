"""Agent Harness reference implementation.

This package deliberately separates deterministic orchestration from LLM text
generation. The Harness owns state transitions, memory, retrieval, tool access,
and audit logs; the model adapter is only one replaceable dependency.
"""

from agent_harness.schemas import HarnessState, SessionConfig

__all__ = ["HarnessState", "SessionConfig"]

