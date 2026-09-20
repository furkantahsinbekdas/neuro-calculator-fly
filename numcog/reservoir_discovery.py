"""
numcog/reservoir_discovery.py — FAZ 7-0: alt ağ keşfi (DİNAMİK DENEY YOK).

Ön-kayıt: HIPOTEZLER.md Faz 7 bölümü (commit `5e7956b`). Faz 0–6-0b DEĞİŞTİRİLMEZ.
Tüm hesaplar float64. Bağlantı dosyası pyarrow.ipc ile PARÇA PARÇA okunur (bellek güvenli).

Ölçülen: A (CX: EB/PB/FB/NO), A_geniş (duyarlılık), B (MB içi: KC/MBON/DAN/PPL/APL/DPM),
C (nöropil-kısıtlı rastgele SCC kontrolü) — hücre/kenar/sinaps, karşılıklılık, en büyük SCC,
NT kapsaması (NaN sayılır), uyarıcı/engelleyici oranı, işaretli W'nin spektral yarıçapı.

CLI: scan      (tek geçiş; tüm adaylar için kenar birikimi + CSV)
     metrics   (birikmiş kenarlardan metrikler + seçim kuralı)
     all       (ikisi birlikte)
"""
from __future__ import annotations
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.ipc as ipc

import number_coding as nc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p7_0")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")
CACHE = os.path.join(OUT, "scan_cache.npz")

BATCH = 1 << 16
CX_CORE = {"EB", "PB", "FB", "NO"}
CX_EXT = CX_CORE | {"GA_L", "GA_R", "CRE_L", "CRE_R", "LAL_L", "LAL_R", "IB_L", "IB_R",
                    "ICL_L", "ICL_R"}
NEUROPIL_MIN_ROWS = 1000
N_C_DRAWS = 30
SCC_LO, SCC_HI = 300, 5000
NT_POS = {"acetylcholine", "dopamine", "serotonin", "octopamine"}
NT_NEG = {"gaba", "glutamate"}
ANN_COLS = ["root_id", "cell_class", "super_class", "hemibrain_type", "cell_type",
            "top_nt", "known_nt", "side"]


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def parse_nt(s):
    """Çok-değerli NT etiketini işarete çevirir (';' ve ',' ile ayrılır; 'negative' -> belirsiz).

    Kural (ön-kayıtlı varsayım): ACh/dopamin/serotonin/oktopamin -> +1; GABA/glutamat -> -1;
    çelişki ya da listede olmayan (ör. histamin, sNPF) -> NaN (o kenar imzasız kalır).
    """
    if not isinstance(s, str) or not s.strip():
        return np.nan
    toks = [t.strip().lower() for t in re.split(r"[;,]", s)]
    toks = [t for t in toks if t and "negative" not in t]
    pos = any(t in NT_POS for t in toks)
    neg = any(t in NT_NEG for t in toks)
    if pos and not neg:
        return 1.0
    if neg and not pos:
        return -1.0
    return np.nan


def load_ann():
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann["root_id"] = ann["root_id"].astype("int64")
    h = ann.hemibrain_type.astype(str)
    known = ann.known_nt
    top = ann.top_nt
    # önce known_nt; NaN ise top_nt (ön-kayıtlı kural)
    lut_k = {v: parse_nt(v) for v in known.dropna().unique()}
    lut_t = {v: parse_nt(v) for v in top.dropna().unique()}
    s_known = known.map(lambda v: lut_k.get(v, np.nan))
    s_top = top.map(lambda v: lut_t.get(v, np.nan))
    ann["sign"] = np.where(s_known.notna(), s_known, s_top)
    ann["nt_used"] = np.where(ann["sign"] == 1, "pozitif",
                              np.where(ann["sign"] == -1, "negatif", "yok"))
    ann["nt_source"] = np.where(s_known.notna(), "known_nt",
                                np.where(s_top.notna(), "top_nt", "yok"))
    mb = (ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)
          | h.str.startswith("MBON") | h.str.startswith("PAM") | h.str.startswith("PPL1")
          | h.str.startswith("PPL2") | h.str.startswith("APL") | h.str.startswith("DPM"))
    ann["is_mb"] = mb
    return ann


def label_counts(ann):
    rows = []
    for nm, mask in (("KC", ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False,
                                                                    na=False)),
                     ("MBON", ann.hemibrain_type.astype(str).str.startswith("MBON")),
                     ("DAN-benzeri(PAM/PPL1/PPL2)",
                      ann.hemibrain_type.astype(str).str.startswith(("PAM", "PPL1", "PPL2"))),
                     ("APL", ann.hemibrain_type.astype(str).str.startswith("APL")),
                     ("DPM", ann.hemibrain_type.astype(str).str.startswith("DPM"))):
        sub = ann[mask]
        rows.append(dict(kume=nm, n=len(sub),
                         top_nt_dolu=int(sub.top_nt.notna().sum()),
                         known_nt_dolu=int(sub.known_nt.notna().sum()),
                         nt_used_dolu=int(sub.nt_used.notna().sum()),
                         sign_pozitif=int((sub.sign == 1).sum()),
                         sign_negatif=int((sub.sign == -1).sum())))
    ldf = pd.DataFrame(rows)
    ldf.to_csv(os.path.join(OUT, "label_counts.csv"), index=False)
    log("=== ADIM: ETİKET SAYIMI (NaN'lar sayıldı; dropna=False) ===")
    for _, r in ldf.iterrows():
        log("  %-26s n=%-5d top_nt=%-5d known_nt=%-5d imza=%-5d (+%d/-%d)"
            % (r.kume, r.n, r.top_nt_dolu, r.known_nt_dolu, r.nt_used_dolu,
               r.sign_pozitif, r.sign_negatif))
    log("  NT kaynağı (tüm annotation): %s"
        % dict(ann.nt_source.value_counts(dropna=False)))
    log("  ham top_nt değerleri (ilk 8): %s"
        % dict(list(ann.top_nt.value_counts(dropna=False).head(8).items())))
    log("  ham known_nt değerleri (ilk 8): %s"
        % dict(list(ann.known_nt.value_counts(dropna=False).head(8).items())))
    log("  NOT (veri gözlemi): KC'lerde top_nt çoğunlukla 'dopamine' (5172/5177) görünüyor ki bu")
    log("  biyolojik beklentiyle çelişir (KC kolinerjik); ön-kayıtlı kural gereği known_nt öncelikli")
    log("  olduğu için KC'lerde imza 'acetylcholine' kaynaklı +1 olur. Bu bir VERİ gözlemidir.")
    return ldf


def map_idx(ids, cells):
    """root_id -> global indeks (dict güncellenir); np.int32 döner."""
    uniq, inv = np.unique(ids, return_inverse=True)
    for r in uniq:
        r = int(r)
        if r not in cells:
            cells[r] = len(cells)
    lut = np.array([cells[int(r)] for r in uniq], dtype=np.int32)
    return lut[inv]


def scan():
    """Tek parça-parça geçiş: nöropil başına kenarlar + MB içi kenarlar + global hücre indeksi."""
    ann = load_ann()
    label_counts(ann)
    mb_arr = np.array(sorted(int(r) for r in ann.root_id[ann.is_mb]), dtype=np.int64)
    log("\n=== ADIM C: PARÇA PARÇA TARAMA (batch=%d, float64) ===" % BATCH)
    log("  MB hücre kümesi (KC+MBON+DAN+APL+DPM): %d" % len(mb_arr))
    cells = {}
    npp = {}
    mb_pre, mb_post, mb_syn = [], [], []
    f = ipc.open_file(nc.CONN_FILE)
    nb = f.num_record_batches
    t0 = time.time()
    tot = 0
    for bi in range(nb):
        b = f.get_batch(bi).to_pandas()
        pre = b.pre_pt_root_id.to_numpy(np.int64)
        post = b.post_pt_root_id.to_numpy(np.int64)
        syn = b.syn_count.to_numpy(np.float32)
        npl = b.neuropil.astype(str).to_numpy()
        pi = map_idx(pre, cells)
        qi = map_idx(post, cells)
        for code in np.unique(npl):
            m = (npl == code)
            npp.setdefault(str(code), []).append((pi[m], qi[m], syn[m]))
        m = np.isin(pre, mb_arr) & np.isin(post, mb_arr)
        if m.any():
            mb_pre.append(pi[m])
            mb_post.append(qi[m])
            mb_syn.append(syn[m])
        tot += len(b)
        if (bi + 1) % 40 == 0:
            log("  %d/%d batch (%d satır, %.0fs, hücre %d, nöropil anahtar %d)"
                % (bi + 1, nb, tot, time.time() - t0, len(cells), len(npp)))
    log("  tarama bitti: %d satır, %d benzersiz hücre (%.0fs)"
        % (tot, len(cells), time.time() - t0))
    ids = np.empty(len(cells), dtype=np.int64)
    for r, i in cells.items():
        ids[i] = r
    out = {"cell_ids": ids,
           "mb_pre": np.concatenate(mb_pre) if mb_pre else np.zeros(0, np.int32),
           "mb_post": np.concatenate(mb_post) if mb_post else np.zeros(0, np.int32),
           "mb_syn": np.concatenate(mb_syn) if mb_syn else np.zeros(0, np.float32)}
    npcount = {}
    for code, lst in npp.items():
        pr = np.concatenate([x[0] for x in lst])
        po = np.concatenate([x[1] for x in lst])
        sy = np.concatenate([x[2] for x in lst])
        out["np_%s_pre" % code] = pr
        out["np_%s_post" % code] = po
        out["np_%s_syn" % code] = sy
        npcount[code] = len(pr)
    np.savez_compressed(CACHE, **out)
    pd.DataFrame(dict(neuropil=list(npcount.keys()), rows=list(npcount.values()))
                 ).sort_values("rows", ascending=False).to_csv(
        os.path.join(OUT, "neuropil_counts.csv"), index=False)
    log("  önbellek yazıldı: %s (%.0f MB)" % (CACHE, os.path.getsize(CACHE) / 1e6))
    log("  MB içi kenar: %d | nöropil anahtarı: %d" % (len(out["mb_pre"]), len(npcount)))
def largest_scc(n, rows, cols):
    """En büyük güçlü bağlı bileşen boyutu (iteratif Tarjan; float64/indeks tabanlı)."""
    adj = [[] for _ in range(n)]
    for a, b in zip(rows.tolist(), cols.tolist()):
        if a != b:
            adj[a].append(b)
    index = [-1] * n
    low = [0] * n
    on = [False] * n
    st = []
    best = 0
    idx = 0
    for v0 in range(n):
        if index[v0] != -1:
            continue
        work = [(v0, 0)]
        while work:
            v, pi = work[-1]
            if pi == 0:
                index[v] = low[v] = idx
                idx += 1
                st.append(v)
                on[v] = True
            descended = False
            av = adj[v]
            while pi < len(av):
                w = av[pi]
                pi += 1
                if index[w] == -1:
                    work[-1] = (v, pi)
                    work.append((w, 0))
                    descended = True
                    break
                if on[w]:
                    low[v] = min(low[v], index[w])
            if descended:
                continue
            work[-1] = (v, pi)
            if low[v] == index[v]:
                cnt = 0
                while True:
                    w = st.pop()
                    on[w] = False
                    cnt += 1
                    if w == v:
                        break
                best = max(best, cnt)
            work.pop()
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    return best


def rho_power(rows, cols, vals, n, iters=400, tol=1e-12, seed=0):
    """Güç iterasyonu ile spektral yarıçap tahmini (float64)."""
    if len(rows) == 0 or n == 0:
        return 0.0
    rng = np.random.RandomState(seed)
    x = rng.normal(size=n)
    x /= (np.linalg.norm(x) + 1e-300)
    rho = 0.0
    for _ in range(iters):
        y = np.bincount(rows, weights=vals * x[cols], minlength=n)
        nr = float(np.linalg.norm(y))
        if nr <= 0:
            return 0.0
        x = y / nr
        if abs(nr - rho) <= tol * max(abs(nr), 1e-12):
            return nr
        rho = nr
    return rho


def metrics_for(name, pre, post, syn, sign_of, cell_ids, do_rho=True):
    """Bir aday için metrikler (float64; ikili yapı + sinaps ağırlığı)."""
    pair = np.stack([pre.astype(np.int64), post.astype(np.int64)], axis=1)
    pairs, inv = np.unique(pair, axis=0, return_inverse=True)
    w = np.zeros(len(pairs), dtype=np.float64)
    np.add.at(w, inv.ravel(), syn.astype(np.float64))
    a, b = pairs[:, 0], pairs[:, 1]
    nodes = np.unique(pairs)
    n = int(nodes.max()) + 1
    # karşılıklılık
    key = a * (int(b.max()) + 1) + b
    key_rev = b * (int(b.max()) + 1) + a
    recip = int(np.isin(key_rev, key).sum())
    scc = largest_scc(n, a, b)
    # işaretler (pre hücrenin NT'si)
    s_pre = sign_of[a]
    exc = int(np.sum(s_pre > 0))
    inh = int(np.sum(s_pre < 0))
    unk = int(len(a) - exc - inh)
    vals = np.where(np.isnan(s_pre), 0.0, s_pre)
    rho_s = rho_power(a, b, vals, n) if do_rho else float("nan")
    rho_a = rho_power(a, b, np.abs(vals), n) if do_rho else float("nan")
    # SCC içine kısıtlı spektral yarıçap (KEŞİFSEL not)
    return dict(candidate=name, cells=int((np.bincount(nodes, minlength=n) > 0).sum()),
                nodes_reached=len(nodes), edges=int(len(pairs)),
                synapses=float(w.sum()), reciprocal=int(recip),
                reciprocal_ratio=float(recip) / max(len(pairs), 1), largest_scc=int(scc),
                edges_exc=exc, edges_inh=inh, edges_unknown=unk,
                exc_frac=exc / max(len(pairs), 1), inh_frac=inh / max(len(pairs), 1),
                unknown_frac=unk / max(len(pairs), 1),
                rho_signed=float(rho_s), rho_abs=float(rho_a),
                g_crit=float(1.0 / rho_s) if rho_s > 0 else float("inf"))


def metrics_all():
    d = np.load(CACHE)
    cell_ids = d["cell_ids"]
    ann = load_ann()
    sig = ann.set_index("root_id").sign
    sign_of = sig.reindex(cell_ids).to_numpy(dtype=float)
    codes = sorted({k[3:-4] for k in d.files if k.startswith("np_") and k.endswith("_pre")})

    def collect(keys):
        pre, post, syn = [], [], []
        for c in keys:
            k = "np_%s_pre" % c
            if k in d.files:
                pre.append(d[k])
                post.append(d["np_%s_post" % c])
                syn.append(d["np_%s_syn" % c])
        if not pre:
            return (np.zeros(0, np.int32),) * 3
        return (np.concatenate(pre), np.concatenate(post), np.concatenate(syn))

    log("\n=== ADIM C: ADAY METRİKLERİ ===")
    rows = []
    for tag, keys in (("A (CX core: EB/PB/FB/NO)", [c for c in codes if c in CX_CORE]),
                      ("A_genis (duyarlılık)", [c for c in codes if c in CX_EXT])):
        pre, post, syn = collect(keys)
        if len(pre) == 0:
            continue
        have = set(np.unique(pre).tolist()) & set(np.unique(post).tolist())
        cells = np.array(sorted(have), dtype=np.int64)
        m = np.isin(pre, cells) & np.isin(post, cells)
        r = metrics_for(tag, pre[m], post[m], syn[m], sign_of, cell_ids)
        r["cx_cell_set"] = int(len(cells))
        r["nt_labeled_cells"] = int(np.sum(~np.isnan(sign_of[cells])))
        r["nt_coverage_cells"] = float(np.mean(~np.isnan(sign_of[cells]))) if len(cells) else 0.0
        rows.append(r)
        log("  %-26s alt-graf hücre=%-6d (CX küme=%d) kenar=%-7d sinaps=%-9.0f "
            "karşılıklı=%.3f SCC=%-6d rho(+/-)=%.3f (|W| %.3f) | kenar imzası: +%.2f -%.2f "
            "belirsiz %.2f"
            % (tag, r["cells"], r["cx_cell_set"], r["edges"], r["synapses"],
               r["reciprocal_ratio"], r["largest_scc"], r["rho_signed"], r["rho_abs"],
               r["exc_frac"], r["inh_frac"], r["unknown_frac"]))
    preB, postB, synB = d["mb_pre"], d["mb_post"], d["mb_syn"]
    rB = metrics_for("B (MB: KC/MBON/DAN/APL/DPM)", preB, postB, synB, sign_of, cell_ids)
    mb_cells = np.unique(np.concatenate([preB, postB]))
    rB["nt_labeled_cells"] = int(np.sum(~np.isnan(sign_of[mb_cells])))
    rB["nt_coverage_cells"] = float(np.mean(~np.isnan(sign_of[mb_cells])))
    rows.append(rB)
    log("  %-26s hücre=%-6d kenar=%-7d sinaps=%-9.0f "
        "karşılıklı=%.3f SCC=%-6d rho(+/-)=%.3f (|W| %.3f) | kenar imzası: +%.2f -%.2f belirsiz %.2f"
        % (rB["candidate"], rB["cells"], rB["edges"], rB["synapses"],
           rB["reciprocal_ratio"], rB["largest_scc"], rB["rho_signed"], rB["rho_abs"],
           rB["exc_frac"], rB["inh_frac"], rB["unknown_frac"]))
    return rows, d, sign_of, cell_ids


def c_and_select(rows, d):
    npc = pd.read_csv(os.path.join(OUT, "neuropil_counts.csv"))
    elig = npc[npc.rows >= NEUROPIL_MIN_ROWS].reset_index(drop=True)
    log("\n  C kontrolü: %d uygun nöropil (>=%d satır)" % (len(elig), NEUROPIL_MIN_ROWS))
    sccs, sizes = {}, {}
    t0 = time.time()
    for code in elig.neuropil:
        pr, po = d["np_%s_pre" % code], d["np_%s_post" % code]
        n = int(max(pr.max(), po.max())) + 1
        sccs[code] = largest_scc(n, pr, po)
        sizes[code] = (len(np.unique(np.concatenate([pr, po]))), len(pr))
    log("  tüm uygun nöropiller için SCC hesaplandı (%.0fs)" % (time.time() - t0))
    ref = max(sccs, key=lambda k: sccs[k])
    rng = np.random.RandomState(7001)
    draws = rng.choice(elig.neuropil.values, size=N_C_DRAWS, replace=True)
    cdf = pd.DataFrame(dict(seed=np.arange(N_C_DRAWS), neuropil=draws,
                            cells=[sizes[c][0] for c in draws],
                            edges=[sizes[c][1] for c in draws],
                            largest_scc=[sccs[c] for c in draws]))
    cdf.to_csv(os.path.join(OUT, "c_draws.csv"), index=False)
    log("  C (30 rastgele nöropil): SCC medyan=%.0f min=%d max=%d | hücre medyan=%.0f"
        % (cdf.largest_scc.median(), cdf.largest_scc.min(), cdf.largest_scc.max(),
           cdf.cells.median()))
    log("  C referans (en büyük SCC): %s (hücre=%d, kenar=%d, SCC=%d)"
        % (ref, sizes[ref][0], sizes[ref][1], sccs[ref]))
    pd.DataFrame(dict(neuropil=list(sccs.keys()), cells=[sizes[k][0] for k in sccs],
                      edges=[sizes[k][1] for k in sccs],
                      largest_scc=[sccs[k] for k in sccs])).sort_values(
        "largest_scc", ascending=False).to_csv(os.path.join(OUT, "neuropil_scc.csv"),
                                               index=False)
    eligible = [r for r in rows if SCC_LO <= r["largest_scc"] <= SCC_HI]
    prim = next((r for r in eligible if r["candidate"].startswith("A (CX core")), None)
    if prim is None:
        prim = next((r for r in eligible if r["candidate"].startswith("B")), None)
    for r in rows:
        r["eligible"] = int(SCC_LO <= r["largest_scc"] <= SCC_HI)
        r["role"] = ("BIRINCIL" if r is prim else
                     ("ikincil" if (r in eligible and r is not prim) else "uygun degil"))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT, "candidates.csv"), index=False)
    log("\n=== SEÇİM KURALI (ön-kayıtlı: SCC 300-5000; A uygunsa A, değilse B) ===")
    for _, r in out.iterrows():
        log("  %-26s SCC=%-6d uygun=%-2d rol=%s" % (r.candidate, r.largest_scc, r.eligible,
                                                    r.role))
    log("  => BİRİNCİL: %s" % (prim["candidate"] if prim is not None else "YOK"))
    if prim is not None:
        E, N = prim["edges"], prim["cells"]
        log("  maliyet (birincil, N=%d, E=%d): seyrek W ~%.0f MB; adım başına ~%d çarpma; "
            "T=500 adım ~%.1f M işlem" % (N, E, 16 * E / 1e6, E, E * 500 / 1e6))
        log("  doğrusal kararlılık: g_crit = 1/rho = %.3f" % prim["g_crit"])
    return out, cdf


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "all"
    if cmd not in ("scan", "metrics", "all"):
        log("bilinmeyen komut: %s" % cmd)
        return
    if cmd in ("scan", "all"):
        scan()
    if cmd in ("metrics", "all"):
        rows, d, _, _ = metrics_all()
        c_and_select(rows, d)


if __name__ == "__main__":
    main()

