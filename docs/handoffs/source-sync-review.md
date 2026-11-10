# Source sync — ponytail-review

What this change does: Discovers notices from two closed DUT publication channels, retains private review candidates and atomically publishes supplied reviewed corpus snapshots. Live jobs keep a single snapshot, while an independent scheduler drains coalesced discovery tasks.

Scope/load checked: one local Linux/WSL scheduler and one FastAPI worker with at most2jobs, current small corpus. Read the whole feature diff, Jobs/run_live/create/source callers, source/health API, registry/HTTP/robots transport, candidate state, review/ingest/corpus validators, queue/scheduler, existing eval runner/harness, fixture adapter, frontend warnings, release packaging and README. Synthetic tests and actual bounded DUT receipts are separate from human source verification.

## Must fix — resolved before final review

1. **Review evidence was not retained with the corpus** (`corpus_store.publish_reviewed`). A packet could pass gates but later provenance kept only a reviewer string. Persist the complete packet and registry hash inside manifest-bound ingest provenance; freeze the exact validated input values before build. Regression reads the stored manifest and verifies the exact packet.
2. **A late durability failure could leave a newly selected pointer after a failed publish** (`corpus_store.replace_pointer`). If directory fsync fails after replace, restore the previous logical pointer and retain both complete snapshots. Regression injects that exact failure. Persistent device failure still requires operator recovery; no code promises durability from a failed disk.
3. **An interrupted batch could lose discovered but unfetched links** (`source_sync._sync`). If the listing rotated before resume, only already-fetched notices were checkpointed. Persist the metadata backlog before fetching, rotate failed attempts, and write failure/interruption receipts. Regression removes the second notice from the next listing and still collects it.
4. **Changed embeds could reuse a prior review identity** (`source_sync.candidate_key`). Equal HTML text with a different attachment would share a candidate directory. Include attachment/title extraction metadata in the candidate key while keeping SourceVersion's text-based identity, and require a new hash-bound review receipt.
5. **Retry pacing and compressed/unreadable policies needed hard bounds** (`source_fetch.SafeFetcher`). Retries must honor crawl-delay; compressed payloads can inflate before byte checks; HTML/access-denied robots bodies are not an allow policy. Enforce pacing on each attempt, request identity encoding/reject encoded responses, and fail closed on unreadable policy. Robots wildcard matching uses stdlib atomic translation to avoid exponential regex behavior.

## Should fix — resolved before final review

6. **An exact promotion retry failed instead of being a no-op** (`corpus_store.publish_reviewed`). Replaying an already recorded packet now restores its stored review provenance and returns the unchanged active version. Altered packets/review history remain rejected.
7. **A corrupt unrelated archive could block a valid historical citation** (`Jobs.source`). Skip invalid retained directories while looking up the immutable version; retain errors for invalid active snapshots. No automatic deletion or mutation of old source versions.

Final checks: offline synthetic registry/security/discovery/review/publication/pinned-request/queue/scheduler tests; existing provider-failure/cancellation/retrieval/eval regressions; contract/corpus checks; actual DUT robots/homepage/listings and bounded notice downloads. No model/API/gold changes or new dependency. Existing exact-notice Python helper remains for existing callers/tests; operational CLI always routes through the registry transport.

Verdict: Ship the technical feature for review with source approval and scheduler activation explicitly pending.

Not checked: human source/rights validation, real user on-demand traffic, ongoing scheduler uptime, real304/changed DUT publication, physical demo laptop or distributed/multi-worker deployment. No UI changed; existing warnings component was read.
