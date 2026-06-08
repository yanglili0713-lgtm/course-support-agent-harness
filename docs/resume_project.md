# CourseSupport-AgentHarness - Resume Summary

Project URL: https://github.com/yanglili0713-lgtm/course-support-agent-harness

Tech stack: Python / RAG / Tool Calling / Agent Workflow / Memory / Risk Gate / Streamlit / Evaluation / Pytest

Truth boundary: all numbers below are deterministic local evaluation results on synthetic mock data. They are
not production metrics.

- Built CourseSupport-AgentHarness for online course after-sales support, targeting access failures, refund threats, invoice requests, account security, PII leakage, and human escalation. Designed a Router-Monitor-Resolver control flow with an MCP-like tool gateway, policy matrix, Risk Gate, memory handling, and transcript replay to constrain unsupported business commitments.
- Constructed an 80-case deterministic CourseSupportBench covering `tool_required`, `pii_safety`, `refund_commitment`, `invoice`, `no_tool_grounding`, `ticket_grounding`, and 10 memory-stress cases. Compared `llm_only`, `rag_only`, `agent_harness_without_gate`, and `agent_harness`, and generated `metrics_summary`, `risk_tag_summary`, `failure_reason_summary`, `failure_cases`, and `transcripts` for replay.
- Encoded support rules as a risk policy matrix with `required_tools`, `required_policy_topics`, `forbidden_claims`, and fallback actions, then combined it with role-based tool allowlists for Router / Monitor / Resolver. This prevents refund eligibility claims without `refund_policy_check`, invoice claims without grounding, fake ticket ids, and raw order/email/phone leakage.
- In deterministic local evaluation, the full Agent Harness achieved `pass_rate = 1.00`, `tool_grounding_rate = 1.00`, `policy_coverage_rate = 1.00`, `gate_action_accuracy = 1.00`, and reduced `risk_violation_rate` from 1.00 in baseline modes to 0.00; memory stress reached `context_carryover_accuracy = 1.00`, `intent_switch_accuracy = 1.00`, and `memory_pollution_rate = 0.00`.
