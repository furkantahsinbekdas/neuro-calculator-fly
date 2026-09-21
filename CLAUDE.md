# flyputer — notes for Claude Code

A local app that runs logic gates and binary arithmetic on the real **FlyWire** fruit-fly
connectome, visualizes it in 3D, and measures the energy cost vs. silicon. Driven by a local
**Gemma** model via Ollama.

---

# Frontend Website Guidelines (design work — read before writing any frontend code)

## First Step (Always)
- **Run the `frontend-design` skill** before writing any frontend code, every session, without exception.

## Reference Images
- If a reference image is provided: replicate layout, spacing, typography, and color precisely. Use placeholder content (images via `https://placehold.co/`, generic text). Do not enhance or extend the design.
- If no reference image: design from scratch with high quality (follow guardrails below).
- Screenshot your output, compare it against the reference, fix any mismatches, re-screenshot. Do a minimum of 2 comparison rounds. Stop only when no visible differences remain or the user confirms.

## Local Server
- **Always serve on localhost** — never screenshot a `file:///` URL.
- Start the dev server: `node serve.mjs` (serves the project root at `http://localhost:3000`)
- `serve.mjs` is located in the project root. Start it in the background before taking any screenshots.
- If the server is already running, do not launch a second instance.

## Screenshot Workflow
- Puppeteer is installed at `C:/Users/nateh/AppData/Local/Temp/puppeteer-test/`. Chrome cache is at `C:/Users/nateh/.cache/puppeteer/`.
- **Always screenshot from localhost:** `node screenshot.mjs http://localhost:3000`
- Screenshots are saved automatically to `./temporary screenshots/screenshot-N.png` (auto-incremented, never overwritten).
- Optional label suffix: `node screenshot.mjs http://localhost:3000 label` → saves as `screenshot-N-label.png`
- `screenshot.mjs` is located in the project root. Use it as-is.
- After screenshotting, read the PNG from `temporary screenshots/` with the Read tool — Claude can see and analyze the image directly.
- When comparing, be precise: "heading is 32px but reference shows ~24px", "card gap is 16px but should be 24px"
- Verify: spacing/padding, font size/weight/line-height, colors (exact hex), alignment, border-radius, shadows, image sizing

## Output Defaults
- Single `index.html` file, all styles inline, unless the user specifies otherwise
- Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive design

## Brand Assets
- Always check the `brand_assets/` folder before starting the design. It may contain logos, color guides, style guides, or images.
- If assets exist, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, apply those exact values — do not invent brand colors.

## Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette values (indigo-500, blue-600, etc.). Choose a custom brand color and derive shades from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body text. Pair a display/serif font with a clean sans-serif. Apply tight tracking (`-0.03em`) on large headings, generous line-height (`1.7`) on body copy.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never use `transition-all`. Use spring-style easing curves.
- **Interactive states:** Every clickable element must have hover, focus-visible, and active states. No exceptions.
- **Images:** Add a gradient overlay (`bg-gradient-to-t from-black/60`) and a color treatment layer using `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens — avoid random Tailwind steps.
- **Depth:** Surfaces should follow a layering system (base → elevated → floating), not all sit at the same z-plane.

## Hard Rules
- Do not add sections, features, or content not present in the reference
- Do not "improve" a reference design — replicate it
- Do not stop after a single screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as the primary color

### Environment (this machine — verified 2026-09-18)
The rules above are the source of truth; only the machine-specific paths differ here. They were
checked: the two helper scripts did **not** exist, so they were written to the workspace root
(`C:\Users\Administrator\Desktop\Genesis_Fly\`) to make the workflow above runnable.
- Puppeteer: `C:/Users/nateh/AppData/Local/Temp/puppeteer-test/` →
  **`C:/Users/Administrator/AppData/Local/Temp/puppeteer-test/`**, where it is installed as
  **`puppeteer-core`** — Chrome is already on the machine at
  `C:/Program Files/Google/Chrome/Application/chrome.exe`, so no bundled Chromium download is
  needed. Chrome cache dir `C:/Users/Administrator/.cache/puppeteer/` (created on first run).
- `serve.mjs` → workspace root, serves the project root at `http://localhost:3000`.
  `node serve.mjs flyputer` serves that subfolder directly; `node serve.mjs . 3001` changes port.
- `screenshot.mjs` → workspace root; writes to `Genesis_Fly/temporary screenshots/`
  (auto-created, auto-incremented, never overwritten). It resolves puppeteer from the temp dir,
  falls back to the installed Chrome via `executablePath`, and prints the install command if
  puppeteer is missing.
- `start.bat` → workspace root; the Windows one-click entry point for the live app on
  `http://localhost:8000`. It locates `flyputer\server.py`, prefers `flyputer\.venv\Scripts\python.exe`
  (else `py -3`, else `python`), verifies `ollama`/`numpy`/`pyarrow` import, warns when Ollama or a
  gemma model is missing, and — if the port is already listening — does NOT start a second server,
  it just opens the browser. `%*` goes straight to `server.py` (`start.bat --port 8081 --no-autonomy`).
- `brand_assets/` → workspace root (empty for now; put logos/palettes there and they must be used).
- **This app's own UI is not a `serve.mjs` page:** `chat3d.html` is served by the Python app at
  `http://localhost:8000/` (`server.py`). That is still localhost — never screenshot `file:///`.
  Use `:3000` for standalone design pages (`index.html`), `:8000` for the live app.
- **The `frontend-design` skill is not available in this environment** (`.claude/` has no skills
  directory). The written guardrails above therefore carry the whole load — follow them literally
  and report that plainly instead of claiming the skill ran.

## Rules
- **Git commits: NEVER add a "Co-Authored-By: Claude" trailer or any Claude/AI attribution to
  commit messages.** Commit as the user only.
- Never commit large data files (`*.feather`, `annotations_783.tsv`), `.venv/`, caches, or
  generated artifacts — they're in `.gitignore`; data is fetched via `get_data.sh`.
- Data is **CC BY-NC 4.0** (non-commercial). Keep the framing factual (see `CITATION.md`):
  we *measure* efficiency; we don't claim to prove anything metaphysical.

## Layout
- `flysim.py` — connectome load + LIF sim + neuron lookup tools
- `logic.py` / `flymath.py` — logic gates + arithmetic on real neurons
- `energy.py` — energy ledger (fly brain vs chip vs Landauer limit)
- `export3d.py` — builds 3D scenes (response / gate / math)
- `server.py` + `chat3d.html` — the live chat + 3D app (`.venv\Scripts\python.exe server.py`; on Windows just double-click `start.bat` in the workspace root)
- `agent.py` / `visualize.py` / `fly3d.html` — CLI agent, matplotlib plot, standalone 3D viewer
- `brain_state.py` — FlyState (vitals + short-lived flags, locked) + thread-safe EventBus + UTF-8 console guard
- `game_loop.py` — LLMExecutor (single worker + PriorityQueue) + GameLoop (tick, autonomous triggers) + CATEGORY_EFFECTS (category -> vitals delta)
- `cognitive_matrix.py` — the mushroom-body classifier: classify(word) -> (category, confidence), scan(text) -> hits, encode(text) -> KC code, teach(word, category) -> live single-step update + measured regression

## Autonomous layer (added in this fork)

- `server.py` is **non-blocking**: all LLM work runs on `game_loop.LLMExecutor`; HTTP handlers
  only enqueue or poll. Everything the fly does is a JSON event on the EventBus, drained by
  the UI with `GET /poll?since=N`.
- Endpoints: `/poll`, `/state` (vitals + loop + executor + **classifier status**), `/health`,
  `POST /chat` (`wait:1` returns the legacy `{answer, viz, classifier}` shape), `POST /mode`.
  There is **no `/motor`** any more — Phase 9 removed the physical layer for good.
- `--require-tool autonomous|always|never`: an autonomous turn may not answer with
  `{"final": ...}` before a tool has run; after two refusals the harness runs the suggested
  tool itself, so the 3D view always lights up. Same guard in `agent.py`'s CLI loop.
- **Effects / reflexes** (`game_loop.CATEGORY_EFFECTS`): ONE table maps a classifier category
  (or an autonomous need, see `NEED_CATEGORY`) to a vitals delta and/or a short-lived flag.
  `hunger` → `besin` → `eat` fires when a food-related tool succeeds (or before a hunger turn
  is allowed to end), published as a `reflex` event with `origin="reflex"`. Seeing food is not
  eating it — the model narrates the outcome, it does not decide it. Without this the impulse
  fires forever, because the vitals never move. To add a category: one row here + words in
  `cognitive_matrix.VOCAB`; both self-tests assert the two tables cover each other.
- **Prompt size is a latency budget.** The system prompt was ~2.9 KB (~716 tokens); trimming
  it from ~5.9 KB roughly halved turn latency (~30 s → ~16 s on Gemma 3:4b/CPU). Measure
  with `.venv/Scripts/python.exe ..\_fly_smoke.py bench` before and after prompt edits.
  Phase 12B added ~1 KB of always-on text (bilingual rule + per-turn reminders), so a calm turn
  is now ~5.7 KB and a stressed one ~6.3 KB — see the Phase 12B note below for what was measured.
- **Text in, text out (Phase 9).** A user message is scanned against the fixed vocabulary
  (`cognitive_matrix.scan`); every hit's word is turned into a real KC code (char 3/4-grams →
  ~11% of the 685 ALPNs → the FlyWire ALPN→KC coincidence matrix) and read out by a delta-rule
  layer. `server.route_message` applies the winning
  category's effect to `FlyState` **before** the model runs and publishes a `classifier`
  event (category, word, confidence, want, delta, flag, alternatives — `want` is the
  table's intent and `delta` what actually moved after 0..100 clamping, with `saturated`
  naming the vitals that were already at a limit). The model then receives
  `game_loop.classifier_note`: the category as a **fact** it may not re-label, plus its own
  post-effect vitals. No vocabulary hit → empty note, ordinary free chat (rule E). Keep that
  separation intact — the LLM narrates, it must never classify.
- **The classifier runs the real wiring; the input layer is ours.** `cognitive_matrix.py`
  reuses `sniff.circuit()` + `sniff.kc_code()` — the actual FlyWire ALPN→KC matrix and its
  coincidence threshold (boolean sparse code, no k-WTA) — and reads it out with a delta-rule
  layer it trains itself. `/state` reports `"connectome": true` *and* `"honest_note"` naming
  what is measured (KC code, layer sizes) vs. ours (the word→ALPN pattern, the readout).
  Never reimplement `kc_code`: call it, so the classifier and `sniff.py` cannot drift apart
  (the self-test asserts the two agree bit-for-bit). The 813 MB feather is required; if it is
  missing `/state` says `"loaded": false` and the server still runs (messages just skip the
  classifier instead of dying).
- **Capacity has two ceilings — never quote one without the other (Phase 10).**
  `capacity_benchmark.py` drives the production encoder/readout (`cm.encode`, `cm.readout`:
  imported, never re-implemented; the vocabulary is repointed for N outputs and restored, and the
  run re-verifies production parity — 1422 epochs, lr 0.01435, 55/55 — before touching anything)
  over the top-N words of a real Turkish frequency list (`data/tr_50k.txt`, auto-downloaded and
  git-ignored; a synthetic fallback is always labelled). Measured at N=500: **no code collision at
  all** (max Jaccard 0.472, zero pairs above the 0.50 warn line; closest pair
  "kendini"/"kendine" with 0.685 containment — shared stems, i.e. our input encoding) and **100%
  argmax accuracy in both the per-word and the 6-output shape**, yet the delta rule stops meeting
  its own ±1 tolerance at N=150 and the 0.40 routing floor breaks at N=200 in the per-word design
  (weakest learned word 0.347, down from 0.720 at N=55; the 6-output production shape still holds
  0.425 at N=500, a margin of only +0.025). So for these sizes the substrate is not the bottleneck
  — our readout's *confidence* is. Re-run: `python capacity_benchmark.py --log
  capacity_report.txt` (~6 min).
- **Live teaching: one delta step, then measure the whole old vocabulary (Phase 11).**
  `/öğret <kelime> <kategori>` is a *command* (`server.parse_teach_command` → `cm.teach`), answered
  without an LLM turn; `/öğret-geri` undoes the last one; relabelling a word the fly already knows
  requires an explicit `onayla` (never a silent relabel). The readout is **not** retrained: one
  single-example step of production's own rule (`W += lr·err⊗x`, `B += lr·err`, `lr = 1/mean-active`
  — `lr·‖x‖² = 1` makes the weight part of one step exact for a single sample, the bias term adds
  `lr·err` on top, so it measures **1-2 updates**), and a brand-new category appends one row to W/B
  at runtime (no restart). Labels: `cm.labels()` = the frozen 6 factory decisions + live-taught
  categories; `cm.CATEGORIES` and `game_loop.CATEGORY_EFFECTS` stay 1:1 (both self-tests assert it)
  and a taught category has no effect row, so the body does not move — the note says so.
- **Every teach re-measures the whole old vocabulary, before and after** (`cm.vocabulary_table()`,
  one matmul over cached codes; the tests assert it equals `classify()` row by row). The delta rule
  writes *every* label row, so "old words are safe" is an assumption — and assumptions get measured.
  Measured: adding a word kept 55/55 with min confidence 0.965 → 0.960; relabelling a factory word
  ("şeker" → tehlike) kept every label but pushed min confidence 0.960 → **0.527**. `lost`/
  `dropped`/`warning` ride in the reply, the `teach` event and a `warning` event; the change is kept
  so a human decides, and `cm.undo_last_teach()` restores W/B + registry exactly (verified with
  `array_equal`). Taught words live in `cm.TAUGHT`, never in `VOCAB` (factory 55 stay hardcoded and
  additive words stay distinguishable); `learned_words.json` is human-editable and is **replayed**
  on top of the base 55 at startup, while the `.npy` pair is only *compared* against the replay —
  a hand-edited file therefore shows up as a measured delta (0.036 in the test) instead of being
  silently overwritten. Past `cm.VOCAB_WARN_SIZE` (100 words) it warns and never blocks: Phase 10
  put the calibration trouble around 150-200.
- **Phase 11.5 closed exactly two measured gaps — no new capability, detection over correction.**
  (a) *Safety net*: `teach()` already re-measured the whole vocabulary, so the alert reuses that
  one `vocabulary_table()` (no second measurement). Two constants, both chosen from measurement:
  `TEACH_SAFETY_MARGIN = 0.10` (a word closer than floor+margin → 0.50) and
  `TEACH_SAFETY_STEP = 0.30` (a single teach that drops one word this much, even while the word is
  still far above the floor). Measured justification: a routine teach moves the weakest word
  0.07-0.13, while relabelling a word whose code has a near neighbour costs that neighbour
  0.396-0.445 in one step. `safety`/`safety_warning` ride in the teach result, the reply gets a
  `⛔ GÜVENLİK SINIRI` block, `level` becomes `"alert"` (in the HTTP response too) and a second
  `warning` event carries `level: "alert"` (+ `safety`) — note `EventBus.publish` flattens the
  payload and *drops* a `kind` key, so the tier travels as `level` and the ⛔ text.
  **Nothing is rolled back automatically.** Measured on the real connectome: repeating the *same*
  flip does not compound (0.493 ↔ 0.965, no crossing, alert fires anyway); *different* teaches do
  (0.965 → 0.832 → 0.756 → 0.662, then a neighbour relabel drops `şekerli` 0.748 → 0.352, i.e.
  below the floor) — alerts `[1,3,5,6,7,8]` vs crossings `[6,7]`, so the alert preceded the
  crossing. Honest limit, printed by the test: in the plain compounding order the first alert
  arrives *at* the crossing teach, because that step is the 0.396 drop — a post-hoc detector cannot
  announce a step it has not seen, which is why `dropped` and `/öğret-geri` are also reported. The
  optional "scale lr down as categories grow" idea was measured and **not** implemented: for a new
  category the drift is structural (0.832 → 0.833 at lr×0.5, 0.840 at lr×0.25 with 8 updates) and
  for a relabel the other rows' total displacement is lr-independent (max|ΔW| 0.01681 → 0.01654
  with 7× the updates) — small-lr gains are just an unconverged target (0.961 → 0.819).
  (b) *Taught categories and the body*: a `/öğret`-born category is still informational by default
  (`CATEGORY_EFFECTS` has no row; `CATEGORIES` stays the frozen 6 and both self-tests assert the
  1:1), but the reply now *asks* (non-blocking) whether to map it, via
  `/öğret-efekt <kategori> <etki>|yok` → `cm.set_effect_alias()`. Aliases borrow an existing row
  (never a copy), persist as `"effect_aliases"` in `learned_words.json`, are replayed after the
  words at startup, are dropped when the teach that created the category is undone, and are refused
  for factory categories / non-factory effects. `server.route_message` resolves the alias and marks
  the decision (`effect_alias`, `effect.alias_of`); with no alias the old `delta={}`/`noop=True`
  path is untouched.
- **Phase 12A put voice input on the typed route and made the safety lines unmissable.**
  Push-to-talk: `#mic` + `webkitSpeechRecognition`, `lang = "tr-TR"`, `continuous = true` (one
  hold may hold a sentence), started by `pointerdown` (or Space/Enter held while focused),
  ended by `pointerup` / `pointercancel` / `onblur` / a document-level `pointerup`; a second
  `onend` while still held restarts listening instead of dropping the turn. The transcript is
  written into `#msg` and sent by `sendInput()` — the *same* function the form's submit handler
  calls — so the request body is exactly `{"message": "..."}` and `voice` only decorates the
  bubble (🎙) and the live label. **Consequence, deliberately:** the page no longer sends
  `sensory: true`, so a spoken turn is no longer tagged `[DUYU]` / `PRIORITY_SENSORY`; the
  documented `/chat {sensory:true}` option is untouched server-side and the frontend smoke still
  proves it with a live POST. Verified by a live comparison run: the same sentence from both
  routes went out byte-identical and arrived as `origin=user` with `[KULLANICI]`. An empty
  transcript, a `not-allowed` (or any other) recognition error prints "anlaşılamadı, tekrar
  dene" in the log — never a silent failure. Notices: `toast()` (top-left `#toasts`,
  `TOAST_MS = 5000`, click-dismiss, `TOAST_MAX = 4`) *duplicates* what `chip()`/`bubble()`
  already wrote — same trigger, same words, `level` (`alert`/`warn`/`ok`/`error`) drives the
  styling only; `/öğret` replies with `level="error"` are the one tier with no bus event behind
  them, so `ask()` raises that single notice itself (teach/warn/alert must not be said twice).
  Dead code removed with it: the `#play`/`#scrub`/`#time` film-strip CSS (no markup, no JS left),
  a stale "classifier chip" comment stranded inside the mic block, and the client-side `sensory`
  branch. `cognitive_matrix.py`, `sniff.py`, `game_loop.py` and `brain_state.py` untouched.
- **Phase 12B gives the fly a real voice, a stress-gated tone and a bilingual reply.** Three
  surfaces, and each one's honesty caveat is written down.
  (a) *Speech out* (`chat3d.html` only, `Say` module): a `say` event now also gets read aloud by
  the browser's own `speechSynthesis` — no third-party voice model, nothing downloaded. Asked for
  **pitch 2.0 / rate 1.5 / `lang="tr-TR"`**; the Web Speech API clamps pitch to 0..2 and rate to
  0.1..10, so both requests are legal and **2.0 is exactly the pitch ceiling** (the page reads the
  values back into `Say.settings().readback` and raises one HUD notice if an engine caps them
  differently, instead of pretending). `#voice` (next to the buzz toggle, default on) is the mute
  switch; it persists in `sessionStorage` under `fly.voice` for the session and is never posted to
  the server — the frontend test proves both by asserting the store contents and that no new fetch
  happens. Off ⇒ `synth.cancel()` mid-word and no reading; on ⇒ a short Turkish confirmation is
  spoken. Task 3's bracketed English is stripped *before* synthesis (`Say.clean`: trailing `[...]`
  first — the contract — then a safety-net pass for a bracket the model tucked mid-sentence): the
  log keeps the full text, the speakers never hear English. A bracket-only reply is silent. The
  user's own line never speaks (it produces no `say` event) and `REPLAY_ONLY` keeps pre-load
  history quiet. **Deliberate trade-off:** the wing-buzz is now the *fallback* voice — when
  `Say.speak()` returns a non-empty string the buzz is skipped, so the 200 Hz carrier never talks
  over the voice; muted or a browser without synthesis falls back to exactly the Phase 2
  behaviour (buzz plays, `#voice` is disabled, a HUD notice says why).
  (b) *Tone under stress* (`server.py`, prompt only): the closed list
  `EXCLAIM_ALLOWLIST = ("lan", "hassiktir", "off", "mahvolduk", "ay")`, the strict threshold
  `STRESS_HUNGER = 80.0` (>80, so 80.0 is calm and 80.1 is not), and `stress_reason()` =
  hunger over the threshold OR the live `startled` flag. `system_prompt()` injects the `STRESS`
  block **only on such a turn**; every other turn gets `CALM_LINE` instead, which forbids the tone
  without ever showing the words. So "never in calm state" is structural, not a hope — the `voice`
  phase asserts none of the five words appears in a calm prompt (user *or* autonomous), and that
  all five do under stress. Behaviour of the model is measured, not assumed (see (d)).
  (c) *Bilingual reply* (prompt only): `BILINGUAL` demands one trailing bracket with the English
  of the same sentences, tone preserved (not a flat literal); `TAIL` repeats the answer shape at
  the very **end** of the prompt, where a 4B model actually honours it; the persona's two "İyi"
  examples now carry brackets too, because the measured failure was the model copying that
  example verbatim and dropping the translation. No second call, no translation API, no JSON
  contract change.
  (d) *Measured fidelity* (`_fly_smoke.py tone`, real Gemma 3:4b, 4 runs ≈ 24 turns): run 1 had
  brackets in 3/6 turns and exceeded "one exclamation" in 3/3 stressed turns ("Lan, off!"); after
  the reminder lines, **6/6 brackets**, the cap was never exceeded, and calm turns carried **0**
  list words. Residual risk, stated rather than hidden: a 4B model can still write a second
  interjection under stress (seen once in one run) and this phase is prompt-only, so there is **no**
  server-side filter; `tone` shouts `[!!]` and tolerates at most one slip, while the calm side is
  hard-asserted. If a hard guarantee is ever wanted, the place to add it is a tiny deterministic
  check on `final`. Prompt budget: a calm turn went ~4.7 KB → **5.7 KB** (+~250 tok) and a stressed
  turn is **6.3 KB**; mean turn in that run was 13.7 s, in line with the recorded ~16 s. First
  thing to trim if latency regresses: the good/bad example pair inside `BILINGUAL`.
- **Phase 12.5 makes "one exclamation" true in the bytes, not just in the prompt** (`server.py` only;
  prompt text, list and threshold untouched). Measured evidence was a 4B model writing two anyway
  ("Lan, off!", "Lan, hassiktir…"), which Phase 12B could only *ask* it not to do. `single_exclaim()`
  now runs at the single place an LLM reply leaves the process — the `final` return of `run_agent` —
  so the `say` event, the `/chat {wait:1}` response and any client see the same filtered text. It
  keeps the **first** allowlist word of the Turkish part and deletes the rest together with the
  whitespace in front of them, then re-closes the punctuation: `"Lan, off!"` → `"Lan!"`,
  `"Lan, hassiktir, bu bir terlik!"` → `"Lan, bu bir terlik!"`, `"LAN, OFF, MAHVOLDUK!"` → `"LAN!"`
  (no `,,`, no dangling comma). Matching is `(?<!\w)…(?!\w)` with an `[iİıI]` class so dotted-capital
  "İ" folds in while "planlama"/"ayran"/"ofis"/"oflaz" never match. With 0 or 1 hit the string is
  returned **byte-identically** (calm replies are a no-op — insurance, not a second gate), and text
  inside `[...]` is never scanned and survives byte-for-byte (the browser's speech strip depends on
  it); the reply is split on bracket groups and re-joined for exactly that reason. Every firing
  prints one line to stderr (`tek ünlem süzgeci (2->1): … -> …`) so the filter is never an
  invisible mask. Verified by the no-model `filter` phase (17-row table: 2-3 hits across positions
  and punctuation, all-caps, `Hassİktİr`, mid-sentence brackets, a two-bracket malformed reply,
  near-miss words, idempotence) plus a `run_agent` integration check with a stubbed rule-breaking
  model; the real-model `tone` phase caught it live — raw `Lan, hassiktir, bu bir terlik!
  [Oh no, that's a slipper!]` reached the client as `Lan, bu bir terlik! [Oh no, that's a
  slipper!]`, and no calm reply was modified in any run.
- **Phase 13 demotes the LLM to a decoder and promotes the connectome's own verdict.** The reported
  problem: elaborate LLM sentences read as "the fly talking", indistinguishable from any chatbot,
  while the actual classification hid in a small line. Fix, in three places and no more:
  (a) `mode` on the turn. `_chat` submits `meta={"mode": "caption"|"chat"}` (caption iff
  `route_message` returned a decision), GameLoop submits `"caption"` for autonomous impulses,
  `_teach` publishes `say` with `"system"`, and `LLMExecutor._run` copies that meta onto the `say`
  payload — so the client is told which voice it is looking at instead of guessing from ordering.
  (b) `system_prompt(origin, signal=False)`: with `signal=True` the chatty `PERSONA` is not in the
  prompt at all — `SYSTEM_SIGNAL` = `DECODER` + `BILINGUAL_FRAGMENT` + `CONTRACT_SIGNAL` + tools,
  the tone blocks are replaced by `signal_state()` (the live mood mapped to one fragment template),
  and `CAPTION_TAIL` restates the cap last. Output is a **2-4 word state fragment** with a ≤4-word
  bracket: `aç · yaklaşıyor [hungry · approaching]`, `ürkmüş · kaçıyor [startled · fleeing]`;
  no first person, no metaphor, no sentence, no exclamation. Decisive detail: the bracket is
  enforced by the *example* in `CONTRACT_SIGNAL`, not by prose — with a prose rule and the old chat
  example still in the contract, 2 of 6 turns dropped the bracket; after swapping the example,
  two consecutive runs came back **6/6**. `game_loop.classifier_note`'s tail and `build_trigger`
  now ask for a fragment too (prompt text only — the effect tables and classification logic are
  untouched). Free-form turns (no vocabulary hit) keep the chatty persona, which is the chosen
  two-mode design.
  (c) chat3d.html hierarchy: a `classifier` event draws a large `.signal` block (headline
  "🧠 sınıflandırıcı kararı — çekirdeğin kendi yanıtı", big line = category · word · confidence,
  small line = vitals/flag/alternatives) and the `say` with `mode:"caption"` draws `.yorum`
  (small, muted, labelled "yorum") underneath. `mode:"system"` is a chip; anything else is a
  bubble labelled **"serbest sohbet (LLM)"**. `.msg.fly`/`.msg.auto` and the "SİNEK" speaker labels
  are gone (the frontend smoke now forbids them), so no bubble can imply a character was chatting.
  TTS is unchanged and speaks the fragment only (`Say.clean` still strips the bracket).
  Verified: `caption` phase (6 categories, real model, fragments + bracket printed per word),
  `llm` (free-form POST now answers `selam · konuşuyor [hello · talking]` for "merhaba"), `autollm`
  (real autonomous impulse answers `aç · yaklaşıyor [hungry · approaching]` while still running the
  tool and the feeding reflex), plus the node suite for the new DOM hierarchy.
- **Phase 14 gives the body and the environment a vote.** Three gaps from live testing, all
  deterministic:
  (a) *The missing energy reflex.* Hunger got a deterministic `eat` in Phase 5; energy never did, so
  a worn-out fly re-queried the clock forever while its energy kept falling. A new
  `AUTONOMIC_EFFECTS` table holds `dinlenme` = `{"delta": {"energy": +8, "hunger": +2},
  "recover": {"energy": 3.0, "ticks": 10}}`: the opening instalment lands through
  `server.fire_reflex` (the existing reflex path, now reachable via `NEED_CATEGORY["energy"]`), and
  the GameLoop's `_tick_rest` applies the rest tick by tick for 10 ticks. It is a *separate* table
  on purpose: `CATEGORY_EFFECTS` is 1:1 with `cognitive_matrix.CATEGORIES` and both self-tests
  assert it (the smoke asserts it too), so `reflex_for()` is the one door that reads both tables
  while `effect_for()` stays classifier-only — a taught category can never borrow an environment
  row. Measured: energy 0 → 27.3 in 11 ticks (critical is 25), → 52.8 fifteen ticks later, the
  repeated `show3d(clock)` impulses stopped exactly when the vital cleared the threshold (10 → 10
  calls) and `top_need()` went empty. `REST_THRESHOLD = 30` (above the 25 critical, so the body
  recovers before the impulse would spin), `REST_COOLDOWN = 60 s`, and it is deliberately not
  gated on autonomy — decay is not either.
  (b) *The environment.* `darbe` (energy −15, boredom −10, `startled`) and `rastgele-besin`
  (hunger −20) are drawn by `ENV_WEIGHTS` and applied through the *same* `apply_effect` →
  delta/flag → `reflex` event pipeline a typed word uses (with `want`/`saturated`, like a
  classifier event). Five gates keep it out of the way: per-tick chance (0.004 ≈ one event per
  ~4 min), 90 s cooldown, `idle_seconds() >= 45` (`_chat` calls `touch()` on every user message),
  45 s since the last impulse, executor idle, no rest episode. `env_rng` is injectable, so each
  gate is tested individually and the probability is tested independently: zero events during a
  conversation, while the executor is busy and mid-nap; `darbe` (energy 80 → 65) and
  `rastgele-besin` (hunger 30 → 10.4) when truly alone; 23 events per 2000 idle ticks at p=0.01
  (expected ~20). Environmental events deliberately start **no** LLM turn — the deterministic
  `reflex` chip plus the vitals move first (the Phase 13 hierarchy).
  (c) *Exclamations on the decoder path.* `DECODER` never saw `EXCLAIM_ALLOWLIST`, so a stressed
  caption could not swear. `system_prompt(signal=True)` now assembles
  `SYSTEM_SIGNAL_STRESS` while the fly is stressed, whose `CONTRACT_SIGNAL_STRESS` example is
  `{"final": "hassiktir · kaçıyor [oh no · fleeing]"}` — the contract example is what this model
  copies (measured three times now) — plus a `CAPTION_STRESS` block (closed list, "the FIRST slot
  WILL be an exclamation", at most one) and a stressed `signal_state()` example
  (`STRESS_FRAGMENT`). A calm caption prompt contains none of the five words at all
  (`CAPTION_CALM`/`CAPTION_TAIL`), and `single_exclaim()` still enforces the cap on the bytes.
  Measured: 2 of 3 stressed turns used a listed word (`hassiktir · sıçradı`, `lan · sıçradı`),
  never more than one, all ≤4 words with their bracket; 5 calm captions had zero. One subtlety the
  measurement surfaced and the test now encodes: *the message's own effect can change the stress
  inside the same turn* — `tehlike yaklaşıyor` starts calm and ends startled (so it correctly got
  an exclamation), while `önünde şeker var` drops hunger by 35 and thus removes the stress; the
  test therefore reads `stress_reason()` **after** `route_message`. The punctuation tidy also
  learned the fragment separator: `hassiktir · off · kaçıyor` → `hassiktir · kaçıyor`, no `· ·`.
- **Phase 15 kills the LLM from the live path entirely, adds fixed phrase banks and physical
  controls.** The verdict was unambiguous: no generated sentences at all, and typing should not be
  the only way in. What changed:
  (a) *`PHRASE_BANKS` + `NEED_PHRASES`* (`server.py`): 39 hand-written lines, ≤4 Turkish + ≤4
  English words each, one trailing bracket, grouped per category with a `stressed` half
  (`tehlike`'s stressed half is where the exclamation vocabulary now lives — the curated answer to
  "what does it scream when scared"). `pick_phrase(category, stressed=None)` picks at random,
  preferring the stressed half while `stress_reason()` fires.
  (b) *The live turn is deterministic and synchronous.* `Handler._chat` walks connectome →
  `route_keyword` ("eş") → `oov_reply()` and returns a phrase immediately; there is no
  `EXECUTOR.submit`, so no `queued`/`accepted`/`think_start`/`token` events exist any more
  (measured 0.02–0.05 s per turn versus 2–20 s before). `route_message` still applies the effect and
  publishes the `classifier` event, so the primary UI element is unchanged; the phrase rides along
  as `say mode="phrase"`. The `sensory` flag is now provenance only (`origin=sensory`), since the
  `[DUYU]` prompt line it existed for is gone.
  (c) *New seventh stimulus "eş"* — a **keyword route**, not a classifier category, because
  `cognitive_matrix.CATEGORIES`/`VOCAB` are frozen (both self-tests assert the 1:1 with
  `CATEGORY_EFFECTS`). `AUTONOMIC_EFFECTS["eş"]` = boredom −20 + a new `heyecanlı` flag (25 s), the
  same machinery as `startled` (brain_state untouched: an unknown flag simply has no mood
  override). Words `dişi sinek`, `dişi`, `eş`, `çiftleş`, `kur yap`, `eşleş`, matched on word
  boundaries after the classifier's own ASCII folding.
  (d) *Buttons and sliders.* `POST /interact {action}` runs feed/poke/mate through
  `publish_decision` (same `apply_effect`, same `classifier`+`state` events, `source="button"` so
  the UI headline does not claim the connectome decided it). `POST /vitals {field, value}` sets a
  vital directly for experiments (one `apply_delta` of the difference — no brain_state change
  needed) and logs a `reflex` chip marked `origin="manual"`. `POST /tool {name}` exists because
  killing free-form chat orphaned the eight connectome scenes that only LLM tool-calls could reach:
  the same `export3d` builders now hang off a button (`gates`, `math`, `compass`, `smells`, `eye`,
  `swatter`, `path`, `navigate`).
  (e) *The autonomous impulse is deterministic too* (`run_impulse` + a GameLoop `impulse` callback):
  real scene → need reflex → fixed phrase, no prompt. `run_agent`, the prompt machinery and the LLM
  executor therefore have **no live caller**; they stay in the file (dead by design, documented here
  and in the harness docstring) so a revert is one line. The frontend marker list now *forbids*
  `serbest sohbet (LLM)`, `.msg.chat`, `e.mode === 'caption'` and the old tool-ish suggestion text,
  and `deterministic` phase asserts the absence of every LLM fingerprint in a live run.
  (f) *UI*: `#controls` (🍯 Besle / 👋 Dokun-Kovala / 🪰 Dişi sinek) and `#tools` (7 scene buttons)
  above the input, plus a `−/+` override pair on each vitals row labelled "manuel override (debug)".
  `say` renders `phrase` → `.yorum` and everything else → a neutral chip; TTS speaks only the fly's
  phrase. `/poll` gained `classifier_ready` so the UI says "çekirdek yükleniyor…" and keeps the send
  button disabled until the connectome matrix is up (a synchronous reply would otherwise look frozen
  for the first ~10–25 s).
- **Persona / dil**: the system prompt carries an explicit Turkish style contract (short
  sentences, banned mechanical phrases, good/bad example pairs) and the tool catalogue
  states the motion-vs-visualisation rule ("yürü/dön/kaç" → move_fly, "göster" → show3d,
  both → motion wins). Keep the prompt small: it is the latency budget
  (`_fly_smoke.py bench`, ~2.9 KB → ~16 s/turn on Gemma 3:4b/CPU).
- Keep the caveats honest: the 3D scenes (`move_fly`, `navigate_fly`, `dodge_swatter`, …) show
  real descending-neuron / looming activity, but they drive nothing — the actuator layer is
  gone. Never describe them as measured behaviour.
- **Phase 16 restyles the whole UI to a figure.ai-flavoured paper-and-ink system and adds an
  opt-in "helium" voice built on a real granular pitch shifter.** Two tasks, one presentation
  layer:
  (a) *Design system* (`chat3d.html`'s `<style>`): the dark-glass theme (`rgba(14,18,30,…)`,
  `backdrop-filter`, 11–12 px radii, neon accents) is gone. Tokens are now `--paper #f6f6ef`,
  `--ink #0c0c0c`, `--ink-2 #1d1d1d`, `--ink-3 #2e2e2e`, `--white`, `--black #000` (button fill
  only), `--line rgba(12,12,12,.16)`, `--sep #dcdcdc` (list rules), `--tr -0.01em`, `--lh 1.5`,
  `--fs-body/--fs-h/--fs-display/--fs-phrase` (clamp lines), `--s*` spacing, `--btn-x` and the two
  radii `--r 2px` / `--r-pill 999px`. The scene panels' fourteen dark cards were migrated mechanically to opaque white
  cards with hairline rules (a scripted, counted substitution over one line range, then reviewed),
  and the shell was hand-built: paper base → dark 3D stage → white chat column → white cards
  floating on the stage. Hierarchy is size/weight/tracking on ONE typeface (the reference's own
  system): `.signal .sbig` 36 px/700 ink at −0.02em (`--fs-display`), `.yorum` 18.5 px `--ink-2`
  (`--fs-phrase`), section heads 23.9 px/700 (`--fs-h`). Four rules are applied literally, because
  they are what carries the reference: (1) **buttons are the only rounded shape** — a `999px` pill
  with generous horizontal padding (`--btn-x`), solid `#000` on pure `#fff` for the primary action
  (`#send`) and as the hover/held state of the outline pills, while the panels, stage, chat sheet,
  input and scroll thumbs stay sharp (measured: the page's only radii are `2px`, the legend/data
  dots' `50%` and `999px`); (2) **lists and logs are index lists** — `#log > *` carries
  `border-bottom: 1px solid #dcdcdc` with `:last-child` left uncrossed, so chat entries are rows and
  not cards (the human's turn is marked by weight + ink + its `SEN` eyebrow instead of a fill, and
  each chip keeps its type colour on a 2px `currentColor` left rule); (3) **nav/meta labels are
  uppercase** with 0.08em tracking (legend, HUD switches, the vitals toggles/mood, all nine panel
  eyebrows and the truth-table header) while body copy and button labels keep their own case;
  (4) **headers are massive, bold and tight** (−0.02em). `neue-haas-grot-text` is
  Grilli Type-licensed, so it is **not** bundled or hotlinked; Inter (open, CDN, `font-display:
  swap`, OS sans fallback) stands in and the same tracking/leading/scale rules apply.
  Deliberate deviations, both stated in the README: the brain keeps its dark stage (the neurons
  are drawn with `THREE.AdditiveBlending`, which cannot work on white without rewriting the
  material/shader — out of scope for a presentation-only phase), and no gradients/glow/grain were
  added although the generic guardrails suggest them (the reference is flat and industrial).
  Vitals bars are monochrome by tone with `--stop` red only at a critical threshold, and their
  fill animates with `transform: scaleX()` (never `width`) — the same conversion was applied to
  the energy and compass bars. Every clickable got `hover` + `:focus-visible` + `:active`.
  Responsiveness is new: two breakpoints (≤980 px stacks the shell and caps each button strip at a
  WHOLE number of pill rows — `box-sizing` is border-box, so a container's own bottom padding counts
  inside the cap: 82/86/86 px = two 34 px rows + gap; ≤620 px trims the legend and header, tightens
  the pills to `--btn-x: 13px` and caps the strips at one row each — 42/46/48 px — which is what a
  390×844 phone actually has left after the head and the form; the numbers were measured in the
  browser, not guessed), because the old page had zero media queries and overlapped at 390 px.
  Honest limit:
  the phone stage is busy — really fixing it means moving the panels into the chat column (a DOM
  change), which was not done.
  (b) *Helium voice*: browser `speechSynthesis` output cannot be captured or routed (no
  MediaStream, no node, no recording API), so shifting the spoken voice in-page is impossible —
  `Say` already sits at the engine's own ceiling (pitch 2.0/rate 1.5). What was built instead:
  a real overlap-add granular pitch shifter (two Hann-windowed taps half a grain apart, `wA+wB=1`
  so the gain never wobbles) shipped as an `AudioWorklet` compiled from an inline Blob (no file,
  no server endpoint, no dependency — `server.py` was not touched), applied to a synthesized
  squeak carrier (1150 Hz saw + 575 Hz body + 3050 Hz band-pass formant + 6.5 Hz ±26 Hz vibrato)
  that follows the line's own syllable envelope from `Buzz.env()`. It plays *under* the TTS at
  `LEVEL 0.16`, and when TTS is muted the buzz itself is routed through the shifter — that path is
  literally shifted rather than layered. Opt-in via the `🎈 aşırı helyum` switch in the vitals
  footer (`sessionStorage: fly.helium`, default off; off means zero nodes created). Measured, not
  assumed: `_fly_frontend_test.js` runs the worklet class in Node and counts output zero
  crossings — 1.0 → 440 Hz out with gain 1.000, 1.5 → 440→655 Hz, 2.0 → 300→602 Hz. Honest
  tradeoffs are in the README: the layer is a squeak, not shifted speech (intelligibility still
  comes from the TTS), a 46 ms grain can chorus if pushed loud, and the very first utterance plays
  the carrier unshifted if the worklet has not compiled yet.
  (c) *Verification assets added*: `verify-phase16.mjs` (reads the browser's *computed* styles —
  the "measured" numbers in the README come from it), `screenshot.mjs` gained `--click "<sel>,…"`
  and `--type "…"` so framework-mutated states and a real user turn can be reviewed, and its
  numbering is now atomic (`wx` reservation) after three parallel runs all claimed number 7.
  Gates: `_fly_smoke.py all` OK, `_fly_smoke.py frontend` 68 markers / 46 forbidden strings,
  `node _fly_frontend_test.js` OK.
