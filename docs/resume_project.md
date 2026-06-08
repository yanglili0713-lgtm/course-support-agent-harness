# CourseSupport-AgentHarness - Resume Summary

Project URL: https://github.com/yanglili0713-lgtm/course-support-agent-harness

Tech stack: Python / RAG / Tool Calling / Agent Workflow / Memory / Risk Gate / Streamlit / Evaluation / Pytest

Note: all metrics below come from the deterministic offline CourseSupportBench in this repository.

- Built a controllable agent harness for online course after-sales support, covering access failures, refund threats, invoice requests, account security, and human escalation. Designed a Router-Monitor-Resolver control flow, an MCP-like tool gateway, a risk gate, four-layer memory, and transcript replay to prevent unsupported business commitments.
- Built a 53-case deterministic CourseSupportBench evaluation set covering access, refund, invoice, escalation, PII leakage, missing tools, false commitments, and memory pollution. Compared four modes: `llm_only`, `rag_only`, `agent_harness_without_gate`, and `agent_harness`, with outputs saved to `metrics_summary.csv`, `failure_cases.jsonl`, and `transcripts.jsonl`.
- Abstracted support constraints into a risk policy matrix that centrally manages `required_tools`, `required_policy_topics`, `forbidden_claims`, and fallback actions. Combined this with MCP-like tool permissions to restrict Router / Monitor / Resolver access and avoid unverified order queries, refund commitments, invoice claims, and PII leakage.
- In deterministic evaluation, the full Agent Harness reduced `risk_violation_rate` from 1.00 to 0.00, achieved `tool_grounding_rate = 1.00`, `policy_coverage_rate = 1.00`, and `gate_action_accuracy = 1.00`, and on 8 memory-stress cases achieved `context_carryover_accuracy = 1.00`, `intent_switch_accuracy = 1.00`, and `memory_pollution_rate = 0.00`.
