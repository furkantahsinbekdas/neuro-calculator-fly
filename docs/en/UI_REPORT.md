# REPORT — INTERFACE (STAGE 2): the calculator connected to the chat interface

Translation of `RAPOR_ARAYUZ.md`; the Turkish original is authoritative.

Date: 2026-09-20. Language: **"in this data, in this model, on this grid"**.
New code lives in **`numcog/`**; only a **thin bridge** was added to `flyputer/`.

## 1. Usage (short)

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 server.py          # server: http://127.0.0.1:8000
# open in a browser: http://127.0.0.1:8000
# top right: "🧮 Hesap Makinesi / Calculator" button -> panel opens
```

- **Panel:** expression box (`3+5`, `12-7`, `7x8`/`7*8`, `9/4`) + **Compute** (Enter also works).
- **Two lines under the answer (honest division of labour):** `fly calls: N · seed: 0 · calibrated:
  yes` and `CONTROLLER: … counter/loop/stop …` + a **collapsible step list** (every fly call: n, op,
  output, confidence).
- **FAKE FLY** button: random output instead of the core → answers break and a **red warning** is
  shown ✓.
- **TR/EN** button (interface text only; **result format identical**) ✓.
- **Batch test (1..9)** button: scans 324 pairs (4 operations) with the real and fake core and reports
  ✓.
- **Limits panel** at the bottom of the panel (number sources: `RAPOR_FAZ_4E.md`,
  `results_p4e/final81_seeds.csv`).

## 2. What was added (ADDITIVE; existing behaviour UNCHANGED)

| file | change | note |
|---|---|---|
| `server.py` | **new** `POST /calc` route + `_calc()` method (~35 lines) | the existing routes (`/`, `/initial`, `/poll`, `/state`, `/health`, `/chat`, `/interact`, `/tool`, `/vitals`, `/mode`) were **not changed at all** |
| `chat3d.html` | **new** block before `</body>`: `<style>`, panel HTML, its own `<script>` | the existing 3D brain / word-chat code was **not touched** |
| `numcog/fly_calc.py` | service (parsing, range validation, step dump, `FakeCore`) | written in stage 1 |
| `_calc_smoke.py` | **substitute** automated test (below) | in place of the missing `_fly_smoke.py` / `_fly_frontend_test.js` |

**Endpoint contract** (`POST /calc`): body `{expr, fake, step_by_step}` →
`{ok, result, remainder, fly_calls, ticks[{i,n,op,out,confidence}], controller_ops[], seed,
calibrated, fake, two_digit, note}`; out-of-range request → **HTTP 422** +
`{ok:false, out_of_range:true, error, limit:"0..81"}`; unparsable input → **HTTP 400**.

## 3. Verification (live server, `http://127.0.0.1:8000`)

| check | result |
|---|---|
| `GET /health` | ✓ `{"ok":true,"model":"gemma3:4b","seq":47}` |
| `GET /state` | ✓ (`bus, classifier, executor, loop, state`) |
| **`POST /chat`** (existing word classification) | ✓ `elma` → "yiyorum · doydum [eating · full]", classifier confidence **0.9674** → **not broken** |
| `POST /calc` `3+5` | ✓ **8**, fly calls **5**, seed **0**, calibrated ✓ |
| `POST /calc` `7x8` | ✓ **56**, calls **56** |
| `POST /calc` `9/4` | ✓ **2 rem 1**, calls **8** |
| `POST /calc` `fake=1`, `3+5` | ✓ broken (**81**) + `note` = "SAHTE SİNEK ETKİN…" |
| `POST /calc` `80+5` / `3-5` / `9x10` | ✓ **HTTP 422** + explicit error text |
| `GET /` (chat3d.html) | ✓ 122,623 bytes; `calcpPanel/calcpBtn/calcpBatch` **present**; existing `chat/viz/log/three.min.js` **present** |

### `_calc_smoke.py` — automated batch test (**substitute**; 10 s, `RED: 0`)

```
[OK] existing endpoint /health responds
[OK] existing endpoint /state responds
[OK] existing endpoint /chat word classification works
[OK] /calc 1..9 all pairs EXPECTED behaviour (324 requests)   -> 324/324
[OK] fake fly answers BREAK (<=0.60)                          -> 0.2346 (76/324)
[OK] 'note' field carries the warning in fake mode
[OK] out-of-range 80+5 / 3-5 / 9x10 raise EXPLICIT error (HTTP 422)
RED: 0   RESULT: ALL TESTS PASSED
```

**SUBSTITUTE WARNING:** the requested `_fly_smoke.py` and `_fly_frontend_test.js` **did not exist in
the repository** (`RELEASE_PREFLIGHT.md` §6) → this script stands in for them; it is **not** them.
What it evidences: (a) the three existing endpoints work, (b) the new endpoint behaves as expected,
(c) the fake core breaks the answers, (d) out-of-range raises an explicit error. **Cross-evidence**
that word classification is "unchanged": `POST /chat` answered live and **no line of that route was
touched** in `server.py` ✓.

## 4. There was 1 RED in the first run (not hidden)

First run: `/calc 1..9` = **288/324** ✗; all reds were **a<b subtractions** (36 pairs). Reason: the
test expected the **historical** `calc_measure` behaviour (subtraction clipped to 0 → `want=0`), while
**the interface explicitly rejects negatives** (per stage 1 §4.3). So it was a **test bug**, not a
code bug ✗ → the test was fixed to "negative subtraction → **rejection** expected" and became
**324/324** ✓. That design difference is also printed in the limits panel ✓.

## 5. Limits / notes of this stage

- **The interface is a front end for the measured calculator**; it contains **no new scientific
  claim**. The numbers (`54.0%`, `95%CI [44.3, 63.4]`, 54 accepted) were taken from
  **`RAPOR_FAZ_4E.md`** and **`results_p4e/final81_seeds.csv`**; **not invented**.
- The fly used is **seed 0** (calibration: table 1.0000 ✓). The other 53 accepted seeds can be built
  with `build_fly.py <seed>`.
- **The server was left running** (PID 2228, port 8000) — to stop it: `Stop-Process -Id 2228`.
- **WIP was secured:** the owner's uncommitted work was recorded in `1bf5dfb` **unmodified**; the
  bridge was written as an **addition** on top of `server.py`/`chat3d.html` ✓.
- The Ollama/LLM path was **not removed**; the "dead code" claim remains `[VERIFY]`
  (`RELEASE_PREFLIGHT.md` §5).
