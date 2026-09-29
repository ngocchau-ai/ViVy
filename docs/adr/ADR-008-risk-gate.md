# ADR-008: RiskGate — a fail-closed safety ally replaces "CẤM GÁC CỔNG LẬP TRÌNH"

**Status:** Accepted · **29/09/2026** (decision owner: project owner, via D-3)
**Supersedes (deliberately):** the "No Programmatic Gatekeepers" rule in
`docs/TECHNICAL_DIRECTION.md` (kept as `[REPLACED 29/09]`)
**Related:** `vivy/src/vivy/hands/risk_gate.py`,
`vivy/src/vivy/hands/mt5_executor.py`, `vivy/src/vivy/core/inference.py`,
`vivy/src/vivy/core/prompts.py`, `vivy/tests/test_risk_gate.py`

---

## Context — what the rule used to be, and what it cost

`docs/TECHNICAL_DIRECTION.md` forbade any programmatic filter in the Hands
layer, in four places (`:2321`, `:2350`, `:2417`, `:2439`, `:2470`):

> **CẤM tuyệt đối bộ lọc cản hay gác cổng lập trình cứng trong Python.**
> *(Absolutely forbid obstructing filters or hard programmatic gatekeepers in Python.)*

and `vivy/src/vivy/core/prompts.py` told the model the same thing:

> **CẤM GÁC CỔNG LẬP TRÌNH:** No hardcoded filters, velocity limits, or
> risk-reward caps exist in code. All risk management … must originate 100%
> from your intelligence.

The intent was good: ViVy is the brain, and a hardcoded strategy filter would
replace the model's judgement with a worse one. The implementation was not.
The review of 29/09/2026 measured the result (G-01, G-02, G-03):

* **0 of 30** adversarial order attempts were stopped.
* `float(raw_json.get("volume", 0.01))` and `float(raw_json.get("stop_loss",
  0.0))` **invented** numbers the model never wrote. A Stop Loss of `0.0` is
  not a judgement — it is an unprotected position, silently created by Python.
* `float("nan")` and `float("inf")` parsed cleanly into a decision and went
  straight to the terminal.
* An entry with no reference price could carry a Take Profit *below* a BUY
  price. Nothing checked.

The rule that was meant to keep the model free to reason also kept every
physically invalid order free to reach MT5.

## Decision

**D-3 (project owner, 29/09/2026):** replace "CẤM GÁC CỔNG LẬP TRÌNH" with a
**fail-closed RiskGate** in front of order execution.

### Scope of the override — what RiskGate is

A **safety ally**, never a strategy. RiskGate may refuse an order only on
grounds that are physically invalid or outside a *declared* risk envelope:

| Check | Refuses |
|:--|:--|
| volume parse | missing, non-numeric, `NaN`, `±Inf`, bool |
| volume bounds | `<= 0`, below `min_volume`, above `max_volume` |
| stop loss / take profit | missing or zero on a BUY/SELL |
| SL/TP side vs reference price | `SL >= price` on BUY, `SL <= price` on SELL (and the mirror for TP) |
| symbol allow-list | anything outside `RiskLimits.allowed_symbols` |
| reference price | an entry with no price at all (fail-closed — never guess) |
| action name | unknown / missing action |

### What RiskGate may NEVER do

* choose *whether* to trade, *when* to enter, or *how much edge* an idea has
* apply a risk-reward ratio, a conviction cap, a velocity limit, a
  max-drawdown-of-the-day rule, or any strategy-shaped filter
* call a model, read a prompt, or change its mind based on the thought text

ViVy still picks the action, the symbol, the volume and the SL/TP. The gate
only refuses orders that could not be valid *as orders*.

### Other decisions bundled here

1. **Paper trading is the default.** `RiskLimits(paper_trading=True)` unless a
   caller passes `paper_trading=False` **explicitly**. An accidental
   `execute_decision` cannot place a real order.
2. **Parsing is strict.** `parse_finite_float` has **no default**. A missing or
   garbage number raises. This also replaced the invented `0.01` / `0.0`
   defaults in `vivy/core/inference.py` (G-02).
3. **Every receipt names the gate's verdict.** `ExecutionReceipt.risk` carries
   the `RiskVerdict.to_dict()`, so a rejected order is never silent.
4. **The model is told.** `VIVY_TRADING_SYSTEM_PROMPT` now says orders pass a
   RiskGate and that it is an ally — the old "no gatekeepers" line is
   `[REPLACED]`. A model that believes no check exists will produce orders the
   check must reject all day.

## Consequences

* **Positive:** 0 of 60 adversarial order shapes reach the terminal (T10).
  Invented Stop Losses are impossible. A NaN volume cannot be an order.
  Reproducible: the same decision dict yields the same verdict.
* **Negative / accepted:** the model can no longer place an order with SL on
  the wrong side of price, or a 100-lot position. That was never judgement —
  it was a bug that reached the terminal. Anyone who *wants* an exotic order
  shape must change `RiskLimits` explicitly, which is the point.
* **Does not touch:** strategy, entry timing, symbol choice, position sizing
  policy, or the research branches (SVD funnel, unitary memory, MoE). Those
  remain governed by their own ADRs and by D-2 (budget-limited, preregistered).

## Out of scope (deliberately)

* **WP-9** owns the *definition* of `confidence`. ADR-008 only requires it to
  be finite and in `[0, 1]` when present.
* **D-4** (Ollama vs Cautreo backend) is unchanged; RiskGate is backend- and
  model-independent.
* Live-order routing to an actual MT5 terminal. `MT5Executor` still has no
  network call to a broker; "LIVE" only means the gate was configured for it.

## Test evidence (T10)

`vivy/tests/test_risk_gate.py` — 60 adversarial decision shapes across the
table above, all paper-trading, all asserting `verdict.allowed is False` (or a
raised `RiskGateError` via `require`). Plus `tests/unit/test_eyes_hands.py`
asserts the executor surfaces `status="REJECTED"` with the gate's reasons.

## Revision history

| Date | Change | By |
|:--|:--|:--|
| 29/09/2026 | Initial — D-3 replaces "CẤM GÁC CỔNG LẬP TRÌNH" | Claude Code (per project owner decision D-3) |
