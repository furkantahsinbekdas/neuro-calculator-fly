"""
numcog/phase4c.py — FAZ 4C: sistematik tablo hatası tanısı + N=81 kapasitesi (mühendislik).

Seçim ölçütü YALNIZCA tablo doğruluğu (tüm 2(N+1) girdi). Çarpma/bölme seçim için kullanılmaz.
Mevcut modüller import edilir, DEĞİŞTİRİLMEZ.
"""
from __future__ import annotations
import os
import time

import numpy as np
import pandas as pd

import number_coding as nc
import arithmetic as ar
import operator_diagnosis as od
import calculator as cal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4c")

SIGMA = 1.5
TOPK = 40
LR = 0.01
EPOCHS = 1000
N_MAIN = 40
N_BIG = 81
SEEDS_DIAG = 100
SEEDS_SWEEP = 30
SEEDS_N81 = 20
SEEDS_FINAL = 100


def gauss_axis(N, seed, sigma=SIGMA, lo=0.0, hi=None, nv=265):
    if hi is None:
        hi = float(N)
    rng = np.random.RandomState(seed)
    positions = np.linspace(float(lo), float(hi), nv)
    pos = positions[rng.permutation(nv)]
    A = np.zeros((N + 1, nv), dtype=np.float32)
    for t in range(N + 1):
        d = t - pos
        A[t] = np.exp(-(d * d) / (2.0 * sigma * sigma))
    return A


def make_code(N, seed, mats, sigma=SIGMA, lo=0.0, hi=None, topk=TOPK):
    A = gauss_axis(N, seed, sigma, lo, hi)
    ops = ar.op_codes(seed, mats["n_alpn"])

    def code(n, op):
        s = mats["W_vpn"] @ A[n] + mats["W_alpn_r"] @ ops[op]
        thr = np.sort(s)[-topk] if topk <= len(s) else s.min()
        return (s >= thr).astype(np.float32)
    return code


def fit_fast(X, y, n_classes, lr=LR, epochs=EPOCHS, seed=0, balanced=False):
    X = X.astype(np.float32)
    y = y.astype(np.int64)
    N, D = X.shape
    rng = np.random.RandomState(seed + 1000)
    W = rng.normal(0.0, 0.01, (n_classes, D)).astype(np.float32)
    b = np.zeros(n_classes, dtype=np.float32)
    if balanced:
        cnt = np.bincount(y, minlength=n_classes).astype(np.float32)
        wts = 1.0 / np.maximum(cnt, 1.0)
        wts = (wts / wts.mean()).astype(np.float32)
    else:
        wts = np.ones(n_classes, dtype=np.float32)
    for _ in range(epochs):
        S = X @ W.T + b
        T = -np.ones((N, n_classes), dtype=np.float32)
        T[np.arange(N), y] = 1.0
        E = (T - S) * wts[None, :]
        W += lr * (E.T @ X) / N
        b += lr * E.mean(0)
    return W, b


def table_eval(N, seed, mats, sigma=SIGMA, lo=0.0, hi=None, topk=TOPK, lr=LR,
               epochs=EPOCHS, balanced=False):
    code = make_code(N, seed, mats, sigma, lo, hi, topk)
    pairs = [(n, op) for n in range(N + 1) for op in ('+', '-')]
    X = np.array([code(n, op) for n, op in pairs], np.float32)
    y = np.array([od.clip_result(n, op, N) for n, op in pairs])
    W, b = fit_fast(X, y, N + 1, lr, epochs, seed, balanced)
    S = X @ W.T + b
    pred = S.argmax(1)
    wrong = []
    for i, (n, op) in enumerate(pairs):
        if pred[i] != y[i]:
            s = S[i].copy()
            cs = float(s[y[i]])
            s[y[i]] = -1e9
            wrong.append(dict(n=n, op=op, pred=int(pred[i]), true=int(y[i]),
                              margin=cs - float(s.max())))
    return float(np.mean(pred == y)), wrong, code


def diagnosis():
    mats = od.load_sets()
    rows, allwrong = [], []
    for seed in range(SEEDS_DIAG):
        acc, wrong, _ = table_eval(N_MAIN, seed, mats)
        rows.append(dict(seed=seed, acc=acc, n_wrong=len(wrong), full=int(len(wrong) == 0)))
        for w in wrong:
            allwrong.append(dict(seed=seed, **w))
    df = pd.DataFrame(rows)
    wdf = pd.DataFrame(allwrong) if allwrong else pd.DataFrame(columns=["seed", "n", "op", "pred", "true", "margin"])
    # kenar girdilerinin komşularıyla kod benzerliği
    sims = []
    for seed in range(min(20, SEEDS_DIAG)):
        _, _, code = table_eval(N_MAIN, seed, mats)
        for n in (0, 1, 2, 38, 39, 40):
            for op in ('+', '-'):
                c = code(n, op)
                nb = [cal.rl._cosine(c, code(nn, oo))
                      for nn in (n - 1, n + 1) if 0 <= nn <= N_MAIN for oo in ('+', '-')]
                sims.append(dict(n=n, op=op, max_sim_nb=float(max(nb)) if nb else float("nan")))
    sdf = pd.DataFrame(sims)
    print("\n=== ADIM 0: TANI (N=%d, %d tohum) ===" % (N_MAIN, SEEDS_DIAG))
    print("tablo TAM dogru tohum: %d / %d (%.1f%%)" % (int(df.full.sum()), len(df), 100 * df.full.mean()))
    print("egitim dogrulugu: ort=%.4f  min=%.4f" % (df.acc.mean(), df.acc.min()))
    if len(wdf):
        print("hatali girdiler (n, op) dagilimi:")
        print(wdf.groupby(["n", "op"]).size().sort_values(ascending=False).head(15).to_string())
        print("marj: ort=%.3f  min=%.3f (negatif = dogru sinif kaybediyor)" % (wdf.margin.mean(), wdf.margin.min()))
    print("kenar girdilerinin komsu kod benzerligi (maks):")
    print(sdf.groupby(["n", "op"]).max_sim_nb.mean().to_string())
    df.to_csv(os.path.join(OUT, "diag_seeds.csv"), index=False)
    wdf.to_csv(os.path.join(OUT, "diag_wrong.csv"), index=False)
    sdf.to_csv(os.path.join(OUT, "diag_similarity.csv"), index=False)
    return df, wdf
ARMS = [
    ("ref", dict()),
    ("ep4x", dict(epochs=4 * EPOCHS)),
    ("ep10x", dict(epochs=10 * EPOCHS)),
    ("pad", dict(lo=-3.0, hi=float(N_MAIN + 3))),
    ("lr0.005", dict(lr=0.005)),
    ("lr0.02", dict(lr=0.02)),
    ("lr0.05", dict(lr=0.05)),
    ("balanced", dict(balanced=True)),
]


class Core:
    """Nominal (one-vs-all) okumalı çekirdek; konfigüre edilebilir."""

    def __init__(self, N, code, W, b):
        self.N = N
        self.code = code
        self.W = W
        self.b = b
        self._pairs = [(n, op) for n in range(N + 1) for op in ('+', '-')]
        self.X = np.array([code(n, op) for n, op in self._pairs], np.float32)
        self.y = np.array([od.clip_result(n, op, N) for n, op in self._pairs])

    def _result(self, n, op):
        return od.clip_result(n, op, self.N)

    def step(self, n, op):
        s = (self.code(n, op)[None, :] @ self.W.T + self.b)[0]
        d = int(np.argmax(s))
        e = np.exp(s - s.max())
        return d, float(e[d] / e.sum())

    def train_accuracy(self):
        return float(np.mean(ar.predict_multi(self.X, self.W, self.b) == self.y))


def run_arms():
    mats = od.load_sets()
    rows = []
    for name, kw in ARMS:
        full, accs = 0, []
        t0 = time.time()
        for seed in range(SEEDS_SWEEP):
            acc, wrong, _ = table_eval(N_MAIN, seed, mats, **kw)
            accs.append(acc)
            full += int(len(wrong) == 0)
        rows.append(dict(arm=name, full_frac=full / SEEDS_SWEEP, acc=float(np.mean(accs)),
                         sec=time.time() - t0))
        print("  %-9s tam-dogru=%d/%d (%.1f%%)  egitim=%.4f  (%.0fs)"
              % (name, full, SEEDS_SWEEP, 100 * full / SEEDS_SWEEP, np.mean(accs), rows[-1]["sec"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "arms40.csv"), index=False)
    return df


def n81_sweep():
    mats = od.load_sets()
    rows = []
    for sigma in (1.0, 1.5):
        for topk in (40, 60, 80, 120):
            full, accs = 0, []
            for seed in range(SEEDS_N81):
                acc, wrong, _ = table_eval(N_BIG, seed, mats, sigma=sigma, topk=topk)
                accs.append(acc)
                full += int(len(wrong) == 0)
            rows.append(dict(sigma=sigma, topk=topk, full_frac=full / SEEDS_N81, acc=float(np.mean(accs))))
            print("  sigma=%.1f topk=%-3d tam-dogru=%d/%d (%.1f%%)  egitim=%.4f"
                  % (sigma, topk, full, SEEDS_N81, 100 * full / SEEDS_N81, np.mean(accs)))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "n81_sweep.csv"), index=False)
    return df


def final_measure(bname, kw, seeds=SEEDS_FINAL):
    mats = od.load_sets()
    rows, chain = [], []
    for seed in range(seeds):
        acc, wrong, code = table_eval(N_MAIN, seed, mats, **kw)
        X = np.array([code(n, op) for n in range(N_MAIN + 1) for op in ('+', '-')], np.float32)
        y = np.array([od.clip_result(n, op, N_MAIN) for n in range(N_MAIN + 1) for op in ('+', '-')])
        W, b = fit_fast(X, y, N_MAIN + 1, kw.get("lr", LR), kw.get("epochs", EPOCHS), seed,
                        kw.get("balanced", False))
        core = Core(N_MAIN, code, W, b)
        r = od.calc_measure(N_MAIN, seed, mats, core)
        rows.append(dict(seed=seed, table=acc, full=int(len(wrong) == 0), add=r["add"],
                         subtract=r["subtract"], multiply=r["multiply"], divide=r["divide"]))
        chain.extend(r["chain"])
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "final_seeds.csv"), index=False)
    cdf = cal.chain_vs_k(chain, float(df["add"].mean()))
    cdf.to_csv(os.path.join(OUT, "final_chain.csv"), index=False)
    print("tablo tam-dogru tohum: %d/%d" % (int(df.full.sum()), len(df)))
    for k in ("add", "subtract", "multiply", "divide"):
        print("  %-9s ort=%.3f +- %.3f  min=%.3f  (GA95: %.3f-%.3f)"
              % (k, df[k].mean(), df[k].std(ddof=1), df[k].min(),
                 df[k].mean() - 1.96 * df[k].std(ddof=1) / np.sqrt(len(df)),
                 df[k].mean() + 1.96 * df[k].std(ddof=1) / np.sqrt(len(df))))
    print("zincir k vs p^k (ilk 6):")
    print(cdf.head(6).to_string(index=False))
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    diagnosis()

    print("\n=== KOLLAR (N=%d, %d tohum) ===" % (N_MAIN, SEEDS_SWEEP))
    arms = run_arms()
    ok = arms[arms.full_frac >= 0.95]
    print(">=%%95 basari saglayan kollar: %s" % (list(ok.arm) if len(ok) else "YOK"))
    pick = (ok if len(ok) else arms).sort_values(["full_frac", "acc"], ascending=False).iloc[0]
    bname = str(pick.arm)
    bkw = dict(ARMS)[bname]
    print("SECILEN KONFIGURASYON: %s %s" % (bname, bkw))

    rej = sum(1 for s in range(SEEDS_SWEEP)
              if len(table_eval(N_MAIN, s, od.load_sets(), **bkw)[1]) > 0)
    print("KONTROLCU KALIBRASYONU (kalite kontrol; sinek kural ogrenmez): %d/%d tohum reddedilir"
          % (rej, SEEDS_SWEEP))

    print("\n=== N=81 TARAMASI (%d tohum) ===" % SEEDS_N81)
    n81 = n81_sweep()
    n81_ok = n81[n81.full_frac >= 0.95]
    print("N=81 >=%%95: %s" % ("VAR" if len(n81_ok) else "YOK -> iki haneli yedek gerekir"))

    print("\n=== SON OLCUM (donmus: %s, %d tohum) ===" % (bname, SEEDS_FINAL))
    final_measure(bname, bkw)
    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

