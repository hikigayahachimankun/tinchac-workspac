What this change does: Prepares a five-family development pilot, human annotation instructions, and offline checks. It keeps all previously exposed families in dev and leaves test and real gold uncreated.

Looks good. Ship for owner review, with no freeze claim.

Checked the T09 CLI flow from Pydantic input parsing through corpus loading, split checks, exact quotes, release cutoff, and private hash receipt. Assumed one local owner running offline commands. The 30 synthetic-fixture tests cover invalid input/gold, duplicate IDs, overlap, future evidence, missing gold, false second annotator, and a full candidate receipt. Receipt tests mock Git status/HEAD only; they verify dirty-tree refusal, actual file hashes, and exclusive creation. They do not commit or read private data.

The input validator rejects extra fields instead of trying to enumerate every possible gold-field alias. Human review still owns claim atomicity, evidence sufficiency, scope, source rights, and annotation truth. A hash receipt certifies bytes checked, not that those human checks are true. The draft protocol records this boundary.

Not checked: real human gold, private test inputs, independent annotation, source owner spot-check, resolved model/config, or T13 benchmark. No comparison to system predictions was used in this review. The existing upstream diff was outside review scope.

Verdict: Ship.
