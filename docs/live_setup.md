# Gemini readiness and bounded preflight

Current state, **10/11/2026**: outside-repo key loaded safely; read-only model metadata GET returned200 for `gemini-3.5-flash-lite`, with generateContent advertised. **Billing, active quota, inference/structured-output compatibility and actual account charges are not verified. Zero generation attempts were made.** D02 remains blocked. Receipts: `docs/evidence/T05/account-readiness-2026-11-10-02.json` (current), `account-readiness-2026-11-10.json` (initial parser refusal, before metadata request).

The user's conditional authorization covers at most3generation attempts including retries/repairs, <=0.03USD. It does not permit billing setup, top-up, plan upgrade, other live cases or a paid request while billing is unverified. HTTP remains LLM_LIVE_ENABLED=false.

## Secret loading

The secret is at `~/.config/tinchac/gemini.env` in WSL, with owner-only permissions. Do not recreate it or paste its value in chat. `scripts.provider_check.load_key` opens a private regular file with no symlink following, checks ownership/mode/size, extracts exactly one literal GEMINI_API_KEY assignment and returns SecretStr. Other variable assignments are ignored. No shell sourcing, expansion, subprocess key argument, environment export, key hash, header logging or error-body dump occurs. Initial refusal of the owner's additional env assignment was fixed without changing the file.

Read-only check, using a **new receipt filename** each time:

```bash
.venv/bin/python -m scripts.provider_check \
  --report data/private/gemini-readiness-new.json
```

This command only performs a model metadata GET, with key in a header and redirects disabled. It returns exit2 while billing/quota are unverified. A200metadata response is not a successful generation or evidence of a paid plan/remaining quota. It does not initialize/reset the ledger or modify the owner's secret/billing settings.

## Billing blocker

Public docs were rechecked successfully: [pricing](https://ai.google.dev/gemini-api/docs/pricing), [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [billing](https://ai.google.dev/gemini-api/docs/billing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Cloud Billing getBillingInfo](https://docs.cloud.google.com/billing/docs/reference/rest/v1/projects/getBillingInfo).

Published Standard prices still match defaults:0.30USD input /2.50USD output per million, including thoughts. This does not establish the account's billing plan, credits, taxes, active quota or key-project billing association. Cloud Billing getBillingInfo needs an authenticated Google Cloud principal and project permission, not merely a Gemini key. Current WSL has neither gcloud nor application-default credentials; available connected tools and plugin discovery supplied no suitable authenticated Cloud Billing/AI Studio reader. No unrelated account connector was installed.

Remaining required access is an authenticated read-only view of the key's project billing/AI Studio status and quota. Do not fabricate a receipt or flip model_verified/billing_verified from metadata success. Provider project spending caps can lag; they are not a0.03USD real-time guarantee. Until actual billing is verified, **do not execute the generation command below**.

## Prepared generation command — NOT executed

After actual account/billing/quota and pricing verification, with the same durable ledger and no reset:

```bash
APP_MODE=live DATABASE_PATH=./data/private/tinchac-live.sqlite3 \
LLM_BUDGET_USD=3 LLM_LIVE_ENABLED=false \
  .venv/bin/python -m scripts.preflight --model-check \
  --secret-file "$HOME/.config/tinchac/gemini.env" \
  --run-id tinchac-preflight-2026-11-10-cap-0p03usd \
  --max-calls 3 --max-cost-usd 0.03 \
  --readiness-report data/private/gemini-account-verified.json
```

The CLI requires a fresh (<=24h), matching-model account readiness receipt with actual billing/quota verification before it loads the secret or initializes provider/ledger. The maintainer must produce that receipt from genuine authenticated account reads; do not create it by editing metadata-only false flags. Current metadata receipts cannot authorize generation.

Preflight now registers immutable run limits in SQLite and uses this stable authorization ID by default. Each retry/reservation shares the same total call/cost allowance. Restart/re-entry cannot clear calls, release unknown charges, raise the cap, change registered pricing/model, or move the allowance to another stage. Global<=3USD and dev<=0.8USD caps remain. Changing run ID needs a new spending authorization; changing DATABASE_PATH to reset counters is prohibited.

The0.03USD cap is an internal reservation limit calculated from verified configured token prices. The prior0.0234USD estimate assumes <=6000billable input and <=2400combined output/thought tokens per attempt; it is not a verified invoice or an unconditional cloud billing guarantee. The GenerateContent-specific [thinking guide](https://ai.google.dev/gemini-api/docs/generate-content/thinking?hl=en) was separately retrieved with HTTP200 and documents the combined thought/response ceiling. This resolves the endpoint documentation check; it does not verify account billing. See `docs/evidence/T05/preflight-public-bounds.json`. Actual usage includes thoughts; unknown attempts retain reservations and total actual cost remains unavailable until reconciled. Three mock successes do not prove real structured-output/thinking compatibility.
