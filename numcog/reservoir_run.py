"""
numcog/reservoir_run.py — FAZ 7-1: connectome rezervuarında DURUM TAŞIMA (asıl deney).

Ön-kayıt: HIPOTEZLER.md Faz 7 + Faz 7-1 ek ön-kayıt (commit `36e52df`). Faz 0–7-0 DEĞİŞTİRİLMEZ.
Model (kilitli): x_{t+1} = (1-a)x_t + a*tanh(g*W*x_t + B*u_t), a=0.5, işaretli W (Dale), rho(W)=1.
float64. Eşzamanlı süreç: 1. Tohum başına ayrı CSV.

CLI: build | pilot | run <kol> <tohum> | merge
     arms: A_gercek A_derece A_agirlik A_er A_w0 A_ideal A_isaretperm A_dengeli
           B_gercek B_derece B_dengeli
"""
from __future__ import annotations
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

import number_coding as nc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p7_1")
P70 = os.path.join(HERE, "results_p7_0")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")
ARMS_NPZ = os.path.join(OUT, "arms_cache.npz")

CX_CORE = {"EB", "PB", "FB", "NO"}
N_RNG = 4236          # A alt ağı (7-0 ölçümü)
A_SHAPE = "A"
B_SHAPE = "B"
K_GRID = (2, 4, 6, 8, 10)
H_GRID = (0, 10, 20, 40)
TRAIN_N, VAL_N, TEST_N = 300, 120, 120
N_EXTRA = 180
T3_TARGETS = (7, 8, 9, 10)
T3_PER_TARGET = 50
G_GRID = (0.5, 0.8, 0.95, 1.1, 1.3)
AMP_GRID = (0.5, 1.0)
ARMS_A = ("A_gercek", "A_derece", "A_agirlik", "A_er", "A_w0", "A_isaretperm", "A_dengeli")
ARMS_MB = ("B_gercek", "B_derece", "B_dengeli")
BATCH = 64
A_COEF = 0.5
GAP = 5
AMP = 1.0
RHO_ITERS = 400
LAMBDA_REL = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0)
NOISE_REL = 1e-3
T2_LEN, T2_MAXLAG = 2000, 60
T4_STEPS = 200
SEEDS_MAIN = 30
SEEDS_MB = 15
SEEDS_PILOT = 10
READOUT_CLASSES = {k: 2 * k + 1 for k in K_GRID}      # s in [-k, k]
ANN_COLS = ["root_id", "hemibrain_type", "cell_class", "known_nt", "top_nt"]


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def nt_sign(s):
    """Faz 7-0'daki işaret kuralı (ACh/DA/5-HT/OA +; GABA/Glu -; 'negative'/diğer -> NaN)."""
    import re
    if not isinstance(s, str) or not s.strip():
        return np.nan
    pos = {"acetylcholine", "dopamine", "serotonin", "octopamine"}
    neg = {"gaba", "glutamate"}
    toks = [t.strip().lower() for t in re.split(r"[;,]", s)]
    toks = [t for t in toks if t and "negative" not in t]
    p, n = any(t in pos for t in toks), any(t in neg for t in toks)
    return 1.0 if (p and not n) else (-1.0 if (n and not p) else np.nan)


def load_signs():
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann["root_id"] = ann["root_id"].astype("int64")
    lut = {}
    for v in ann.known_nt.dropna().unique():
        lut[v] = nt_sign(v)
    for v in ann.top_nt.dropna().unique():
        lut.setdefault(v, nt_sign(v))
    s_known = ann.known_nt.map(lambda v: lut.get(v, np.nan))
    s_top = ann.top_nt.map(lambda v: lut.get(v, np.nan))
    sign = np.where(s_known.notna(), s_known, s_top)
    return dict(zip(ann.root_id.astype("int64").tolist(), sign.tolist()))


def build_subnet(which):
    """7-0 önbelleğinden A (CX çekirdek) veya B (MB) alt ağını kurar (işaretli, ağırlıklı)."""
    d = np.load(os.path.join(P70, "scan_cache.npz"))
    if which == A_SHAPE:
        pre, post, syn = [], [], []
        for c in CX_CORE:
            k = "np_%s_pre" % c
            if k in d.files:
                pre.append(d[k]); post.append(d["np_%s_post" % c]); syn.append(d["np_%s_syn" % c])
        pre = np.concatenate(pre); post = np.concatenate(post); syn = np.concatenate(syn)
        have = set(np.unique(pre).tolist()) & set(np.unique(post).tolist())
        keep = np.isin(pre, list(have)) & np.isin(post, list(have))
        pre, post, syn = pre[keep], post[keep], syn[keep]
    else:
        pre, post, syn = d["mb_pre"], d["mb_post"], d["mb_syn"]
    nodes = np.unique(np.concatenate([pre, post]))
    rid = d["cell_ids"][nodes]
    remap = -np.ones(int(nodes.max()) + 1, np.int64)
    remap[nodes] = np.arange(len(nodes))
    r, c = remap[pre], remap[post]
    pair = np.stack([r, c], 1)
    pairs, inv = np.unique(pair, axis=0, return_inverse=True)
    w = np.zeros(len(pairs)); np.add.at(w, inv.ravel(), syn.astype(np.float64))
    return rid, pairs[:, 0], pairs[:, 1], w


def signed_matrix(rid, r, c, w, cell_sign, sign_override=None, keep_mag=True):
    """Dale: işaret pre-nöron başına. İmzasız pre-nöronun kenarı HARİÇ (7-0 kuralı)."""
    N = int(max(r.max(), c.max())) + 1
    if sign_override is not None:
        s_pre = sign_override
    else:
        s_pre = np.array([cell_sign.get(int(x), np.nan) for x in rid])
    ok = ~np.isnan(s_pre[r])
    r2, c2, w2 = r[ok], c[ok], w[ok]
    vals = np.abs(w2) if keep_mag else np.ones(len(w2))
    vals = vals * s_pre[r2]
    W = sp.csr_matrix((vals, (r2, c2)), shape=(N, N))
    return W, N


def rho_power(W, iters=RHO_ITERS, seed=0, tol=1e-12):
    """Spektral yarıçap (güç iterasyonu, float64)."""
    n = W.shape[0]
    rng = np.random.RandomState(seed)
    x = rng.normal(size=n)
    x /= np.linalg.norm(x)
    rho = 0.0
    for _ in range(iters):
        y = W @ x
        nr = float(np.linalg.norm(y))
        if nr <= 0:
            return 0.0
        x = y / nr
        if abs(nr - rho) <= tol * max(abs(nr), 1e-12):
            return nr
        rho = nr
    return rho


def build_all():
    """Tüm kolları kurar, rho=1'e normalize eder ve önbelleğe yazar."""
    sign_map = load_signs()
    store = {}
    meta = []
    for shape, tag in ((A_SHAPE, "A"), (B_SHAPE, "B")):
        rid, r, c, w = build_subnet(shape)
        N = int(max(r.max(), c.max())) + 1
        s_pre = np.array([sign_map.get(int(x), np.nan) for x in rid])
        rng = np.random.RandomState(7001 if shape == A_SHAPE else 7002)
        arms = {}
        arms["%s_gercek" % tag] = (r, c, np.abs(w), s_pre)
        R, C = swap_edges(r, c, 10 * len(r), rng, N)
        mg = np.abs(w).copy(); rng.shuffle(mg)
        arms["%s_derece" % tag] = (R, C, mg, s_pre)
        mg2 = np.abs(w).copy(); rng.shuffle(mg2)
        arms["%s_agirlik" % tag] = (r, c, mg2, s_pre)
        # Erdos-Renyi (ayni N ve yogunluk)
        E = len(r)
        ne = int(E * 1.05)
        rr = rng.randint(0, N, size=ne)
        cc = rng.randint(0, N, size=ne)
        keep = rr != cc
        rr, cc = rr[keep], cc[keep]
        pp, inv = np.unique(np.stack([rr, cc], 1), axis=0, return_inverse=True)
        rr, cc = pp[:, 0], pp[:, 1]
        mg3 = rng.choice(np.abs(w), size=len(rr), replace=True)
        arms["%s_er" % tag] = (rr, cc, mg3, s_pre)
        # isaret permutasyonu (ayni +/- orani)
        sp2 = s_pre.copy()
        rng.shuffle(sp2)
        arms["%s_isaretperm" % tag] = (r, c, np.abs(w), sp2)
        # dengeli isaret (yarisi rastgele -)
        sp3 = np.where(rng.random(N) < 0.5, -1.0, 1.0)
        arms["%s_dengeli" % tag] = (r, c, np.abs(w), sp3)
        if shape == A_SHAPE:
            arms["A_w0"] = (np.zeros(0, np.int64), np.zeros(0, np.int64),
                            np.zeros(0), np.zeros(N))
        for name, (rr2, cc2, mag, sg) in arms.items():
            if len(rr2) == 0:
                W = sp.csr_matrix((N, N))
                rho = 0.0
            else:
                W0, _ = signed_matrix(rid, rr2, cc2, mag, None, sign_override=sg)
                rho = rho_power(W0)
                W = W0 * (1.0 / rho) if rho > 0 else W0
            store[name] = W
            meta.append(dict(arm=name, shape=tag, N=N, E=int(W.nnz), rho_raw=rho,
                             pos=int((W.data > 0).sum()), neg=int((W.data < 0).sum())))
            log("  %-14s N=%-5d E=%-7d rho_raw=%.3f (norm sonrasi 1) +%-6d -%-6d"
                % (name, N, W.nnz, rho, meta[-1]["pos"], meta[-1]["neg"]))
    out = {}
    for name, W in store.items():
        out[name + "__data"] = W.data.astype(np.float64)
        out[name + "__indices"] = W.indices.astype(np.int32)
        out[name + "__indptr"] = W.indptr.astype(np.int64)
        out[name + "__shape"] = np.array(W.shape, dtype=np.int64)
    np.savez_compressed(ARMS_NPZ, **out)
    pd.DataFrame(meta).to_csv(os.path.join(OUT, "arms_meta.csv"), index=False)
    log("kollar önbelleğe yazıldı: %s (%.0f MB)" % (ARMS_NPZ,
                                                   os.path.getsize(ARMS_NPZ) / 1e6))
    return store, meta


def load_arm(name):
    d = np.load(ARMS_NPZ)
    W = sp.csr_matrix((d[name + "__data"], d[name + "__indices"], d[name + "__indptr"]),
                      shape=tuple(int(x) for x in d[name + "__shape"]))
    return W


def make_sequences(n, rng, max_pulses=10, cap=8):
    """Her dizi için ±1 darbe dizisi; koşan toplam [-cap, cap]; TÜM diziler BENZERSİZ."""
    P = np.zeros((n, max_pulses), np.int8)
    seen = set()
    i = 0
    while i < n:
        s = 0
        row = np.zeros(max_pulses, np.int8)
        for j in range(max_pulses):
            ch = [v for v in (1, -1) if abs(s + v) <= cap]
            v = ch[rng.randint(len(ch))]
            row[j] = v
            s += v
        key = tuple(row.tolist())
        if key in seen:
            continue
        seen.add(key)
        P[i] = row
        i += 1
    return P


def simulate(W, Win, pulses, k, read_times, g, amp, center=False, a=A_COEF):
    """Seyrek W x yoğun durum matrisi (toplu). Döner: (len(read_times), N, n_seq)."""
    N = W.shape[0]
    n = pulses.shape[0]
    T = max(read_times) + 1
    outs = np.empty((len(read_times), N, n), np.float64)
    rmap = {t: i for i, t in enumerate(read_times)}
    input_scale = amp
    for lo in range(0, n, BATCH):
        P = pulses[lo:lo + BATCH]
        B = P.shape[0]
        X = np.zeros((N, B), np.float64)
        for t in range(T):
            d = (W @ X) if W.nnz else np.zeros_like(X)
            if center:
                d = d - d.mean(axis=0, keepdims=True)
            drive = g * d
            if t % GAP == 0 and (t // GAP) < k:
                v = P[:, t // GAP].astype(np.float64)
                drive = drive + input_scale * (Win @ np.stack([np.maximum(v, 0),
                                                               np.maximum(-v, 0)]))
            X = (1.0 - a) * X + a * np.tanh(drive)
            if t in rmap:
                outs[rmap[t], :, lo:lo + B] = X
    return outs


def make_win(N, k_in, rng, mode="I1", share=None):
    """W_in: (N,2) kanal matrisi (+ ve - ayrık kümeler)."""
    if mode == "I2" and share is not None:
        top = np.argsort(-share)[:max(int(0.10 * N), 2 * k_in)]
        pool = top
    else:
        pool = np.arange(N)
    sel = rng.choice(pool, size=2 * k_in, replace=False)
    Win = np.zeros((N, 2), np.float64)
    Win[sel[:k_in], 0] = 1.0
    Win[sel[k_in:], 1] = 1.0
    return Win


def swap_edges(r, c, n_swaps, rng, N):
    """Derece-korunmuş çift-kenar takası (ikili yapı; satır ve sütun dereceleri korunur)."""
    B = np.zeros((N, N), dtype=bool)
    B[r, c] = True
    R = r.astype(np.int64).copy()
    C = c.astype(np.int64).copy()
    m = len(R)
    for _ in range(n_swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = R[i], C[i]
        cc, d = R[j], C[j]
        if a == cc or b == d or B[a, d] or B[cc, b]:
            continue
        B[a, b] = False
        B[cc, d] = False
        B[a, d] = True
        B[cc, b] = True
        R[i], C[i] = a, d
        R[j], C[j] = cc, b
    return R, C


def ridge_eval(Xtr, ytr, Xva, yva, Xte, yte, rng, scalar=False, n_classes=None,
               lams=LAMBDA_REL):
    """Dual (kernel) ridge; gürültü; λ yalnızca validasyonda seçilir."""
    sd = float(Xtr.std())
    Xtr = Xtr + rng.normal(0.0, NOISE_REL * sd, Xtr.shape)
    Xva = Xva + rng.normal(0.0, NOISE_REL * sd, Xva.shape)
    Xte = Xte + rng.normal(0.0, NOISE_REL * sd, Xte.shape)
    K = Xtr @ Xtr.T
    scale = float(np.mean(np.diag(K))) or 1.0
    if scalar:
        T = (ytr.astype(np.float64))[:, None]
    else:
        T = np.zeros((len(ytr), n_classes))
        T[np.arange(len(ytr)), ytr] = 1.0
    Kva = Xva @ Xtr.T
    Kte = Xte @ Xtr.T
    I = np.eye(len(K))
    best = None
    for lam in lams:
        alpha = np.linalg.solve(K + lam * scale * I, T)
        pv = Kva @ alpha
        vacc = (float(np.mean(np.round(pv[:, 0]) == yva)) if scalar
                else float(np.mean(pv.argmax(1) == yva)))
        if best is None or vacc > best[2]:
            best = (lam, alpha, vacc)
    lam, alpha, vacc = best
    pt = Kte @ alpha
    if scalar:
        pred = np.round(pt[:, 0])
        return dict(lam=lam, val=vacc, test=float(np.mean(pred == yte)),
                    tol=float(np.mean(np.abs(pred - yte) <= 1)))
    pred = pt.argmax(1)
    return dict(lam=lam, val=vacc, test=float(np.mean(pred == yte)))


def state_diag(X):
    """Doygunluk, aktivite, aktif oran, katılım oranı (efektif boyut)."""
    sat = float(np.mean(np.abs(X) > 0.9))
    act = float(np.mean(np.abs(X)))
    active = float(np.mean(np.abs(X).max(axis=0) > 0.1))
    Xc = X - X.mean(axis=0, keepdims=True)
    C = (Xc.T @ Xc) / max(len(Xc) - 1, 1)
    ev = np.linalg.eigvalsh(C)
    ev = np.maximum(ev, 0.0)
    pr = float((ev.sum() ** 2) / (np.sum(ev ** 2) + 1e-300))
    return dict(sat=sat, activity=act, active_frac=active, participation_ratio=pr)


def make_extrapolation(rng, per_target=T3_PER_TARGET):
    """T3 test dizileri: hedef toplam s in {7,8,9,10}; k = 9 (tek s) / 10 (cift s)."""
    seqs = {}
    for s in T3_TARGETS:
        k = 9 if s % 2 else 10
        P = np.ones((per_target, k), np.int8)
        n_neg = (k - s) // 2
        assert (k - s) % 2 == 0 and n_neg >= 0
        for i in range(per_target):
            idx = rng.permutation(k)[:n_neg]
            P[i, idx] = -1
        assert (P.sum(axis=1) == s).all()
        seqs[s] = P
    return seqs


def simulate_x0(W, Win, pulses, k, read_times, g, amp, center, x0):
    """simulate() ile aynı, farklı başlangıç durumundan (x0: (N, n_seq))."""
    N = W.shape[0]
    n = pulses.shape[0]
    T = max(read_times) + 1
    outs = np.empty((len(read_times), N, n), np.float64)
    rmap = {t: i for i, t in enumerate(read_times)}
    for lo in range(0, n, BATCH):
        P = pulses[lo:lo + BATCH]
        B = P.shape[0]
        X = x0[:, lo:lo + B].copy()
        for t in range(T):
            d = (W @ X) if W.nnz else np.zeros_like(X)
            if center:
                d = d - d.mean(axis=0, keepdims=True)
            drive = g * d
            if t % GAP == 0 and (t // GAP) < k:
                v = P[:, t // GAP].astype(np.float64)
                drive = drive + amp * (Win @ np.stack([np.maximum(v, 0),
                                                       np.maximum(-v, 0)]))
            X = (1.0 - A_COEF) * X + A_COEF * np.tanh(drive)
            if t in rmap:
                outs[rmap[t], :, lo:lo + B] = X
    return outs


def run_seed(arm, seed, g, amp, center=False, warm=False):
    """Bir tohum × kol için T1–T3 + tanılar (uzun format satırlar)."""
    W = load_arm(arm)
    N = W.shape[0]
    rng = np.random.RandomState(20000 + seed)
    win_rng = np.random.RandomState(90000 + seed)
    Win = make_win(N, 50, win_rng)
    n_main = TRAIN_N + VAL_N + TEST_N
    P = make_sequences(n_main, rng, max_pulses=10, cap=8)
    assert len({tuple(x) for x in P.tolist()}) == len(P), "dizi cakismasi var (egitim/test)"
    rows = []
    k10_states = None
    for k in K_GRID:
        read_t = [GAP * (k - 1) + H for H in H_GRID]
        out = simulate(W, Win, P, k, read_t, g, amp, center)
        sums = P[:, :k].sum(axis=1)
        for hi, H in enumerate(H_GRID):
            X = out[hi].T
            Xtr = X[:TRAIN_N]
            Xva = X[TRAIN_N:TRAIN_N + VAL_N]
            Xte = X[TRAIN_N + VAL_N:]
            y = (sums + k).astype(np.int64)
            n_cl = 2 * k + 1
            r = ridge_eval(Xtr, y[:TRAIN_N], Xva, y[TRAIN_N:TRAIN_N + VAL_N],
                           Xte, y[TRAIN_N + VAL_N:], rng, n_classes=n_cl)
            reach = np.unique(y)
            rows.append(dict(arm=arm, seed=seed, task="T1", k=k, H=H, acc=r["test"],
                             val=r["val"], lam=r["lam"], n_classes=n_cl,
                             reachable=len(reach), chance=1.0 / len(reach)))
            if k == 10 and H == 0:
                k10_states = X
                d = state_diag(X)
                rows.append(dict(arm=arm, seed=seed, task="diag", k=10, H=0, acc=np.nan,
                                 val=np.nan, lam=np.nan, **d))
    # T3 (ekstrapolasyon; skaler regresyon-yuvarlama)
    seqs = make_extrapolation(rng)
    tr_mask = np.abs(np.cumsum(P, axis=1)).max(axis=1) <= 6
    assert tr_mask.sum() >= 100
    ytr_s = P[tr_mask].sum(axis=1).astype(np.float64)
    Xtr3 = k10_states[tr_mask]
    for s, Ps in seqs.items():
        k = Ps.shape[1]
        out = simulate(W, Win, Ps, k, [GAP * (k - 1)], g, amp, center)
        Xte3 = out[0].T
        r = ridge_eval(Xtr3, ytr_s, Xtr3, ytr_s, Xte3, np.full(len(Ps), float(s)), rng,
                       scalar=True)
        rows.append(dict(arm=arm, seed=seed, task="T3", k=k, H=0, acc=r["test"],
                         val=r["val"], lam=r["lam"], target=s, tol=r["tol"]))
    # T3 (görülmemiş başlangıç durumu)
    Ps = seqs[8]
    Wn = W.shape[0]
    x0 = rng.normal(0.0, 0.5, size=(Wn, len(Ps)))
    out = simulate_x0(W, Win, Ps, 10, [GAP * 9], g, amp, center, x0)
    r = ridge_eval(Xtr3, ytr_s, Xtr3, ytr_s, out[0].T, np.full(len(Ps), 8.0), rng,
                   scalar=True)
    rows.append(dict(arm=arm, seed=seed, task="T3_x0", k=10, H=0, acc=r["test"],
                     val=r["val"], lam=r["lam"], target=8, tol=r["tol"]))
    return rows


def task_t2(W, Win, seed, g, amp, center=False):
    """Jaeger bellek kapasitesi (gecikme 1..60; tek akis, her adimda ±1 girdi)."""
    rng = np.random.RandomState(30000 + seed)
    n = T2_LEN + T2_MAXLAG + 1
    u = rng.choice([-1.0, 1.0], size=n)
    N = W.shape[0]
    X = np.zeros((N, 1))
    states = np.empty((n, N))
    for t in range(n):
        v = u[t]
        drive = (g * (W @ X)) if W.nnz else np.zeros_like(X)
        if center:
            drive = drive - drive.mean(axis=0, keepdims=True)
        drive = drive + amp * (Win @ np.array([[max(v, 0.0)], [max(-v, 0.0)]]))
        X = (1.0 - A_COEF) * X + A_COEF * np.tanh(drive)
        states[t] = X[:, 0]
    tr, va, te = slice(T2_MAXLAG, 1260), slice(1260, 1660), slice(1660, n)
    Xtr, Xva, Xte = states[tr], states[va], states[te]
    K = Xtr @ Xtr.T
    scale = float(np.mean(np.diag(K))) or 1.0
    Kva, Kte = Xva @ Xtr.T, Xte @ Xtr.T
    I = np.eye(len(K))

    def r2(pred, true):
        pred = pred - pred.mean()
        true = true - true.mean()
        den = np.sqrt((pred ** 2).sum() * (true ** 2).sum())
        return float((pred * true).sum() / den) ** 2 if den > 0 else 0.0

    lam_best, best = None, -1.0
    for lam in LAMBDA_REL:
        ytr = u[tr.start - 1:tr.stop - 1]
        alpha = np.linalg.solve(K + lam * scale * I, ytr[:, None])
        val = r2((Kva @ alpha)[:, 0], u[va.start - 1:va.stop - 1])
        if val > best:
            best, lam_best = val, lam
    mc = 0.0
    per_lag = []
    for d in range(1, T2_MAXLAG + 1):
        alpha = np.linalg.solve(K + lam_best * scale * I, u[tr.start - d:tr.stop - d][:, None])
        r2d = r2((Kte @ alpha)[:, 0], u[te.start - d:te.stop - d])
        per_lag.append(dict(arm="T2", lag=d, r2=r2d))
        mc += r2d
    return mc, per_lag, lam_best


def task_t4(W, Win, g, amp, seed=0, center=False):
    """Yanki-durum ozelligi: iki farkli baslangictan yorungeler yakinsiyor mu."""
    rng = np.random.RandomState(40000 + seed)
    u = rng.choice([-1.0, 1.0], size=T4_STEPS)
    N = W.shape[0]
    xa = np.zeros((N, 1))
    xb = rng.normal(0.0, 1.0, size=(N, 1))
    d0 = float(np.linalg.norm(xa - xb) / np.sqrt(N))
    for t in range(T4_STEPS):
        v = u[t]
        ia = amp * (Win @ np.array([[max(v, 0.0)], [max(-v, 0.0)]]))
        da = g * ((W @ xa) if W.nnz else np.zeros_like(xa))
        db = g * ((W @ xb) if W.nnz else np.zeros_like(xb))
        if center:
            da = da - da.mean(axis=0, keepdims=True)
            db = db - db.mean(axis=0, keepdims=True)
        xa = (1.0 - A_COEF) * xa + A_COEF * np.tanh(da + ia)
        xb = (1.0 - A_COEF) * xb + A_COEF * np.tanh(db + ia)
    d1 = float(np.linalg.norm(xa - xb) / np.sqrt(N))
    return dict(d0=d0, d_end=d1, ratio=d1 / max(d0, 1e-12))


def run_arm_seed(arm, seed, g, amp, center=False, do_t2=False, do_t4=False):
    rows = run_seed(arm, seed, g, amp, center)
    W = load_arm(arm)
    Win = make_win(W.shape[0], 50, np.random.RandomState(90000 + seed))
    if do_t2:
        mc, per_lag, lam = task_t2(W, Win, seed, g, amp, center)
        rows.append(dict(arm=arm, seed=seed, task="T2", acc=mc, lam=lam, n_classes=np.nan))
        for pl in per_lag:
            rows.append(dict(arm=arm, seed=seed, task="T2_lag", k=pl["lag"], acc=pl["r2"]))
    if do_t4:
        for gg in G_GRID:
            r = task_t4(W, Win, gg, amp, seed, center)
            rows.append(dict(arm=arm, seed=seed, task="T4", k=np.nan, H=gg, acc=r["d_end"],
                             val=r["ratio"]))
    path = os.path.join(OUT, "%s_seed%02d.csv" % (arm, seed))
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def pilot():
    """10 tohumluk pilot: (g, amp) yalnızca validasyonda seçilir (T1, k=10, H=0)."""
    rows = []
    for arm in ("A_gercek", "A_w0"):
        W = load_arm(arm)
        N = W.shape[0]
        for g in G_GRID:
            for amp in AMP_GRID:
                vals = []
                for seed in range(SEEDS_PILOT):
                    rng = np.random.RandomState(20000 + seed)
                    Win = make_win(N, 50, np.random.RandomState(90000 + seed))
                    P = make_sequences(TRAIN_N + VAL_N, rng, 10, 8)
                    out = simulate(W, Win, P, 10, [GAP * 9], g, amp)
                    X = out[0].T
                    y = (P.sum(1) + 10).astype(np.int64)
                    r = ridge_eval(X[:TRAIN_N], y[:TRAIN_N], X[TRAIN_N:], y[TRAIN_N:],
                                   X[:8], y[:8], np.random.RandomState(777 + seed),
                                   n_classes=21)
                    vals.append(r["val"])
                rows.append(dict(arm=arm, g=g, amp=amp, val=float(np.mean(vals)),
                                 n=len(vals)))
                log("  pilot %-9s g=%.2f amp=%.1f val=%.4f" % (arm, g, amp, rows[-1]["val"]))
    pdf = pd.DataFrame(rows)
    pdf.to_csv(os.path.join(OUT, "pilot.csv"), index=False)
    sub = pdf[pdf.arm == "A_gercek"].sort_values("val", ascending=False)
    best = sub.iloc[0]
    frozen = dict(g=float(best.g), amp=float(best.amp))
    pd.DataFrame([frozen]).to_csv(os.path.join(OUT, "frozen_config.csv"), index=False)
    log("  DONDU: g=%.2f amp=%.1f (validasyon; TEST kullanilmadi)"
        % (frozen["g"], frozen["amp"]))
    return frozen


def runall(arms, nseeds, g, amp, center=False, deep=()):
    """deep: T2/T4 de kosacak kollar. Kollar sinirli tohumla kosabilir: 'ARM:n' bicimi."""
    t00 = time.time()
    for spec in arms:
        arm, _, nn = spec.partition(":")
        n = int(nn) if nn else nseeds
        for seed in range(n):
            t0 = time.time()
            p = run_arm_seed(arm, seed, g, amp, center, do_t2=(arm in deep),
                             do_t4=(arm in deep))
            log("  %-14s seed%02d -> %s (%.0fs, toplam %.0f dk)"
                % (arm, seed, os.path.basename(p), time.time() - t0,
                   (time.time() - t00) / 60))
    log("runall bitti (%.0f dk)" % ((time.time() - t00) / 60))


def load_all():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "*_seed[0-9][0-9].csv")))
    if not fs:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)


def ci95(v):
    v = np.asarray(v, float)
    m = float(v.mean())
    sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return m, sd, 1.96 * sd / np.sqrt(max(len(v), 1))


def disjoint(a, b):
    """(ort, GA) ikilileri için ayriklik testi."""
    return (a[0] + a[1] < b[0] - b[1]) or (b[0] + b[1] < a[0] - a[1])


def merge():
    df = load_all()
    if df.empty:
        log("merge: CSV yok")
        return None, None
    t1 = df[df.task == "T1"].copy()
    rows = []
    for (arm, k, H), sub in t1.groupby(["arm", "k", "H"]):
        m, sd, c = ci95(sub.acc.values)
        rows.append(dict(arm=arm, k=int(k), H=int(H), mean=m, std=sd, ci95=c, n=len(sub),
                         chance=float(sub.chance.mean())))
    agg = pd.DataFrame(rows)
    agg.to_csv(os.path.join(OUT, "summary_T1.csv"), index=False)
    log("\n=== T1 OZET (ort +- sd, %%95 GA) — k=10 satirlari ===")
    for arm in agg.arm.unique():
        s = agg[(agg.arm == arm) & (agg.k == 10)].sort_values("H")
        log("  %-14s " % arm + " | ".join(
            "H%-2d: %.3f+-%.3f" % (r.H, r["mean"], r.ci95) for _, r in s.iterrows()))

    def cell(arm, k, H):
        s = agg[(agg.arm == arm) & (agg.k == k) & (agg.H == H)]
        return None if len(s) == 0 else (float(s["mean"].iloc[0]), float(s.ci95.iloc[0]))

    res = {}
    log("\n=== BASARI OLCUTLERI (T1) ===")
    for H in H_GRID:
        c1, c5 = cell("A_gercek", 10, H), cell("A_w0", 10, H)
        if c1 is None or c5 is None:
            continue
        ok = bool(c1[0] >= 0.90 and disjoint(c1, c5))
        res["k10_H%d" % H] = ok
        log("  k=10 H=%-2d: A_gercek %.3f+-%.3f | W=0 %.3f+-%.3f | GA ayrik=%s -> %s"
            % (H, c1[0], c1[1], c5[0], c5[1], disjoint(c1, c5),
               "GECTI" if ok else "GECMEDI"))
    res["tasima_k10_H10"] = bool(res.get("k10_H10", False))
    for arm in ("A_derece", "A_agirlik", "A_er"):
        c = cell(arm, 10, 10)
        if c is None:
            continue
        log("  k=10 H=10: %-10s %.3f+-%.3f | A_gercekten ayrik=%s"
            % (arm, c[0], c[1], disjoint(cell("A_gercek", 10, 10), c)))
    s = agg[(agg.arm == "A_gercek")].sort_values(["k", "H"])
    below = s[s["mean"] < 0.90]
    ml = None if len(below) == 0 else (int(below.k.iloc[0]), int(below.H.iloc[0]))
    res["bellek_uzunlugu"] = str(ml)
    log("  bellek uzunlugu (ilk <0.90): %s" % (ml,))
    res["merkezlemesiz"] = True
    return agg, res


def report_tasks(df):
    log("\n=== T3 EKSTRAPOLASYON (hedef |s|>6; skaler regresyon-yuvarlama) ===")
    t3 = df[df.task == "T3"]
    if len(t3):
        for s, sub in t3.groupby("target"):
            log("  hedef s=%-2d: kesin %.3f | tol(+/-1) %.3f | oge=%d (%d tohum x %d dizi)"
                % (s, sub.acc.mean(), sub.tol.mean(), len(sub) * T3_PER_TARGET, len(sub),
                   T3_PER_TARGET))
        log("  ORTALAMA: kesin %.3f | tol %.3f | toplam oge=%d | sans=%.2f -> %s"
            % (t3.acc.mean(), t3.tol.mean(), len(t3) * T3_PER_TARGET, 0.25,
               "SANS USTU" if t3.acc.mean() > 0.30 else "sans duzeyi"))
    ex = df[df.task == "T3_x0"]
    if len(ex):
        log("  gorulmemis baslangic durumu (s=8): kesin %.3f | tol %.3f"
            % (ex.acc.mean(), ex.tol.mean()))
    log("\n=== T2 (Jaeger MC, gecikme 1..60) ===")
    t2 = df[df.task == "T2"]
    for arm, sub in t2.groupby("arm"):
        m, sd, c = ci95(sub.acc.values)
        log("  %-14s MC=%.2f +- %.2f (sd %.2f)" % (arm, m, c, sd))
    log("\n=== T4 (yanki-durum; d_end -> 0 yakinsama; g taramasi) ===")
    t4 = df[df.task == "T4"]
    for arm, sub in t4.groupby("arm"):
        log("  %-14s d_end ort=%.4f (min %.4f, max %.4f)"
            % (arm, sub.acc.mean(), sub.acc.min(), sub.acc.max()))
    log("\n=== TANILAR (k=10, H=0) ===")
    dg = df[df.task == "diag"]
    for arm, sub in dg.groupby("arm"):
        log("  %-14s doygun=%.4f aktivite=%.4f aktif_oran=%.3f katilim_orani=%.1f"
            % (arm, sub.sat.mean(), sub.activity.mean(), sub.active_frac.mean(),
               sub.participation_ratio.mean()))


def hypotheses(agg, df):
    """H7.1-H7.6: eslesmis farklar + Holm; GA ayriklik kurali da raporlanir."""
    from scipy import stats

    def per_seed(arm, k, H):
        s = df[(df.task == "T1") & (df.arm == arm) & (df.k == k) & (df.H == H)]
        return s.set_index("seed").acc.sort_index()

    tests = []
    ref = per_seed("A_gercek", 10, 10)
    for arm in ("A_w0", "A_derece", "A_agirlik", "A_er", "A_isaretperm", "A_dengeli"):
        o = per_seed(arm, 10, 10)
        common = ref.index.intersection(o.index)
        if len(common) < 3:
            continue
        rv, ov = ref.loc[common].values, o.loc[common].values
        t = stats.ttest_rel(rv, ov)
        tests.append(dict(test="A_gercek vs %s (k10,H10)" % arm, diff=float(np.mean(rv - ov)),
                          p_raw=float(t.pvalue), n=len(common)))
    if tests:
        ps = np.array([t["p_raw"] for t in tests])
        order = np.argsort(ps)
        adj = np.empty(len(ps))
        prev = 0.0
        for rank, i in enumerate(order):
            prev = max(prev, min(1.0, (len(ps) - rank) * ps[i]))
            adj[i] = prev
        for t, a in zip(tests, adj):
            t["p_holm"] = float(a)
        log("\n=== HIPOTEZLER (eslesmis t-testi; Holm m=%d) ===" % len(tests))
        for t in sorted(tests, key=lambda x: x["p_raw"]):
            log("  %-32s fark=%+.4f p_ham=%.4f p_holm=%.4f -> %s"
                % (t["test"], t["diff"], t["p_raw"], t["p_holm"],
                   "AYRISIR" if t["p_holm"] < 0.05 else "ayrisamaz"))
        pd.DataFrame(tests).to_csv(os.path.join(OUT, "hypotheses.csv"), index=False)
    # H7.4 monotonluk (k ve H)
    s = agg[agg.arm == "A_gercek"]
    for H in H_GRID:
        v = s[s.H == H].sort_values("k")["mean"].values
        mono = bool(all(v[i + 1] <= v[i] + 1e-12 for i in range(len(v) - 1)))
        log("  H7.4 (H=%-2d) k boyunca degerler %s -> monoton_azalan=%s"
            % (H, np.round(v, 3), mono))
    for k in K_GRID:
        v = s[s.k == k].sort_values("H")["mean"].values
        mono = bool(all(v[i + 1] <= v[i] + 1e-12 for i in range(len(v) - 1)))
        log("  H7.4 (k=%-2d) H boyunca degerler %s -> monoton_azalan=%s"
            % (k, np.round(v, 3), mono))
    # H7.6 A vs B (MB; 15 tohum) - k=10, H=10
    b = per_seed("B_gercek", 10, 10)
    if len(b):
        t = stats.ttest_ind(ref.values, b.values, equal_var=False)
        log("  H7.6 (yon yok): A_gercek ort=%.3f | B_MB ort=%.3f | fark=%+.3f p=%.4f "
            "(n_A=%d, n_B=%d)"
            % (ref.mean(), b.mean(), ref.mean() - b.mean(), t.pvalue, len(ref), len(b)))


def main():
    a = sys.argv[1:]
    if not a:
        log("kullanim: build | pilot | runall <nseeds> <kollar...> | run <kol> <tohum> <g> <amp> "
            "| merge")
        return
    cmd = a[0]
    if cmd == "build":
        build_all()
    elif cmd == "pilot":
        pilot()
    elif cmd == "runall":
        frozen = pd.read_csv(os.path.join(OUT, "frozen_config.csv")).iloc[0]
        runall(list(a[2:]), int(a[1]), float(frozen.g), float(frozen.amp),
               deep=("A_gercek", "A_w0", "B_gercek"))
    elif cmd == "run":
        run_arm_seed(a[1], int(a[2]), float(a[3]), float(a[4]), do_t2=True)
    elif cmd == "merge":
        agg, res = merge()
        if agg is not None:
            df = load_all()
            report_tasks(df)
            hypotheses(agg, df)
    else:
        log("bilinmeyen komut: %s" % cmd)


if __name__ == "__main__":
    main()

