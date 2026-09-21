# INTEGRITY REPORT — CALCULATOR (CLOSING STAGE 1)

Translation of `RAPOR_HESAP_MAKINESI_BUTUNLUK.md`; the Turkish original is authoritative.

Date: 2026-09-20. Question: **does the fly core do the arithmetic, or does Python?**
Language: **"in this data, in this model, on this grid"**. Sources: a static read of `calculator.py`,
`phase4c.py`, `operator_diagnosis.py` + the output of `numcog/tests/test_calculator_integrity.py`.
**No historical file was changed** (the test and the service are **new** files: `fly_calc.py`,
`tests/test_calculator_integrity.py`, `build_fly.py`).

## 1. STATIC CHECK — is there direct arithmetic on the operands?

| file / function | arithmetic line | what it produces | legitimate? |
|---|---|---|---|
| `FlyCore._result` | `min(max(n + (±1), 0), N)` | **expected value** (training target + `train_accuracy`) | ✓ **not the answer path** |
| `od.clip_result` | `min(max(n ± 1, 0), N)` | expected value (measurement comparison) | ✓ not the answer path |
| `CyborgFly.add` | `range(b)`, `n = self._step(n, '+')` | loop bound + **result from the core** | ✓ |
| `CyborgFly.subtract` | `range(b)`, `self._step(n, '-')` | same | ✓ |
| `CyborgFly.multiply` | `n = 0`, `range(b)`, `self.add(n, a)` | accumulator init + loop | ✓ (value comes from `add`) |
| `CyborgFly.divide` | `n = a`, `q = 0`, `while n >= b and q < 50`, `q += 1` | start / counter / **stop condition** (+ safety bound) | ✓ comparison + counter, not arithmetic on values |
| `measure_calculator` | `a * b`, `a // b`, `b * (a // b)` | **expected value + chain metadata** | ✓ measurement/comparison |
| `phase4c.Core.step` | `code(n,op) @ W.T + b`, `argmax`, `exp(s-s.max())` | **the readout that produces the answer** | ✓ this **is** the model |
| `gauss_axis` / `code` | `A[n]` | **code-table lookup** (no arithmetic on n) | ✓ |
| `fit_fast` / `_fit32` | delta-rule training | weights | ✓ **learning**, not answer production |
| **`fly_calc.expected`** (NEW) | `a+b`, `a-b`, `a*b`, `a//b`, `a%b` | expected value: **range validation only** | ✓ labelled as such in code |

**STATIC RESULT:** the returned result is **not produced by direct arithmetic on the operands**; the
only production path is `core.step` (a trained readout) plus the controller's **loop/counter** logic.

## 2. DYNAMIC CHECK — raw results

Command: `python -X utf8 -m numcog.tests.test_calculator_integrity` · **duration 1 s** · core:
`numcog/fly_weights/fly_N81_seed0.npz` (phase-4E calibration-passing **seed 0**, table **1.0000**).
**RED: 0 / 34 → ALL TESTS PASSED.**

**A. Real core** (all 1..9 pairs, `od.calc_measure` — the historical measurement function):
add **1.0000** · subtract **1.0000** · multiply **1.0000** · divide **1.0000** · table (164 inputs)
**1.0000**.

**B. FAKE core (random output) vs design baselines:**

| op | real | **fake** | design baseline ("most frequent answer") |
|---|---|---|---|
| add | 1.0000 | **0.0000** | 0.1111 |
| subtract | 1.0000 | **0.0123** | **0.5556** (45/81 pairs give `max(a-b,0)=0`) |
| multiply | 1.0000 | **0.0000** | 0.0494 |
| divide | 1.0000 | **0.4815** | **0.4444** (in 36/81 pairs with a<b the loop never runs) |
| **mean** | 1.000 | **0.1235** | — |

**B2. Decision evidence — the call count does not depend on the core:** `3+5` 5 calls (real) vs 5
(fake) but results **8 vs 68**; `9-4` 4 vs 4; `6x7` 42 vs 42; `8-3` 3 vs 3.
→ The **controller** builds the loop; the **answer comes from the core**.

**C. Step counts (exact asserts):** `add(3,5)`=5, `subtract(9,4)`=4, `multiply(3,4)`=12,
`divide(9,4)`=8 calls (q·b = 2·4) → results 8, 5, 12, (2, remainder 1) ✓.

**D. Boundary behaviour (no silent wrong answer):** `9x9`, `81+0`, `0+0`, `9/1`, `8-8` **work**;
`80+5` (85), `82+0` (82), `9x10` (90), `3-5` (−2), `0-1` (−1), `45+45` (90) → **explicit error**
("sonuç 85 > 81: sinek tablosu 0..81 ile sınırlı" / "… (negatif yok)").

## 3. THE FIRST RUN WAS RED — not hidden

With the arbitrary threshold "all ops < 0.30" the divide value came out **0.4815** → RED.
Investigation: in `divide(a,b)`, **36/81 pairs have a < b so the loop body never executes** → q = 0 =
the correct answer **without ever calling the core** → baseline **36/81 = 0.4444**. Likewise in
`subtract`, **45/81** pairs have the expected value 0 → baseline 0.5556. So this is **not** evidence
of "Python computing"; it is the **degenerate baseline of the historical functions**.
→ The threshold was replaced by the **design-computed baseline** (`design_baselines()`), and B2 was
added. **Honest note:** `divide = 1.0000` is **36/81 without the core** (trivial); "divide 100%" must
not be read as core performance. For `add`/`multiply` there are no trivial pairs ✓.

## 4. CONCLUSION

1. **The fly does the arithmetic, Python does not** ✓ — the only production path is `core.step`;
   the fake core breaks the answers (mean 1.000 → **0.1235**; `3+5`: 8 → 68) while the **call count is
   unchanged** ✓.
2. **State and logic are in the controller** (counter, loop, stop, remainder) ✓ — the fly only does
   `n → n±1`.
3. **Out-of-range operations are never silently mis-answered**: results >81 or <0 raise an **explicit
   error** ✓.
4. **Scope/limits:** digits 1..9 (measured domain); result 0..81; `divide` = **integer quotient +
   remainder**; two-digit input is accepted by the interface only if the result ≤ 81 and is labelled
   **EXPLORATORY**; **"multi-digit arithmetic" does NOT exist** (never implemented); no fractional or
   negative results.
5. **Simulation**; single connectome (hemibrain 783); number→VPN assignment **arbitrary**; the
   calibration gate rejects **46%** of seeds (phase 4E) → the shipped fly is **seed 0** (accepted ✓).

## 5. OUTPUTS OF THIS STAGE

`numcog/build_fly.py` → `numcog/fly_weights/fly_N81_seed0.npz` (**0.14 MB**, table 1.0000) ·
`numcog/fly_calc.py` · `numcog/tests/test_calculator_integrity.py` (one command, **1 s**, 34 checks,
0 red) · `numcog/__init__.py`, `numcog/tests/__init__.py` · this report.
