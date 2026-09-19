"""
numcog/calculator.py — FAZ 4A: ardışık hesap makinesi.

İŞ BÖLÜMÜ (açık): Sinek çekirdeği yalnızca (n, op) -> clip(n±1, 0..N) tek adımını yapar
(Faz 3c mimarisi: coarse_kc + sürekli Gauss çıktı). Sayaç, döngü, durma koşulu, durum geri
beslemesi ve sonuç okuma TAMAMEN KONTROLCÜDE (Python). Sinek durum taşımaz.
"""
from __future__ import annotations
import os
import time

import numpy as np
import pandas as pd

import number_coding as nc
import arithmetic as ar
import rule_learning as rl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4a")

SIGMA = 1.5
TOPK = 40
LR = 0.01
EPOCHS = 500
NV = 265
N_SEEDS = 20


def gauss_codes_N(N, seed, nv=NV):
    """(N+1, nv) Gauss kodları; n ∈ 0..N, eksen [0,N]."""
    rng = np.random.RandomState(seed)
    positions = np.linspace(0.0, float(N), nv)
    perm = rng.permutation(nv)
    pos = positions[perm]
    A = np.zeros((N + 1, nv), dtype=np.float32)
    for t in range(N + 1):
        d = t - pos
        A[t] = np.exp(-(d * d) / (2.0 * SIGMA * SIGMA))
    return A


def _fit32(X, T, lr=LR, epochs=EPOCHS, seed=0):
    X = X.astype(np.float32)
    T = T.astype(np.float32)
    N, D = X.shape
    out_dim = T.shape[1]
    rng = np.random.RandomState(seed + 1000)
    W = rng.normal(0.0, 0.01, (out_dim, D)).astype(np.float32)
    b = np.zeros(out_dim, dtype=np.float32)
    for _ in range(epochs):
        Y = X @ W.T + b
        E = T - Y
        W += lr * (E.T @ X) / N
        b += lr * E.mean(axis=0)
    return W, b


def _batch_decode(Y, refs):
    Yn = Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-12)
    Rn = refs / (np.linalg.norm(refs, axis=1, keepdims=True) + 1e-12)
    S = Yn @ Rn.T
    return S.argmax(axis=1)


class FlyCore:
    """Sinek çekirdeği: (n,op) -> clip(n±1,0..N) tek adımı. Durum TAŞIMAZ."""

    def __init__(self, N, seed=0, mats=None):
        self.N = N
        self.seed = seed
        self.A = gauss_codes_N(N, seed)
        self.mats = mats if mats is not None else ar.load_arithmetic()
        self.ops = ar.op_codes(seed, self.mats["n_alpn"])
        self.pairs = [(n, op) for n in range(N + 1) for op in ('+', '-')]
        self._build()

    def _result(self, n, op):
        return int(min(max(n + (1 if op == '+' else -1), 0), self.N))

    def _kc_code(self, n, op, noise=0.0, rng=None):
        num = self.A[n]
        if noise > 0 and rng is not None:
            num = num + noise * rng.normal(0.0, 1.0, num.shape).astype(np.float32)
            num = np.clip(num, 0.0, None)
        W_vpn = self.mats["W_vpn"]
        W_alpn_r = self.mats["W_alpn_r"]
        score = W_vpn @ num + W_alpn_r @ self.ops[op]
        thr = np.sort(score)[-TOPK] if TOPK <= len(score) else score.min()
        return (score >= thr).astype(np.float32)

    def _build(self):
        self.X = np.array([self._kc_code(n, op) for n, op in self.pairs], np.float32)
        self.true = np.array([self._result(n, op) for n, op in self.pairs], dtype=np.int64)
        T = self.A[self.true]
        self.W, self.b = _fit32(self.X, T, seed=self.seed)

    def step(self, n, op, noise=0.0, rng=None):
        x = self._kc_code(n, op, noise, rng)
        y = x @ self.W.T + self.b
        d = int(_batch_decode(y[None, :], self.A)[0])
        conf = rl._cosine(y, self.A[d])
        return d, conf

    def train_accuracy(self):
        Y = self.X @ self.W.T + self.b
        d = _batch_decode(Y, self.A)
        return float(np.mean(d == self.true))

    def mean_confidence(self):
        Y = self.X @ self.W.T + self.b
        d = _batch_decode(Y, self.A)
        return float(np.mean([rl._cosine(Y[i], self.A[d[i]]) for i in range(len(d))]))
def capacity_measurement():
    mats = ar.load_arithmetic()
    rows = []
    for N in (10, 20, 40, 81):
        accs, confs, times = [], [], []
        for seed in range(N_SEEDS):
            t0 = time.time()
            fc = FlyCore(N, seed, mats)
            accs.append(fc.train_accuracy())
            confs.append(fc.mean_confidence())
            times.append(time.time() - t0)
        rows.append(dict(N=N, train_acc=float(np.mean(accs)), acc_std=float(np.std(accs, ddof=1)),
                         conf=float(np.mean(confs)), time=float(np.mean(times))))
        print("  N=%d: train_acc=%.3f conf=%.3f (%.1fs/tohum)" % (N, rows[-1]["train_acc"], rows[-1]["conf"], rows[-1]["time"]))
    return pd.DataFrame(rows)


class CyborgFly:
    """KONTROLCÜ: sayaç, döngü, durma koşulu, durum geri beslemesi, sonuç okuma."""

    def __init__(self, core):
        self.core = core
        self.calls = 0
        self.log = []

    def _step(self, n, op):
        d, conf = self.core.step(n, op)
        self.calls += 1
        self.log.append((n, op, d, conf))
        return d

    def add(self, a, b):
        n = a
        for _ in range(b):
            n = self._step(n, '+')
        return n

    def subtract(self, a, b):
        n = a
        for _ in range(b):
            n = self._step(n, '-')
        return n

    def multiply(self, a, b):
        n = 0
        for _ in range(b):
            n = self.add(n, a)
        return n

    def divide(self, a, b):
        n = a
        q = 0
        while n >= b and q < 50:   # güvenlik sınırı (kontrolcünün durma koşulu)
            n = self.subtract(n, b)
            q += 1
        return q, n


def measure_calculator(fc):
    cf = CyborgFly(fc)
    p = fc.train_accuracy()
    chain = []
    mul_ok = mul_tot = div_ok = div_tot = 0
    for a in range(1, 10):
        for b in range(1, 10):
            r = cf.multiply(a, b)
            mul_ok += int(r == a * b)
            mul_tot += 1
            chain.append(dict(op='mul', a=a, b=b, k=a * b, ok=int(r == a * b), got=r, want=a * b))
            q, rem = cf.divide(a, b)
            div_ok += int(q == a // b)
            div_tot += 1
            chain.append(dict(op='div', a=a, b=b, k=b * (a // b), ok=int(q == a // b), got=q, want=a // b))
    return dict(p=p, mul_acc=mul_ok / mul_tot, div_acc=div_ok / div_tot,
                chain=chain, calls=cf.calls)


def chain_vs_k(chain, p):
    import collections
    byk = collections.defaultdict(list)
    for c in chain:
        byk[c['k']].append(c['ok'])
    rows = []
    for k in sorted(byk):
        ok = byk[k]
        rows.append(dict(k=k, n=len(ok), acc=float(np.mean(ok)), p_k=float(p ** k)))
    return pd.DataFrame(rows)


def noise_curve(fc, seed):
    levels = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]
    out = []
    for nl in levels:
        rng = np.random.RandomState(seed + 99)
        ok = tot = 0
        for n in range(fc.N + 1):
            for op in ('+', '-'):
                d, _ = fc.step(n, op, noise=nl, rng=rng)
                ok += (d == fc._result(n, op))
                tot += 1
        out.append(dict(noise=nl, acc=ok / tot))
    return out


def demo_add(fc, a, b):
    cf = CyborgFly(fc)
    n = a
    print("demo add(%d,%d):" % (a, b))
    for i in range(b):
        before = n
        n = cf._step(n, '+')
        print("  Tick %d: %d -> %d (güven=%.2f)" % (i + 1, before, n, cf.log[-1][3]))
    print("  sonuç = %d (beklenen %d)" % (n, a + b))


def demo_multiply(fc, a, b):
    cf = CyborgFly(fc)
    n = 0
    print("demo multiply(%d,%d):" % (a, b))
    for i in range(b):
        for j in range(a):
            before = n
            n = cf._step(n, '+')
            print("  Tick %d: %d -> %d (güven=%.2f)" % (cf.calls, before, n, cf.log[-1][3]))
    print("  sonuç = %d (beklenen %d)" % (n, a * b))


def main():
    os.makedirs(OUT, exist_ok=True)
    cap = capacity_measurement()
    cap.to_csv(os.path.join(OUT, "capacity.csv"), index=False)
    print("=== KAPASITE (N tarama, 20 tohum) ===")
    print(cap.to_string(index=False))
    ok100 = cap[cap.train_acc >= 0.999]
    Ncalc = int(ok100.N.max()) if len(ok100) else int(cap.loc[cap.train_acc.idxmax(), 'N'])
    print("100%% calisan en buyuk N = %s  ->  hesap makinesi N = %d"
          % (("yok, en iyi %d" % Ncalc) if not len(ok100) else Ncalc, Ncalc))

    mats = ar.load_arithmetic()
    rows = []
    all_chain = []
    for seed in range(N_SEEDS):
        fc = FlyCore(Ncalc, seed, mats)
        r = measure_calculator(fc)
        rows.append(dict(seed=seed, p=r["p"], mul_acc=r["mul_acc"], div_acc=r["div_acc"], calls=r["calls"]))
        all_chain.extend(r["chain"])
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "calculator.csv"), index=False)
    print("\n=== HESAP MAKINESI (N=%d, 20 tohum) ===" % Ncalc)
    print("p (tek adim)  = %.4f +- %.4f" % (float(df.p.mean()), float(df.p.std(ddof=1))))
    print("multiply acc  = %.4f +- %.4f" % (float(df.mul_acc.mean()), float(df.mul_acc.std(ddof=1))))
    print("divide acc    = %.4f +- %.4f" % (float(df.div_acc.mean()), float(df.div_acc.std(ddof=1))))
    print("ort. sinek cagrisi/cagri = %.1f" % float(df.calls.mean()))

    p_mean = float(df.p.mean())
    cvk = chain_vs_k(all_chain, p_mean)
    cvk.to_csv(os.path.join(OUT, "chain_vs_k.csv"), index=False)
    print("\n=== ZINCIR UZUNLUGU k vs DOGRULUK (p^k) ===")
    print(cvk.to_string(index=False))

    fc0 = FlyCore(Ncalc, 0, mats)
    print("\n=== GURULTU ===")
    for r in noise_curve(fc0, 0):
        print("noise=%.2f  acc=%.3f" % (r["noise"], r["acc"]))

    fc0 = FlyCore(Ncalc, 0, mats)
    print()
    demo_add(fc0, 3, 2)
    print()
    demo_multiply(fc0, 2, 3)

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

