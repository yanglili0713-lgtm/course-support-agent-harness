from pathlib import Path

from agent_harness.business.support_schemas import SupportConfig, SupportIntent
from agent_harness.control_plane.support_gates import gate_support_response
from agent_harness.control_plane.support_runner import SupportHarnessRunner
from agent_harness.evaluation.support_eval import run_support_eval
from agent_harness.llm import MockLLMClient
from agent_harness.memory import MemoryStore
from agent_harness.schemas import GateAction, MemoryLayer


def test_support_monitor_corrects_high_confidence_refund_threat_route(tmp_path):
    runner = SupportHarnessRunner(_config(tmp_path), MockLLMClient())

    result = runner.run(["我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。"])

    turn = result.turns[0]
    assert turn.route.intent == SupportIntent.REFUND_REQUEST
    assert turn.final_intent == SupportIntent.ACCESS_ISSUE
    assert "route_corrected:refund_threat_to_access_issue" in turn.monitor_flags
    assert result.report_path.exists()


def test_support_gate_blocks_raw_order_id_leak():
    decision = gate_support_response(
        intent=SupportIntent.ACCESS_ISSUE,
        answer="你的订单 ord_rag_20260601_8899 已恢复。",
        tool_results=[{"success": True}],
        policy_topics_found=["access", "identity"],
    )

    assert decision.action == GateAction.HALT


def test_invoice_gate_replans_unsupported_invoice_promise():
    decision = gate_support_response(
        intent=SupportIntent.INVOICE_REQUEST,
        answer="您回复抬头后，我将为您开具发票。",
        tool_results=[{"success": True}],
        policy_topics_found=["invoice", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "unsupported invoice action promise"


def test_invoice_gate_replans_arrange_invoice_promise():
    decision = gate_support_response(
        intent=SupportIntent.INVOICE_REQUEST,
        answer="请您登录平台订单页面提交发票申请信息，我们会为您安排开具。",
        tool_results=[{"success": True}],
        policy_topics_found=["invoice", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "unsupported invoice action promise"


def test_invoice_gate_replans_invoice_data_collection_without_tool():
    decision = gate_support_response(
        intent=SupportIntent.INVOICE_REQUEST,
        answer="请提供发票抬头和纳税识别号，我会继续处理。",
        tool_results=[{"success": True}],
        policy_topics_found=["invoice", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "unsupported invoice data collection"


def test_gate_replans_refund_eligibility_without_refund_tool():
    decision = gate_support_response(
        intent=SupportIntent.ACCESS_ISSUE,
        answer="当前购买 1 天且进度 12%，符合条件。",
        tool_results=[{"success": True, "name": "access_reset"}],
        policy_topics_found=["access", "identity", "refund"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "unsupported refund eligibility claim"


def test_gate_replans_access_reset_overclaim():
    decision = gate_support_response(
        intent=SupportIntent.ACCESS_ISSUE,
        answer="权限已刷新，现在您可以重新打开课程。",
        tool_results=[{"success": True, "name": "access_reset"}],
        policy_topics_found=["access", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "access reset overclaimed as resolved"


def test_gate_replans_ticket_promise_without_ticket_tool():
    decision = gate_support_response(
        intent=SupportIntent.ACCESS_ISSUE,
        answer="已将问题升级至人工复核工单。",
        tool_results=[{"success": True, "name": "access_reset"}],
        policy_topics_found=["access", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "unsupported ticket promise"


def test_gate_replans_inconsistent_ticket_id():
    decision = gate_support_response(
        intent=SupportIntent.ACCESS_ISSUE,
        answer="已创建工单，工单编号 002。",
        tool_results=[{"success": True, "name": "escalation_ticket", "data": {"ticket_id": "T0001"}}],
        policy_topics_found=["access", "identity"],
    )

    assert decision.action == GateAction.REPLAN
    assert decision.reason == "ticket id not grounded in tool result"


def test_working_memory_compaction_preserves_old_context_as_semantic_memory():
    store = MemoryStore()
    for index in range(6):
        store.add(MemoryLayer.WORKING, f"turn_{index}: access_issue still unresolved", kind="user_message")

    promoted = store.compact_working_memory(keep_last=4)

    assert len(store.list(MemoryLayer.WORKING)) == 4
    assert promoted[0].layer == MemoryLayer.SEMANTIC
    assert "access_issue" in promoted[0].content


def test_support_eval_suite_passes(tmp_path):
    summary = run_support_eval(tmp_path / "support_eval.json")

    assert summary["passed"] == summary["total"]


def test_explicit_intent_wins_over_old_memory_terms(tmp_path):
    runner = SupportHarnessRunner(_config(tmp_path), MockLLMClient())

    result = runner.run(
        [
            "我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。",
            "如果能打开就不用退了，顺便帮我看下发票什么时候能开。",
        ]
    )

    invoice_turn = result.turns[-1]
    assert invoice_turn.final_intent == SupportIntent.INVOICE_REQUEST
    assert "发票" in invoice_turn.answer
    assert "刷新了课程访问权限" not in invoice_turn.answer


def test_repeated_access_failure_creates_escalation_ticket(tmp_path):
    runner = SupportHarnessRunner(_config(tmp_path), MockLLMClient())

    result = runner.run(["刚才还是进不去，你们是不是把我的账号弄错了？"])

    tool_names = [item["name"] for item in result.turns[0].tool_results]
    assert "access_reset" in tool_names
    assert "escalation_ticket" in tool_names


def test_support_runner_repairs_multiple_unsafe_drafts(tmp_path):
    runner = SupportHarnessRunner(_config(tmp_path), MultiRepairClient())

    result = runner.run(["顺便帮我看下发票什么时候能开。"])

    assert result.state.value == "DONE"
    assert result.turns[0].final_intent == SupportIntent.INVOICE_REQUEST
    assert "平台订单页面" in result.turns[0].answer
    assert any("unsupported invoice action promise" in flag for flag in result.turns[0].monitor_flags)
    assert any("unsupported ticket promise" in flag for flag in result.turns[0].monitor_flags)


def _config(tmp_path: Path) -> SupportConfig:
    return SupportConfig(
        run_root=tmp_path,
        knowledge_path=Path("examples/support_policy_kb.jsonl"),
        customer_db_path=Path("examples/support_customers.yaml"),
        offline=True,
    )


class MultiRepairClient(MockLLMClient):
    def __init__(self):
        self.responses = [
            "我将为您开具发票。",
            "已创建工单，请等待处理。",
            "当前发票未申请，请登录平台订单页面提交发票申请信息。",
        ]

    def chat(self, messages, *, temperature=0.2):
        prompt = "\n".join(message.content for message in messages)
        if "Support Resolver Agent" in prompt:
            return self.responses.pop(0)
        return super().chat(messages, temperature=temperature)
