"""
numcog/phase4e_chain.py — FAZ 4E Adım 4: zincir (p^k) ölçümü — kesintiye dayanıklı, tek iş parçacıklı.

Kalibrasyon kapısından geçen her sinek için kontrolcü zinciri ölçülür; her tohumdan SONRA ham
zincir satırları diske eklenir (kesinti olsa da ilerleme korunur). Ön-kayıt/konfigürasyon değişmedi
(4D en iyi hücre: ep 25000, lr 0.05, top-k 80, sigma=1.5, N=81).
"""
from __future__ import annotations
import os
import sys
import time

import numpy as np
import pandas as pd

import operator_diagnosis as od
import calculator as cal
import phase4c as p4c
import phase4e as p4e

OUT = p4e.OUT
N_BIG = p4e.N_BIG
BEST = dict(p4e.BEST)
SIGMA = p4e.SIGMA
ROWS = os.path.join(OUT, "chain81_rows.csv")
FINAL = os.path.join(OUT, "final81_chain.csv")
COLS = ["seed", "op", "a", "b", "k", "ok", "got", "want"]


def shard_path(i, nsh):
    return os.path.join(OUT, "chain81_rows_shard%d.csv" % i) if nsh > 1 else ROWS


def _load_seeds(path):
    if not os.path.exists(path):
        return set()
    try:
        old = pd.read_csv(path)
        if "seed" in old.columns and len(old):
            return set(int(s) for s in old.seed)
    except Exception:
        pass
    return set()


def merge_and_finish():
    import glob
    parts = [ROWS] + sorted(glob.glob(os.path.join(OUT, "chain81_rows_shard*.csv")))
    parts = [p for p in parts if os.path.exists(p) and os.path.getsize(p) > 0]
    raw = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    raw = raw.drop_duplicates(subset=["seed", "op", "a", "b", "k"])
    raw.to_csv(ROWS, index=False)
    fin = pd.read_csv(os.path.join(OUT, "final81_seeds.csv"))
    cdf = cal.chain_vs_k(raw.to_dict("records"), float(fin["add"].mean()))
    cdf.to_csv(FINAL, index=False)
    p4e.log("zincir BIRLESTIRILDI: %d adim / %d tohum; hepsi dogru = %s"
            % (len(raw), int(raw.seed.nunique()), bool((raw.ok == 1).all())))
    p4e.log(cdf.head(4).to_string(index=False))
    p4e.log(cdf.tail(4).to_string(index=False))
    return cdf


def main():
    shard, nsh = 0, 1
    args = [a for a in sys.argv[1:]]
    if args and args[0] == "merge":
        merge_and_finish()
        p4e.log("\nZincir olcumu tamamlandi.")
        return
    if len(args) >= 2:
        shard, nsh = int(args[0]), int(args[1])
    fin = pd.read_csv(os.path.join(OUT, "final81_seeds.csv"))
    seeds = [int(x) for x in fin.seed]
    done = _load_seeds(ROWS)
    for i in range(max(nsh, 1)):
        done |= _load_seeds(shard_path(i, nsh))
    todo = [s for s in seeds[shard::nsh] if s not in done]
    rp = shard_path(shard, nsh)
    p4e.log("\n=== ADIM 4 (zincir p^k) shard %d/%d: %d tohum olculecek (toplam %d kabul) ==="
            % (shard + 1, nsh, len(todo), len(seeds)))
    mats = od.load_sets()
    pairs = p4e.pairs_all()
    for s in todo:
        t0 = time.time()
        code = p4c.make_code(N_BIG, s, mats, SIGMA, 0.0, None, BEST["topk"])
        X = np.array([code(n, op) for n, op in pairs], np.float32)
        y = np.array([od.clip_result(n, op, N_BIG) for n, op in pairs])
        W, b = p4c.fit_fast(X, y, N_BIG + 1, BEST["lr"], BEST["epochs"], s)
        r = od.calc_measure(N_BIG, s, mats, p4c.Core(N_BIG, code, W, b))
        rows = [dict(seed=s, **c) for c in r["chain"]]
        wh = (not os.path.exists(rp)) or os.path.getsize(rp) == 0
        pd.DataFrame(rows, columns=COLS).to_csv(rp, mode="a", header=wh, index=False)
        p4e.log("  [shard %d] tohum %3d: %5d zincir adimi, hepsi dogru=%s (%.0fs)"
                % (shard + 1, s, len(rows), bool(all(c["ok"] == 1 for c in rows)),
                   time.time() - t0))
    p4e.log("shard %d bitti." % (shard + 1))



if __name__ == "__main__":
    main()
