from agent_harness.control_plane.gates import extract_score, gate_grade, gate_question
from agent_harness.schemas import GateAction


def test_question_gate_requests_replan_for_empty_question():
    decision = gate_question("", tool_audit=[], round_index=1)

    assert decision.action == GateAction.REPLAN


def test_question_gate_halts_on_failed_tool():
    decision = gate_question("这是一个足够长的问题吗？", tool_audit=[{"success": False}], round_index=1)

    assert decision.action == GateAction.HALT


def test_grade_gate_extracts_score():
    assert extract_score("score: 88\nstrengths: ok") == 88

    decision = gate_grade("score: 88\nstrengths: ok", tool_audit=[{"success": True}], round_index=1)

    assert decision.action == GateAction.PASS

