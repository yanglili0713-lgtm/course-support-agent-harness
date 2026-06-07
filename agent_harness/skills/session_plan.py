from __future__ import annotations

from agent_harness.schemas import PlanStep, SessionConfig, SessionPlan


DIMENSIONS = ["concept", "system_design", "debugging", "evaluation", "tradeoff"]


def build_session_plan(config: SessionConfig, profile: dict) -> SessionPlan:
    """Build a deterministic plan without asking the LLM.

    Skills are the right home for reproducible planning rules. The Harness can
    audit why a session asked each dimension instead of reverse-engineering a
    hidden model choice.
    """

    preferred = profile.get("target_dimensions") or DIMENSIONS
    steps: list[PlanStep] = []
    for index in range(config.rounds):
        dimension = preferred[index % len(preferred)]
        steps.append(
            PlanStep(
                round_index=index + 1,
                topic=config.topic,
                dimension=dimension,
                difficulty=config.difficulty,
                learning_goal=f"Validate {config.topic} knowledge through {dimension} evidence.",
                metadata={"skill": "deterministic_session_plan", "source": "profile+config"},
            )
        )
    return SessionPlan(candidate_name=profile.get("name", "candidate"), steps=steps)

