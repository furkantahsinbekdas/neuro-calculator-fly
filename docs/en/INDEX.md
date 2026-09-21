# docs/en — English translations: INDEX and COVERAGE

Rule: **the Turkish originals stay in place and are authoritative.** Each translation starts with
*"Translation of `<file>`; the Turkish original is authoritative."* Numbers, table cells, hypothesis
IDs, commit hashes, every caveat ("in this data, in this model, on this grid"), every
supported/refuted/void verdict and every limitation are preserved; sentences are neither softened nor
strengthened; labels such as "not measured", "exploratory", "post-hoc", "assumption" are **kept**.
Ambiguities are flagged with `[TRANSLATOR NOTE: ...]`.

## Coverage (as of the closing package)

| original (TR) | English | status |
|---|---|---|
| `V1_OZET.md` | `docs/en/V1_SUMMARY.md` | **complete** ✓ |
| `PROJE_KAPANIS.md` | `docs/en/PROJECT_CLOSING.md` | **partial** ✗ — the pre-registration/goal/verdict sections are translated; the artifact and limitation tables are summarised with a `[TRANSLATOR NOTE]` pointing at the Turkish original |
| `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` | `docs/en/CALCULATOR_REPORT.md` | **complete (compact)** ✓ |
| `RAPOR_IKI_HANELI.md` | `docs/en/TWO_DIGIT_REPORT.md` | **complete (compact)** ✓ |
| `RAPOR_ARAYUZ.md` | `docs/en/UI_REPORT.md` | **complete (compact)** ✓ |
| `RESULTS_SUMMARY.md` | (already bilingual TR/EN in one file) | **complete** ✓ |
| `RELEASE_PREFLIGHT.md` | `docs/en/RELEASE_PREFLIGHT.en.md` | **complete (compact)** ✓ |
| `RAPOR_FAZ_0.md` … `RAPOR_FAZ_8.md` (21 phase reports) | `docs/en/PHASES.md` | **covered by the per-phase English digest** ✓ — every phase: question, pre-registration, code/result files and the stated verdict (a digest, not a word-for-word translation; the Turkish text stays authoritative) |
| `HIPOTEZLER.md` (pre-registration log, ~1,260 lines) | `docs/en/PHASES.md` (provenance rule + per-phase pre-registration commits) | **partly covered** ✓ — the rule and the per-phase commits are in the digest; the 1,260-line log itself is still **PENDING** ✗ |
| `README.md` (root) | (bilingual section added in place) | **complete** ✓ |
| `NOTICE.md`, `DATA.md`, `REPRODUCE.md`, `CITATION.cff` | (written in English first) | **complete** ✓ |

## [TRANSLATOR NOTE: pending volume]

The 21 `RAPOR_FAZ_*.md` phase reports are now covered by **`docs/en/PHASES.md`** (per-phase English
digest: question, design/pre-registration, code and result files, stated verdict). `HIPOTEZLER.md`
is partly covered (provenance rule + the per-phase pre-registration commits) and remains **PENDING**
as a full line-by-line translation.
This is stated openly rather than silently skipped: translating them faithfully is a mechanical but
large job (≈200 KB of Turkish prose covering phases 0–8, including many tables of measurements).
**The Turkish originals remain the authoritative record**; the English reader is pointed to
`RESULTS_SUMMARY.md` (bilingual, per-phase question/hypothesis/verdict/key numbers/source/commits)
and to the translated closing documents above. **Nothing was summarised away in place of a
translation** — the pending files are listed as pending.

## What must never be lost in any future translation

1. The pre-registration status of each phase (and that phase 2b was post-hoc, and that 7-2/7-3/8 are
   exploratory re-tests written **after** seeing earlier results — HARKing risk accepted).
2. Every "refuted / supported / void / not measured" verdict.
3. Every limitation, especially: single connectome (hemibrain 783) · simulation · arbitrary
   number→VPN and operator→ALPN assignment · NT signs are an assumption (KC = +1/ACh fixed) · the
   calibration gate rejects 46% of seeds (accepted 54.0%, 95%CI [44.3, 63.4]) · no cell passed the 95%
   criterion at N=81 (best 93.3%) · the two-digit tens/units design was **never implemented** ·
   Group 2 = 3 items, single architecture · MB compartments are an **inference** (k=12, unbalanced) ·
   valance assumption untested · a single plasticity-rule form (LTD only).
4. The "what we do NOT claim" list (`PROJE_KAPANIS.md` §7).
