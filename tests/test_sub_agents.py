from agent_harness.context import ContextBuilder
from agent_harness.llm import MockLLMClient
from agent_harness.mcp.gateway import build_default_gateway
from agent_harness.schemas import PlanStep, ToolCall
from agent_harness.sub_agents import ExaminerAgent, GraderAgent


def test_sub_agents_have_isolated_histories_and_tool_allow_lists():
    client = MockLLMClient()
    gateway = build_default_gateway({"highlights": ["RAG"], "projects": []})
    builder = ContextBuilder()
    examiner = ExaminerAgent(client, gateway, builder)
    grader = GraderAgent(client, gateway, builder)
    step = PlanStep(
        round_index=1,
        topic="rag",
        dimension="concept",
        difficulty="mid",
        learning_goal="test isolation",
    )

    question = examiner.generate_question(step=step, memories=[], evidence=[])
    grade = grader.grade_answer(step=step, question=question.content, answer="answer", memories=[], evidence=[])
    denied = gateway.call(ToolCall(agent="examiner", name="rubric_lookup"))

    assert examiner.history
    assert grader.history
    assert examiner.history is not grader.history
    assert "score:" in grade.content
    assert denied.success is False

