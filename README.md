Terminali (Git Bash, WSL veya Linux) aç, aşağıdaki bloğu olduğu gibi kopyalayıp yapıştır ve Enter'a bas.

Tek tırnaklı `'EOF'` kullandığım için hiçbir değişken (`$`), formül ya da karakter karışmayacak; dosya UTF-8 olarak doğrudan diske yazılacak:

```bash
cat << 'EOF' > README.md
# Ask the Fly Brain 🪰🧠

A computational framework utilizing the FlyWire fruit-fly connectome simulation. Query the biological circuit to observe how the real connectome (the ~140k-neuron wiring diagram of an adult Drosophila) processes inputs through spiking simulations, logic gates, arithmetic tables, heading memories, and escape reflexes.

```text
you (English) ─▶ Gemma (local, via Ollama) ─▶ {"tool": ...}
                                                  │
        find_neurons ─ stimulate ─ show_logic_gate ─ do_math ─ show_compass
        ─ move_fly ─ navigate_fly ─ show_path ─ dodge_swatter ─ neuroglancer
                                                  │
                          real FlyWire data + a tiny LIF sim
                                                  │
                                results ─▶ Gemma ─▶ plain-English answer

```

---

## 🤖 Autonomous Layer — Fork Architecture & Extensions

This fork refactors the original reactive, turn-based harness into an autonomous cybernetic agent: the fly maintains its own internal state, triggers spontaneous behaviors, and relies strictly on the connectome's decisions as primary output. Neural classification results appear as the primary display block; language models serve solely to decode the output into concise 2–4 word status fragments (Phase 13). Out-of-vocabulary inputs stream into an isolated bubble marked as `Free Chat (LLM)`; voice readout is handled via native browser speech synthesis (or a 200 Hz wing buzz fallback).

As of Phase 9, the physical simulation layer has been completely decoupled (`mujoco_bridge.py`, the `/motor` endpoint, telemetry panels, and MJPEG streams were removed, eliminating dependencies on `mujoco`, `glfw`, and `pillow`). The agent now operates purely on signal: user inputs pass through a static lexicon, valid tokens are routed through the Mushroom Body (Kenyon Cell) classifier (`cognitive_matrix.py`), the predicted category deterministically updates `FlyState`, and the agent emits a pre-scripted phrase tailored to that state (Phase 15: zero generative hallucinations in live paths).

```text
[Browser: 3D Brain + Vitals HUD + Primary Signal Block + Caption + TTS 🗣 + Buzz + 🎙
          + Action Buttons (Feed / Poke / Mate) + 7 Scene Buttons + Vitals Manual Override]
     │  ▲ GET /poll?since=N            ┌── GameLoop (1 Hz tick) ──┐
     │  │  EventBus (Sequential JSON) ◀┤ Deterministic threshold  │
     │  │                              └── run_impulse ───────────┘
     │  └─ POST /chat ─▶ Fully SYNCHRONOUS and LLM-free (no queue, ~0.05 s latency)
     │                   POST /interact (feed|poke|mate) · POST /vitals · POST /tool
     │
     └──────────────────────────────────────────────────────────────┐
        Input Text ─▶ Lexicon Matching ─▶ cognitive_matrix (KC Code) ─▶ Category
                                              │  (Fallback: Keyword match ─▶ OOV)
                              CATEGORY_EFFECTS ─▶ FlyState Delta + Flags
                                              │
                              Classifier Event + Static String from PHRASE_BANKS

```

> **Note on LLM Deprecation:** `run_agent` and legacy prompting routines remain in the repository for historical benchmarks, but no active production path calls them.

### Key Architecture Modules

* **`brain_state.py`**: Encapsulates `FlyState` (energy, hunger, boredom + transient status flags, thread-locked), `EventBus` (thread-safe sequential JSON event ledger), and console UTF-8 handlers.
* **`game_loop.py`**: Houses `GameLoop` (1 Hz tick engine, need thresholds, and cooldown logic; routes autonomous impulses to deterministic `run_impulse` handlers) and state transition tables: `CATEGORY_EFFECTS` (classifier categories mapped 1:1) and `AUTONOMIC_EFFECTS` (resting reflexes, ambient events, courtship triggers).
* **`cognitive_matrix.py`**: Mushroom Body classifier: `classify(word)` -> `(category, confidence)`, `scan(text)` -> `hits`, `encode(text)` -> boolean Kenyon Cell sparse code.

---

## Quickstart

```bash
# Production web UI + 3D connectome viewer (LLM disabled in live path)
.venv/Scripts/python.exe server.py

# Conversation-only mode
.venv/Scripts/python.exe server.py --no-autonomy

```

### Endpoints

* `GET /poll?since=N`: Event stream and `classifier_ready` status.
* `GET /state`: Vitals, GameLoop status, and classifier telemetry.
* `GET /health`: Core health checks.
* `POST /chat`: `{"message": str, "sensory": bool}` — Process inputs.
* `POST /interact`: `{"action": "feed" | "poke" | "mate"}` — Direct reflexes.
* `POST /vitals`: `{"field": str, "value": float}` — Manual override (debug).
* `POST /tool`: `{"name": str}` — Trigger connectome visualization scenes.
* `POST /mode`: `{"autonomy": bool}` — Toggle autonomous loop.

---

## Functional Capabilities & Phases

* **On-the-Fly Vocabulary Adaptation (Phase 11):** Issue `/teach <word> <category>` to update weights instantaneously via a single delta-rule step without re-training the full corpus. The server calculates pre- and post-adaptation metrics across baseline tokens. `/teach` inspects state; `/teach-undo` rolls back synaptic deltas. Re-assigning existing tokens requires explicit confirmation (`... confirm`).
* **Physiological Impact Binding (Phase 11.5):** New classes defined via `/teach fear threat-2` carry no default metabolic footprint. Assign physiological responses via `/teach-effect threat-2 threat` to bind the class to one of the six core metabolic vectors (persisted in `learned_words.json` under `effect_aliases`). Decouple via `/teach-effect threat-2 none`.
* **Push-to-Talk & HUD Notifications (Phase 12A):** Hold the microphone button (`#mic`, Web Speech API) to record speech; audio streams directly to the input pipeline. Transient system events and safety alerts render as non-blocking HUD toasts.
* **Dual-Language TTS & Tone Modulation (Phase 12B):** Native client-side `speechSynthesis` outputs responses instantly. When stress flags trip (hunger > 80 or startled states), the agent introduces bounded stress exclamations.
* **Deterministic Signal Decoding (Phase 13):** Eliminates verbose conversational filler. Connectome decisions render prominently in the primary status block (`🧠 category · token · confidence`), while decoded status fragments (`hungry · approaching`) appear subordinated.
* **Homeostatic Recovery & Ambient Stimuli (Phase 14):** When energy drops below 30, homeostatic resting reflexes engage automatically, restoring vitality over sequential ticks. Low-probability ambient environmental perturbations (impacts, food discovery) occur during idle periods without invoking language models.
* **Full LLM Elimination & Deterministic String Banks (Phase 15):** User inputs evaluate in 0.02–0.05 s across three deterministic paths:
1. *Recognized Token:* Kenyon Cell activation -> Category -> Static lexical item selected from `PHRASE_BANKS`.
2. *Courtship Cue:* Direct keyword match triggering transient excitement flags and wing vibration displays.
3. *Out-of-Vocabulary Token:* Predictable rejection notification presenting category exemplars.



### Static Phrase Banks (Bilingual Samples)

| Category | Normal State | Stressed State |
| --- | --- | --- |
| **Food** | `approaching · sugar`, `scent · strong`, `eating · full` | `starving · critical`, `hunger · severe` |
| **Danger** | `danger · flying off`, `shadow · large`, `retreating` | `fleeing · fast`, `threat · evasive action` |
| **Greeting** | `greeting · acknowledged`, `antennae · active` | — |
| **Hunger** | `hunger · low`, `stomach · empty` | `energy · exhausted` |
| **Approval** | `understood · affirmative`, `signal · verified` | — |
| **Refusal** | `refusal · firm`, `avoiding · contact` | — |
| **Courtship** | `courtship · active`, `wing · vibrating` | — |

---

## UI System & Audio Engineering

* **Industrial Paper & Ink Styling (Phase 16, Task 1):** Replaced heavy glassmorphism with high-contrast, structured surfaces (`#f6f6ef` paper base, `#0c0c0c` ink, crisp 2 px panel radii, pill buttons, tracking-adjusted Inter typography).
* **Granular Pitch-Shifting AudioWorklet (Phase 16, Task 2):** Bypasses browser TTS ceiling limitations using an inline granular overlap-add worklet that synthesizes high-frequency formant cues alongside speech generation.

---

## Honest Notes & Implementation Caveats

* **Visual Perception vs. Nutrient Intake:** Visualizing food (`show3d("sugar")`) does not alter metabolic state; nutrient consumption is tied strictly to explicit reflex triggers (`origin="reflex"`).
* **Connectome Classifier Topology:** `cognitive_matrix.py` executes on FlyWire's verified ALPN -> KC projection network (685 Projection Neurons -> 5,177 Kenyon Cells, 23,501 synaptic connections, edge weight >= 3). Character n-grams hash deterministically onto the 685 PNs (~11% active density). Sparse activation codes are parsed through a 6-output linear readout layer trained with delta learning rules.
* **Capacity Bounds (Phase 10):** The 5,177-neuron Kenyon Cell coding space supports up to 500 discrete patterns without code collision. However, the linear readout boundary loses tolerance above N = 150, indicating that capacity bottlenecks stem from readout calibration rather than biological network sparsity.

---

## ⚠ TWO SEPARATE TRACKS — In One Repository

The legacy `flyputer` application (interactive 3D brain and local agent loop) remains accessible as the interface front-end. The `numcog/` pipeline constitutes a separate, rigorous scientific investigation analyzing arithmetic, working memory, and plasticity limits within the connectome.

---

## `numcog` — Connectome Simulations on the FlyWire Brain

### Abstract

An empirical investigation into whether the static anatomical wiring of the adult Drosophila connectome (FlyWire v783) inherently exhibits inductive biases for arithmetic, working memory, or symbolic reasoning.

We systematically implemented and benchmarked:

1. **Numerical Encodings:** Discrete spatial activation patterns mapped across VPN -> KC and ALPN -> KC projections.
2. **Gated Hybrid Bio-Calculator:** A bounded Lookup Table (LUT) covering 0 to 81, where the biological core executes incremental transitions (n -> n ± 1) driven by an external loop controller.
3. **Reservoir Working Memory:** Transient state retention within the Central Complex (CX) subcircuit (N = 4,236).
4. **Mushroom Body Plasticity:** Associative learning models utilizing dopamine-modulated KC -> MBON depression.

### Key Empirical Findings

* **Zero Rule Extrapolation:** Networks exposed to successor/predecessor pairs or size comparisons succeed within training bounds (99–100%) but collapse to chance (0%) on unseen operands. The system operates as a neighborhood memory table rather than an arithmetic logic unit.
* **Gated Calculator Execution:** Multi-step arithmetic (+, -, ×, ÷) operates with 1.0000 accuracy across digits 1 to 9 **only** within the 54/100 seeds that pass strict pre-calibration. Random surrogate cores fail completely when substituted (0.1235 accuracy), demonstrating that the calibrated state transitions genuinely rely on the underlying matrix.
* **Transient Reservoir Retention:** The Central Complex holds sequential state for up to k <= 6 steps (99% retention) before decaying rapidly (23% at step 10). Its performance does not exceed degree-preserving random surrogates (Erdős–Rényi).
* **Absence of Connectome-Specific Advantage:** Across all functional benchmarks, biologically wired matrices performed comparably to, or were matched by, randomized control graphs. Structural specialization exists, but does not confer inherent algorithmic advantages for symbolic tasks.

---

## Verification & Integrity Testing

```bash
# Verify static and dynamic integrity of the calculator (34 checks, ~1s)
python -X utf8 -m numcog.tests.test_calculator_integrity

# Execute interface smoke validation
python -X utf8 _calc_smoke.py

# Run two-digit exploratory probe (16,000 operation pairs)
python -X utf8 numcog/two_digit_probe.py

```

### Verified Benchmark Data

| Benchmark / Probe | Tested Scope | Result | Key Finding |
| --- | --- | --- | --- |
| **Integrity Suite** | 34 automated unit checks | **34/34 Pass** | Arithmetic output derives strictly from the neural core, not controller math tricks. |
| **Null Core Test** | Randomized weight substitution | **1.0000 -> 0.1235** | System collapses under fake weights while call count remains fixed (5 == 5). |
| **Single-Digit 4-Op** | Digits 1–9 (N = 81) | **1.0000 (54% seeds)** | Flawless integer execution across calibrated seeds within 0–81 bounds. |
| **Two-Digit Probe** | 16,000 operation pairs | **0.9984** | Out-of-range deviations caused by controller loop guards (q < 50), not core failure. |
| **Reservoir Memory** | Step sequence retention | **k <= 6 steps** | Retention degrades to chance by step 10; identical to random network baselines. |

---

## Explicit Boundaries & What We Do NOT Claim

* **We do NOT claim the fly computes arithmetic:** The biological core provides an analog step transition (n -> n ± 1); loop counters, carry flags, and termination conditions are maintained by external software.
* **We do NOT claim rule extraction:** The circuits demonstrate spatial memorization; they cannot generalize logic rules beyond trained ranges.
* **We do NOT claim connectome computational supremacy:** The static graph topology showed no measurable superiority over randomized control graphs on these tasks.
* **We do NOT claim living experimentation:** All data is derived from post-mortem electron microscopy segmentations evaluated inside numerical software.

---

## License & Attribution

* **Code:** MIT License. Copyright (c) 2026 Migen Karriqi (original architecture), Copyright (c) 2026 Furkan Tahsin Bekdaş (modifications, neuro-calculator, and benchmark suite).
* **Connectome Data:** FlyWire Drosophila connectome data is licensed under CC BY-NC 4.0 (Non-Commercial). See `DATA.md` and `CITATION.md` for upstream citations.
EOF

```

---

*(Eğer bash değil de doğrudan standart **Windows PowerShell** ekranındaysan, tek satırda dosya oluşturmak için PowerShell'e şunu yapıştırabilirsin: `Get-Clipboard | Out-File -FilePath README.md -Encoding utf8`)*

```