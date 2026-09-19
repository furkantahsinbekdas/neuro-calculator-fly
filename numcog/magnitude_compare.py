"""
numcog/magnitude_compare.py — FAZ 2: büyüklük karşılaştırması ("hangisi büyük").

Delta kuralı (LMS) ile ikili sınıflandırma: sol büyük = +1, sağ büyük = -1.
Faz 1'de ölçülen hiperparametreler: coarse_kc sigma=1.5, top_k=40; ayrı popülasyonlar.
Kodlayıcı/aktivasyon number_coding.py'den import edilir (yeniden yazılmaz).
"""
from __future__ import annotations
import os
import json
import hashlib

import numpy as np
import pandas as pd

import number_coding as nc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p2")

SIGMA = 1.5
TOPK = 40
LR = 0.01
EPOCHS = 500
N_SEEDS = 20

TRAIN = [(1, 2), (2, 3), (4, 5), (5, 6), (1, 3)]
TEST1 = [(3, 5), (3, 6), (2, 5)]
TEST2 = [(7, 8), (8, 9), (7, 9)]


def with_reversals(pairs):
    return pairs + [(b, a) for a, b in pairs]


def label(pair):
    a, b = pair
    return 1.0 if a > b else -1.0


def assert_no_leak():
    train = set(with_reversals(TRAIN))
    for p in with_reversals(TEST1) + with_reversals(TEST2):
        assert p not in train, "SIZINTI: %r egitimde var" % (p,)


def make_encoders(seed, nv):
    """Ayrı popülasyonlar: sol sayı H1'de, sağ sayı H2'de. sep_vec(n1,n2) -> (nv,) vektör."""
    half1 = nv // 2
    A1, _ = nc.gauss_codes(half1, SIGMA, seed)
    A2, _ = nc.gauss_codes(nv - half1, SIGMA, seed + 1)

    def sep_vec(n1, n2):
        x = np.zeros(nv, dtype=np.float32)
        x[:half1] = A1[n1 - 1]
        x[half1:] = A2[n2 - 1]
        return x

    return sep_vec


def kc_code(sep_vec, W, topk=TOPK):
    score = nc.activate_weighted(sep_vec, W)
    thr = np.sort(score)[-topk] if topk <= len(score) else score.min()
    return (score >= thr).astype(np.float32)


def hash_pair_code(n1, n2, dim, active, seed):
    key = ("%d,%d|%d" % (n1, n2, seed)).encode()
    rng = np.random.RandomState(int.from_bytes(hashlib.sha256(key).digest()[:4], "little"))
    v = np.zeros(dim, dtype=np.float32)
    v[rng.choice(dim, size=active, replace=False)] = 1.0
    return v


def delta_fit(X, y, lr=LR, epochs=EPOCHS, seed=0):
    X = X.astype(np.float64)
    y = np.asarray(y, dtype=np.float64)
    N, D = X.shape
    rng = np.random.RandomState(seed + 1000)
    w = rng.normal(0.0, 0.01, D).astype(np.float64)
    b = 0.0
    for _ in range(epochs):
        err = y - (X @ w + b)
        w += lr * (X.T @ err) / N
        b += lr * err.mean()
    return w, b


def predict(X, w, b):
    return np.where(X @ w + b >= 0, 1.0, -1.0)


def acc(y_true, y_pred):
    return float(np.mean(y_true == y_pred))
MODELS = ["coarse_direct", "coarse_kc", "coarse_kc_shuffled", "hash"]


def run_seed(seed, W, Wsh, nv, dim_kc):
    enc = make_encoders(seed, nv)

    def code(p, m):
        if m == "coarse_direct":
            return enc(p[0], p[1])
        if m == "coarse_kc":
            return kc_code(enc(p[0], p[1]), W)
        if m == "coarse_kc_shuffled":
            return kc_code(enc(p[0], p[1]), Wsh)
        if m == "hash":
            return hash_pair_code(p[0], p[1], dim_kc, TOPK, seed)
        raise ValueError(m)

    tr = with_reversals(TRAIN)
    te1 = with_reversals(TEST1)
    te2 = with_reversals(TEST2)
    ytr = np.array([label(p) for p in tr])
    yte1 = np.array([label(p) for p in te1])
    yte2 = np.array([label(p) for p in te2])

    Xtr = {m: np.array([code(p, m) for p in tr], np.float32) for m in MODELS}
    Xe1 = {m: np.array([code(p, m) for p in te1], np.float32) for m in MODELS}
    Xe2 = {m: np.array([code(p, m) for p in te2], np.float32) for m in MODELS}

    row = {}
    for m in MODELS:
        w, b = delta_fit(Xtr[m], ytr, seed=seed)
        row[m + "_train"] = acc(ytr, predict(Xtr[m], w, b))
        row[m + "_test1"] = acc(yte1, predict(Xe1[m], w, b))
        row[m + "_test2"] = acc(yte2, predict(Xe2[m], w, b))
        for pairs in (TEST1, TEST2):
            for (a, bb) in pairs:
                pa = code((a, bb), m)
                pb = code((bb, a), m)
                ya = label((a, bb))
                yb = label((bb, a))
                hit = (int(predict(pa[None, :], w, b)[0] == ya) +
                       int(predict(pb[None, :], w, b)[0] == yb))
                row["%s_pair%d_%d" % (m, a, bb)] = hit / 2.0
        # Kontrol 1: rastgele etiket
        rng = np.random.RandomState(seed + 2000)
        ys = ytr.copy()
        rng.shuffle(ys)
        wc, bc = delta_fit(Xtr[m], ys, seed=seed)
        row[m + "_randlabel_test1"] = acc(yte1, predict(Xe1[m], wc, bc))
        row[m + "_randlabel_test2"] = acc(yte2, predict(Xe2[m], wc, bc))
    return row


def main():
    os.makedirs(OUT, exist_ok=True)
    assert_no_leak()
    print("sizinti kontrolu: OK (test ciftleri egitimde yok)")

    M = nc.build_matrices(min_syn=1)
    W = M["W_vpn"]
    nk, nv = W.shape
    Wsh = nc.degree_preserving_shuffle(W, seed=12345)
    print("W: %d KC x %d VPN; karistirilmis W ayni boyut" % (nk, nv))

    df = pd.DataFrame([run_seed(s, W, Wsh, nv, nk) for s in range(N_SEEDS)])
    df.to_csv(os.path.join(OUT, "seeds_raw.csv"), index=False)

    print("\n=== OZET (mean +- std, %%95 GA, n=%d) ===" % N_SEEDS)
    summary = []
    for m in MODELS:
        for key in ("train", "test1", "test2"):
            mm = df[m + "_" + key].mean()
            ss = df[m + "_" + key].std(ddof=1)
            ci = 1.96 * ss / np.sqrt(N_SEEDS)
            summary.append(dict(model=m, metric=key, mean=mm, std=ss, ci95=ci))
            print("%-20s %-6s %6.3f +- %.3f   [%.3f, %.3f]" % (m, key, mm, ss, mm - ci, mm + ci))
    pd.DataFrame(summary).to_csv(os.path.join(OUT, "summary.csv"), index=False)

    print("\n=== TEST CIFTI BAZINDA DOGRULUK (mean over 20 tohum) ===")
    pp = []
    for m in MODELS:
        for (a, b) in TEST1 + TEST2:
            col = "%s_pair%d_%d" % (m, a, b)
            mm = df[col].mean()
            d = abs(a - b)
            pp.append(dict(model=m, a=a, b=b, d=d, acc=mm,
                           in_range=(a, b) in TEST1))
    pdf = pd.DataFrame(pp)
    pdf.to_csv(os.path.join(OUT, "per_pair.csv"), index=False)
    for m in MODELS:
        line = " ".join("(%d,%d)=%.3f" % (r.a, r.b, r.acc) for r in pdf[pdf.model == m].itertuples())
        print("%-20s %s" % (m, line))

    print("\nhep-sol taban cizgisi = 0.500 (test1/test2 dengeli)")

    print("\n=== KONTROL 1: RASTGELE ETIKET (mean) ===")
    for m in MODELS:
        print("%-20s test1=%.3f  test2=%.3f"
              % (m, df[m + "_randlabel_test1"].mean(), df[m + "_randlabel_test2"].mean()))

    print("\n=== H2.3 MESAFE ETKISI: acc vs |n-m| (Pearson r, 6 test cifti) ===")
    for m in ("coarse_direct", "coarse_kc"):
        sub = pdf[pdf.model == m]
        r = float(np.corrcoef(sub.d, sub.acc)[0, 1])
        print("%-20s r=%.3f   (d=%s, acc=%s)"
              % (m, r, list(sub.d), [round(x, 3) for x in sub.acc]))

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

