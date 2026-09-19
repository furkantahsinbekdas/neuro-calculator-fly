"""
numcog/rule_learning.py — FAZ 3c: kural öğrenimi (sürekli/topolojik çıktı).

Çıktı, girdi ile aynı topolojik kaba kodla temsil edilir: hedef sayı t ∈ 0..10, eksen [0,10]
üzerinde Gauss (σ=1.5) ya da Termometre vektörü. MSE kaybı, kosinüs ile decode. Amaç: modelin
"çıktıyı girdiye kıyasla sağa/sola kaydırmayı" (bir kural olarak) öğrenip öğrenmediği.

arithmetic.py ve number_coding.py'yi yeniden kullanır.
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

import number_coding as nc
import arithmetic as ar

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p3c")

SIGMA = 1.5
TOPK = 40
N_SEEDS = 20
LR = 0.01
EPOCHS = 500
NV = 265
N_TARGETS = 11        # 0..10

TRAIN = [(1, '+'), (2, '+'), (3, '+'), (4, '+'), (5, '+'), (6, '+'), (7, '+'),
         (1, '-'), (2, '-'), (3, '-')]
TEST_COMBO_G1 = [(4, '-')]
TEST_COMBO_G2 = [(5, '-'), (6, '-'), (7, '-')]
TEST_NEWN = [(8, '+'), (8, '-'), (9, '+'), (9, '-')]


def result(pair):
    n, op = pair
    return n + 1 if op == '+' else n - 1


def assert_split():
    tr = set(TRAIN)
    for p in TEST_COMBO_G1 + TEST_COMBO_G2 + TEST_NEWN:
        assert p not in tr, "sizinti: %r egitimde" % (p,)
    tr_n = set(n for n, _ in TRAIN)
    for n, _ in TEST_NEWN:
        assert n not in tr_n, "sizinti: n=%d egitimde" % n
    # (1) parite korelasyonu yok: her paritede iki op de var
    for parity in ("odd", "even"):
        ns = [n for n, _ in TRAIN if (n % 2 == 1) == (parity == "odd")]
        ops = {op for n, op in TRAIN if n in ns}
        assert ops == {'+', '-'}, "parite korelasyonu var: %s" % parity
    # (3) Grup 2 izolasyonu: (n-1,op) ve (n+1,op) egitimde degil
    for (n, op) in TEST_COMBO_G2:
        assert (n - 1, op) not in tr, "G2 izolasyon ihlali: %r" % ((n - 1, op),)
        assert (n + 1, op) not in tr, "G2 izolasyon ihlali: %r" % ((n + 1, op),)
    # (4) egitim hedefleri bitisik
    targets = sorted({result(p) for p in TRAIN})
    assert targets == list(range(targets[0], targets[-1] + 1)), "hedefler bitisik degil: %s" % targets
    print("asserts OK: G1=%d G2=%d NEWN=%d egitim=%d (hedefler %d..%d)"
          % (len(TEST_COMBO_G1), len(TEST_COMBO_G2), len(TEST_NEWN),
             len(TRAIN), targets[0], targets[-1]))


def gauss_codes_11(seed, nv=NV):
    rng = np.random.RandomState(seed)
    positions = np.linspace(0.0, 10.0, nv)
    perm = rng.permutation(nv)
    pos = positions[perm]
    A = np.zeros((N_TARGETS, nv), dtype=np.float32)
    for t in range(N_TARGETS):
        d = t - pos
        A[t] = np.exp(-(d * d) / (2.0 * SIGMA * SIGMA))
    return A


def thermo_out(t, nv=NV):
    v = np.zeros(nv, dtype=np.float32)
    v[:int(t * nv / 10)] = 1.0
    return v
ARMS = ["coarse_direct", "coarse_kc_gercek", "coarse_kc_shuffled",
        "coarse_kc_ablasyon", "coarse_kc_ortusme_kontrol", "coarse_kc_gercek_termometre"]


def make_code(arm, seed, mats, W_vpn_sh):
    W_vpn = mats["W_vpn"]
    W_alpn_r = mats["W_alpn_r"]
    W_alpn_r6 = mats["W_alpn_r6"]
    shared = mats["shared_idx"]
    n_alpn = mats["n_alpn"]
    A = gauss_codes_11(seed)
    ops = ar.op_codes(seed, n_alpn)

    def code(n, op):
        num = A[n]
        if arm == "coarse_direct":
            return np.concatenate([num, ops[op]])
        Wv = W_vpn_sh if arm == "coarse_kc_shuffled" else W_vpn
        Wa = W_alpn_r6 if arm == "coarse_kc_ortusme_kontrol" else W_alpn_r
        score = Wv @ num + Wa @ ops[op]
        if arm == "coarse_kc_ablasyon":
            score = score.copy()
            score[shared] = -1e9
        thr = np.sort(score)[-TOPK] if TOPK <= len(score) else score.min()
        return (score >= thr).astype(np.float32)

    return code


def delta_fit_reg(X, T, lr=LR, epochs=EPOCHS, seed=0):
    X = X.astype(np.float64)
    T = T.astype(np.float64)
    N, D = X.shape
    out_dim = T.shape[1]
    rng = np.random.RandomState(seed + 1000)
    W = rng.normal(0.0, 0.01, (out_dim, D)).astype(np.float64)
    b = np.zeros(out_dim, dtype=np.float64)
    for _ in range(epochs):
        Y = X @ W.T + b
        E = T - Y
        W += lr * (E.T @ X) / N
        b += lr * E.mean(axis=0)
    return W, b


def _cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def decode(y, refs):
    return int(np.argmax([_cosine(y, r) for r in refs]))


def run_seed(seed, arm, mats, W_vpn_sh):
    A = gauss_codes_11(seed)
    code = make_code(arm, seed, mats, W_vpn_sh)
    thermo = (arm == "coarse_kc_gercek_termometre")
    if thermo:
        refs = np.array([thermo_out(t) for t in range(N_TARGETS)], np.float32)
    else:
        refs = A

    def target_vec(t):
        return thermo_out(t) if thermo else A[t]

    Xtr = np.array([code(n, op) for n, op in TRAIN], np.float32)
    Ttr = np.array([target_vec(result((n, op))) for n, op in TRAIN], np.float32)
    W, b = delta_fit_reg(Xtr, Ttr, seed=seed)

    def evaluate(pairs):
        ex, tol = [], []
        for (n, op) in pairs:
            y = code(n, op) @ W.T + b
            d = decode(y, refs)
            t = result((n, op))
            ex.append(d == t)
            tol.append(abs(d - t) <= 1)
        return float(np.mean(ex)), float(np.mean(tol))

    out = {"arm": arm, "seed": seed}
    out["train_exact"], out["train_tol"] = evaluate(TRAIN)
    out["g1_exact"], out["g1_tol"] = evaluate(TEST_COMBO_G1)
    out["g2_exact"], out["g2_tol"] = evaluate(TEST_COMBO_G2)
    out["newn_exact"], out["newn_tol"] = evaluate(TEST_NEWN)

    flips = 0
    for n in range(1, 10):
        dp = decode(code(n, '+') @ W.T + b, refs) - n
        dm = decode(code(n, '-') @ W.T + b, refs) - n
        if dp * dm < 0:
            flips += 1
    out["op_flip"] = flips / 9.0

    if not thermo:
        T_all = np.array([A[result(p)] for p in TRAIN], np.float32)
        out["dead_units"] = int((T_all.max(axis=0) < 0.01).sum())
    else:
        out["dead_units"] = 0
    return out
def baseline_metrics(pairs):
    def eval_base(predict_fn):
        ex, tol = [], []
        for (n, op) in pairs:
            p = predict_fn(n, op)
            t = result((n, op))
            ex.append(p == t)
            tol.append(abs(p - t) <= 1)
        return float(np.mean(ex)), float(np.mean(tol))

    a1 = eval_base(lambda n, op: n + 1)
    ident = eval_base(lambda n, op: n)
    return dict(always_n1_exact=a1[0], always_n1_tol=a1[1],
                identity_exact=ident[0], identity_tol=ident[1],
                random_exact=1.0 / N_TARGETS, random_tol=3.0 / N_TARGETS)


def main():
    os.makedirs(OUT, exist_ok=True)
    assert_split()
    mats = ar.load_arithmetic()
    W_vpn_sh = nc.degree_preserving_shuffle(mats["W_vpn"], seed=12345)

    rows = []
    for arm in ARMS:
        for seed in range(N_SEEDS):
            rows.append(run_seed(seed, arm, mats, W_vpn_sh))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "arms_raw.csv"), index=False)

    print("\n=== OZET (mean +- std, %%95 GA, n=%d) ===" % N_SEEDS)
    summary = []
    for arm in ARMS:
        sub = df[df.arm == arm]
        for key in ("train_exact", "g1_exact", "g2_exact", "g2_tol",
                    "newn_exact", "newn_tol", "op_flip"):
            mm = float(sub[key].mean())
            ss = float(sub[key].std(ddof=1))
            ci = 1.96 * ss / np.sqrt(N_SEEDS)
            summary.append(dict(arm=arm, metric=key, mean=mm, std=ss, ci95=ci))
            print("%-26s %-12s %6.3f +- %.3f [%.3f, %.3f]"
                  % (arm, key, mm, ss, mm - ci, mm + ci))
    pd.DataFrame(summary).to_csv(os.path.join(OUT, "summary.csv"), index=False)

    print("\n=== TABAN CIZGILERI ===")
    for name, pairs in [("G1", TEST_COMBO_G1), ("G2", TEST_COMBO_G2), ("NEWN", TEST_NEWN)]:
        b = baseline_metrics(pairs)
        print("%-5s hep-n+1 exact=%.3f tol=%.3f | kimlik exact=%.3f tol=%.3f | rastgele exact=%.3f tol=%.3f"
              % (name, b["always_n1_exact"], b["always_n1_tol"],
                 b["identity_exact"], b["identity_tol"],
                 b["random_exact"], b["random_tol"]))

    print("\n=== OLU BIRIM (Gauss cikti; egitimde max aktivasyon <0.01) ===")
    for arm in ARMS:
        sub = df[df.arm == arm]
        if sub.dead_units.eq(0).all():
            continue
        print("%-26s %d birim (265 icinde)" % (arm, int(sub.dead_units.mean())))

    print("\n=== RASTGELE ETIKET KONTROLU (coarse_kc_gercek) ===")
    vals = {"g2_exact": [], "newn_exact": []}
    for seed in range(N_SEEDS):
        A = gauss_codes_11(seed)
        code = make_code("coarse_kc_gercek", seed, mats, W_vpn_sh)
        Xtr = np.array([code(n, op) for n, op in TRAIN], np.float32)
        Ttr = np.array([A[result(p)] for p in TRAIN], np.float32)
        rng = np.random.RandomState(seed + 4000)
        rng.shuffle(Ttr)
        W, b = delta_fit_reg(Xtr, Ttr, seed=seed)
        for key, pairs in [("g2_exact", TEST_COMBO_G2), ("newn_exact", TEST_NEWN)]:
            ex = []
            for (n, op) in pairs:
                d = decode(code(n, op) @ W.T + b, A)
                ex.append(d == result((n, op)))
            vals[key].append(float(np.mean(ex)))
    for k in vals:
        print("%-10s %6.3f +- %.3f" % (k, float(np.mean(vals[k])), float(np.std(vals[k], ddof=1))))

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()


