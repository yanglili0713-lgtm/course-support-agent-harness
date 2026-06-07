# Online Validation Notes

## 2026-06-07 DeepSeek Online Run

User challenged whether the online output was actually correct. The challenge was valid: the first successful online run exposed model behavior that looked fluent but was not fully grounded by tools.

## Fixes Made

1. Invoice over-promise:
   - Problem: the model said it could issue or process an invoice, but the Harness has no `invoice_create` tool.
   - Fix: added invoice promise gate and invoice data collection gate.
   - Result: invoice answers must tell the user to submit invoice application info in the platform order page.

2. Unsupported ticket promise:
   - Problem: the model said an escalation ticket had been created when the tool chain had not created one.
   - Fix: repeated access failure now calls `escalation_ticket` after `access_reset`.
   - Result: ticket promises are backed by tool results.

3. Ticket id grounding:
   - Problem: the model can alter ticket ids, such as turning `T0001` into `002`.
   - Fix: if the answer mentions a ticket id, Gate verifies it matches the `escalation_ticket` tool result exactly.

4. Access routing gap:
   - Problem: the Router did not treat `进不去` as an access issue in a single-turn test.
   - Fix: added `进不去` to access routing signals.

5. Invoice promise variant:
   - Problem: the model avoided direct "开具" wording but still said `我们会为您安排开具`.
   - Fix: extended invoice promise Gate to catch `安排开具 / 会为您安排开具`.

6. Refund eligibility claim without refund tool:
   - Problem: in an access recovery turn, the model inferred refund eligibility from order fields without calling `refund_policy_check`.
   - Fix: added refund eligibility Gate. Claims like `符合条件 / 可进入退款审核 / 可退款` require a successful `refund_policy_check` tool result.

## Verification

```powershell
python -m pytest
# 17 passed

python -m agent_harness support --online
# Finished: DONE
# Run dir: runs\support_9ad1fc65aedb
```

In the latest online run, the invoice turn triggered:

```text
response_replanned:unsupported ticket promise
rag_backfill:invoice,identity
```

This is expected. It means the Harness caught an unsafe draft and forced a safer final answer.

## Follow-up Fix: HALT After Single Repair

One online run ended with:

```text
Finished: HALT
```

Root cause:

- Turn 3 first draft promised unsupported invoice creation.
- The first repair draft then mentioned a ticket promise that was not grounded in the current turn's tool results.
- The old runner allowed only one repair attempt after the first failed Gate, so it halted.

Fix:

- `SupportConfig.max_replans` default changed to `2`.
- `SupportHarnessRunner` now performs a bounded repair loop.
- Resolver prompt now says to answer only the current intent and avoid carrying old refund/access/ticket context into unrelated turns.
- Added `test_support_runner_repairs_multiple_unsafe_drafts`.

Latest verification:

```powershell
python -m pytest
# 18 passed

python -m agent_harness support --online
# Finished: DONE
# Run dir: runs\support_84b8c0ef5f6e
```

## Follow-up Fix: Access Reset Overclaim

After running the augmented public-data KB, the online model said the user could now reopen the course after `access_reset`.

Root cause:

- `access_reset` only proves the backend token was refreshed.
- It does not prove the user's browser/session/device can access the course.

Fix:

- Added `ACCESS_RESOLVED_OVERCLAIM_PATTERN`.
- Access answers can say the token was refreshed and ask the user to retry after re-login.
- Access answers must not claim the issue is solved or that the user can now definitely open the course.

Latest verification:

```powershell
python -m pytest
# 23 passed

python -m agent_harness support --online --knowledge examples/support_augmented_kb.jsonl
# Finished: DONE
# Run dir: runs\support_bd8f3e7910d9

python -m agent_harness support-eval --output runs\eval\support_eval_after_data.json
# Support eval: 3/3 passed
```
