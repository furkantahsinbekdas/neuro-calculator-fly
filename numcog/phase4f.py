"""
numcog/phase4f.py — FAZ 4F: N=81, dolgu + sigma genişletme (kısa, ön-kayıtlı).

Izgara: dolgu sabit [-3, N+3]; sigma in {2.0,2.5,3.0,4.0} x top-k in {80,120}; ep 25000, lr 0.05;
30 tohum. Başarı: >=%95 tohum %100 tablo. Seçim ölçütü YALNIZCA tablo doğruluğu.
Mevcut modüller import edilir, DEĞİŞTİRİLMEZ.

CLI (paralel/shard'lı, sonuçlar seri koşuyla birebir aynıdır):
  cell <cid> [shard nsh] | merge | sanity | final <shard> <nsh> | finalmerge
"""
from __future__ import annotations
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

import operator_diagnosis as od
import calculator as cal
import phase4c as p4c

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4f")
P4E = os.path.join(HERE, "results_p4e")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

N_BIG = 81
PAD = (-3.0, float(N_BIG + 3))          # 4E'nin en iyi dolgusu (sabit)
SIGMAS = (2.0, 2.5, 3.0, 4.0)
TOPKS = (80, 120)
CELLS = [(sg, tk) for sg in SIGMAS for tk in TOPKS]
EPOCHS = 25000
LR = 0.05
SEEDS = 30
SEEDS_FINAL = 100
SUCCESS = 0.95
PAIRS = [(n, op) for n in range(N_BIG + 1) for op in ('+', '-')]
CHAIN_COLS = ["op", "a", "b", "k", "ok", "got", "want"]


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def wilson(k, n):
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2.0 * n)
    hw = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return float((c - hw) / d), float((c + hw) / d)


def dup_conflicts(X, y):
    """Özdeş kod + farklı etiket çatışması (satır sayısı)."""
    _, _, inv = np.unique(X, axis=0, return_index=True, return_inverse=True)
    groups = {}
    for i, g in enumerate(inv):
        groups.setdefault(int(g), []).append(i)
    return int(sum(len(ids) for ids in groups.values()
                   if len(ids) > 1 and len({int(y[i]) for i in ids}) > 1))


def build(sigma, topk, seed, mats, lo=PAD[0], hi=PAD[1]):
    """Kod + X + y + eğitim; tablo doğruluğu (table_eval ile aynı matematik)."""
    code = p4c.make_code(N_BIG, seed, mats, sigma, lo, hi, topk)
    X = np.array([code(n, op) for n, op in PAIRS], np.float32)
    y = np.array([od.clip_result(n, op, N_BIG) for n, op in PAIRS])
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        W, b = p4c.fit_fast(X, y, N_BIG + 1, LR, EPOCHS, seed)
        pred = (X @ W.T + b).argmax(1)
    nan = int(not (np.isfinite(W).all() and np.isfinite(b).all()))
    return dict(code=code, X=X, y=y, W=W, b=b, acc=float(np.mean(pred == y)),
                n_wrong=int(np.sum(pred != y)), nan=nan)


def cell_paths(cid):
    return sorted(glob.glob(os.path.join(OUT, "cell%d_s*.csv" % cid)))


def done_seeds(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return set()
    try:
        df = pd.read_csv(path)
        return set(int(s) for s in df.seed) if "seed" in df.columns else set()
    except Exception:
        return set()


def cell_job(cid, shard=0, nsh=1):
    sg, tk = CELLS[cid]
    path = os.path.join(OUT, "cell%d_s%d.csv" % (cid, shard))
    done = set()
    for p in cell_paths(cid):
        done |= done_seeds(p)
    todo = [s for s in range(SEEDS)[shard::nsh] if s not in done]
    log("\n=== HUCRE %d: sigma=%.1f top-k=%d dolgu=%s | shard %d/%d, %d tohum ==="
        % (cid, sg, tk, PAD, shard + 1, nsh, len(todo)))
    mats = od.load_sets()
    for s in todo:
        t0 = time.time()
        r = build(sg, tk, s, mats)
        row = dict(seed=s, sigma=sg, topk=tk, acc=r["acc"], n_wrong=r["n_wrong"],
                   full=int(r["n_wrong"] == 0), nan=r["nan"],
                   dup_conflict=dup_conflicts(r["X"], r["y"]),
                   rank=int(np.linalg.matrix_rank(r["X"])), sec=time.time() - t0)
        wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
        pd.DataFrame([row]).to_csv(path, mode="a", header=wh, index=False)
        log("  [s%d] tohum %2d: acc=%.4f tam=%d cakisma=%d rank=%d tasma(NaN)=%d (%.0fs)"
            % (shard, s, row["acc"], row["full"], row["dup_conflict"], row["rank"],
               row["nan"], row["sec"]))
    log("hucre %d shard %d bitti." % (cid, shard + 1))


def merge():
    parts = [pd.read_csv(p) for cid in range(len(CELLS)) for p in cell_paths(cid)]
    raw = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["seed", "sigma", "topk"])
    raw = raw.sort_values(["sigma", "topk", "seed"])
    raw.to_csv(os.path.join(OUT, "grid81_4f.csv"), index=False)
    rows = []
    for sg, tk in CELLS:
        sub = raw[(raw.sigma == sg) & (raw.topk == tk)]
        n = len(sub)
        if n == 0:
            log("  sigma=%.1f topk=%-3d -> veri YOK (atlandi)" % (sg, tk))
            continue
        full = int(sub.full.sum())
        lo, hi = wilson(full, n)
        rows.append(dict(sigma=sg, topk=tk, n=n, full=full, frac=full / n, ci_lo=lo, ci_hi=hi,
                         acc=float(sub.acc.mean()), dup_mean=float(sub.dup_conflict.mean()),
                         dup_total=int(sub.dup_conflict.sum()),
                         nan_total=int(sub.nan.sum()),
                         rank_lt=int((sub["rank"] < len(PAIRS)).sum())))
        log("  sigma=%.1f topk=%-3d tam=%2d/%d (%5.1f%%) GA95=[%4.1f,%4.1f] egitim=%.4f "
            "cakisma(ort/top)=%.2f/%d rank<%d: %d/%d tasma(NaN)=%d"
            % (sg, tk, full, n, 100 * full / n, 100 * lo, 100 * hi, rows[-1]["acc"],
               rows[-1]["dup_mean"], rows[-1]["dup_total"], len(PAIRS), rows[-1]["rank_lt"], n,
               rows[-1]["nan_total"]))
    gdf = pd.DataFrame(rows)
    gdf.to_csv(os.path.join(OUT, "grid81_4f_summary.csv"), index=False)
    verd = []
    for tk in TOPKS:
        s = gdf[gdf.topk == tk].sort_values("sigma")
        seq = [float(x) for x in s.frac]
        mono = all(seq[i + 1] >= seq[i] - 1e-12 for i in range(len(seq) - 1))
        base = float(s[s.sigma == 2.0].frac.iloc[0])
        drop = bool(((s.sigma.isin([3.0, 4.0])) & (s.frac < base)).any())
        verd.append(dict(topk=tk, seq=seq, monotone=mono, refuted=drop))
        log("H4f.1 (top-k=%d): sigma dizisi %s | monoton=%s | sigma 3.0/4.0 < sigma 2.0 -> %s"
            % (tk, [round(x, 3) for x in seq], mono, "CURUTULDU" if drop else "DESTEK"))
    pd.DataFrame(verd).to_csv(os.path.join(OUT, "h4f1.csv"), index=False)
    ok = gdf[gdf.frac >= SUCCESS]
    if len(ok):
        best = ok.sort_values(["frac", "acc"], ascending=False).iloc[0]
        frozen = dict(sigma=float(best.sigma), topk=int(best.topk), frac=float(best.frac))
        log("BASARILI HUCRE: sigma=%.1f top-k=%d (%.1f%%) -> DONDU"
            % (best.sigma, best.topk, 100 * best.frac))
    else:
        frozen = None
        log(">=%95 saglayan hucre YOK -> bu izgarada ulasilamadi; kalibrasyon kapisi cozum olarak kalir.")
    with open(os.path.join(OUT, "frozen.json"), "w", encoding="utf-8") as f:
        json.dump(frozen, f)
    return gdf, frozen


def sanity():
    fin = pd.read_csv(os.path.join(P4E, "final81_seeds.csv"))
    pool = sorted(int(x) for x in fin.seed)
    rng = np.random.RandomState(2026)
    pick = sorted(int(x) for x in rng.choice(pool, size=3, replace=False))
    ref = pd.read_csv(os.path.join(P4E, "chain81_rows.csv"))
    log("\n=== SAGLAMA (determinizm): 4E kabul edilen 54 tohumdan 3'u = %s ===" % pick)
    mats = od.load_sets()
    rows = []
    for s in pick:
        r = build(1.5, 80, s, mats, 0.0, None)          # 4E hücresi: sigma=1.5, dolgu YOK
        res = od.calc_measure(N_BIG, s, mats, p4c.Core(N_BIG, r["code"], r["W"], r["b"]))
        got = pd.DataFrame([dict(seed=s, **c) for c in res["chain"]])
        got = got.sort_values(["op", "a", "b"])[CHAIN_COLS].reset_index(drop=True)
        want = ref[ref.seed == s].sort_values(["op", "a", "b"])[CHAIN_COLS].reset_index(drop=True)
        same = bool(len(got) == len(want)) and bool(got.equals(want))
        diff = 0 if same else int((got.values != want.values).sum()) if len(got) == len(want) else -1
        rows.append(dict(seed=s, n_rows=len(got), identical=int(same), diff_cells=diff,
                         table_acc=r["acc"]))
        log("  tohum %2d: %d satir | BIREBIR AYNI = %s (farkli hucre: %s) | tablo=%.4f"
            % (s, len(got), same, diff, r["acc"]))
    sdf = pd.DataFrame(rows)
    sdf.to_csv(os.path.join(OUT, "sanity_determinism.csv"), index=False)
    log("SAGLAMA SONUC: %s" % ("TAM AYNI (3/3)" if bool((sdf.identical == 1).all())
                               else "FARK VAR -> incelenmeli"))
    return sdf


def final_job(shard=0, nsh=1):
    with open(os.path.join(OUT, "frozen.json"), encoding="utf-8") as f:
        frozen = json.load(f)
    if not frozen:
        log("\ndonmus konfigurasyon YOK -> kapisiz son olcum yapilmaz (on-kayitli karar).")
        return
    sg, tk = float(frozen["sigma"]), int(frozen["topk"])
    path = os.path.join(OUT, "final_s%d.csv" % shard)
    cpath = os.path.join(OUT, "final_chain_s%d.csv" % shard)
    done = set()
    for p in glob.glob(os.path.join(OUT, "final_s*.csv")):
        done |= done_seeds(p)
    todo = [s for s in range(SEEDS_FINAL)[shard::nsh] if s not in done]
    log("\n=== SON OLCUM (KALIBRASYON KAPISI YOK, %d tohum) sigma=%.1f top-k=%d dolgu=%s | "
        "shard %d/%d: %d tohum ===" % (SEEDS_FINAL, sg, tk, PAD, shard + 1, nsh, len(todo)))
    mats = od.load_sets()
    for s in todo:
        t0 = time.time()
        r = build(sg, tk, s, mats)
        res = od.calc_measure(N_BIG, s, mats, p4c.Core(N_BIG, r["code"], r["W"], r["b"]))
        row = dict(seed=s, table=r["acc"], full=int(r["n_wrong"] == 0),
                   add=res["add"], subtract=res["subtract"], multiply=res["multiply"],
                   divide=res["divide"], calls=res["calls"])
        wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
        pd.DataFrame([row]).to_csv(path, mode="a", header=wh, index=False)
        crows = [dict(seed=s, **c) for c in res["chain"]]
        cwh = (not os.path.exists(cpath)) or os.path.getsize(cpath) == 0
        pd.DataFrame(crows).to_csv(cpath, mode="a", header=cwh, index=False)
        log("  [s%d] tohum %2d: tablo=%.4f tam=%d add=%.3f sub=%.3f mul=%.3f div=%.3f (%.0fs)"
            % (shard, s, row["table"], row["full"], row["add"], row["subtract"],
               row["multiply"], row["divide"], time.time() - t0))
    log("son olcum shard %d bitti." % (shard + 1))


def finalmerge():
    parts = [pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT, "final_s*.csv")))]
    raw = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["seed"]).sort_values("seed")
    raw.to_csv(os.path.join(OUT, "final81_4f_seeds.csv"), index=False)
    log("\nKAPISIZ son olcum: %d tohum | tablosu %100 olan = %d/%d"
        % (len(raw), int(raw.full.sum()), len(raw)))
    for k in ("add", "subtract", "multiply", "divide"):
        v = raw[k]
        m = float(v.mean())
        sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
        ci = 1.96 * sd / np.sqrt(len(v))
        log("  %-9s ort=%.4f +- %.4f min=%.4f GA95=[%.4f,%.4f] dagilim=%s"
            % (k, m, sd, float(v.min()), m - ci, m + ci,
               dict(v.value_counts().sort_index())))
    bad = raw[raw.full == 0]
    log("  tablosu %100 OLMAYAN %d tohumda: add=%.4f sub=%.4f mul=%.4f div=%.4f"
        % (len(bad), float(bad["add"].mean()) if len(bad) else float("nan"),
           float(bad["subtract"].mean()) if len(bad) else float("nan"),
           float(bad["multiply"].mean()) if len(bad) else float("nan"),
           float(bad["divide"].mean()) if len(bad) else float("nan")))
    cparts = [pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT, "final_chain_s*.csv")))]
    craw = pd.concat(cparts, ignore_index=True).drop_duplicates(subset=["seed", "op", "a", "b", "k"])
    craw.to_csv(os.path.join(OUT, "final81_4f_rows.csv"), index=False)
    cdf = cal.chain_vs_k(craw.to_dict("records"), float(raw["add"].mean()))
    cdf.to_csv(os.path.join(OUT, "final81_4f_chain.csv"), index=False)
    log("zincir: %d adim / %d tohum; adim dogrulugu = %.4f"
        % (len(craw), int(craw.seed.nunique()), float(craw.ok.mean())))
    log(cdf.head(4).to_string(index=False))
    log(cdf.tail(4).to_string(index=False))
    return raw, cdf


def main():
    a = sys.argv[1:]
    if not a:
        log("kullanim: cell <cid> [shard nsh] | merge | sanity | final <shard> <nsh> | finalmerge")
        return
    cmd = a[0]
    if cmd == "cell":
        cid = int(a[1])
        shard, nsh = (int(a[2]), int(a[3])) if len(a) >= 4 else (0, 1)
        cell_job(cid, shard, nsh)
    elif cmd == "merge":
        merge()
    elif cmd == "sanity":
        sanity()
    elif cmd == "final":
        shard, nsh = (int(a[1]), int(a[2])) if len(a) >= 3 else (0, 1)
        final_job(shard, nsh)
    elif cmd == "finalmerge":
        finalmerge()
    else:
        log("bilinmeyen komut: %s" % cmd)


if __name__ == "__main__":
    main()


