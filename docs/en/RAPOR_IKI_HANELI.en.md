# REPORT — TWO-DIGIT INPUT measurement (STAGE 3, EXPLORATORY)

Translation of `RAPOR_IKI_HANELI.md`; the Turkish original is authoritative.

Pre-registration committed **before** the measurement: **`d6bd546`**. Code:
`numcog/two_digit_probe.py` · result CSV: `numcog/results_release/two_digit.csv`.
Language: **"in this data, in this model, on this grid"**. **EXPLORATORY** — it does not change
phase 4E's pre-registered criteria.

## 1. Question, expectation, criterion (pre-registered)

- **Question:** does the calculator work with **two-digit inputs** (at least one operand ≥ 10)?
- **Expectation:** **it works if the result ≤ 81** — because the core is only an `n → n±1` **table**
  (state 0..81); operand magnitude changes the **number of loop steps**, not the table.
- **Refutation threshold:** accuracy **< 99%** (per operation). **Operations above 81 are NOT
  measured** (the interface rejects them).

## 2. Design (fixed before the measurement)

| item | value |
|---|---|
| seeds | **20 accepted seeds**: `[0, 3, 5, 7, 8, 9, 10, 11, 12, 14, 15, 20, 21, 22, 23, 24, 25, 28, 31, 32]` (`results_p4e/final81_seeds.csv`, `table == 1.0`) |
| sampling | per seed, random integers `a,b ∈ [1,81]`, **at least one operand ≥ 10** |
| filter | expected result **[0,81]** (subtract `a ≥ b`; add `a+b ≤ 81`; multiply `a·b ≤ 81`; divide `b ≥ 1`) |
| items | **200 pairs per operation × 20 seeds = 4,000** (total **16,000**) |
| criterion | expected == (core + controller) result; for divide **quotient and remainder** |

## 3. Results (raw)

```
=== SUMMARY (two-digit input; 20 seeds x 200 pairs/op) ===
  add       accuracy=1.0000 +- 0.0000 (n=20 seeds, 4000 pairs) -> WORKS (>= 99%)
  subtract  accuracy=1.0000 +- 0.0000 (n=20 seeds, 4000 pairs) -> WORKS (>= 99%)
  multiply  accuracy=1.0000 +- 0.0000 (n=20 seeds, 4000 pairs) -> WORKS (>= 99%)
  divide    accuracy=0.9935 +- 0.0023 (n=20 seeds, 4000 pairs) -> WORKS (>= 99%)
  OVERALL accuracy=0.9984 | pairs=16000 | 349 s
  threshold 99% -> PASSED
```

**Expectation SUPPORTED:** with two-digit inputs (result ≤ 81) the **overall accuracy is 0.9984 ≥
0.99** ✓; `add`/`subtract`/`multiply` are **exactly 1.0000** ✓.

## 4. Why is `divide` 0.9935? (mechanism — MEASURED)

The source is **not the fly but the CONTROLLER**: the historical `CyborgFly.divide` loop is
`while n >= b and q < 50`; **when the quotient reaches 50 the loop stops early** and the result is
truncated. Verification (historical controller, cached weights):

| expression | result | expected | match |
|---|---|---|---|
| `81/1` | **50** | 81 | ✗ (loop stopped at `q<50`) |
| `60/1` | **50** | 60 | ✗ (same) |
| `50/1` | 50 | 50 | ✓ |
| `81/2` | 40 | 40 | ✓ (80 fly calls) |

The deviation rate is consistent with this mechanism: in the sampling the probability of `b=1` and
`a ≥ 51` is ≈0.5% → measured 0.65% ✓ *in this data, in this model, on this grid*.

**Therefore the interface was hardened (a GUARD added after the measurement; the measurement design
and thresholds did NOT change):** `fly_calc.run` now raises an **explicit error** when the **expected
quotient ≥ 50** ("bölüm 81 >= 50: kontrolcünün durma sınırı (q < 50) sonucu kırpar") → **no silent
wrong answer** ✓. Because the probe calls the controller **directly** (not through the interface), the
guard **does not change the measurement** ✓ — the measurement reports the historical controller's
**actual** behaviour ✓.

## 5. Interpretation and limits

- **Expectation confirmed:** two-digit input is **not a new capability** for the core; the core only
  does `n → n±1`, a bigger operand just means **more steps** (e.g. `81/2` = **80 fly calls**).
- **"MULTI-DIGIT ARITHMETIC" DOES NOT EXIST**; the two-digit (tens/units) design was **NOT
  IMPLEMENTED** — this measurement only probes input magnitude ✓.
- **Results above 81 were not measured**; the interface rejects them with an **explicit error** ✓.
- **Controller limit:** quotient ≥ 50 → the historical loop truncates (above) ✓; the interface rejects
  it ✓.
- Other limits are as in phases 4E/7-0: **single connectome** (hemibrain 783), **simulation**,
  **arbitrary number→VPN assignment**, **the calibration gate rejects 46% of seeds**, **the state is in
  the controller, not the fly**.
