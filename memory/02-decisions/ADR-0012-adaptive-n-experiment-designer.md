# ADR-0012: Adaptive N Controller, Information-Gain Ranker, and Experiment Bundler

## Status

Accepted

## Context

Stage 4 (`ARCHITECTURE.md` Section 7 & 13.5) requires:
1. Adaptive allocation of hypothesis population size $N_h$ based on uncertainty density, contradiction count, and budget constraints.
2. Deduplication and merge candidate detection for hypotheses with identical or highly overlapping claims.
3. Expected information gain $E[IG]$ ranking of hypotheses.
4. Experiment bundling to produce discriminative `ExperimentContract` contracts testing multiple hypotheses simultaneously.

## Decision

### 1. Module Ownership

`src/nps_core/adaptive_n/` owns `AdaptiveNController`, `InformationGainRanker`, `ExperimentBundler`, and domain errors (`AdaptiveNError`, `BudgetExceededError`).

### 2. Adaptive Allocation and Deduplication

`AdaptiveNController.compute_target_n` calculates target $N_h$ subject to `max_budget`. `detect_duplicates` returns pairs of thoughts with matching claims for merging.

### 3. Ranking & Bundling

`InformationGainRanker.rank_hypotheses` orders hypotheses by $E[IG] = (1 - confidence) \times risk\_if\_wrong \times information\_need$. `ExperimentBundler.bundle_needs` packages verification needs into multi-hypothesis `ExperimentContract` objects.

## Consequences

- Stage 4 exit criteria are 100% fulfilled.
- Standard-library runtime dependencies only; zero external I/O.
