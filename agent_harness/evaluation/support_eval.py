from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_harness.business.support_schemas import SupportConfig, SupportIntent
from agent_harness.control_plane.support_gates import EMAIL_PATTERN, RAW_ORDER_PATTERN
from agent_harness.control_plane.support_runner import SupportHarnessRunner
from agent_harness.llm import MockLLMClient
from agent_harness.skills.support_playbooks import get_playbook


@dataclass(frozen=True)
class EvalCase:
    name: str
    messages: list[str]
    expected_final_intent: SupportIntent
    expected_flag: str | None = None
    expected_raw_route: SupportIntent | None = None


CASES = [
    EvalCase(
        name="refund_threat_is_access_issue",
        messages=["我昨天买的 RAG 实战课今天打不开了，再不解决我就要退款。"],
        expected_final_intent=SupportIntent.ACCESS_ISSUE,
        expected_flag="route_corrected:refund_threat_to_access_issue",
        expected_raw_route=SupportIntent.REFUND_REQUEST,
    ),
    EvalCase(
        name="plain_invoice",
        messages=["帮我看一下发票什么时候能开。"],
        expected_final_intent=SupportIntent.INVOICE_REQUEST,
        expected_flag=None,
    ),
    EvalCase(
        name="security_escalation",
        messages=["我的账号好像被盗了，邮箱也被改了。"],
        expected_final_intent=SupportIntent.ACCOUNT_SECURITY,
        expected_flag=None,
    ),
]


def run_support_eval(output_path: Path | None = None) -> dict:
    """Run a tiny end-to-end regression suite.

    This is not a benchmark. It is a guardrail suite built from incidents that
    matter to this business workflow.
    """

    results = []
    totals = {
        "route_expected": 0,
        "route_match": 0,
        "final_intent_match": 0,
        "required_flag_match": 0,
        "required_flag_total": 0,
        "tool_calls": 0,
        "tool_success": 0,
        "policy_coverage": 0,
        "pii_safe": 0,
    }
    for case in CASES:
        config = SupportConfig(run_root=Path("runs") / "eval", offline=True)
        runner = SupportHarnessRunner(config, MockLLMClient())
        result = runner.run(case.messages)
        last = result.turns[-1]
        final_intent_match = last.final_intent == case.expected_final_intent
        passed = final_intent_match
        if case.expected_flag:
            totals["required_flag_total"] += 1
            flag_match = case.expected_flag in last.monitor_flags
            totals["required_flag_match"] += int(flag_match)
            passed = passed and flag_match
        route_match = None
        if case.expected_raw_route:
            totals["route_expected"] += 1
            route_match = last.route.intent == case.expected_raw_route
            totals["route_match"] += int(route_match)
        tool_success = sum(1 for item in last.tool_results if item.get("success"))
        tool_total = len(last.tool_results)
        coverage = _has_policy_coverage(result.run_dir / "transcript.jsonl", case.expected_final_intent)
        pii_safe = not RAW_ORDER_PATTERN.search(last.answer) and not EMAIL_PATTERN.search(last.answer)
        totals["final_intent_match"] += int(final_intent_match)
        totals["tool_calls"] += tool_total
        totals["tool_success"] += tool_success
        totals["policy_coverage"] += int(coverage)
        totals["pii_safe"] += int(pii_safe)
        results.append(
            {
                "name": case.name,
                "passed": passed,
                "expected_raw_route": case.expected_raw_route.value if case.expected_raw_route else None,
                "raw_route_match": route_match,
                "expected_final_intent": case.expected_final_intent.value,
                "actual_final_intent": last.final_intent.value,
                "monitor_flags": last.monitor_flags,
                "tool_success": tool_success,
                "tool_total": tool_total,
                "policy_coverage": coverage,
                "pii_safe": pii_safe,
                "run_dir": str(result.run_dir),
            }
        )
    summary = {
        "passed": sum(1 for item in results if item["passed"]),
        "total": len(results),
        "metrics": _metrics(totals, len(results)),
        "results": results,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _metrics(totals: dict[str, int], case_count: int) -> dict[str, float]:
    return {
        "final_intent_accuracy": _ratio(totals["final_intent_match"], case_count),
        "raw_route_expected_accuracy": _ratio(totals["route_match"], totals["route_expected"]),
        "required_monitor_flag_recall": _ratio(totals["required_flag_match"], totals["required_flag_total"]),
        "tool_success_rate": _ratio(totals["tool_success"], totals["tool_calls"]),
        "policy_coverage_rate": _ratio(totals["policy_coverage"], case_count),
        "pii_safe_rate": _ratio(totals["pii_safe"], case_count),
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


def _has_policy_coverage(transcript_path: Path, intent: SupportIntent) -> bool:
    required = set(get_playbook(intent).required_policy_topics)
    found: set[str] = set()
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event_type") == "support_response_gate":
            found.update(event["payload"].get("policy_topics_found", []))
    return required.issubset(found)
