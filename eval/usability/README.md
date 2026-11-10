# T14 — planned materials, not human outcomes

Tasks use four existing exposed dev families and input metadata to cover an award statement, one-value modification, unverified fee assertion and payment deadline. Selection does not assign expected model labels or human answers. Human action-key review remains false/null. `action_key.draft.json` adds an agent source-reviewed candidate with source version/hash/quote and an explicit ceiling-effect limitation under broad task wording. No model prediction or gold was used to choose tasks or draft actions.

Allocation is deterministic: planned IDs U01–U12; task order is P1–P4 rotated by `(participant_index % 6) % 4`; first six use manual/manual/TinChac/TinChac, next six reverse conditions. This yields four distinct families/person, two tasks/condition and six appearances/task/condition. These assertions were executed in recovery. Participants are planned placeholders, not recruited people.

Start with [`protocol.md`](protocol.md). Current actual n=0; no invitation sent, consent inferred or user result fabricated. CLI: `python -m scripts.user_pilot --help`.

`readiness.blank.json` deliberately blocks collection until the selected release passes QA for **all four tasks** and the action rubric is reviewed with source/scope/time rationale. Current fixture has only one family and cannot substitute for this pilot.

```bash
.venv/bin/python -m scripts.user_pilot validate-allocation
.venv/bin/python -m pytest eval/tests/test_user_pilot.py -q
.venv/bin/python -m scripts.user_pilot rehearse --work /tmp/tinchac-T14-synthetic
```

Rehearsal requires a new directory, uses the **same collector** with synthetic clock/input, and always reports `actual_real_participants=0`. It does not open the UI or call a provider. Never copy rehearsal rows into real results.

`results.blank.csv` matches the requested seven-column pilot CSV (not an API schema): participant_id/case_id/condition/order/duration/action_correct/comments. Duration is seconds. Real results, consent/status/evidence/source-count/label sidecars and locked manifest are created only in ignored `data/private/user_pilot/`, with restrictive permissions. Summary validates consent/materials/allocation/scoring, retains timeouts/errors/partial sessions, regenerates CSV and prints no individual comments/IDs. Protocol explains participant-level deltas, denominators, retention/deletion and study limits. Do not commit participant files or disclose individual free text.
