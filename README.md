# Course After-Sales Customer Support Agent Harness

This project is a local, runnable business prototype for a course-platform after-sales support scenario. It is not a SupportOps Evaluation framework, not a RAG benchmark, and not a GraphRAG benchmark.

The goal is to show how an Agent Harness can make risky customer-support actions controllable, verifiable, and replayable. DeepSeek API only generates customer-facing text. Intent routing, tool execution, policy evidence checks, risk gates, memory handling, and transcript replay are controlled by deterministic Harness code.

The covered business cases are course access failure, refund threats, invoice lookup, account security, and human escalation.

## Why This Needs An Agent Harness

A plain chatbot can answer generic support questions, but it cannot safely reset access, discuss refund eligibility, mention a ticket id, or guide invoice handling without checking business state and policy evidence.

This Harness makes those checks explicit:

- Router identifies the initial intent and routing signals.
- Skills Playbook defines risk level, required tools, and required policy topics.
- Monitor checks high-risk misrouting and policy evidence gaps.
- Resolver builds the reply from the current intent, retrieved policy evidence, and tool results.
- Risk Gate performs the final interception for unsafe business promises, PII leaks, ungrounded ticket ids, missing refund checks, missing invoice tools, and access-reset overclaims.
- Transcript files record route decisions, Monitor flags, tool results, Gate decisions, memory snapshots, and final answers.

## Tech Stack

Python, DeepSeek API, OpenAI-compatible API, RAG, local hash embedding, JSONL retrieval, metadata filter, Skills Playbook, MCP-like tool gateway, multi-agent workflow, Working/Episodic/Semantic/Procedural memory, Risk Gate/Replan, transcript replay, pytest.

The core support demo runs on the Python standard library. `pytest` is only needed for the test suite.

## Architecture

### Router / Monitor / Resolver

`SupportRouterAgent` produces the initial `RouteDecision`: intent, confidence, reason, and routing signals. It does not directly decide the risk level.

Risk level is defined by the deterministic Skills Playbook. `SupportMonitorAgent` mainly checks high-confidence wrong routes and missing policy topics. Tool-call absence, unsupported business commitments, refund eligibility without `refund_policy_check`, missing `invoice_create`, ticket-id grounding, and PII leakage are finally blocked by `gate_support_response`.

### RAG + Skills Playbook

The knowledge base is JSONL policy data. Retrieval follows:

```text
embedding -> vector search -> metadata filter -> dedupe -> difficulty rerank -> policy-topic backfill
```

The Skills Playbook maps each intent to required policy topics and tools:

- `refund_request`: identity + refund policy, `refund_policy_check`
- `access_issue`: identity + access recovery, `access_reset`
- `invoice_request`: identity + invoice policy, order lookup only
- `account_security`: identity + security policy, escalation
- `escalate`: human-review ticket

`support-eval` is an end-to-end business regression check built from known bad cases. It is not a benchmark and should not be described as SupportOpsBench, Recall@5, Precision@5, or leaderboard evaluation.

### MCP-like Gateway

The project uses an in-process MCP-like gateway, not the real MCP SDK or a production MCP server. It models the engineering contract that matters here: tool specs, agent allow-lists, auditable tool results, and side-effect control.

Mock business tools:

- `customer_lookup`
- `order_lookup`
- `access_reset`
- `refund_policy_check`
- `escalation_ticket`

All user, order, invoice, and ticket data are synthetic mock data. They are not real user logs, real orders, or real platform records.

### Risk Gate / PII Guard / Grounding Guard

The final Gate can block or replan when:

- A tool fails but the answer still promises success.
- The answer discusses refund eligibility without a successful `refund_policy_check`.
- The answer promises invoice issuance even though this Harness has no `invoice_create` tool.
- The answer invents or rewrites an escalation ticket id.
- The answer leaks raw order ids or full email addresses.
- The answer claims `access_reset` has definitely solved the user's local access problem.

PII Guard protects user-visible customer replies. It is not a complete transcript redaction system: transcripts intentionally keep synthetic internal tool payloads so the run can be replayed and audited.

### Memory

The memory store has four layers:

- Working memory: recent user turns.
- Episodic memory: route and resolution events.
- Semantic memory: compacted long-dialog facts.
- Procedural memory: repair rules learned from Gate failures.

This supports cases such as the user later saying "still cannot enter" while also reducing old access-issue memory pollution when the current turn is clearly about invoice or refund.

### Replay Artifacts

Each support run writes:

- `runs/<session>/transcript.jsonl`
- `runs/<session>/memory_snapshot.json`
- `runs/<session>/support_report.md`

These artifacts are the main interview evidence for route correction, RAG evidence coverage, tool grounding, Gate decisions, and bad-case repair.

## Quick Start

Create `.env` in the project root:

```env
AGENT_HARNESS_BASE_URL=https://api.deepseek.com
AGENT_HARNESS_API_KEY=your_deepseek_api_key
AGENT_HARNESS_CHAT_MODEL=deepseek-v4-flash
AGENT_HARNESS_EMBEDDING_MODEL=local-hash
```

Run the offline demo:

```powershell
python -m agent_harness support --offline --knowledge examples/support_augmented_kb.jsonl
```

Run the online DeepSeek demo:

```powershell
python -m agent_harness support --online --knowledge examples/support_augmented_kb.jsonl
```

Run tests and regression evaluation:

```powershell
python -m pytest
python -m agent_harness support-eval --output runs\eval\support_eval.json
```

## Streamlit Demo

The repository also includes a lightweight Streamlit page for interview and resume demos. It is only a display layer and does not change the core Agent Harness behavior.

Install Streamlit when you want to run the UI:

```powershell
pip install streamlit
streamlit run demo_app.py
```

The page provides preset customer cases and manual input. After `Run Harness`, it shows:

- Final customer response.
- Raw route and final intent.
- RAG evidence retrieved for each turn.
- MCP-like tool calls and tool results.
- Risk Gate decisions.
- Working/Episodic/Semantic/Procedural memory summary.
- Full transcript JSON.

Current local verification:

```text
pytest: 23 passed
support-eval: 3/3 passed
```

## Public Data Ingestion

The project can optionally ingest a public Hugging Face Bitext customer-support dataset. It is used only as public utterance/response examples, not as real user logs or real platform policy.

```powershell
python scripts\ingest_bitext_public.py --download --limit 500 --merge-policy-kb
```

Generated files:

- `examples/public_support_utterances.jsonl`
- `examples/support_augmented_kb.jsonl`
- `data/source_registry/bitext_customer_support.json`

## Evidence Boundaries

Safe claims:

- Local runnable course-support Agent Harness prototype.
- DeepSeek online demo for customer-facing response generation.
- Router / Monitor / Resolver workflow.
- RAG policy-topic coverage and metadata backfill.
- Skills Playbook for intent-specific risk, required tools, and required policy topics.
- MCP-like in-process tool gateway with allow-list and audit.
- Risk gates for PII, invoice promise, refund eligibility, ticket id grounding, and access reset overclaim.
- Four-layer memory and working-memory compaction.
- End-to-end regression tests and `support-eval`.

Do not claim:

- Production deployment.
- Real users, real order data, or real invoice records.
- Full MCP SDK/server integration.
- GraphRAG or SupportOps benchmark results.
- Formal answer-faithfulness proof. Resolver grounding is constrained by prompt contract, Gate rules, and regression tests.
- High concurrency.
- Completed LoRA/SFT training.
- Accuracy, cost, or latency improvement percentages without a measured baseline.

## Key Files

- `agent_harness/control_plane/support_runner.py`: support workflow control plane.
- `agent_harness/control_plane/support_gates.py`: Risk Gate, PII Guard, and grounding checks.
- `agent_harness/sub_agents/support_agents.py`: Router, Monitor, Resolver.
- `agent_harness/skills/support_playbooks.py`: deterministic business playbooks.
- `agent_harness/mcp/support_gateway.py`: MCP-like business tools.
- `agent_harness/memory/store.py`: four-layer memory.
- `agent_harness/rag/store.py`: JSONL vector store and retrieval pipeline.
- `agent_harness/evaluation/support_eval.py`: business regression evaluation, not a benchmark.
- `docs/online_validation_notes.md`: online bad cases and fixes.
- `docs/data_ingestion.md`: safe public-data ingestion boundary.
- `output/12_final_resume_agent_harness.md`: resume-ready project content.
