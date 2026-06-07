# Demo Guide

## Standard Demo

```powershell
python -m agent_harness support --online
```

Expected behavior:

- Turn 1: refund threat is corrected from `refund_request` to `access_issue`.
- Turn 2: repeated access failure creates a grounded escalation ticket.
- Turn 3: invoice lookup stays within tool boundaries and asks the user to submit invoice information on the platform order page.
- Final state should be `DONE`.

Generated artifacts:

- `runs/<support_session>/transcript.jsonl`
- `runs/<support_session>/memory_snapshot.json`
- `runs/<support_session>/support_report.md`

## Augmented KB Demo

```powershell
python scripts\ingest_bitext_public.py --download --limit 500 --merge-policy-kb
python -m agent_harness support --online --knowledge examples/support_augmented_kb.jsonl
```

The public Bitext dataset is used only for public support utterance examples. Real customer, order, and ticket data remain synthetic.

## Evaluation

```powershell
python -m agent_harness support-eval --output runs\eval\support_eval.json
```

Metrics include:

- final intent accuracy
- raw route expected accuracy
- required monitor flag recall
- tool success rate
- policy coverage rate
- PII safe rate

## Tests

```powershell
python -m pytest
```

Current coverage includes routing correction, RAG filtering/backfill, tool allow-listing, PII gate, invoice/refund/ticket grounding, access reset overclaim, memory compaction, public data ingestion, and full runner smoke tests.

## Resume Boundary

Safe wording:

```text
Local runnable Agent Harness prototype with DeepSeek online demo, transcript replay, support-eval, and risk gates for high-risk customer-support actions.
```

Unsafe wording:

```text
Production customer-service system, real user data, completed fine-tuning, high concurrency, or accuracy improvement percentage.
```

