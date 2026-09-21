# DATA — FlyWire connectome (download, license, what the code reads)

This repository does **not** ship the connectome. Two files must exist in the repository root.

## 1. Files and how to get them

| file | ~size | how |
|---|---|---|
| `proofread_connections_783.feather` | **812 MB** (working tree) | `bash get_data.sh` (existing script) → downloads `https://zenodo.org/records/10676866/files/proofread_connections_783.feather` |
| `annotations_783.tsv` | **30 MB** (working tree) | auto-downloaded on the first run of `flysim.py` (per the header comment of `get_data.sh`) |

Both are listed in `.gitignore` (`proofread_connections_783.feather`, `annotations_783.tsv`) ✓ and
`git ls-files --error-unmatch <file>` confirms **neither is tracked** ✓
(`numcog/RELEASE_PREFLIGHT.md` §2).

## 2. License

**CC BY-NC 4.0 (non-commercial)** — as stated in this repository's existing `CITATION.md`
("Bulk connectivity (v783), CC BY-NC 4.0: https://zenodo.org/records/10676866").
**[VERIFY: license terms of the FlyWire/Codex release used]** — the upstream license page was **not**
independently checked while writing this document.

Cite (from `CITATION.md`): Dorkenwald et al. 2024 *Nature* 634 · Schlegel et al. 2024 *Nature* ·
Zheng et al. 2018 *Cell* 174.

## 3. What the code actually reads (columns)

| where | columns used | source |
|---|---|---|
| `numcog/number_coding.py::_load()` | annotations: `root_id`, `cell_class`, `super_class`, `hemibrain_type`; connections: `pre_pt_root_id`, `post_pt_root_id`, `syn_count` | code |
| `numcog/reservoir_run.py::ANN_COLS` | annotations: `root_id`, `hemibrain_type`, `cell_class`, `known_nt`, `top_nt` | code |
| `numcog/mb_learning.py::load_ann()` | annotations (full `read_csv`, sep="\t") | code |

## 4. Edge thresholds used per phase (they differ — check before comparing)

| phase / module | threshold | note |
|---|---|---|
| Faz 1 (`number_coding.build_matrices`) | **`min_syn = 3`** | `RAPOR_FAZ_1.md` |
| Faz 4x (`operator_diagnosis.load_sets`) | **`min_syn = 1`** | code (`nc.build_matrices(min_syn=1)`) |
| Faz 7-0/7-1 (`reservoir_run`, `reservoir_fair`) | **`min_syn = 3`** | `RAPOR_FAZ_7_0.md`, code |
| Faz 8 (`mb_learning.MIN_SYN`) | **`min_syn = 3`** | `RAPOR_FAZ_8.md` §0 |

**This matters:** "edge counts" in different reports are **not** directly comparable if the
thresholds differ (e.g. ALPN→KC: 23,618 edges at `min_syn=3` in Faz 8 vs the Faz-4x matrices built at
`min_syn=1`).

## 5. Cell-class labels used

`Kenyon_Cell` (KC, 5,177) · `ALPN` (685) · `MBON` (96) · `DAN` (331; PAM 307 / PPL1 16 / PPL2 8) ·
`super_class == visual_projection` (VPN, 265 with ≥1 edge) · CX neuropils `EB/PB/FB/NO`
(`numcog/reservoir_discovery.py`). **NT labels:** `known_nt` → `top_nt`, with the sign rule of
`RAPOR_FAZ_7_0.md`; **known conflict:** KC `top_nt = "dopamine"` for 5,172/5,177 cells, while
`known_nt` says acetylcholine → **KC sign fixed to +1 (ACh)** in Faz 7-3/8 (`RAPOR_FAZ_7_3.md`,
`RAPOR_FAZ_8.md`).
