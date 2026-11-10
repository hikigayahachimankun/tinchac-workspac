# Gemini Free Tier readiness and ledger

Current state, **10/11/2026**: the owner confirms the key's project is Free Tier and reports approximately15RPM /250000inputTPM /500RPD in AI Studio. This is an owner attestation, not an authenticated console scrape. No billing was enabled, no credit purchased and no paid service used. Public [pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite) and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) were retrieved with HTTP200: model input/output are free on Free Tier, quotas are project-scoped and daily limits reset at Pacific midnight. Exact remaining account-wide quota is not visible to this process.

**Actual preflight passed:3generation attempts,859input /1126output tokens including thoughts,3validated structured outputs.** The actual model version returned `gemini-3.5-flash-lite`; temperature0 /MINIMAL thinking /SDK3.0.0 worked. Estimated Free Tier generation charge is0USD; this is not an invoice or an audit of unrelated project activity. Receipts: `docs/evidence/T05/free-tier-owner-authorization-2026-11-10.json` and `free-tier-preflight-2026-11-10.jsonl`. Older metadata-only/billing-blocked receipts remain historical and are superseded for authorized Free Tier use.

## Safe secret use

The configured file is `~/.config/tinchac/gemini.env`, outside Git, owner-only0600. `scripts.provider_check.load_key` reads it as data into SecretStr using a no-symlink regular-file ownership/mode/size check. It accepts one literal GEMINI_API_KEY assignment and ignores other assignments. Never source/eval the file, export or print the key, hash it, pass it on a subprocess command line, log headers/error bodies, or commit it. No secret setup change is currently needed.

`Settings(_env_file=None)` prevents accidental workspace .env loading. Live CLIs accept `--secret-file` and `--readiness-report`; no process export is needed. `account_mode` accepts either a fresh matching-model genuine verified-paid receipt or the owner's explicitly identified Free Tier attestation. These are distinct: `billing_verified` and `quota_verified` remain false in the owner receipt; model metadata alone authorizes neither. Paid mode has no authorization in this session.

## Do not rerun the consumed preflight

The authorized stable run ID `tinchac-preflight-2026-11-10-cap-0p03usd` has consumed **all3attempts** in `data/private/tinchac-live.sqlite3`. Its immutable SQLite limit is3attempts/0.03USD including retries. Do not reset/remove the DB, change the run ID/stage/model/prices or copy counters to obtain more preflight calls. This preflight gate is closed successfully, not replenished by a new CLI invocation.

The owner separately permits subsequent Free Tier recovery after successful preflight, subject to project stage/global caps, quota and freeze. The twelve-case public HTTP suite is separate DEV QA, not a fourth preflight sample or benchmark. Global HTTP remains disabled by default (`LLM_LIVE_ENABLED=false`); the explicit local public QA runner enables it only inside its own TestClient process.

## Quota and accounting controls

`LLM_BILLING_MODE=free_tier` records known successful token usage with0estimated charge, while retaining conservative paid-equivalent reservations at0.30/2.50USD per million. Unknown attempts keep their reservation and cannot be reported as zero tokens/cost. The ledger enforces global<=3USD, dev<=0.8USD, evaluation<=1.4USD, demo<=0.8USD. Paid-equivalent holds are internal protection, not actual Free Tier charges.

All attempts, including failures, count in shared-ledger15RPM /250000conservative inputTPM /500Pacific-day RPD; sequential calls wait about5seconds. Other apps may use the same project, so the local ledger cannot guarantee remaining cloud quota. On provider403/404/429, no retry or paid fallback occurs; the durable refusal also blocks later Free Tier runs across restarts. Stop and record the blocker; do not delete the refusal to continue. General503/timeout retains the existing at-most-one retry and unknown accounting; a recovered retry does not hide an unknown earlier attempt.

No sealed test/gold, private images or URL supplied by an end user is sent to this Free Tier smoke. Freeze/data/human gates in `eval/protocol.md` still apply. See T05/T08/T12 handoffs for actual public QA outcomes, including failed runs; do not replace them with fixture/replay results.
