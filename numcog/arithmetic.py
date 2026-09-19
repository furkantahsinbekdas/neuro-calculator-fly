"""
numcog/arithmetic.py — FAZ 3: toplama/çıkarma (n±1), operatör = koku, sayı = görsel.

Sayı: Faz 1-2 kodlayıcı (sigma=1.5 Gauss, top-k=40, gerçek VPN->KC). Operatör: iki ayrık
rastgele ALPN alt kümesi (op+/op-), tohum başına. KC katmanı VPN+ALPN girdisini AYNI hücrede
toplar (gerçek matrisler, top-k). Çıktı: 0..10 (11 sınıf), çok-sınıflı delta kuralı.

number_coding.py ve magnitude_compare.py'yi yeniden kullanır.
"""
from __future__ import annotations
import os
import hashlib

import numpy as np
import pandas as pd

import number_coding as nc
import magnitude_compare as mc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p3")

SIGMA = 1.5
TOPK = 40
N_SEEDS = 20
LR = 0.01
EPOCHS = 1000
K_GLOOMS = 32          # operatör başına aktif ALPN birimi (~%10)
N_CLASSES = 11         # sonuç 0..10

TRAIN = [(1, '+'), (1, '-'), (2, '+'), (2, '-'), (3, '+'), (3, '-'),
         (4, '+'), (5, '-'), (6, '+')]
TEST_COMBO = [(4, '-'), (5, '+'), (6, '-')]
TEST_NEWN = [(7, '+'), (7, '-'), (8, '+'), (8, '-'), (9, '+'), (9, '-')]


def result(pair):
    n, op = pair
    return n + 1 if op == '+' else n - 1


def assert_no_leak():
    tr = set(TRAIN)
    for p in TEST_COMBO + TEST_NEWN:
        assert p not in tr, "SIZINTI: %r egitimde" % (p,)
    tr_n = set(n for n, _ in TRAIN)
    for n, _ in TEST_NEWN:
        assert n not in tr_n, "SIZINTI: n=%d egitimde" % n


def load_arithmetic():
    M = nc.build_matrices(min_syn=1)
    W_vpn = M["W_vpn"]                      # 427 x 265
    kc_vpn = M["kc_vpn"]
    W_alpn = M["W_alpn"]                    # 4887 x 319
    kc_alpn = M["kc_alpn"]
    n_alpn = W_alpn.shape[1]
    ka = {r: i for i, r in enumerate(kc_alpn)}
    rows = [ka.get(r) for r in kc_vpn]
    W_alpn_r = np.zeros((len(kc_vpn), n_alpn), dtype=np.float32)
    for j, ri in enumerate(rows):
        if ri is not None:
            W_alpn_r[j] = W_alpn[ri]
    shared_idx = np.array([j for j, ri in enumerate(rows) if ri is not None])
    # Arm 6: ALPN girdisini aynı sayıda (n_shared) rastgele KC'ye taşı
    rng = np.random.RandomState(999)
    W_alpn_r6 = np.zeros_like(W_alpn_r)
    rand_rows = rng.choice(len(kc_vpn), size=len(shared_idx), replace=False)
    for dst, src in zip(rand_rows, shared_idx):
        W_alpn_r6[dst] = W_alpn_r[src]
    return dict(W_vpn=W_vpn, W_alpn_r=W_alpn_r, W_alpn_r6=W_alpn_r6,
                nv=W_vpn.shape[1], n_alpn=n_alpn, shared_idx=shared_idx,
                n_shared=len(shared_idx))


def op_codes(seed, n_alpn, k=K_GLOOMS):
    rng = np.random.RandomState(seed + 500)
    idx = rng.permutation(n_alpn)
    p = np.zeros(n_alpn, dtype=np.float32)
    p[idx[:k]] = 1.0
    m = np.zeros(n_alpn, dtype=np.float32)
    m[idx[k:2 * k]] = 1.0
    return {'+': p, '-': m}


def thermo_code(n, nv):
    v = np.zeros(nv, dtype=np.float32)
    v[:int(n * nv / 9)] = 1.0
    return v


def hash_code(n, op, dim, active, seed):
    key = ("%d%s|%d" % (n, op, seed)).encode()
    rng = np.random.RandomState(int.from_bytes(hashlib.sha256(key).digest()[:4], "little"))
    v = np.zeros(dim, dtype=np.float32)
    v[rng.choice(dim, size=active, replace=False)] = 1.0
    return v
def delta_fit_multi(X, Y, lr=LR, epochs=EPOCHS, seed=0, n_classes=N_CLASSES):
    X = X.astype(np.float64)
    Y = np.asarray(Y, dtype=np.int64)
    N, D = X.shape
    rng = np.random.RandomState(seed + 1000)
    W = rng.normal(0.0, 0.01, (n_classes, D)).astype(np.float64)
    b = np.zeros(n_classes, dtype=np.float64)
    for _ in range(epochs):
        S = X @ W.T + b
        T = -np.ones((N, n_classes))
        T[np.arange(N), Y] = 1.0
        E = T - S
        W += lr * (E.T @ X) / N
        b += lr * E.mean(axis=0)
    return W, b


def predict_multi(X, W, b):
    return (X @ W.T + b).argmax(axis=1)


ARMS = ["hash", "coarse_direct", "coarse_kc", "coarse_kc_shuffled",
        "coarse_kc_shared_removed", "coarse_kc_overlapctl", "thermo"]


def make_code(arm, seed, mats, W_vpn_sh):
    W_vpn = mats["W_vpn"]
    W_alpn_r = mats["W_alpn_r"]
    W_alpn_r6 = mats["W_alpn_r6"]
    nv = mats["nv"]
    n_alpn = mats["n_alpn"]
    shared = mats["shared_idx"]
    A, _ = nc.gauss_codes(nv, SIGMA, seed)
    ops = op_codes(seed, n_alpn)

    def num_vec(n):
        return thermo_code(n, nv) if arm == "thermo" else A[n - 1]

    def code(n, op):
        if arm == "hash":
            return hash_code(n, op, 427, TOPK, seed)
        if arm == "coarse_direct":
            return np.concatenate([num_vec(n), ops[op]])
        Wv = W_vpn_sh if arm == "coarse_kc_shuffled" else W_vpn
        Wa = W_alpn_r6 if arm == "coarse_kc_overlapctl" else W_alpn_r
        score = Wv @ num_vec(n) + Wa @ ops[op]
        if arm == "coarse_kc_shared_removed":
            score = score.copy()
            score[shared] = -1e9
        thr = np.sort(score)[-TOPK] if TOPK <= len(score) else score.min()
        return (score >= thr).astype(np.float32)

    return code


def run_seed(seed, arm, mats, W_vpn_sh):
    code = make_code(arm, seed, mats, W_vpn_sh)

    def codeset(pairs):
        return np.array([code(n, op) for n, op in pairs], np.float32)

    Xtr = codeset(TRAIN)
    ytr = np.array([result(p) for p in TRAIN])
    W, b = delta_fit_multi(Xtr, ytr, seed=seed)

    def evaluate(pairs):
        X = codeset(pairs)
        y = np.array([result(p) for p in pairs])
        pr = predict_multi(X, W, b)
        exact = float(np.mean(pr == y))
        mag = float(np.mean([1.0 if p in (n + 1, n - 1) else 0.0
                             for (n, _), p in zip(pairs, pr)]))
        return exact, mag

    tr_exact, _ = evaluate(TRAIN)
    cb_exact, cb_mag = evaluate(TEST_COMBO)
    nn_exact, nn_mag = evaluate(TEST_NEWN)

    per = []
    for (n, op) in TEST_COMBO + TEST_NEWN:
        pr = int(predict_multi(code(n, op)[None, :], W, b)[0])
        per.append(dict(arm=arm, seed=seed, n=n, op=op, true=result((n, op)), pred=pr))

    shared_frac = float("nan")
    if arm not in ("hash", "coarse_direct"):
        shared = mats["shared_idx"]
        fracs = []
        for (n, op) in TRAIN + TEST_COMBO + TEST_NEWN:
            c = code(n, op)
            active = np.where(c > 0)[0]
            fracs.append(float(np.intersect1d(active, shared).size / len(active))
                         if len(active) else 0.0)
        shared_frac = float(np.mean(fracs))

    return dict(arm=arm, seed=seed, train=tr_exact, combo=cb_exact, combo_mag=cb_mag,
                newn=nn_exact, newn_mag=nn_mag, shared_frac=shared_frac), per
def random_label_control(arm, mats, W_vpn_sh):
    vals = {"combo": [], "newn": []}
    for seed in range(N_SEEDS):
        code = make_code(arm, seed, mats, W_vpn_sh)
        Xtr = np.array([code(n, op) for n, op in TRAIN], np.float32)
        ytr = np.array([result(p) for p in TRAIN])
        rng = np.random.RandomState(seed + 3000)
        ys = ytr.copy()
        rng.shuffle(ys)
        W, b = delta_fit_multi(Xtr, ys, seed=seed)
        for key, pairs in [("combo", TEST_COMBO), ("newn", TEST_NEWN)]:
            X = np.array([code(n, op) for n, op in pairs], np.float32)
            y = np.array([result(p) for p in pairs])
            pr = predict_multi(X, W, b)
            vals[key].append(float(np.mean(pr == y)))
    return {k: (float(np.mean(v)), float(np.std(v, ddof=1))) for k, v in vals.items()}


def only_n_control(mats):
    vals = {"combo": [], "newn": []}
    for seed in range(N_SEEDS):
        A, _ = nc.gauss_codes(mats["nv"], SIGMA, seed)
        Xtr = np.array([A[n - 1] for n, _ in TRAIN], np.float32)
        ytr = np.array([result(p) for p in TRAIN])
        W, b = delta_fit_multi(Xtr, ytr, seed=seed)
        for key, pairs in [("combo", TEST_COMBO), ("newn", TEST_NEWN)]:
            X = np.array([A[n - 1] for n, _ in pairs], np.float32)
            y = np.array([result(p) for p in pairs])
            pr = predict_multi(X, W, b)
            vals[key].append(float(np.mean(pr == y)))
    return {k: (float(np.mean(v)), float(np.std(v, ddof=1))) for k, v in vals.items()}


def main():
    os.makedirs(OUT, exist_ok=True)
    assert_no_leak()
    print("sizinti kontrolu: OK")
    mats = load_arithmetic()
    W_vpn_sh = nc.degree_preserving_shuffle(mats["W_vpn"], seed=12345)
    print("W_vpn %d x %d | W_alpn_r %d x %d | ortak KC = %d" % (
        mats["W_vpn"].shape[0], mats["W_vpn"].shape[1],
        mats["W_alpn_r"].shape[0], mats["W_alpn_r"].shape[1], mats["n_shared"]))

    rows, per_rows = [], []
    for arm in ARMS:
        for seed in range(N_SEEDS):
            r, per = run_seed(seed, arm, mats, W_vpn_sh)
            rows.append(r)
            per_rows.extend(per)
    df = pd.DataFrame(rows)
    pdf = pd.DataFrame(per_rows)
    df.to_csv(os.path.join(OUT, "arms_raw.csv"), index=False)
    pdf.to_csv(os.path.join(OUT, "per_pair.csv"), index=False)

    print("\n=== OZET (mean +- std, %%95 GA, n=%d) ===" % N_SEEDS)
    summary = []
    for arm in ARMS:
        sub = df[df.arm == arm]
        for key in ("train", "combo", "combo_mag", "newn", "newn_mag"):
            mm = float(sub[key].mean())
            ss = float(sub[key].std(ddof=1))
            ci = 1.96 * ss / np.sqrt(N_SEEDS)
            summary.append(dict(arm=arm, metric=key, mean=mm, std=ss, ci95=ci))
            print("%-24s %-10s %6.3f +- %.3f [%.3f, %.3f]" % (arm, key, mm, ss, mm - ci, mm + ci))
    pd.DataFrame(summary).to_csv(os.path.join(OUT, "summary.csv"), index=False)

    print("\n=== AKTIF ORTAK KC PAYI (topk=40 icinde, KC kollari) ===")
    for arm in ARMS:
        sub = df[df.arm == arm]
        if sub.shared_frac.isna().all():
            continue
        print("%-24s %.3f +- %.3f" % (arm, float(sub.shared_frac.mean()),
                                      float(sub.shared_frac.std(ddof=1))))

    print("\n=== OP BAZINDA (combo+newn, mean dogruluk) ===")
    for op in ("+", "-"):
        sub = pdf[pdf.op == op]
        acc = float((sub.pred == sub.true).mean())
        print("op%s  dogruluk=%.3f  (n=%d)" % (op, acc, len(sub)))

    print("\n=== N BAZINDA (combo+newn, mean dogruluk) ===")
    for n in range(1, 10):
        sub = pdf[pdf.n == n]
        if len(sub) == 0:
            continue
        acc = float((sub.pred == sub.true).mean())
        print("n=%d  dogruluk=%.3f" % (n, acc))

    print("\n=== KONTROLLER ===")
    print("sans (11 sinif) = %.3f" % (1.0 / N_CLASSES))
    for arm in ("hash", "coarse_direct", "coarse_kc"):
        rc = random_label_control(arm, mats, W_vpn_sh)
        print("%-24s rastgele-etiket combo=%.3f+-%.3f newn=%.3f+-%.3f"
              % (arm, rc["combo"][0], rc["combo"][1], rc["newn"][0], rc["newn"][1]))
    on = only_n_control(mats)
    print("sadece-n (op yok say)        combo=%.3f+-%.3f newn=%.3f+-%.3f"
          % (on["combo"][0], on["combo"][1], on["newn"][0], on["newn"][1]))

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()


