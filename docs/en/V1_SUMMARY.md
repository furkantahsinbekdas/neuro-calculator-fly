# V1 SUMMARY — phase 0–6-0b closing summary (NO new measurement)

Translation of `V1_OZET.md`; the Turkish original is authoritative.

Date: 2026-09-20. This document rests **only on the existing reports**; it contains **no new
measurement**. Language rule: **"in this data / with this method / on this grid"**. Expressions such
as "we proved", "flawless", "definitively closed" are **not used**.

## 1. What was measured, what was found (summary)

| Phase | Question | Result (in this data, with this method) |
|---|---|---|
| 0 | VPN→KC neuropil/label structure | Confined to CX (EB/PB) neuropils; a small γ-specific VPN→KC path exists; **no** wedge/glomerulus label |
| 1 | Number coding (VPN→KC) | Real VPN→KC + top-k builds a 9×9 cosine structure; the number→VPN assignment is **arbitrary** |
| 2 | "Which is bigger" | In-range test **0.992 ± 0.037**; **out-of-range 0.208 ± 0.131**; real vs shuffle **indistinguishable** |
| 2b | Extrapolation diagnosis (EXPLORATORY) | Edge-padding / shared-readout diagnostics; added after seeing the phase-2 results |
| 3 / 3c | Rule vs memorisation | Memorisation (adjacent targets) works; **rule (G2) = 0.000 in all arms**; real/shuffle/overlap-control did not separate |
| 4A / 4A-2 | Calculator core | An n±1 table can be built with a nominal readout; **state, counter and loop are in the controller** |
| 4B-0 | Multiplication + CX survey | Multiplication 0.790 (N=40 **range** limit); CX types (EPG 51, PEN 42, Delta7 42) and edge counts measured |
| 4C | N=40 table error diagnosis | **ep10x frozen**; errors concentrate at the edges (n=0,1,38,39,40) |
| 4D / 4E / 4F | N=81 capacity | No grid cell passed the **95%** criterion (best **93.3%**); **H4d.1/H4f.1 refuted** |
| 4E | N=81 diagnosis + calibration | Errors at the edges + **code collision**; **closed form = delta rule**; shuffle: **indistinguishable** |
| 5 | Structural analysis (M1–M4) | M2/M3/M4 **separate**; **M1 degenerate** (a function of the degree sequence); no task difference under shuffle |
| 6-0 / 6-0b | CX ring geometry | **The ring could not be constructed in this data release** (H6.1–H6.3 and H6b.2 refuted) |

## 2. Engineering status (the phase-4 chain)

- **Gated calculator:** at N=81, all 1..9 add/subtract/**multiply**/**divide = 1.0000** and the chain
  p^k = 1.0 (k = 0..81) — **but only in the 54/100 seeds that pass the calibration gate**
  (rejection rate **46.0% [36.6–55.7]**). The gate is a **controller-side quality check**; it is not
  rule learning.
- **State is in the controller:** counter, loop, stop condition, feedback and readout are in the
  controller; **the fly does not carry state** (this is v1's clearest architectural feature).
- **The 95% criterion was not met at N=81 on this grid** (best 93.3%: σ=2.0, top-k=80, padded); the
  float32 overflow in the top-k=120 cells is **numerical divergence**, it carries **no capacity
  information**.
- **The two-digit fallback** was labelled a design; it was **not implemented**.

## 3. The two clearest limits

1. **The real connectome did not separate from the shuffle/control arms on task performance**
   (phases 2, 3, 3c, 4E, 5). Although the structural measures (M2–M4) separated, a **task** advantage
   **could not be shown in this data, in these architectures, on these grids**.
2. **The CX ring geometry could not be constructed in this data release:** the soma-based tests
   (H6.1–H6.3) and the coordinate-free spectral test (H6b.2) were refuted; there is **no**
   wedge/glomerulus ROI label and no per-synapse table; a ~80° mismatch between somas and PEN input
   centres was measured.

## 4. Limitations (for the whole of v1)

- **Group 2 = 3 items**, **single architecture** (feedforward KC + linear readout) → the rule results
  are specific to this architecture; this is not a general judgement.
- Because the **entire task behaviour lives in the controller**, the claim "the fly computes" was
  **not** measured; what was measured is that **the code + readout layer can build the n±1 table**.
- The **number→VPN and operator→ALPN assignments are arbitrary**; the only real part is the
  **VPN→KC / ALPN→KC wiring**. The thermometer code is an **external aid**.
- **Phase 2b is post-hoc**; some criteria are trivial (in 4A-2 the reference arm scored full marks);
  the **M1 test is degenerate** (it cannot be tested against a degree-preserving null).
- Shuffle comparisons have **n=30 and limited power**; "indistinguishable" ≠ "no difference".
- **Simulation**; not a live fly. **Single connectome sample** (hemibrain 783).
- The learning rule / sensitivity (lr, float32) was **not changed** across the grid; changing it would
  have been a DESIGN CHANGE and was not done in these phases.

## 5. Open question handed to phase 7

**Can the network's internal state carry the number, instead of the controller?** In v1 the state was
**entirely** in the controller; that was v1's deliberate design and it is **v2's actual question**.
Phase 7-0 **pre-registers** the framework for that question and **measures the sub-network
candidates**; it runs **no dynamic experiment**.
