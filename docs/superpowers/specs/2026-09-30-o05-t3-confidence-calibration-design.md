# O-05/T3 — Confidence Calibration Infrastructure

> **Status:** DRAFT — awaiting user review
> **Date:** 30/09/2026
> **Author:** Claude Code
> **Gate:** T3 (Definition of Done)
> **Source:** REVIEW_VIVY_2026-09-29.md §7.2 (O-05), §8 (T3), F-C05, G6

---

## 1. Purpose

Build the measurement and calibration infrastructure that gives ViVy **one calibrated confidence definition** with proven calibration quality (ECE ≤ 0.10, AUROC ≥ 0.70 on held-out). Currently ≥6 incompatible confidence definitions exist with no measurement of whether any of them predict correctness.

**Scope (decided by user 30/09/2026):** measurement + calibration infrastructure only. Runtime integration (wiring calibrated confidence into `decision_controller` / `epistemic_gate`) is deferred to GĐ2 (O-06/O-08).

**Acceptance (T3 gate):**
- For each of 7 definitions: compute ECE, AUROC, Brier on held-out
- Selected definition must reach **ECE ≤ 0.10 AND AUROC ≥ 0.70** on held-out
- If no definition passes → `selected = "verifier"` (binary fallback per spec)

---

## 2. Context

### 2.1 Existing confidence definitions (F-C05)

| # | Name | Producer | Formula | Alive? |
|---|---|---|---|---|
| 1 | `schmidt_spectrum` | `funnel/filter.py:135` | `σ × consistency × brevity` (aggregate: mean of kept) | Yes |
| 2 | `state_norm` | `orchestrator/epistemic_gate.py:170` | `state.norm()` clipped [0,1] | Yes; ≈1.0 always |
| 3 | `llm_declared` | `src/vivy/core/inference.py:98` | JSON `confidence` field | Yes (trading path) |
| 4 | `ncore_min` | `orchestrator/graph_bridge.py:382` | `min(c.score)` across candidates | Yes |
| 5 | `linear_tribunal` | `src/nps_core/.../calibration.py:18` | `prior + 0.1·(support−oppose)` | **Dead** (no prod caller) |
| 6 | `self_consistency` | — | **Not implemented** | Greenfield |
| 7 | `verifier` | `integration/evidence.py:85` | `1.0` if ≥1 tool ok and 0 fail, else `0.0` | Yes |

### 2.2 Existing metrics code (reusable)

- `training/learned_router.py:37–68` — `brier_score()`, `expected_calibration_error()` (ECE ≤ 0.10 threshold already encoded at L29)
- `training/independent_baselines.py:278–304` — `ece_binary()`
- **AUROC:** zero implementations in repo — must write
- **Isotonic regression:** zero implementations in repo — must write
- **Self-consistency sampler:** zero implementations — must write

### 2.3 Labels source

Correctness labels come from `benchmarks/checker.py::check_answer` (ground truth by construction — programmatic answer checking, no substring matching). The dev split (32 items) and held-out split (88 items) are defined in `benchmarks/eval_set/`.

---

## 3. Architecture

```
vivy/benchmarks/calibration/          # NEW subpackage
├── __init__.py                       # public API re-exports
├── features.py                       # 7 confidence definition extractors
├── isotonic.py                       # PAV isotonic regression (pure Python)
├── metrics.py                        # ECE, AUROC, Brier
└── evaluate.py                       # T3 evaluation pipeline + verdict

vivy/benchmarks/harness.py            # EXTEND: confidence_by_definition per item
vivy/tests/test_calibration.py        # NEW: unit tests
```

**Dependency policy:** zero new dependencies. Pure Python only (PAV, AUROC). Numpy is permitted (already used in `funnel/`, `training/`).

---

## 4. Components

### 4.1 `features.py` — confidence definition extractors

Each extractor takes an eval-item context and returns a `float` score in [0,1].

```python
@dataclass(frozen=True)
class FeatureContext:
    """What an extractor needs to produce its score for one eval item."""
    item_id: str
    question: str
    model_reply: str
    tool_results: list[dict] | None      # for verifier
    parsed_answer: str | None            # from checker
    # --- raw signals from the pipeline arm ---
    funnel_confidence: float | None      # definition 1
    state_norm: float | None             # definition 2
    llm_confidence: float | None         # definition 3
    ncore_min_score: float | None        # definition 4
    # --- for linear_tribunal ---
    prior_confidence: float | None       # definition 5 input
    supporting_count: int | None         # definition 5 input
    opposing_count: int | None           # definition 5 input
    # --- for self-consistency ---
    k_samples: list[str] | None          # definition 6: k model replies
```

Extractor registry:

```python
EXTRACTORS: dict[str, Callable[[FeatureContext], float]] = {
    "schmidt_spectrum": _schmidt_spectrum,
    "state_norm": _state_norm,
    "llm_declared": _llm_declared,
    "ncore_min": _ncore_min,
    "linear_tribunal": _linear_tribunal,
    "self_consistency": _self_consistency,
    "verifier": _verifier,
}
```

**Self-consistency k=5:** count the most frequent declared answer across k samples; score = `count / k`. If fewer than k samples available, score = `0.0` (fail-closed).

**Extraction rules:**
- Extractors that need a signal that is `None` return `0.0` (fail-closed, not silently `1.0`)
- `verifier` is the T3 fallback: `1.0` if ≥1 tool result with `ok=True` and zero `ok=False`, else `0.0`

### 4.2 `isotonic.py` — PAV isotonic regression

Pure Python, ~30 lines. No sklearn.

```python
class IsotonicModel:
    """Monotone step function mapping raw score → calibrated probability."""
    thresholds: list[float]   # sorted unique raw scores
    values: list[float]       # calibrated probability at each threshold

    def predict(self, score: float) -> float: ...

def isotonic_regression(
    scores: Sequence[float],
    labels: Sequence[int],     # 0 or 1
) -> IsotonicModel: ...
```

**Algorithm (PAV — Pool Adjacent Violators):**
1. Sort pairs by score
2. For each point, create a block with its label
3. While any adjacent block violates monotonicity (left mean > right mean): merge them
4. Output: step function — each block's mean is the calibrated value for its score range

**Edge cases:**
- All labels identical → constant function (that constant)
- Single sample → constant function (that label as float)
- Duplicate scores → pooled into one block

### 4.3 `metrics.py` — ECE, AUROC, Brier

```python
def expected_calibration_error(
    confidences: Sequence[float],
    labels: Sequence[int],
    n_bins: int = 10,
) -> float: ...

def auroc(
    scores: Sequence[float],
    labels: Sequence[int],
) -> float: ...

def brier_score(
    confidences: Sequence[float],
    labels: Sequence[int],
) -> float: ...
```

**ECE:** equal-width bins (reuse formula from `training/learned_router.py:46-68`). `ECE = Σ_m (n_m/n) · |acc_m − conf_m|`. Returns `0.0` for empty input.

**AUROC:** rank-based. `AUC = P(score_positive > score_negative)`. Implementation:
1. Sort by score, track ranks (handle ties with average rank)
2. `AUC = (Σ ranks_positive − n_pos·(n_pos+1)/2) / (n_pos · n_neg)`
3. Return `0.5` when either class is empty (no discrimination possible)

**Brier:** `mean((p − y)²)`. Reuse formula from `training/learned_router.py:37-43`.

### 4.4 `evaluate.py` — T3 evaluation pipeline

```python
@dataclass(frozen=True)
class DefinitionMetrics:
    definition: str
    ece: float
    auroc: float
    brier: float
    n_items: int
    passes: bool                # ece <= 0.10 and auroc >= 0.70

@dataclass(frozen=True)
class T3Verdict:
    selected: str               # definition name, or "verifier" if fallback
    status: str                 # "PASS" | "FALLBACK"
    metrics: dict[str, DefinitionMetrics]
    isotonic_model: dict        # serializable calibration curve for the winner

def run_t3_evaluation(
    scores_by_def: dict[str, list[float]],   # definition → score per item
    labels: list[int],                        # correctness from checker
    *,
    dev_indices: list[int],                   # calibration split
    heldout_indices: list[int],               # evaluation split
) -> T3Verdict: ...
```

**Pipeline:**
1. For each definition:
   a. Fit `IsotonicModel` on dev scores + labels
   b. Apply calibration to heldout scores
   c. Compute ECE, AUROC, Brier on heldout
   d. Set `passes = (ece <= 0.10) and (auroc >= 0.70)`
2. Select first definition (in registry order) where `passes=True`
3. If none pass → `selected="verifier"`, `status="FALLBACK"`
4. Serialize the winner's `IsotonicModel` as `{"thresholds": [...], "values": [...]}`

**Thresholds (from T3 spec):** `ECE_THRESHOLD = 0.10`, `AUROC_THRESHOLD = 0.70`.

### 4.5 Harness integration

Extend `benchmarks/harness.py`:

1. **`ItemScore`** gets a new field: `confidence_by_definition: dict[str, float]`
2. **Pipeline arm** runs all 7 extractors per item (self-consistency k=5 only when `--t3` flag is passed, to avoid 5× LLM cost in normal T2 runs)
3. **Receipt** gets a `t3_verdict` block (nullable — only populated when `--t3` is active)

The `--t3` flag is opt-in because self-consistency k=5 multiplies LLM calls by 5. T2 measurement runs without it.

---

## 5. Testing strategy

All tests in `vivy/tests/test_calibration.py`, TDD (RED → GREEN → REFACTOR).

### 5.1 Metric correctness (synthetic data with known answers)

| Test | Input | Expected |
|---|---|---|
| ECE perfect calibration | scores=labels in 10 bins | ECE = 0.0 |
| ECE worst case | all scores 1.0, all labels 0 | ECE = 1.0 |
| ECE known value | hand-crafted 10-bin distribution | ECE = 0.15 (or whatever the math gives) |
| AUROC perfect separation | scores=[0.9]*5 + [0.1]*5, labels=[1]*5+[0]*5 | AUROC = 1.0 |
| AUROC random | scores random, labels random | AUROC ≈ 0.5 |
| AUROC inverted | perfect negative correlation | AUROC = 0.0 |
| AUROC ties | all scores equal | AUROC = 0.5 |
| Brier perfect | scores=labels | Brier = 0.0 |
| Brier all wrong | scores=1−labels | Brier = 1.0 |

### 5.2 PAV isotonic regression

| Test | Input | Expected |
|---|---|---|
| Already monotonic | scores sorted, labels monotonic | Output = labels |
| Needs pooling | scores=[0.1,0.2,0.3], labels=[1,0,1] | All → 0.667 (pooled) |
| Constant | all labels=1 | All → 1.0 |
| Single sample | one pair | That label as float |
| Monotonicity invariant | any input | Output is non-decreasing |

### 5.3 Feature extractors

| Test | Scenario | Expected |
|---|---|---|
| Each extractor returns [0,1] | Normal input | Score in [0,1] |
| Missing signal → 0.0 | `funnel_confidence=None` | Score = 0.0 (fail-closed) |
| Self-consistency | 3/5 agree | Score = 0.6 |
| Self-consistency empty | `k_samples=None` | Score = 0.0 |
| Verifier all ok | 2 tools, both ok | Score = 1.0 |
| Verifier has failure | 2 tools, 1 fail | Score = 0.0 |
| Verifier no tools | `tool_results=None` | Score = 0.0 |

### 5.4 T3 evaluation pipeline

| Test | Scenario | Expected |
|---|---|---|
| One definition passes | synthetic data where def "a" has ECE=0.05, AUROC=0.85 | `selected="a"`, `status="PASS"` |
| None pass | all definitions have ECE>0.10 | `selected="verifier"`, `status="FALLBACK"` |
| Verdict serializes | any | `isotonic_model` is JSON-safe dict |
| Multiple pass → first in order | defs "a" and "b" both pass | `selected="a"` |

### 5.5 Edge cases

- Empty labels list → all metrics return 0.0, no crash
- All labels identical → AUROC = 0.5
- Dev split = all items (no heldout) → raises `ValueError`
- Dev split = empty → raises `ValueError`

---

## 6. Constraints

1. **Zero new dependencies** — pure Python for PAV and AUROC. Numpy permitted (already in `funnel/`, `training/`).
2. **D-7 compliance:** held-out is outside the repo. Calibration fits on dev only. Held-out scores are computed and measured but never used for fitting.
3. **Gate 9 (honest capability):** every metric lands in the receipt. No "calibrated" claim without a measurement receipt. U-09 in `CAPABILITY_LEDGER.md` closes when T3 verdict has `status="PASS"` with receipts.
4. **Scope boundary:** measurement + calibration only. No runtime integration with `decision_controller`, `epistemic_gate`, or `funnel`. That is GĐ2 work (O-06/O-08).
5. **Self-consistency cost:** k=5 runs only under `--t3` flag. Normal T2 harness runs skip it to avoid 5× LLM cost.
6. **Isolate, don't delete:** existing confidence code (`funnel/filter.py`, `graph_bridge.py`, `calibration.py`, etc.) stays untouched. The new module reads from them; it does not replace them. Old definitions become "ablation features" by being measured alongside the new ones — no code is marked `[ISOLATED]` by this work package.

---

## 7. Deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Feature extractors | `vivy/benchmarks/calibration/features.py` |
| 2 | PAV isotonic regression | `vivy/benchmarks/calibration/isotonic.py` |
| 3 | ECE / AUROC / Brier | `vivy/benchmarks/calibration/metrics.py` |
| 4 | T3 evaluation pipeline | `vivy/benchmarks/calibration/evaluate.py` |
| 5 | Harness extension | `vivy/benchmarks/harness.py` (modify) |
| 6 | Unit tests | `vivy/tests/test_calibration.py` |
| 7 | T3 receipt schema | `benchmarks/calibration/evaluate.py` (T3Verdict) |
| 8 | CAPABILITY_LEDGER update | `docs/CAPABILITY_LEDGER.md` — U-09 → receipt |

---

## 8. Success criteria

| Criterion | Measure |
|---|---|
| T3 gate | At least one definition: ECE ≤ 0.10 AND AUROC ≥ 0.70 on held-out |
| Metric correctness | All synthetic-data tests pass with exact expected values |
| PAV monotonicity | `IsotonicModel.predict()` is non-decreasing for any input |
| Fail-closed | Missing signals → 0.0, never silently 1.0 |
| Zero new deps | `pyproject.toml` unchanged |
| Health stack | `tests/` baseline grows (currently 982 passed); mypy 66 source files clean; ruff clean |

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| No definition reaches ECE ≤ 0.10 | Medium | Spec explicitly allows `FALLBACK` to verifier. T3 says "stop if none pass." |
| Self-consistency k=5 too expensive on CPU | High | Only runs under `--t3` flag. T2 runs skip it. |
| Small dev set (32 items) → isotonic overfit | Medium | Isotonic is non-parametric and conservative. Report both dev and heldout metrics. |
| Existing extractors return garbage for benchmark items | Medium | Fail-closed to 0.0. T3 measures what it gets. |

---

## 10. Out of scope (GĐ2)

- Runtime integration (confidence → HALT / insufficient_evidence decisions)
- Isotonic model deployment (serving calibrated scores at inference time)
- O-06 tribunal (real sandbox re-execution, log-odds calibrator)
- O-08 NPS loop closure (hypothesis generator, executor, confidence writeback)
- Ablation study infrastructure (running old definitions as features in a learned model)

---

## Changelog

| Date | Agent | Change |
|---|---|---|
| 30/09/2026 | Claude Code | Initial design — Approach A (benchmarks-side calibration module). User approved scope: measurement + calibration only. |
