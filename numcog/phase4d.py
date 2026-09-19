"""
numcog/phase4d.py — FAZ 4D: N=81 tablo kapasitesi, uzun optimizasyonla (kısa).

Izgara: epoch {10000,25000} x lr {0.01,0.05} x topk {40,80}, sigma=1.5, N=81.
Seçim ölçütü YALNIZCA tablo doğruluğu. Mevcut modüller import edilir, DEĞİŞTİRİLMEZ.
"""
from __future__ import annotations
import os
import time

import numpy as np
import pandas as pd

import operator_diagnosis as od
import calculator as cal
import phase4c as p4c

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4d")
N_BIG = 81
SEEDS_GRID = 30
SEEDS_FINAL = 100
GRID = [(ep, lr, tk) for ep in (10000, 25000) for lr in (0.01, 0.05) for tk in (40, 80)]


def run_grid():
    mats = od.load_sets()
    rows = []
    for (ep, lr, tk) in GRID:
        full, accs = 0, []
        t0 = time.time()
        for s in range(SEEDS_GRID):
            acc, wrong, _ = p4c.table_eval(N_BIG, s, mats, epochs=ep, lr=lr, topk=tk)
            accs.append(acc)
            full += int(len(wrong) == 0)
        rows.append(dict(epochs=ep, lr=lr, topk=tk, full=full, frac=full / SEEDS_GRID,
                         acc=float(np.mean(accs)), sec=time.time() - t0))
        print("  ep=%-6d lr=%.2f topk=%-3d tam-dogru=%2d/%d (%.1f%%) egitim=%.4f (%.0fs)"
              % (ep, lr, tk, full, SEEDS_GRID, 100 * full / SEEDS_GRID, np.mean(accs), rows[-1]["sec"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "grid81.csv"), index=False)
    return df


def final_measure(ep, lr, tk, seeds=SEEDS_FINAL):
    mats = od.load_sets()
    rows, chain = [], []
    for s in range(seeds):
        acc, wrong, code = p4c.table_eval(N_BIG, s, mats, epochs=ep, lr=lr, topk=tk)
        X = np.array([code(n, op) for n in range(N_BIG + 1) for op in ('+', '-')], np.float32)
        y = np.array([od.clip_result(n, op, N_BIG) for n in range(N_BIG + 1) for op in ('+', '-')])
        W, b = p4c.fit_fast(X, y, N_BIG + 1, lr, ep, s)
        core = p4c.Core(N_BIG, code, W, b)
        r = od.calc_measure(N_BIG, s, mats, core)
        rows.append(dict(seed=s, table=acc, full=int(len(wrong) == 0), add=r["add"],
                         subtract=r["subtract"], multiply=r["multiply"], divide=r["divide"]))
        chain.extend(r["chain"])
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "final_seeds.csv"), index=False)
    cdf = cal.chain_vs_k(chain, float(df["add"].mean()))
    cdf.to_csv(os.path.join(OUT, "final_chain.csv"), index=False)
    print("tablo tam-dogru: %d/%d" % (int(df.full.sum()), len(df)))
    for k in ("add", "subtract", "multiply", "divide"):
        m = float(df[k].mean())
        sd = float(df[k].std(ddof=1))
        ci = 1.96 * sd / np.sqrt(len(df))
        print("  %-9s ort=%.4f +- %.4f  min=%.3f  (GA95 %.4f-%.4f)"
              % (k, m, sd, df[k].min(), m - ci, m + ci))
    print("zincir (ilk 3 / son 3):")
    print(cdf.head(3).to_string(index=False))
    print(cdf.tail(3).to_string(index=False))
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=== IZGARA (N=%d, %d tohum) ===" % (N_BIG, SEEDS_GRID))
    g = run_grid()
    ok = g[g.frac >= 0.95]
    if len(ok):
        best = ok.sort_values(["frac", "acc"], ascending=False).iloc[0]
        ep, lr, tk = int(best.epochs), float(best.lr), int(best.topk)
        print("\nBASARILI: ep=%d lr=%.2f topk=%d (%.1f%%) -> KONFIG DONDU"
              % (ep, lr, tk, 100 * best.frac))
        print("\n=== SON OLCUM (donmus, %d tohum, N=%d) ===" % (SEEDS_FINAL, N_BIG))
        final_measure(ep, lr, tk)
    else:
        print("\nBU IZGARADA ULASILAMADI (hicbir hucre >=%95).")
        print("IKI HANELI YEDEK (TASARIM): onlar/birler ayri kanal (her biri N=9), elde/borc KONTROLCUDE.")
    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()
