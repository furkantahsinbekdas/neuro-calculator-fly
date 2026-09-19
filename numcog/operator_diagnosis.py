"""
numcog/operator_diagnosis.py — FAZ 4A-2: operatör yıkanmasının tanısı ve düzeltme denemesi.

Nominal sınıf okuması (Faz 3 tarzı). Kollar: referans, operatör kazancı ×g, kanal başına
inhibisyon, birleşim KC seti. Başarı ölçütü: N=10 eğitim ≥0.99 VE op-duyarlılık ≥%95.
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

import number_coding as nc
import arithmetic as ar
import calculator as cal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4a2")

SIGMA = 1.5
TOPK = 40
N_SEEDS = 20
N_MAIN = 10
N_SECOND = 20
GAINS = (1, 2, 4, 8)
SUCCESS_ACC = 0.99
SUCCESS_OPSENS = 0.95


def load_sets():
    M = nc.build_matrices(min_syn=1)
    W_vpn = M["W_vpn"]
    kc_vpn = M["kc_vpn"]
    W_alpn = M["W_alpn"]
    kc_alpn = M["kc_alpn"]
    n_alpn = W_alpn.shape[1]
    ka = {r: i for i, r in enumerate(kc_alpn)}
    rows_v = [ka.get(r) for r in kc_vpn]
    W_alpn_r = np.zeros((len(kc_vpn), n_alpn), dtype=np.float32)
    for j, ri in enumerate(rows_v):
        if ri is not None:
            W_alpn_r[j] = W_alpn[ri]
    shared = np.array([j for j, ri in enumerate(rows_v) if ri is not None])
    # örtüşme-kontrol: ALPN ağırlıklarını rastgele aynı sayıda KC'ye taşı
    rng = np.random.RandomState(999)
    W_alpn_r_rand = np.zeros_like(W_alpn_r)
    for dst, src in zip(rng.choice(len(kc_vpn), size=len(shared), replace=False), shared):
        W_alpn_r_rand[dst] = W_alpn_r[src]
    # birleşim kümesi
    union_ids = sorted(set(kc_vpn) | set(kc_alpn))
    vi = {r: i for i, r in enumerate(kc_vpn)}
    ai = {r: i for i, r in enumerate(kc_alpn)}
    U = len(union_ids)
    W_vpn_u = np.zeros((U, W_vpn.shape[1]), dtype=np.float32)
    W_alpn_u = np.zeros((U, n_alpn), dtype=np.float32)
    shared_u = []
    for u, r in enumerate(union_ids):
        if r in vi:
            W_vpn_u[u] = W_vpn[vi[r]]
        if r in ai:
            W_alpn_u[u] = W_alpn[ai[r]]
        if (r in vi) and (r in ai):
            shared_u.append(u)
    return dict(W_vpn=W_vpn, W_alpn_r=W_alpn_r, W_alpn_r_rand=W_alpn_r_rand, shared=shared,
                n_alpn=n_alpn, W_vpn_u=W_vpn_u, W_alpn_u=W_alpn_u,
                shared_u=np.array(shared_u), U=U, n_vpn=W_vpn.shape[1])


def pairs_for(N):
    return [(n, op) for n in range(N + 1) for op in ('+', '-')]


def clip_result(n, op, N):
    return int(min(max(n + (1 if op == '+' else -1), 0), N))


ARMS = ["ref", "gain", "perchan", "union", "shuffled", "ablation", "overlapctl"]


def make_code(arm, N, seed, mats, g=1.0, kv=20, ka=20, Wsh=None):
    A = cal.gauss_codes_N(N, seed)
    ops = ar.op_codes(seed, mats["n_alpn"])

    def topk_mask(s, k):
        thr = np.sort(s)[-k] if k <= len(s) else s.min()
        return s >= thr

    def code(n, op):
        if arm == "union":
            s = mats["W_vpn_u"] @ A[n] + g * (mats["W_alpn_u"] @ ops[op])
            return topk_mask(s, TOPK).astype(np.float32)
        if arm == "perchan":
            sv = mats["W_vpn_u"] @ A[n]
            sa = g * (mats["W_alpn_u"] @ ops[op])
            return (topk_mask(sv, kv) | topk_mask(sa, ka)).astype(np.float32)
        Wv = Wsh if (arm == "shuffled" and Wsh is not None) else mats["W_vpn"]
        Wa = mats["W_alpn_r_rand"] if arm == "overlapctl" else mats["W_alpn_r"]
        s = Wv @ A[n] + g * (Wa @ ops[op])
        if arm == "ablation":
            s = s.copy()
            s[mats["shared"]] = -1e9
        return topk_mask(s, TOPK).astype(np.float32)

    return code
def eval_metrics(arm, N, seed, mats, g=1.0, kv=20, ka=20, Wsh=None, shuffle_labels=False):
    code = make_code(arm, N, seed, mats, g=g, kv=kv, ka=ka, Wsh=Wsh)
    pairs = pairs_for(N)
    X = np.array([code(n, op) for n, op in pairs], np.float32)
    y = np.array([clip_result(n, op, N) for n, op in pairs])
    if shuffle_labels:
        rng = np.random.RandomState(seed + 4000)
        rng.shuffle(y)
    W, b = ar.delta_fit_multi(X, y, seed=seed, n_classes=N + 1)
    train_acc = float(np.mean(ar.predict_multi(X, W, b) == y))
    flip = 0
    for n in range(N + 1):
        p_plus = int(ar.predict_multi(code(n, '+')[None, :], W, b)[0])
        p_minus = int(ar.predict_multi(code(n, '-')[None, :], W, b)[0])
        if p_plus != p_minus:
            flip += 1
    return train_acc, flip / (N + 1)


def select_g(arm, N, seed, mats, Wsh=None, kv=20, ka=20):
    pairs = pairs_for(N)
    val = [p for i, p in enumerate(pairs) if i % 5 == 0]
    tr = [p for p in pairs if p not in val]
    best_g, best_acc = GAINS[0], -1.0
    for g in GAINS:
        code = make_code(arm, N, seed, mats, g=g, kv=kv, ka=ka, Wsh=Wsh)
        X = np.array([code(n, op) for n, op in tr], np.float32)
        y = np.array([clip_result(n, op, N) for n, op in tr])
        W, b = ar.delta_fit_multi(X, y, seed=seed, n_classes=N + 1)
        Xv = np.array([code(n, op) for n, op in val], np.float32)
        yv = np.array([clip_result(n, op, N) for n, op in val])
        acc = float(np.mean(ar.predict_multi(Xv, W, b) == yv))
        if acc > best_acc:
            best_acc, best_g = acc, g
    return best_g


def diagnosis(N, seed, mats, gains=GAINS):
    A = cal.gauss_codes_N(N, seed)
    ops = ar.op_codes(seed, mats["n_alpn"])
    W_vpn = mats["W_vpn"]
    W_alpn_r = mats["W_alpn_r"]
    shared = mats["shared"]
    out = []
    for g in gains:
        act_list, surv_list, cos_list = [], [], []
        for n in range(N + 1):
            sp = W_vpn @ A[n] + g * (W_alpn_r @ ops['+'])
            sm = W_vpn @ A[n] + g * (W_alpn_r @ ops['-'])
            cp = sp >= np.sort(sp)[-TOPK]
            cm = sm >= np.sort(sm)[-TOPK]
            act_list.append(np.intersect1d(np.where(cp)[0], shared).size)
            sig = W_alpn_r @ ops['+']
            tot = float(sig.sum()) if sig.sum() > 0 else 1e-9
            surv_list.append(float(sig[cp].sum()) / tot)
            cos_list.append(cal.rl._cosine(cp.astype(float), cm.astype(float)))
        out.append(dict(N=N, seed=seed, g=g, alpn_active_kc=float(np.mean(act_list)),
                        alpn_survival=float(np.mean(surv_list)), code_cos=float(np.mean(cos_list))))
    return out


def calc_measure(N, seed, mats, core):
    """Aynı CyborgFly kontrolcüsüyle add/sub/mul/div ölçümü (1..9)."""
    cf = cal.CyborgFly(core)
    chain, res = [], {}
    for opname in ("add", "subtract", "multiply"):
        ok = tot = 0
        for a in range(1, 10):
            for b in range(1, 10):
                if opname == "add":
                    r = cf.add(a, b); want = a + b; k = b
                elif opname == "subtract":
                    r = cf.subtract(a, b); want = max(a - b, 0); k = b
                else:
                    r = cf.multiply(a, b); want = a * b; k = a * b
                good = int(r == want)
                ok += good; tot += 1
                chain.append(dict(op=opname, a=a, b=b, k=k, ok=good, got=r, want=want))
        res[opname] = ok / tot
    ok = tot = 0
    for a in range(1, 10):
        for b in range(1, 10):
            q, rem = cf.divide(a, b)
            good = int(q == a // b)
            ok += good; tot += 1
            chain.append(dict(op="divide", a=a, b=b, k=b * (a // b), ok=good, got=q, want=a // b))
    res["divide"] = ok / tot
    res["calls"] = cf.calls
    res["chain"] = chain
    return res


class NominalFlyCore:
    """Nominal (one-vs-all) okumalı sinek çekirdeği — Faz 4A-2 düzeltmesi."""

    def __init__(self, N, seed, mats):
        self.N = N
        self.code = make_code("ref", N, seed, mats)
        pairs = pairs_for(N)
        X = np.array([self.code(n, op) for n, op in pairs], np.float32)
        self.X = X
        self.y = np.array([clip_result(n, op, N) for n, op in pairs])
        self.W, self.b = ar.delta_fit_multi(X, self.y, seed=seed, n_classes=N + 1)

    def _result(self, n, op):
        return clip_result(n, op, self.N)

    def step(self, n, op):
        s = (self.code(n, op)[None, :] @ self.W.T + self.b)[0]
        d = int(np.argmax(s))
        e = np.exp(s - s.max())
        return d, float(e[d] / e.sum())

    def train_accuracy(self):
        pred = ar.predict_multi(self.X, self.W, self.b)
        return float(np.mean(pred == self.y))


def main():
    os.makedirs(OUT, exist_ok=True)
    mats = load_sets()
    Wsh = nc.degree_preserving_shuffle(mats["W_vpn"], seed=12345)
    print("birlesim KC = %d, ortak KC = %d" % (mats["U"], len(mats["shared_u"])))

    print("\n=== ADIM 0: TANI (top-k=40, N=10, g ile), 20 tohum ===")
    diag = []
    for seed in range(N_SEEDS):
        diag.extend(diagnosis(N_MAIN, seed, mats))
    ddf = pd.DataFrame(diag)
    ddf.to_csv(os.path.join(OUT, "diagnosis.csv"), index=False)
    for g in GAINS:
        sub = ddf[ddf.g == g]
        print("  g=%d: alpn_aktif_KC=%.1f/40  alpn_hayatta=%.3f  kod_kosinus=%.3f"
              % (g, sub.alpn_active_kc.mean(), sub.alpn_survival.mean(), sub.code_cos.mean()))

    print("\n=== KOLLAR (N=10, 20 tohum) ===")
    rows = []
    for arm in ARMS:
        gs = [select_g(arm, N_MAIN, s, mats, Wsh=Wsh) if arm in ("gain", "perchan", "union") else 1
              for s in range(N_SEEDS)]
        g_mode = max(set(gs), key=gs.count)
        for seed in range(N_SEEDS):
            g = g_mode if arm in ("gain", "perchan", "union") else 1
            acc, ops = eval_metrics(arm, N_MAIN, seed, mats, g=g, Wsh=Wsh)
            rows.append(dict(arm=arm, seed=seed, g=g, train_acc=acc, op_sens=ops))
        sub = pd.DataFrame([r for r in rows if r["arm"] == arm])
        ok = sub.train_acc.mean() >= SUCCESS_ACC and sub.op_sens.mean() >= SUCCESS_OPSENS
        print("%-11s g=%d  train=%.3f+-%.3f  op_sens=%.3f+-%.3f  %s"
              % (arm, g_mode, sub.train_acc.mean(), sub.train_acc.std(ddof=1),
                 sub.op_sens.mean(), sub.op_sens.std(ddof=1), "GECTI" if ok else ""))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "arms.csv"), index=False)

    ra = [eval_metrics("ref", N_MAIN, s, mats, shuffle_labels=True)[0] for s in range(N_SEEDS)]
    print("\nrastgele etiket (ref) train=%.3f +- %.3f" % (float(np.mean(ra)), float(np.std(ra, ddof=1))))

    print("\n=== KARAR (olcut: train>=%.2f VE op_sens>=%.2f) ===" % (SUCCESS_ACC, SUCCESS_OPSENS))
    winners = [arm for arm in ARMS
               if df[df.arm == arm].train_acc.mean() >= SUCCESS_ACC
               and df[df.arm == arm].op_sens.mean() >= SUCCESS_OPSENS]
    print("GECEN KOLLAR:", winners if winners else "YOK")
    if not winners:
        print("HICBIR KOL OLCUTU SAGLAMADI -> feedforward KC + okuma, operatorlu +-1 tablosunda YETERSIZ.")

    if winners:
        print("\n=== HESAP MAKINESI (ref/nominal cekirdek, N secimi) ===")
        Npass = None
        for N in (10, 20, 40, 81):
            accs = [eval_metrics("ref", N, s, mats) for s in range(N_SEEDS)]
            ta = float(np.mean([a for a, o in accs]))
            osn = float(np.mean([o for a, o in accs]))
            ok = ta >= SUCCESS_ACC and osn >= SUCCESS_OPSENS
            print("  N=%-3d train=%.3f op_sens=%.3f %s" % (N, ta, osn, "GECTI" if ok else ""))
            if ok:
                Npass = N
        if Npass is None:
            print("  kriteri gecen N yok -> hesap makinesi olculemedi")
        else:
            print("  hesap makinesi N = %d" % Npass)
            agg = {"add": [], "subtract": [], "multiply": [], "divide": [], "calls": []}
            allchain = []
            for seed in range(N_SEEDS):
                core = NominalFlyCore(Npass, seed, mats)
                r = calc_measure(Npass, seed, mats, core)
                for k in ("add", "subtract", "multiply", "divide", "calls"):
                    agg[k].append(r[k])
                allchain.extend(r["chain"])
            for k in ("add", "subtract", "multiply", "divide"):
                print("  %-9s acc=%.3f +- %.3f" % (k, float(np.mean(agg[k])), float(np.std(agg[k], ddof=1))))
            print("  ort. sinek cagrisi/islem = %.1f" % float(np.mean(agg["calls"])))
            cdf = cal.chain_vs_k(allchain, float(np.mean(agg["add"])))
            cdf.to_csv(os.path.join(OUT, "chain_vs_k.csv"), index=False)
            print("  zincir k vs dogruluk (ilk 8):")
            print(cdf.head(8).to_string(index=False))
            mchain = [c for c in allchain if c["op"] == "multiply"]
            okpairs = sorted({(c["a"], c["b"]) for c in mchain if c["ok"]})
            print("  multiply'de calisan (a,b) cifti: %d / 81  (ust sinir: %d)" % (len(okpairs), Npass))
            pd.DataFrame(allchain).to_csv(os.path.join(OUT, "calculator_chain.csv"), index=False)

    print("\n=== N=20 (ikincil) ===")
    for arm in ("ref", "perchan", "union"):
        accs, opss = [], []
        for seed in range(N_SEEDS):
            g = select_g(arm, N_SECOND, seed, mats, Wsh=Wsh) if arm in ("perchan", "union") else 1
            a, o = eval_metrics(arm, N_SECOND, seed, mats, g=g, Wsh=Wsh)
            accs.append(a)
            opss.append(o)
        print("  %-11s train=%.3f  op_sens=%.3f" % (arm, float(np.mean(accs)), float(np.mean(opss))))

    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

