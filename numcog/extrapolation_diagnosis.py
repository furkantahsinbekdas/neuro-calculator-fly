"""
numcog/extrapolation_diagnosis.py — FAZ 2b (keşifsel): aralık-dışı ters çevirme tanısı.

Kollar: (1) skor eğrisi f(n), (2) kenar dolgusu [-3,13], (3) paylaşımlı işaret-ters okuma,
(4) eğitim aralığı 1-4/1-6/1-8. Her kolda gerçek W vs degree-preserving karıştırılmış W.
Faz 2'nin magnitude_compare.py ve number_coding.py modüllerini yeniden kullanır.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

import number_coding as nc
import magnitude_compare as mc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p2b")

SIGMA = 1.5
TOPK = 40
N_SEEDS = 20

TRAIN16 = mc.TRAIN
TEST1 = mc.TEST1
TEST2 = mc.TEST2
TRAIN14 = [(1, 2), (2, 3), (3, 4), (1, 3)]
TRAIN18 = [(1, 2), (2, 3), (4, 5), (5, 6), (1, 3), (6, 7), (7, 8)]
ADJ = [(5, 6), (6, 7), (7, 8), (8, 9)]   # aralık ablasyonu için komşu test ızgarası


def gauss_codes_axis(n, sigma, seed, lo, hi):
    rng = np.random.RandomState(seed)
    positions = np.linspace(lo, hi, n)
    perm = rng.permutation(n)
    pos = positions[perm]
    A = np.zeros((9, n), dtype=np.float32)
    for k in range(1, 10):
        d = k - pos
        A[k - 1] = np.exp(-(d * d) / (2.0 * sigma * sigma))
    return A, pos


def make_encoders(seed, nv, lo=1.0, hi=9.0):
    half1 = nv // 2
    A1, _ = gauss_codes_axis(half1, SIGMA, seed, lo, hi)
    A2, _ = gauss_codes_axis(nv - half1, SIGMA, seed + 1, lo, hi)

    def sep(n1, n2):
        x = np.zeros(nv, dtype=np.float32)
        x[:half1] = A1[n1 - 1]
        x[half1:] = A2[n2 - 1]
        return x

    return sep


def kc_code(sep, W):
    score = nc.activate_weighted(sep, W)
    thr = np.sort(score)[-TOPK] if TOPK <= len(score) else score.min()
    return (score >= thr).astype(np.float32)


def run(train_pairs, test_pairs, model, W, seed, nv, lo=1.0, hi=9.0):
    """Fit delta kuralı, değerlendir. (w, b, code) döndürür (tanı için)."""
    enc = make_encoders(seed, nv, lo, hi)

    def code(p):
        if model == "coarse_direct":
            return enc(p[0], p[1])
        return kc_code(enc(p[0], p[1]), W)

    tr = mc.with_reversals(train_pairs)
    Xtr = np.array([code(p) for p in tr], np.float32)
    ytr = np.array([mc.label(p) for p in tr])
    w, b = mc.delta_fit(Xtr, ytr, seed=seed)
    res = {"train": mc.acc(ytr, mc.predict(Xtr, w, b))}
    for name, tp in test_pairs:
        te = mc.with_reversals(tp)
        Xe = np.array([code(p) for p in te], np.float32)
        ye = np.array([mc.label(p) for p in te])
        res[name] = mc.acc(ye, mc.predict(Xe, w, b))
    return res, w, b, code


def run_shared(train_pairs, test_pairs, seed, nv, lo=1.0, hi=9.0):
    """Paylaşımlı işaret-ters okuma (w_sol = -w_sağ) == fark kodlaması g(n1)-g(n2)."""
    half = nv // 2
    A, _ = gauss_codes_axis(half, SIGMA, seed, lo, hi)

    def diff(n1, n2):
        return A[n1 - 1] - A[n2 - 1]

    tr = mc.with_reversals(train_pairs)
    Xtr = np.array([diff(p[0], p[1]) for p in tr], np.float32)
    ytr = np.array([mc.label(p) for p in tr])
    w, b = mc.delta_fit(Xtr, ytr, seed=seed)
    res = {"train": mc.acc(ytr, mc.predict(Xtr, w, b))}
    for name, tp in test_pairs:
        te = mc.with_reversals(tp)
        Xe = np.array([diff(p[0], p[1]) for p in te], np.float32)
        ye = np.array([mc.label(p) for p in te])
        res[name] = mc.acc(ye, mc.predict(Xe, w, b))
    return res
def main():
    os.makedirs(OUT, exist_ok=True)
    M = nc.build_matrices(min_syn=1)
    W = M["W_vpn"]
    nk, nv = W.shape
    Wsh = nc.degree_preserving_shuffle(W, seed=12345)
    print("W: %d x %d; karistirilmis W hazir" % (nk, nv))

    ARMS = [("coarse_direct", None), ("coarse_kc", W), ("coarse_kc_shuffled", Wsh)]

    # --- Kol 1: skor eğrisi f(n) ---
    print("\n=== KOL 1: skor egrisi f(n) = skor(sol=n, sag=5), mean +- std, n=20 ===")
    diag = []
    for model, W_ in ARMS:
        curves = []
        for seed in range(N_SEEDS):
            res, w, b, code = run(TRAIN16, [], model, W_, seed, nv)
            f = np.array([float(code((n, 5)) @ w + b) for n in range(1, 10)])
            curves.append(f)
        c = np.array(curves)
        mean = c.mean(0)
        std = c.std(0)
        peak = int(np.argmax(mean)) + 1
        diag.append(dict(model=model, peak=peak))
        print("%-20s f(1..9)=%s  peak=%d" % (model, np.round(mean, 2).tolist(), peak))
        for n in range(9):
            diag[-1]["f%d" % (n + 1)] = float(mean[n])
            diag[-1]["s%d" % (n + 1)] = float(std[n])
    pd.DataFrame(diag).to_csv(os.path.join(OUT, "diagnosis_fn.csv"), index=False)

    # --- Kol 2: kenar dolgusu [-3,13] ---
    print("\n=== KOL 2: kenar dolgusu eksen [-3,13] (test1/test2) ===")
    pad = []
    for model, W_ in ARMS:
        acc = {"train": [], "test1": [], "test2": []}
        for seed in range(N_SEEDS):
            r, _, _, _ = run(TRAIN16, [("test1", TEST1), ("test2", TEST2)],
                             model, W_, seed, nv, -3.0, 13.0)
            for k in acc:
                acc[k].append(r[k])
        for k in acc:
            pad.append(dict(model=model, metric=k,
                            mean=float(np.mean(acc[k])), std=float(np.std(acc[k], ddof=1))))
            print("%-20s %-6s %6.3f +- %.3f" % (model, k, np.mean(acc[k]), np.std(acc[k], ddof=1)))
    pd.DataFrame(pad).to_csv(os.path.join(OUT, "padding.csv"), index=False)

    # --- Kol 3: paylaşımlı işaret-ters okuma (coarse_direct, KC yok) ---
    print("\n=== KOL 3: paylasimli isaret-ters okuma (coarse_direct) ===")
    sh = []
    acc = {"train": [], "test1": [], "test2": []}
    for seed in range(N_SEEDS):
        r = run_shared(TRAIN16, [("test1", TEST1), ("test2", TEST2)], seed, nv)
        for k in acc:
            acc[k].append(r[k])
    for k in acc:
        sh.append(dict(metric=k, mean=float(np.mean(acc[k])), std=float(np.std(acc[k], ddof=1))))
        print("%-6s %6.3f +- %.3f" % (k, np.mean(acc[k]), np.std(acc[k], ddof=1)))
    pd.DataFrame(sh).to_csv(os.path.join(OUT, "shared_readout.csv"), index=False)

    # --- Kol 4: eğitim aralığı ablasyonu ---
    print("\n=== KOL 4: egitim araligi 1-4/1-6/1-8 -> ekstrapolasyon dogrulugu ===")
    ranges = [("1-4", TRAIN14, 4), ("1-6", TRAIN16, 6), ("1-8", TRAIN18, 8)]
    rr = []
    for model, W_ in ARMS:
        for tr_name, tr, tr_max in ranges:
            beyond = [(a, b) for (a, b) in ADJ if min(a, b) > tr_max]
            for (a, b) in beyond:
                d = min(a, b) - tr_max
                accs = []
                for seed in range(N_SEEDS):
                    r, _, _, _ = run(tr, [("t", [(a, b)])], model, W_, seed, nv)
                    accs.append(r["t"])
                rr.append(dict(model=model, train=tr_name, pair="%d,%d" % (a, b),
                               dist=d, mean=float(np.mean(accs)), std=float(np.std(accs, ddof=1))))
    rdf = pd.DataFrame(rr)
    rdf.to_csv(os.path.join(OUT, "range_ablation.csv"), index=False)
    for model, _ in ARMS:
        print("--- %s ---" % model)
        sub = rdf[rdf.model == model].sort_values(["train", "dist"])
        for row in sub.itertuples():
            print("  train %s  %s  dist=%d  acc=%.3f +- %.3f" % (row.train, row.pair, row.dist, row.mean, row.std))

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

