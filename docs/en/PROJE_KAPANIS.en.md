# PROJECT CLOSING (v1 + v2) — full record of what was measured

Translation of `PROJE_KAPANIS.md`; the Turkish original is authoritative.

Date: 2026-09-20. **No new measurement**; every number is source-linked. Language rule: **"in this
data, in this model, on this grid"**. Forbidden expressions were not used: "we proved", "flawless",
"the fly does mathematics", "multi-digit arithmetic", "language logic", "connectome gives a special
advantage".

## 1. Goals and their status

| # | goal | status (in this data, in this model, on this grid) | evidence |
|---|---|---|---|
| 1 | connectome for **number/coding** | **partial:** 9×9 cosine structure via VPN→KC; **number→VPN assignment arbitrary** | `RAPOR_FAZ_1.md` |
| 2 | **comparison** ("which is bigger") | in-range **0.992 ± 0.037**; **out-of-range 0.208 ± 0.131**; real↔shuffle **indistinguishable** | `RAPOR_FAZ_2.md` |
| 3 | **rule** learning (n±1) | memorisation works; **rule (G2) = 0.000 in all arms** | `RAPOR_FAZ_3.md`, `3c.md` |
| 4 | **calculator** (gated, N=81) | **works:** add/sub/mul/div **1.0000**; chain p^k=1.0 (k=0..81) — **only in the 54/100 calibration-passing seeds** | `RAPOR_FAZ_4E.md` |
| 4b | **95% table** at N=81 | **not met** (best **93.3%**) | `RAPOR_FAZ_4F.md`, `frozen.json`=**null** |
| 5 | M1–M4 | M2/M3/M4 **separate**; **M1 degenerate** | `RAPOR_FAZ_5.md` |
| 6 | CX **ring geometry** | **could not be constructed** (H6.1–H6.3, H6b.2 refuted) | `RAPOR_FAZ_6_0.md`, `6_0b.md` |
| 7 | **network carries state** | **No.** Fair gain: k≤8 (k=6 **0.990**) but **k=10 collapses**; **not superior to surrogates** | `RAPOR_FAZ_7_1.md`, `7_2.md` |
| 8 | **rule/extrapolation** (T3) | **None.** S1-far **0.002**, S2 **0.128** — **below chance** (0.50) | `RAPOR_FAZ_7_3.md` |
| 9 | **biological learning rule** (MB) | **works** (G1 **0.982**; T1 N≤4 **0.971**); **no connectome-specific advantage** (ER equal/better) | `RAPOR_FAZ_8.md` |

**Verdict:** *in this data, in this model, on this grid* two things **work** — the **gated table
calculator** and **DAN-gated KC→MBON plasticity**; a **connectome-specific task advantage could not
be shown**.

## 2. Phase-by-phase numbers (source-linked)

[TRANSLATOR NOTE: the Turkish §2 table gives, per phase, the measured question, key numbers and
source file. It is identical in content to the **already-bilingual** table in
`numcog/RESULTS_SUMMARY.md`; refer to it so the numbers cannot diverge.] Anchors: 4E accepted
**54/100 (54.0%, 95%CI [44.3, 63.4])**, add/sub/**mul**/**div = 1.0000**, chain **17,496 steps**;
7-2 k=6 **0.990**, k=8 **0.710**, k=10 **0.227**, gain **g=40 (grid edge)**; 7-3 S1-far **0.002**, S2
**0.128**, T3-P **0.508**; 8 G0 (MBON 96, k=12, KC→MBON 35,204), G1 **0.982**, T1 N≤4 **0.971**,
**ER 1.000**, T6a **0.678**.

## 3. WHAT COULD NOT BE MEASURED / DONE

| what | why |
|---|---|
| **Multi-digit arithmetic** | **Not implemented** — the two-digit (tens/units) design was written but **never coded**; result space bounded by **0..81** |
| **95% table criterion at N=81** | **Not met** (best 93.3%); `results_p4f/frozen.json` = **null** |
| **CX ring geometry** | **Not constructible in this data release** (H6.1–H6.3, H6b.2 refuted) |
| **Rule learning (n±1)** | **0.000** in all arms (Group 2 = 3 items) |
| **State carried by the network** | k≤8 yes, **k=10 no**; **not superior to surrogates** |
| **Connectome-specific advantage** | **Not demonstrated in any phase** (2, 3, 3c, 4E, 5, 7-1, 7-2, 7-3, 8) |
| **T3 rule/extrapolation** | **Collapsed** (below chance) |
| **T7, T6c** | **Labelled EXPLORATORY and NOT RUN** |
| **Two-digit grid sweep** | Only **one setting** measured (pre-registered design) |
| **Live fly** | **Simulation**; single connectome (hemibrain 783) |
| **Ollama/LLM path dead?** | **Not verified** — referenced by `server.py`/`game_loop.py` → `[VERIFY]` |
| **E-mail exposure** | No secrets in tracked files; **git author e-mail in history** → fix = rewrite → **owner's call** |
| **Historical large blobs** | **87.15 MB** + **11.12 MB**, removed but **still in history** → `[decision]` |

## 4. What did the FLY do alone, what did the CONTROLLER do?

| job | fly | controller (Python) |
|---|---|---|
| single step `n → n±1` (0..81) | **entirely the fly** (trained readout) ✓ | — |
| counter, loop count, stop condition | — | **controller** ✓ |
| add/sub/mul/div flow | only the single steps | **controller** ✓ |
| **remainder** (division) | — | **controller** ✓ |
| reading/reporting the output | — | **controller** ✓ |
| state (which number we are on) | **does NOT carry it** | **controller** ✓ |

**Dynamic evidence:** the **call count** is the same with the real and **fake** core (`3+5`→5,
`6x7`→42) but the **result differs** (`3+5`: 8 vs 68) → the controller builds the loop, the **core
supplies the answer** ✓ (`RAPOR_HESAP_MAKINESI_BUTUNLUK.md` §2.B2). Scientifically: the calculator is
a **table machine**, it does **not learn arithmetic**; MB learning **exists** but works
**independently of the wiring**.

## 5. Artifacts caught (source-linked)

[TRANSLATOR NOTE: the Turkish §5 table lists **17** artifacts with phase / how caught / commit. Key
entries, with their sources: phase-0 **NaN groupby trap** (`RAPOR_FAZ_5.md:19`, `RAPOR_FAZ_7_0.md`
§0) · **MSE/continuous-readout fragility** (`RAPOR_FAZ_4A.md:32`) · **insufficient epochs**
(`HIPOTEZLER.md:359`) · **degenerate M1** (`RAPOR_FAZ_5.md:128-139`) · **float32 overflow/NaN**
(`RAPOR_FAZ_4F.md:42-45`) · **dead unit** (`RAPOR_FAZ_3c.md:55`) · **ρ=1 normalisation artifact**
(7-1→7-2) · **component-structure warning** (`results_p7_2/spec_summary.csv`: real 239 SCCs vs ER 2) ·
**grid edge** (7-2, g=40) · **`np.polyfit` singular system** (commit `3e243a9`, before measurement) ·
**jitter sensitivity** (7-3) · **`np.clip(..., out=mask)` copy bug** (phase 8, commit `a69a8d9`) ·
**degenerate `divide` baseline** (closing/1: 36/81 pairs never call the core) · **controller `q < 50`
stop bound** (closing/3: `81/1 → 50`) · **substitute-test mistake** (closing/2) · **wrongly committed
87 MB / 12 MB caches** (`70bbb0f`, `838aae1`). One claimed artifact — the **`np.bool_` summation
error** — **could not be traced in this repository** → `[VERIFY: which phase/commit]`. The verbatim
table is in the Turkish original.]

## 6. Limitations (whole of v1+v2)

**Single connectome** (hemibrain 783) · **simulation** · **number→VPN and operator→ALPN assignments
arbitrary** (only the **wiring** is real) · **NT signs are an ASSUMPTION** (KC = +1/ACh fixed) · the
**calibration gate rejects 46% of seeds** (accepted 54.0%, 95%CI [44.3, 63.4]) · **no 95% criterion at
N=81** (best 93.3%) · **two-digit design not implemented** · **Group 2 = 3 items**, single
architecture (feedforward KC + linear readout) · **phase 2b post-hoc**; in 4A-2 the reference arm
scored full marks (trivial criterion); **M1 test degenerate** · **shuffle comparisons n=30/20, limited
power** ("indistinguishable" ≠ "no difference") · **MB compartments are an INFERENCE** (k=12,
unbalanced; not real anatomy) · **valance assumption untested**, **US not type-selective** · **single
plasticity-rule form** (LTD only) · **phases 7-2, 7-3, 8 are EXPLORATORY re-tests** (HARKing risk
accepted) · grids fixed.

## 7. What we do NOT claim

1. **"The fly does mathematics"** — no: the core only does `n→n±1`; **counter/loop/remainder are in
   the controller**.
2. **"Multi-digit arithmetic"** — **does not exist**; the two-digit design was **not implemented**.
3. **"Language logic"** — **no language model in `numcog/`** (the word classifier is the **separate**
   `flyputer/` app).
4. **"The connectome gives a special advantage"** — it **did not separate**; not shown in any phase.
5. **"It learns rules"** — the rule tests (G2/T3) are **below chance**.
6. **"The network carries state"** — partially for k≤8, **not at k=10**, and **not superior to
   surrogates**.
7. **Biological accuracy** — NT signs are an **assumption**, compartments an **inference**, input
   choice **arbitrary**.

## 8. Future work (all **NOT DONE**)

- **Labelled CX data** (wedge/glomerulus ROI, per-synapse table) → retry the ring geometry.
- **Neuromodulation**: non-DAN modulators (OA/5-HT), dopamine dynamics, **LTP + LTD together**.
- **Synaptic unreliability** (stochastic release) and a **time-constant grid**.
- **Implement the two-digit (tens/units) design** → the only route to multi-digit arithmetic.
- Let **MBON→DAN and DAN→KC feedback** participate in learning (currently feed-forward only).
- **Cross-validation with a connectome other than hemibrain.**

