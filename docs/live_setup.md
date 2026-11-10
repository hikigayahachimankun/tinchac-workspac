# Gemini account setup — owner secret, no key in chat

D02 is unresolved. Recovery has made zero paid requests. The HTTP implementation is ready offline, but `LLM_LIVE_ENABLED=false` by default. Published Standard defaults (0.30 input / 2.50 output USD per million, including thoughts) were rechecked on 10/11/2026; account pricing/quota/taxes remain unverified. Sources: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing), [thinking](https://ai.google.dev/gemini-api/docs/thinking).

Store the secret outside the repository in WSL, for example `~/.config/tinchac/gemini.env`. Enter it through a hidden terminal prompt; never paste it into chat or put it on a command line. These are owner-run setup commands, not commands recovery has executed:

```bash
install -d -m 700 "$HOME/.config/tinchac"
umask 077
read -rsp 'Gemini API key: ' TINCHAC_API_SECRET
printf '\n'
printf 'GEMINI_API_KEY=%s\n' "$TINCHAC_API_SECRET" > "$HOME/.config/tinchac/gemini.env"
unset TINCHAC_API_SECRET
set -a
source "$HOME/.config/tinchac/gemini.env"
set +a
```

Use a separate app project/key and a durable ledger; do not delete/reset it between runs. Verify model availability, paid-use permission, quota and displayed prices in your account before the following connection test. No top-up or billing change is authorized. The proposed test is at most three generation attempts, including retries/repairs, stage dev <=0.8 USD and global <=3 USD; expected maximum token-reservation cost is below 0.03 USD with current defaults, but actual account charges require dashboard reconciliation. Re-running the command creates another run, so do not repeat it to bypass the attempt limit.

```bash
APP_MODE=live DATABASE_PATH=./data/private/tinchac-live.sqlite3 \
LLM_BUDGET_USD=3 LLM_LIVE_ENABLED=false \
  .venv/bin/python -m scripts.preflight --model-check --max-calls 3
```

The command reads only three approved public source excerpts. Output contains run ID, model, thinking config and usage; no key or raw provider exception. Verify `model_version`, complete token accounting (including thoughts), ledger reservations/unknown states and account dashboard. Record those facts in D02. Do not mark `model_verified=true` from documentation alone.

After successful preflight and explicit paid-use authorization, start HTTP with `APP_MODE=live`, that same durable DATABASE_PATH and `LLM_LIVE_ENABLED=true`. HTTP uses demo <=0.8 USD/global <=3 USD and sends only confirmed text, never raw images; contact masking is limited and is not full anonymization. Test only approved public samples initially. Never put secrets in frontend/Vite variables.
