# KNOWN_LIMITATIONS — every GAP / NOT_RUN / FAIL that bounds the claims

**Status:** binding companion to `docs/plans/P5_FINAL_ACCEPTANCE.md`
**Date:** 2026-09-24
**Implementer:** Claude Code (replacing Antigravity)
**Rule:** anything listed here is **outside** every PASS verdict in the packets.
Nothing in this file may be quietly dropped from a later summary.

Ghi chú bắt buộc (Changelog):
- 2026-09-24 (Claude Code — P5 FINAL): initial exhaustive limitations register.
  Isolate-not-delete. No claim in any packet outranks this file.

---

## §1 How to read this file

| Label | Meaning |
|---|---|
| **GAP** | the contract requires a bar/evidence that does not exist yet (e.g. spec is silent) |
| **NOT_RUN** | the harness exists or is specified, but the measurement was not executed here |
| **INCONCLUSIVE** | something ran, but the evidence level is not enough for the claim |
| **FAIL (isolated)** | a real defect, contained so it cannot silently propagate |
| **BLOCKED** | an external prerequisite (server, human label, pinned upstream) is missing |

A `PASS (scoped)` elsewhere is bounded by every row below that touches it.

---

## §2 Register

### §2.1 Live backend / accuracy

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-01 | **NOT_RUN** | llama-server `:8080` was down (`WinError 10061`). Known-answer accuracy is `null`, not `0%`. Receipt `evidence/VIVY-C01-KNOWN-ANSWER-LLAMA-2026-09-24-001.json` = `INFRA_INCOMPLETE`. | C01 live, Gate 10, §4 decision-quality bar |
| L-02 | **NOT_RUN** | Live C09 thinking-budget A/B (budgets 0 / 384 / 1024) never reached a server. | C09 live, token/quality tradeoff |
| L-03 | **NOT_RUN** | Live C10 `cautreo.dll` memory put/get/delete path not exercised (DLL not present in this run). | C10 native path |
| L-04 | **NOT_RUN** | C11.7 live repeat-rate + harm/false-inhibition with CI. The 100-task pilot is `SIMULATED_PROTOCOL`. | VM-11 live, Gate 10 |
| L-05 | **NOT_RUN** | C12.6 real-model inference evidence. Atlas/size/load tests are not inference. | C12 acceptance at model level |
| L-06 | **NOT_RUN** | C12 `semantic_accuracy` on real labels (fixture has none). | C12 phase completeness |
| L-07 | **NOT_RUN** | C12 OS RSS / private working set / page-faults (`GetProcessMemoryInfo` via psapi unavailable → `os_probe=NOT_RUN`). RSS is **not** inferred from `allocated_buffer_bytes`. | C12.2 measurement completeness |
| L-08 | **NOT_RUN** | C13.7 VM-01…VM-11 live effectiveness (sensitivity, modality confusion, retrieval recall, eviction correctness, directive executability, RCA, self-heal, TTFT, paired-N, live repeat-rate). | every VM effectiveness claim |
| L-09 | **NOT_RUN** | Gate 3 multimodal: vision needs real image bytes + reference labels. Text-described images are `NOT_RUN` and do not count as grounding. | Gate 3 |
| L-10 | **NOT_RUN** | Gate 6 live delegate verification (worker model identity from runtime config on a real delegate call). | Gate 6 |
| L-11 | **NOT_RUN** | Gate 10 live scenario battery (incomplete input, stream disagreement, shared false premise, contradictory evidence, timeout/refusal, unavailable CAUTREO tool, restart mid-reasoning, promotion of unverified lesson) — covered as harness negatives only. | Gate 10 |

### §2.2 Spec / threshold gaps

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-20 | **GAP** | `VIVY_COGNITIVE_CORE_SPEC.md` (2026-09-19), `ACCURACY_AND_MATURATION_STRATEGIES.md` (2026-09-20) and `ACCEPTANCE_GATES.md` (2026-09-19) contain **no** VM-01…VM-11 numeric threshold table. 11/11 thresholds are GAPS. **No bar was invented.** | any "VM-x PASS on effectiveness" claim |
| L-21 | **GAP** | §4 "Ngưỡng nghiệm thu v1" decision-quality bar (paired Δaccuracy lower 95% CI > 0) has no live measurement. | quality-gain claim |
| L-22 | **GAP** | §4 token bar (≥20% token/task reduction) has no live end-to-end token corpus. | token-saving claim |
| L-23 | **GAP** | §4 risk-vs-coverage curve (risk must fall as coverage falls) has no live measurement. Always-abstain predictors are explicitly disqualified. | OOD/abstention claim |

### §2.3 Data / labels

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-30 | **INCONCLUSIVE** | `gold_outcome` is `unknown` on all 50 gold selection rows (Category B = 0; no capture/postcondition store exists). This work produced **selection labels only**. | any action-success claim; max `PROVISIONAL_RESULT`, never `VERIFIED_RESULT` |
| L-31 | **BLOCKED** | Human confirmation of gold (`legacy-455` + ~5 `A_template` spot-checks) is the user's call. Oracle is propose-only and is **not** ground truth and **not** LLM critique. | Gate 10 metrics on gold rows |
| L-32 | **GAP** | §2.12 Laya/Verdict schema pin: no pinned upstream revision, license, or adapter mapping on disk. Internal NOUL/score schema is **not** claimed compatible. | schema-compatibility claim |
| L-33 | **NOT_RUN** | Learned router quality and baseline quality on live predictions (fixture/replay must not close this). | "learned router" goal item |

### §2.4 Isolated defects

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-40 | **FAIL (isolated)** | Native CAUTREO semantic substrate: prompt/tokenizer parity 24/24 IDs, but forward/logits parity fails — first token `177869/gug` vs reference `26391/Four` for `2+2=4` (`VIVY-CAUTREO-GEMMA4-CHAT-171/188`, `REFERENCE-TOKEN-194`, `EXACT-PROMPT-196`). **Native only** — this does not indict llama-server `:8080`. | Gate 1 native residency; any native-parity claim |
| L-41 | **FAIL (must not ship)** | Naive condition-blind dampener drives `repeat_rate` 0.39→0.00 **and** `false_inhibition` 0.00→1.00 (20/20). C11 finding. Do not ship; condition-aware gating is a prerequisite for any live VM-11 claim. | VM-11 dampener promotion |
| L-42 | **INCONCLUSIVE** | C12 sparse activation is not free: 12.5% activation (k=8/n=64) costs output cosine **0.67** on identical weights/input. Never present sparse as a free win. | sparse-as-optimization claim |
| L-43 | **INCONCLUSIVE** | C10 memory-on/off lesson gain is n=3 held-out (`gain=2 / harm=0 / tie=1`) — a mechanism check, not a quality claim. | lesson-quality claim |
| L-44 | **NOT_RUN** | 100B-on-10GB stays `UNVERIFIED`; `extrapolated_from_smaller_artifact=false`. The `qwen2-vl-72b.catlas` artifact is not 100B measured. | 100B capacity claim |

### §2.5 Operational / process

| ID | Label | Limitation | Blocks |
|---|---|---|---|
| L-50 | **BLOCKED** | Hosted push + PR to `main`: no git remote (`git remote -v` empty), no `gh` CLI. Local `main` branch and PR package (`docs/plans/PR_TO_MAIN.md`) are prepared. Hosted PR cannot open until a remote + `gh` (or manual host upload) exist. | delivery via hosted PR |
| L-51 | **SUPERSEDED** | Standing order **"Chưa commit ngay"** was replaced by the user request **"Tạo PR và main. tạo file báo cáo kết quả"** (2026-09-24). Scoped commit of the phase work is therefore authorized. That authorization does **not** extend to gold-dataset edits, receipt/checkpoint deletion, or `:8080` default-model swap. | — |
| L-52 | **PARTIAL** | §4 protocol item "commit + hash dirty diff": file hashes are recorded per packet; this delivery adds a scoped commit on `feat/gold-triage-oracle` and local `main`. Hosted PR still L-50. | protocol completeness |
| L-53 | **OUT OF SCOPE** | Production swap, paid services, and any out-of-scope action are **user decisions**, not implementer actions. | production deployment |
| L-54 | **CONSTRAINT** | `LLMClient.chat(..., fallback=True)` is `[ISOLATED]` — it silently walks 17 `DEFAULT_MODELS`. Use `fallback=False` or `make_unitary_fn`. | silent-fallback leakage |
| L-55 | **CONSTRAINT** | `:8080` default model (`gemma4-e4b`) must not be changed. Do not run full SFT/LoRA on the 501 legacy rows. Do not claim "RLCD complete" for `SFTTrainer`-only notebooks. | all training claims |

### §2.6 Claim bans (Gate 9) — always in force

| Banned claim | Unless |
|---|---|
| `PRODUCTION-READY` | production evidence that does not exist here |
| `0%` error | report `n` + CI instead; 0 in n samples is not 0% |
| `O(1)` | a real complexity benchmark |
| any latency SLA / "zero latency" | `LATENCY_CLAIM = "NOT_A_PHYSICAL_ZERO"` is the standing label |
| synthetic result presented as accuracy | label `FAST_SIGNAL` / `PROVISIONAL_RESULT` / `VERIFIED_RESULT` honestly |
| simulation presented as production | C11 pilot is `SIMULATED_PROTOCOL` and FAILs the VM-11 live gate |
| checkpoint / receipt / test-count as quality evidence | evidence must be the measurement itself |
| `EXECUTE_DIRECTLY` before Evidence Gate PASS | never |
| fabricated gold / LLM critique as ground truth | never |

---

## §3 Immutables (never modified by this work)

| File | sha256 |
|---|---|
| `vivy_train_dataset.jsonl` | `8d1e68421572708324248ff8a06326e77449c292d2214498759f231a82b4531b` |
| `evidence/gold_train.jsonl` | `630a2ee442f20d942be210d219ca40eca4e2905cb83247c2d1e0d1e589ec44c7` |
| `evidence/gold_review_queue.jsonl` | `93cdcf3675facc0bf7dbaf2baef5f35cff1c5c47c0c13968ac176d97f8ca2ef7` |
| `evidence/shadow_receipts.jsonl` | `695a224b16b82baeeeac499cb3e50fb74ceb2036e439ee8d92fbed51efbd0576` |

No datasets, receipts, or checkpoints were deleted. Hardening was isolate-not-delete
(`[ISOLATED / DEPRECATED / REPLACED]`).

---

## §4 One-paragraph summary for a reader who will not read §2

The C01–C13 **harness, contracts, negative gates and resilience mechanisms** are
implemented and tested (339 unit/contract tests, scoped PASS). **Every claim
that needs a live model, a live service, a real image set, an OS RSS probe, a
pinned Laya/Verdict revision, human-confirmed gold outcomes, or a versioned
numeric threshold in the spec is NOT_RUN or GAP.** The native CAUTREO
forward/logits parity failure is real and isolated (it does not indict
`:8080`). The naive dampener that zeroes repeats at the cost of 100% false
inhibition must not ship. Sparse activation costs quality (cosine 0.67 at 12.5%
activation). Nothing here is `PRODUCTION-READY`, nothing is `0%`, nothing is
`O(1)`, and no latency is a physical zero. Production swaps and out-of-scope
actions remain user decisions.

---

## §5 Changelog

| Date | Actor | Change |
|---|---|---|
| 2026-09-24 | Claude Code | Initial KNOWN_LIMITATIONS register (L-01…L-55 + claim bans). |
