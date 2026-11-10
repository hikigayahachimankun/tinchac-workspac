# T05 preflight follow-up — technical self-review

What this change does: It loads the designated private key without running shell text, inspects public model metadata, and makes the authorized three-attempt/three-cent internal budget durable. Generation remains unexecuted because actual billing/quota access is unavailable.

Scope/load: one local owner, one durable SQLite ledger; concurrent/retried provider attempts must share the same allowance. Read callers in preflight, verification_dev, HTTP Jobs and eval harness, and SDK retry/accounting behavior. No API/schema/frontend/corpus change.

Checked: key fd ownership/mode/type/no symlink and literal parsing; additional env assignments are ignored, never evaluated or exported. HTTP key only in a header to the fixed HTTPS Google host; no redirect/raw-error/body/header echo or secret hash. Metadata200 does not certify billing or inference. The actual secret file was not modified.

Budget registration is transactional and immutable across restart. Reserve reads registered limits from SQLite even when a caller omits max_calls, sums unknown held charges, and retains independent global/stage limits. Concurrent two-cent reservations cannot exceed the three-cent run allowance. Retry/re-entry share one stable preflight ID; changing its cap, call limit or pricing/model is rejected. The CLI exposes the stable ID/cap and optional safe secret file, and the CLI additionally requires a fresh matching-model genuine billing/quota readiness receipt; no generation command was executed with the current unverified account.

353 backend/eval tests passed; contract export31examples/no drift and real corpus validation pass. Source/secret tests use synthetic keys, not the owner's file. Only the single explicit read-only metadata command used the owner's key. Provider compatibility/usage tests are mocks and are not relabeled as live.

Verdict: Ship the offline safety/metadata changes on the follow-up branch. Full T05 remains blocked on authenticated billing/quota verification and actual capped generation compatibility/usage reconciliation. No public release/deployment or payment action.
