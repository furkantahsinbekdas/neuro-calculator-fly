# NOTICE — upstream sources, attributions and licenses

This repository contains **two** things:

1. **`flyputer`** — the web app (3D brain viewer + word chat). Code: **MIT** (`LICENSE`).
2. **`numcog/`** — the connectome science project (phases 0–8, the calculator, the closing
   documents). Same repository, same **MIT** code license.

## Data (NOT in this repository)

The FlyWire connectome files are **not** committed (see `DATA.md` and `.gitignore`):

| file | size (working tree) | source |
|---|---|---|
| `proofread_connections_783.feather` | ~812 MB | downloaded by `get_data.sh` |
| `annotations_783.tsv` | ~30 MB | downloaded on first run of `flysim.py` |

- **License of the data:** **CC BY-NC 4.0 (non-commercial)** — per this repository's existing
  `CITATION.md`. **[VERIFY: license terms of the FlyWire/Codex release used]** (upstream license pages
  were **not** independently checked while writing this notice).
- Consequently the **outputs derived from the data** in this repository (results CSVs, reports) are
  subject to the same non-commercial terms — this is the reading adopted in `CITATION.md`.

## Third-party code / models

| component | location | status |
|---|---|---|
| **flybody** (MuJoCo fruit-fly body model) | `models/flybody/` (**not** committed; `.gitignore`) | external project; its own `LICENSE` ships inside that tree — **[VERIFY: flybody license terms]** (not read while writing this notice) |
| **three.js** 0.128.0 | loaded from `cdn.jsdelivr.net` in `chat3d.html` | MIT (upstream) — **[VERIFY: version/license of the CDN copy]** |
| **FlyWire connectome** | data, see above | CC BY-NC 4.0 — cite Dorkenwald 2024, Schlegel 2024, Zheng 2018 (listed in `CITATION.md`) |

## Please cite

See **`CITATION.md`** (existing) for the citation list (Dorkenwald et al. 2024 *Nature* 634;
Schlegel et al. 2024 *Nature*; Zheng et al. 2018 *Cell* 174) and for the energy-model references.
`CITATION.cff` is a **draft** with the author fields left **empty on purpose** — see
`RELEASE_CHECKLIST.md`.

## Not affiliated

**flyputer is an independent hobby project.** It is **not affiliated with, nor endorsed by,** the
FlyWire consortium, Princeton University, or the Allen Institute for Brain Science
(statement carried over from `CITATION.md`).

## Notes carried into the closing package (transparency)

- `LICENSE` (MIT) names **"Copyright (c) 2026 Migen Karriqi"**, while the **git author** of the 68
  commits is **`Furkan Tahsin Bekdaş`** → **inconsistency; decision pending with the owner**
  (`RELEASE_CHECKLIST.md`).
- The LLM/Ollama code path is **referenced by the live `server.py`/`game_loop.py`**; whether it is
  *unused* is **not verified** → marked `[VERIFY: is the Ollama/LLM path still used?]` in
  `numcog/RELEASE_PREFLIGHT.md` §5. Nothing was deleted.
- Historical large blobs (87.15 MB and 11.12 MB, both later removed) still exist **in git history**;
  history was **not** rewritten (`numcog/RELEASE_PREFLIGHT.md` §3).
