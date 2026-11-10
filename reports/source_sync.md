# Verified DUT Source Discovery & Auto-Sync

Technical implementation ready for review on `feature/verified-source-sync`, based on integrated RC `a97b3c4`. Source approval, rights and unattended operation remain separate gates. Public API/schema1.0, tracked research corpus, split/protocol, prompts, A/B/C/C_NO_TIME and gold are unchanged.

## Actual DUT runs

See [machine-readable receipts](../docs/evidence/source-sync/smoke.json). All requests used the closed registry, robots, TLS and public-IP pinned transport. Last successful collection finished **11/11/2026 00:04:50 UTC+07** (`2026-11-10T17:04:50.258431Z`). No provider/model calls or costs.

| Measurement | Actual result |
|---|---:|
| Official units with homepage-link validation | 2: CTSV, KHTC |
| Unique listing URLs checked | 3 |
| Listing checks over four recorded runs | 12 |
| Distinct discovered notice URLs / metadata backlog registered | 18 |
| New URLs in final run, measured against prior collection state | 12 |
| Notice HTML200 responses over four runs | 10 |
| Successfully retained candidate versions | 8 |
| Unchanged / content-updated versions observed live | 0 / 0 |
| Pending complete candidates / quarantined candidates | 0 / 8 |
| Newly approved sources / newly published facts | 0 / 0 |
| Initial failures, preserved in receipts | 2 content_empty; 2 redirect_denied |
| Recorded HTTP requests over four runs | 35 |
| Recorded run durations | 7.290 + 9.243 + 12.714 + 8.575 = 37.822 seconds |
| Additional listing inspection | 2 successful listing reads; request count was not persisted, ≤6requests/20seconds configured |
| Model calls / tokens / estimated model cost | 0 / 0 / 0USD (0VND) |

Counts describe operational collection state, not independent research families. Seed notices can reappear through aliases. The first three historical receipts counted `new_urls` among attempted URLs; final code records the complete discovered backlog before fetching, so its `new_urls=12` is newly registered discovery metadata. `urls_discovered=18` is deduplicated within each run, not summed across runs. Ten HTML responses include two initially rejected metadata-only pages; eight candidate versions remain after handling unread embeds as quarantined metadata. No real304 or changed publication was observed; deterministic tests cover both, without asserting live server support.

Trust evidence: `https://dut.udn.vn/` links to `https://dut.udn.vn/Phong/CTSV` and `https://dut.udn.vn/Phong/Taichinh`; CTSV scholarship listing `https://dut.udn.vn/Phong/CTSV/Tintucds/gid/332` links the `/Phong/Sinhvien/Thongbao/id/...` alias channel. Registry records that observed relationship. Registered same-unit redirects resolved12395/12394/12373 to `/Phong/CTSV/...`; arbitrary/cross-unit/private targets remain denied. This verifies publication-channel provenance, not the correctness of individual claims or an independent human review.

Retained canonical notice IDs: CTSV12395/12394/12373; KHTC12387/12381/12340/12337/12319. Every candidate's origin, unit, transport/text hash, first_seen, trust evidence and quarantine reasons are in the receipt artifact. Actual HTML and candidate text stay under ignored `data/private/source-sync`; no raw/PDF/image or personal list was published. Attachments were **not fetched**. Unread images/iframes/links and payment/amendment review gates keep all eight quarantined. Source12381 remains excluded from approved retrieval; its personal-data PDF was not reopened. Public availability does not grant redistribution rights.

## Corpus publication and runtime

Research/reference corpus stays `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982`:6versions/5approved/7chunks. Offline bootstrap copied the same reviewed seed into a private store as `corpus-6b5cb0eb9e0b4f5029857ffe83259f77290af8585d05aa50216fee0d122142e5`. The manifest differs because its ingest commit is the current RC base; **no discovered source was approved or added**. Bootstrap receipt/pointer is summarized in the machine-readable artifact. An actual Jobs runtime loaded this private snapshot locally without a provider call. The app must be configured with `SOURCE_SYNC_STORE` to adopt this store; fixture and existing direct-directory mode remain available.

Reviewed publication uses existing offline `ingest()`, a private staging directory, full corpus/register validation, runtime construction, manifest-bound review packets and file hashes. Directory/file fsync precedes atomic pointer replacement. Existing versions/review provenance cannot be rewritten or dropped; same-source families cannot split; identical text at different canonical sources cannot become duplicate evidence. Each in-flight job pins one runtime through extraction/retrieval/verification; new jobs read the new pointer. Historical source versions remain reachable after restart and rollback. No automatic archive deletion is implemented.

Synthetic tests exercise real publish→Jobs→retrieval/source API paths, concurrent extraction paused during publication, failed builds, pre/post-replace failures, restart, rollback, exact review replay, source-after-approval and old-result immutability. These are technical integration results, not DUT claim-accuracy or human source approval results.

## Schedule and on-demand

Independent CLI scheduler available via `scripts.sync_sources daemon --mode live --enable`, configurable3600second interval/10second queue polling. Config defaults disabled. **No persistent scheduler/service was installed or left running**; `systemctl --user is-system-running` reports `offline` here. Synthetic scheduler start/tick/queue-drain/stop/restart tests passed. Actual uninterrupted scheduled operation has not been measured. The host/WSL must remain on.

Production on-demand triggers only when no approved same-scope source exists. It enqueues fixed authority IDs only: raw user input, programme/year text, images, phone/account data and arbitrary URLs never enter an outbound lookup. Queue capacity2, one task/unit, cooldown900seconds and lease300seconds bound/coalesce abuse. Verification does not wait for web and keeps the pinned corpus. Unreviewed discoveries do not produce supported/contradicted; provider errors remain technical errors. Daemon failure does not change completed results.

Actual on-demand user traffic: **0**. Synthetic production-pipeline tests show a missing programme queues one unit and returns NEI with the existing warning mechanism; matching approved scope skips discovery. Concurrent enqueue tests accept exactly1of20 equivalent requests. Fixture/replay refuse networking even when lookup settings are enabled; eval harness never imports this queue.

## Validation and performance

Baseline397backend/eval tests passed. Final backend/eval471tests passed (19.27s), including74feature tests. Commands and outcomes are recorded in the [handoff](../docs/handoffs/source-sync.md); frontend37unit tests and build passed,31contract examples/OpenAPI matched, and reference corpus6sources/7chunks validated. Existing locked research inputs and corpus files have no diff. Tests use synthetic fixtures/httpx.MockTransport/scripted SDK responses, no DUT dependency or provider generation.

Same-host runtime lookup measurement:10000calls after initial load, same six seed sources. Baseline direct mode0.699µs/call; final direct0.943µs/call; opt-in pointer mode42.945µs/call (≈0.043ms). Pointer mode performs a local atomic-pointer read and path check; unchanged snapshot is not reloaded/reindexed. No retrieval algorithm/index optimization, corpus-growth claim or LLM latency claim is made.

Security policy consulted: [RFC9309](https://www.rfc-editor.org/rfc/rfc9309.html), [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html). Longest-match robots groups/wildcards/unreserved escapes, response bounds, retry/backoff/Retry-After, pacing including retries, DNS answer validation/pinning, redirect scope and safe content retention have offline tests. This is a bounded local Linux/WSL collector with existing pinned httpx/httpcore, not a claim of universal crawler compatibility.

## Remaining gates

- Actual reviewer must verify completeness, family/scope, facts and content-use rights before promotion. Fees, changed money/deadline, amendments and external/scan/attachment material require actual identified human review evidence. No new packet was fabricated.
- Eight unread/incomplete candidates remain quarantined; no PDF/image/OCR completeness or independent human source spot-check is claimed. Existing T02 source shortage/rights and T09/T13/T15 acceptance remain open.
- Scheduler must be deliberately operated on an available host; no continuous-sync claim. Actual source update/304 and on-demand user traffic remain unobserved live.
- Git scope is public code, closed registry, synthetic tests, plans and safe metadata/docs only. Native HTTPS has no credential; connected GitHub transport can publish the exact checked feature tree with equality verification. No merge/tag/deploy or source-content upload.
