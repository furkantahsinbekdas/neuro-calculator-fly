# PHASES.en.md — English digest of every phase (Faz 0 → Faz 8 + closing package)

**What this file is.** A per-phase English digest of the `numcog/` science track: for each phase,
the *question*, the *design/pre-registration*, the *code and result files*, and the *verdict as
stated in the Turkish report*. It exists so that readers outside Türkiye can follow the work
without Turkish.

**What this file is not.** It is **not** a word-for-word translation and it is **not** a new
measurement. The Turkish reports (`numcog/RAPOR_FAZ_*.md`) and the raw CSVs under
`numcog/results_*/` remain the **authoritative** record; every number below is a pointer to them.
No Faz 0–8 result file was changed to write this digest.

**Language rule inherited from the project.** Results are phrased as *"in this data, with this
method, on this grid"* — never "proved", "perfect", "finally closed". That rule is kept here.

**Provenance rule inherited from the project.** Every phase pre-registered its hypotheses
**before** measuring (see `numcog/HIPOTEZLER.md` and the commit hashes in each report header).
Diagnostics added *after* seeing results are labelled exploratory and do **not** change the
pre-registered criteria.

---

## 1. Phase-by-phase table

| Phase | Question | Code | Result (as stated in the Turkish report) |
|---|---|---|---|
| **0** | Is there a real VPN → KC (visual projection → Kenyon cell) wiring substrate in the connectome data? | data read directly with pandas (no `flysim` / `cognitive_matrix` / `sniff` import) | Label counts and the VPN→KC edge set are reported in `RAPOR_FAZ_0.md`; this phase only *describes* the data — no model is trained |
| **1** | Can a number 1..9 be represented over real VPNs as a coarse population code? | `numcog/number_coding.py` | Gaussian tuning `a_i(n)=exp(-(n-p_i)²/(2σ²))` over 265 VPNs; positions and top-k fixed in pre-registration |
| **2** | Can a linear read-out compare two numbers ("which is bigger")? | `numcog/magnitude_compare.py` | Four read-out models compared (incl. `coarse_direct`); accuracy reported in `RAPOR_FAZ_2.md` |
| **2b** | *Exploratory*: why does extrapolation fail? | `numcog/extrapolation_diagnosis.py` | Diagnosis added **after** Faz 2; Faz 2 hypotheses/report were **not** modified |
| **3** | Can `n±1` be learned with the operator carried by smell (ALPN) and the number by vision (VPN)? | `numcog/arithmetic.py` | KC = `W_vpn·g(n) + W_alpn·op` (same 427 cells, top-k=40); output 0..10 |
| **3c** | Can rules be learned with a continuous/topological output instead of one-hot? | `numcog/rule_learning.py` | Target `t∈0..10` as a Gauss (σ=1.5) or thermometer vector over 265 units; MSE, lr=0.01, 500 epochs, full batch, no early stopping |
| **4A** | Engineering: build a sequential calculator with an **open** division of labour | `numcog/calculator.py` (`FlyCore` + `CyborgFly`) | The fly core does **only** one step `(n,op) → clip(n±1,0..N)`; the controller owns counter/loop/stopping |
| **4C** | Systematic start-up error and N=81 capacity | Faz 4C scripts | Selection criterion is **table accuracy only** (all 2(N+1) inputs learned); multiplication/division were **not** used for selection |
| **4D** | N=81 table capacity with long optimisation | Faz 4D lineage | Short report; same selection rule (table accuracy only) |
| **4E** | N=81 diagnosis, calibration and shuffle control | `numcog/phase4e_chain.py`, `phase4e_step4_calc.py` | Short report; same selection rule. **This is the cell that ships** in the release calculator (σ=1.5, top-k=80, epochs=25000, lr=0.05) |
| **4F** | N=81 with padding + wider σ (pre-registered) | `numcog/results_p4f/frozen.json` (value: `null`) | Pre-registered; the frozen cell is `null`, so the release weights were **not** taken from 4F |
| **5** | Two-part structural analysis of the connectome + phase closure | `numcog/structural_analysis.py` | Edge definition identical to Faz 0/1: `min_syn=1`, KC `cell_class="Kenyon_Cell"`, VPN `super_class="visual_projection"` → **427 KC × 265 VPN = 1,843 edges**; ALPN → 4,887 KC × 319 ALPN. Metrics on the binary matrix, only for KCs with ≥1 input |
| **6-0** | CX ring geometry: is there a physical ring layout in the data? | `numcog/cx_geometry.py` | Measurement only, **no dynamic simulation**; primary position column `soma_x/y/z`, angle plane = EPG soma plane (fixed in pre-registration) |
| **6-0b** | Coordinate-independent ring test (spectral) | `numcog/cx_spectral.py` | Edge definition identical to Faz 4B-0 (synapse table, `pre ∈ EPG`); measurement only, no dynamic simulation |
| **7-0** | Statics + framework pre-registration for the reservoir work | `numcog/reservoir_discovery.py` | **No dynamic experiment.** float64; the connectivity file read in 258 batches × 65,536 rows. Result language: *"in this data version, with this selection rule"* |
| **7-1** | State carrying in the connectome reservoir (the main experiment) | `numcog/reservoir_run.py` | Pre-registration committed **before** measuring (`36e52df`, `5f816d2`, `80fda08`); float64, one CSV per seed; language pattern *"in this data, with this model, on this grid"* |
| **7-2** | Fair-regime test: per-arm `g` selection + spectrum diagnosis | `numcog/reservoir_fair.py` → `results_p7_2/` | Pre-registration `137b034`; contains an explicit **design-change declaration**; Faz 7-1 files untouched |
| **7-3** | Rule / extrapolation test (T3) in the 6-step regime | `numcog/reservoir_rule.py` → `results_p7_3/` | Pre-registration `29bf396`; technical fix (`np.polyfit` singular system) `3e243a9` **before** measuring; explicit "exploratory re-test statement (criteria **not** loosened)" |
| **8** | Biological learning rule in MB: DAN-gated KC→MBON plasticity + MB's natural tasks | `numcog/mb_learning.py` → `results_p8/` | Pre-registration `3d7d638`; gate results printed at the **top** of the report; float64, one CSV per seed |

---

## 2. What actually runs in the release (verified in this session)

Two things work end-to-end and are covered by tests; everything else is reported as a **measurement**.

1. **A gated table calculator.** `numcog/fly_calc.py` drives the Faz 4E fly cell:
   * the fly core (`core.step`) is the **only** thing that produces an answer;
   * operands 1..9, results 0..81, so the full table is 2×81 entries → measured table accuracy
     **1.0000** (`numcog/fly_weights/fly_N81_seed0.npz`, 0.14 MB);
   * integer division = quotient + remainder; a quotient **≥ 50** is rejected (the controller's
     `q < 50` stop bound) and negative / >81 results are rejected loudly — never silently wrong;
   * integrity tests: `numcog/tests/test_calculator_integrity.py` (**34/34**, ~1 s) — static
     (only `core.step` answers) **and** dynamic (a fake core breaks the answers: mean agreement
     1.0000 → 0.1235 while the number of core calls is unchanged).
2. **DAN-gated KC→MBON plasticity** (`numcog/mb_learning.py`, Faz 8): the biological learning rule
   is implemented and gated; the measured verdict is in `RAPOR_FAZ_8.md`.

**Not demonstrated anywhere in Faz 0–8:** a connectome-specific task advantage. `RESULTS_SUMMARY.md`,
`PROJE_KAPANIS.md` and the README section say this explicitly, and so does this digest.

## 3. Closing package — where the new numbers live

| Artifact | What it adds |
|---|---|
| `numcog/build_fly.py` → `numcog/fly_weights/fly_N81_seed0.npz` | Rebuildable release weights (table 1.0000). Deviation note: the working 4E cell (σ=1.5, top-k=80, ep=25000, lr=0.05) was used because the 4F `frozen.json` is `null` — documented at the top of `build_fly.py` |
| `numcog/fly_calc.py` | Table-driven core wrapper + bilingual answer/error text (`lang="en"` default, `"tr"` available) |
| `POST /calc` + the interface panel | Batch test, limits board, step dump, FAKE-FLY self-test; arithmetic typed into the chat box is routed to the same core |
| `numcog/two_digit_probe.py` → `results_release/two_digit.csv` | **Exploratory** two-digit probe: 20 seeds × 200 pairs × 4 ops = 16,000 trials, pre-registered in `d6bd546` **before** measuring → overall **0.9984** (add/sub/mul 1.0000, divide 0.9935; the losses are the controller's `q<50` bound). Faz 4E criteria unchanged |
| `RELEASE_PREFLIGHT.md`, `RELEASE_CHECKLIST.md` | Preflight facts (68 commits; history blobs 87.15 MB + 11.12 MB; `scipy` missing from `requirements.txt`) and the **owner decisions still open** |
| `docs/en/INDEX.md`, this file | English coverage: 5 translated documents + the per-phase digest above. The 21 Turkish phase reports are covered **here** rather than as 21 separate files |

**Source map.** Per phase: `RAPOR_FAZ_0.md` … `RAPOR_FAZ_8.md`, `RAPOR_FAZ_6_0.md`,
`RAPOR_FAZ_6_0b.md`, `RAPOR_FAZ_7_0.md` … `RAPOR_FAZ_7_3.md` (Turkish, authoritative) →
their English summaries above. Pre-registration log: `PREREG_LOG.md`. Harness: `numcog/tests/`.

