# Evidence Packet Template (D7)

> Copy this template for each evidence packet. Fill every section. Leave no section blank — use `NOT_RUN` or `GAP` if applicable.

## Metadata

| Field | Value |
|---|---|
| Packet ID | `<B-P1-001>` |
| Plan phase | `<B / D / A / C / W2>` |
| Date | `<YYYY-MM-DD>` |
| Actor | `<implementer>` |
| Label | `<LIVE_MODEL_OBSERVATION / SIMULATED_PROTOCOL / FAST_SIGNAL / PROVISIONAL_RESULT / VERIFIED_RESULT>` |

## Requirement IDs

| ID | Requirement | Status |
|---|---|---|
| `<C01>` | `<known-answer accuracy>` | `<PASS / FAIL / NOT_RUN / GAP>` |

## Source / Diff Hashes

| File | SHA256 |
|---|---|
| `<path>` | `<sha256>` |

## Raw Outputs

```
<paste raw tool / model output here — no summarisation>
```

## Controls & Negatives

| Control | Expected | Observed | Verdict |
|---|---|---|---|
| `<negative test>` | `<reject / refuse>` | `<what happened>` | `<PASS / FAIL>` |

## Scoped Verdicts

| Claim | Evidence | Scope | Verdict |
|---|---|---|---|
| `<claim text>` | `<receipt_id or file>` | `<scoped limit>` | `<PASS (scoped) / FAIL / NOT_RUN>` |

## W2 Aggregate

| Check | Status | Accuracy | Reason |
|---|---|---|---|
| C01 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| C09 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| C10 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| C11.7 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| C12.2 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| C12.6 | `<PASS / NOT_RUN / FAIL>` | `<n/d or null>` | `<note>` |
| **Overall** | `<6/6 terminal-honest / FAIL>` | | |

## Immutables Check

| File | SHA256 before | SHA256 after | Unchanged |
|---|---|---|---|
| `vivy_train_dataset.jsonl` | | | `<YES/NO>` |
| `evidence/gold_review_queue.jsonl` | | | `<YES/NO>` |
| `evidence/gold_train.jsonl` | | | `<YES/NO>` |
| `evidence/shadow_receipts/` | | | `<YES/NO>` |

## Gate 9 Disclaimer

All metrics above are MEASURED, not claimed. No `0%`, `0ms`, `O(1)`, or `PRODUCTION-READY` assertions are made. Every rate carries a denominator and 95% CI. Every latency measurement is labelled `LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"`.

## KNOWN_LIMITATIONS Cross-Reference

List every `L-xx` ID from `KNOWN_LIMITATIONS.md` that bounds this packet's verdicts:

- `<L-xx>: <one-line reason>`
