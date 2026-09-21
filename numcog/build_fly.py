"""
numcog/build_fly.py — hesap makinesi sineğini eğitir ve ağırlıkları küçük bir .npz'ye yazar.

Donmuş hücre (Faz 4E Adım 4; 4D'nin en iyi hücresi): N=81, sigma=1.5, top-k=80,
epochs=25000, lr=0.05.  Tohum, Faz 4E kalibrasyon kapısından (164/164 doğru tablo) geçen
tohumlar arasından **CSV'den okunur** (`results_p4e/final81_seeds.csv`, sutun `table == 1.0`).

NOT (dürüstlük): kapanış paketi metni "sigma=2.0, dolgu" diyor; o ayar **Faz 4F** ızgarasıdır ve
4F'nin `frozen.json` değeri **null**'dur (hiçbir hücre %95 ölçütünü geçmedi). Çalışan ve
kalibrasyondan geçen hesap makinesi **4E**'nin hücresidir → bu betik **4E hücresini** kullanır.

Kullanım:  python -X utf8 numcog/build_fly.py [tohum]
Çıktı:     numcog/fly_weights/fly_N81_seed<tohum>.npz  (<5 MB, depoda tutulur)
"""
from __future__ import annotations
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

OUTD = os.path.join(HERE, "fly_weights")
ACCEPT_CSV = os.path.join(HERE, "results_p4e", "final81_seeds.csv")
N = 81
SIGMA = 1.5
TOPK = 80
EPOCHS = 25000
LR = 0.05


def weights_path(seed):
    return os.path.join(OUTD, "fly_N81_seed%d.npz" % seed)


def accepted_seeds():
    """Faz 4E kalibrasyon kapısından geçen tohumlar (tablo 1.0000)."""
    df = pd.read_csv(ACCEPT_CSV)
    ok = df[np.isclose(df["table"].astype(float), 1.0)]
    return [int(s) for s in ok.seed]


def build(seed, verbose=True):
    import operator_diagnosis as od
    import phase4c as p4c
    from operator_diagnosis import clip_result

    t0 = time.time()
    mats = od.load_sets()
    code = p4c.make_code(N, seed, mats, SIGMA, 0.0, None, TOPK)
    pairs = [(n, op) for n in range(N + 1) for op in ("+", "-")]
    X = np.array([code(n, op) for n, op in pairs], np.float32)
    y = np.array([clip_result(n, op, N) for n, op in pairs], np.int64)
    W, b = p4c.fit_fast(X, y, N + 1, LR, EPOCHS, seed)
    S = X @ W.T + b
    pred = np.argmax(S, 1)
    table_acc = float(np.mean(pred == y))
    os.makedirs(OUTD, exist_ok=True)
    p = weights_path(seed)
    Xc = sp.csr_matrix(X)
    np.savez_compressed(
        p, W=W.astype(np.float32), b=b.astype(np.float32),
        X_data=Xc.data.astype(np.float32), X_indices=Xc.indices.astype(np.int32),
        X_indptr=Xc.indptr.astype(np.int64), X_shape=np.array(Xc.shape, np.int64),
        pair_n=np.array([p[0] for p in pairs], np.int64),
        pair_op=np.array([0 if p[1] == "+" else 1 for p in pairs], np.int8),
        meta=np.array([json.dumps(dict(seed=seed, N=N, sigma=SIGMA, topk=TOPK,
                                       epochs=EPOCHS, lr=LR, table_acc=table_acc,
                                       source="Faz 4E Adim 4 donmus hucre",
                                       note="kapanis paketi metni sigma=2.0/dolgu diyor; "
                                            "o ayar 4F'dir ve 4F frozen=null -> 4E kullanildi"))],
                      dtype=object))
    if verbose:
        print("tohum %d: tablo dogrulugu=%.4f | %.0fs | %s (%.2f MB)"
              % (seed, table_acc, time.time() - t0, p, os.path.getsize(p) / 1e6))
    return dict(path=p, seed=seed, table_acc=table_acc)


def main():
    if len(sys.argv) > 1:
        seeds = [int(sys.argv[1])]
    else:
        seeds = accepted_seeds()[:5]
    print("kalibrasyondan gecen ilk tohumlar: %s" % seeds)
    for s in seeds:
        r = build(s)
        if r["table_acc"] >= 1.0:
            print("KALIBRASYON GECTI (tablo=%.4f) -> %s" % (r["table_acc"], r["path"]))
            return 0
        print("  tohum %d tablo=%.4f -> gecmedi, sonraki denenecek" % (s, r["table_acc"]))
    print("HICBIR TOHUM kalibrasyonu gecmedi (DUR)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
