"""
numcog/reservoir_fair.py — FAZ 7-2: ADİL REJİM TESTİ (kol başına g) + SPEKTRUM TANISI.

Ön-kayıt: HIPOTEZLER.md "Faz 7-2 ek ön-kayıt" (commit `137b034`, ÖLÇÜMDEN ÖNCE).
**TASARIM DEĞİŞİKLİĞİ** — 7-1 sonuçları görüldükten sonra yazıldı (bkz. ön-kayıt §TASARIM DEĞİŞİKLİĞİ).
Faz 0–7-1 dosyaları/sonuçları DEĞİŞTİRİLMEZ; bu modül `results_p7_1/` dizinine **YAZMAZ**.
Çıktı: `results_p7_2/`. float64. Seyrek W × yoğun durum matrisi. Tohum başına ayrı CSV.

CLI: spec | pilot | runall <nseeds> <kollar...> | merge
"""
from __future__ import annotations
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse import csgraph
from scipy.sparse import linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import reservoir_run as R          # YALNIZCA saf yardımcılar; 7-1 çıktılarına yazılmaz

OUT = os.path.join(HERE, "results_p7_2")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")
RAW_NPZ = os.path.join(OUT, "arms_raw_cache.npz")

ARMS = ("A_gercek", "A_derece", "A_er", "A_w0")
DEEP = ("A_gercek", "A_w0")                 # T2 yalnızca bunlarda
K_GRID = (2, 4, 6, 8, 10)
H_GRID = (0, 10, 20)
G_GRID7 = (0.8, 1.3, 2.0, 3.0, 5.0, 8.0, 13.0, 20.0, 40.0)
AMP_GRID = (0.5, 1.0)
TRAIN_N, VAL_N, TEST_N = 300, 120, 120
SEEDS_PILOT = 10
SEEDS_MAIN = 20
CRIT_K, CRIT_H = 6, 10                      # Adım 1 ana ölçüt
TIE_K, TIE_H = 4, 10                        # basamak 2
TIE_TOL = 1e-9
G_EDGE = (0.8, 40.0)
NEIG = 50
ARPACK_MAXITER = 5000
SLOW_FRAC = 0.90
T2_LEN, T2_MAXLAG = 2000, 40
N_IN = 50
G71, AMP71 = 1.30, 0.5                      # 7-1 donmuş değerleri (aktivite yeniden üretimi)
G71_ACTIVE = {"A_gercek": 0.024, "A_derece": 0.651, "A_er": 0.931, "A_w0": 0.024}


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def signed_raw(rid, r, c, mag, s_pre):
    """Ham (normalize edilmemiş) işaretli ağırlıklı W; Dale; imzasız pre-nöron kenarı hariç."""
    W, _ = R.signed_matrix(rid, r, c, mag, None, sign_override=s_pre)
    return W


def build_raw_arms():
    """7-1 ile AYNI kurulum tohumlarını (RandomState(7001)) kullanarak 4 kolu ham hâlde kurar."""
    sign_map = R.load_signs()
    rid, r, c, w = R.build_subnet("A")
    N = int(max(r.max(), c.max())) + 1
    s_pre = np.array([sign_map.get(int(x), np.nan) for x in rid])
    rng = np.random.RandomState(7001)       # 7-1 build_all ile AYNI sıra
    raw = {}
    raw["A_gercek"] = signed_raw(rid, r, c, np.abs(w), s_pre)
    R2, C2 = R.swap_edges(r, c, 10 * len(r), rng, N)
    mg = np.abs(w).copy(); rng.shuffle(mg)
    raw["A_derece"] = signed_raw(rid, R2, C2, mg, s_pre)
    mg2 = np.abs(w).copy(); rng.shuffle(mg2)          # 7-1'de A_agirlik: RNG sırası korunur
    E = len(r)
    ne = int(E * 1.05)
    rr = rng.randint(0, N, size=ne)
    cc = rng.randint(0, N, size=ne)
    keep = rr != cc
    rr, cc = rr[keep], cc[keep]
    pp, inv = np.unique(np.stack([rr, cc], 1), axis=0, return_inverse=True)
    rr, cc = pp[:, 0], pp[:, 1]
    mg3 = rng.choice(np.abs(w), size=len(rr), replace=True)
    raw["A_er"] = signed_raw(rid, rr, cc, mg3, s_pre)
    raw["A_w0"] = sp.csr_matrix((N, N))
    rho, norm, meta = {}, {}, []
    for name in ARMS:
        W = raw[name].tocsr()
        W.sort_indices()
        rho[name] = R.rho_power(W) if W.nnz else 0.0
        norm[name] = (W * (1.0 / rho[name])) if rho[name] > 0 else W
        meta.append(dict(arm=name, N=N, E=int(W.nnz), rho_raw=rho[name],
                         pos=int((W.data > 0).sum()), neg=int((W.data < 0).sum())))
        log("  %-10s N=%-5d E=%-7d rho_raw=%.3f  (7-1 kontrolu)"
            % (name, N, W.nnz, rho[name]))
    pd.DataFrame(meta).to_csv(os.path.join(OUT, "arms_raw_meta.csv"), index=False)
    out = {}
    for name in ARMS:
        for tag, W in (("raw", raw[name]), ("norm", norm[name])):
            out["%s__%s__data" % (name, tag)] = W.data.astype(np.float64)
            out["%s__%s__indices" % (name, tag)] = W.indices.astype(np.int32)
            out["%s__%s__indptr" % (name, tag)] = W.indptr.astype(np.int64)
    out["shape"] = np.array([N, N], dtype=np.int64)
    np.savez_compressed(RAW_NPZ, **out)
    log("ham+normalize kollar yazıldı: %s (%.1f MB)" % (RAW_NPZ, os.path.getsize(RAW_NPZ) / 1e6))
    return norm, meta


def load_arm(name, kind="norm"):
    d = np.load(RAW_NPZ)
    shape = tuple(int(x) for x in d["shape"])
    return sp.csr_matrix((d["%s__%s__data" % (name, kind)],
                          d["%s__%s__indices" % (name, kind)],
                          d["%s__%s__indptr" % (name, kind)]), shape=shape)


def eigs_diag(W, tag, k=NEIG):
    """ARPACK ile en büyük ~k özdeğer; yakınsamazsa uyarı + 'spektrum eksik' işareti + DEVAM."""
    if W.nnz == 0:
        return (dict(scope=tag, n=int(W.shape[0]), nnz=0, rho=0.0, max_real=0.0,
                     slow_modes=0, converged=False, note="bos matris (W=0)"),
                np.zeros(0, complex))
    try:
        vals, _ = spla.eigs(W.astype(np.float64), k=min(k, W.shape[0] - 2), which="LM",
                            maxiter=ARPACK_MAXITER)
        note = ""
    except Exception as exc:                                   # yakınsamazsa devam
        log("  !! ARPACK yakınsamadı (%s): %s -> 'spektrum eksik/yakınsamadı'"
            % (tag, type(exc).__name__))
        return (dict(scope=tag, n=int(W.shape[0]), nnz=int(W.nnz), rho=np.nan,
                     max_real=np.nan, slow_modes=np.nan, converged=False,
                     note="spektrum eksik/yakınsamadı"), np.zeros(0, complex))
    absv = np.abs(vals)
    rho = float(absv.max())
    slow = int((absv / rho >= SLOW_FRAC).sum()) if rho > 0 else 0
    return (dict(scope=tag, n=int(W.shape[0]), nnz=int(W.nnz), rho=rho,
                 max_real=float(vals.real.max()), slow_modes=slow, converged=True,
                 note=note), vals)


def spec():
    """Adım 0: spektrum + izole hücre + en büyük GB bileşen + aktivite yeniden üretimi."""
    if not os.path.exists(RAW_NPZ):
        build_raw_arms()
    log("\n=== ADIM 0: SPEKTRUM TANISI (ham W, normalizasyondan ÖNCE; ARPACK k=%d) ===" % NEIG)
    rows, eig_rows = [], []
    for name in ARMS:
        W = load_arm(name, "raw")
        m, vals = eigs_diag(W, name)
        B = (W != 0).astype(np.int8)
        deg = np.asarray(B.sum(axis=0)).ravel() + np.asarray(B.sum(axis=1)).ravel()
        n_iso = int((deg == 0).sum())
        n_comp, lab = csgraph.connected_components(B, directed=True, connection="strong")
        sizes = np.bincount(lab)
        idx = np.where(lab == int(sizes.argmax()))[0]
        m.update(arm=name, n_isolated=n_iso, n_components=int(n_comp), biggest_scc=int(len(idx)))
        rows.append(m)
        for i, v in enumerate(np.sort_complex(vals)[::-1]):
            eig_rows.append(dict(arm=name, scope=name, rank=i + 1, re=float(v.real),
                                 im=float(v.imag), abs=float(abs(v))))
        log("  %-10s rho=%.2f max_real=%.1f yavas_mod(|l|/rho>=%.2f)=%d | izole_hucre=%d "
            "GB_bilesen=%d en_buyuk_GB=%d/%d"
            % (name, m["rho"], m["max_real"], SLOW_FRAC, m["slow_modes"], n_iso, n_comp,
               len(idx), W.shape[0]))
        if 0 < len(idx) < W.shape[0]:
            sub = W[idx][:, idx].tocsr()
            sub.sort_indices()
            m2, vals2 = eigs_diag(sub, name + "_SCC")
            m2.update(arm=name, n_isolated=n_iso, n_components=int(n_comp),
                      biggest_scc=int(len(idx)))
            rows.append(m2)
            for i, v in enumerate(np.sort_complex(vals2)[::-1]):
                eig_rows.append(dict(arm=name, scope=name + "_SCC", rank=i + 1,
                                     re=float(v.real), im=float(v.imag), abs=float(abs(v))))
            log("  %-10s [en büyük GB, N=%d] rho=%.2f max_real=%.1f yavas_mod=%d"
                % (name, len(idx), m2["rho"], m2["max_real"], m2["slow_modes"]))
        else:
            log("  %-10s tek parça (en büyük GB = tümü) -> SCC tekrarı gerekmedi" % name)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "spec_summary.csv"), index=False)
    pd.DataFrame(eig_rows).to_csv(os.path.join(OUT, "spec_eigs.csv"), index=False)
    log("\n  Aktivite yeniden üretimi (7-1 donmuş g=%.2f, amp=%.1f; dizi=%d, k=10 H=0, tohum 0):"
        % (G71, AMP71, TRAIN_N + VAL_N + TEST_N))
    rng = np.random.RandomState(20000)
    P = R.make_sequences(TRAIN_N + VAL_N + TEST_N, rng, 10, 8)
    N = load_arm("A_gercek").shape[0]
    Win = R.make_win(N, N_IN, np.random.RandomState(90000))
    act_rows = []
    for name in ARMS:
        W = load_arm(name, "norm")
        out = R.simulate(W, Win, P, 10, [R.GAP * 9], G71, AMP71)
        X = out[0].T
        act = float(np.mean(np.abs(X).max(axis=0) > 0.1))
        sat = float(np.mean(np.abs(X) > 0.9))
        ref = G71_ACTIVE[name]
        act_rows.append(dict(arm=name, scope="activity_g1.30", active_frac=act, sat=sat,
                             ref_7_1=ref, consistent=bool(abs(act - ref) < 0.05)))
        log("  %-10s aktif_oran=%.3f (7-1: %.3f -> tutarlı=%s) doygunluk=%.4f"
            % (name, act, ref, abs(act - ref) < 0.05, sat))
    pd.DataFrame(act_rows).to_csv(os.path.join(OUT, "activity_g130.csv"), index=False)


def ridge_fit(Xtr, ytr, Xva, yva, rng, scalar=False, n_classes=None):
    """Dual (kernel) ridge; λ yalnızca validasyonda. Döner (val_acc, val_mse, lam)."""
    sd = float(Xtr.std())
    Xtr = Xtr + rng.normal(0.0, R.NOISE_REL * sd, Xtr.shape)
    Xva = Xva + rng.normal(0.0, R.NOISE_REL * sd, Xva.shape)
    K = Xtr @ Xtr.T
    scale = float(np.mean(np.diag(K))) or 1.0
    if scalar:
        T = ytr.astype(np.float64)[:, None]
    else:
        T = np.zeros((len(ytr), n_classes))
        T[np.arange(len(ytr)), ytr] = 1.0
    Kva = Xva @ Xtr.T
    I = np.eye(len(K))
    if scalar:
        best = (np.inf, np.inf, np.nan)            # mse, acc, lam
        for lam in R.LAMBDA_REL:
            pv = (Kva @ np.linalg.solve(K + lam * scale * I, T))[:, 0]
            mse = float(np.mean((pv - yva) ** 2))
            if mse < best[0]:
                best = (mse, float(np.mean(np.round(pv) == yva)), lam)
        return best[1], best[0], best[2]
    best = (-1.0, np.nan, np.nan)
    for lam in R.LAMBDA_REL:
        pv = Kva @ np.linalg.solve(K + lam * scale * I, T)
        acc = float(np.mean(pv.argmax(1) == yva))
        if acc > best[0]:
            best = (acc, np.nan, lam)
    return best[0], best[1], best[2]


def pilot_data(N):
    """7-1 ile aynı tohumlu diziler/girişler (yalnızca eğitim+doğrulama)."""
    out = []
    for seed in range(SEEDS_PILOT):
        rng = np.random.RandomState(20000 + seed)
        P = R.make_sequences(TRAIN_N + VAL_N, rng, 10, 8)
        Win = R.make_win(N, N_IN, np.random.RandomState(90000 + seed))
        out.append((seed, P, Win))
    return out


def acc_at(W, P, Win, k, H, g, amp, seed, scalar=False):
    """Bir (k,H) koşulunda doğrulama kesin doğruluğu (+ skaler MSE)."""
    rt = R.GAP * (k - 1) + H
    out = R.simulate(W, Win, P, k, [rt], g, amp)
    X = out[0].T
    y = (P[:, :k].sum(axis=1) + k).astype(np.int64)
    acc, mse, lam = ridge_fit(X[:TRAIN_N], y[:TRAIN_N], X[TRAIN_N:], y[TRAIN_N:],
                              np.random.RandomState(777 + seed), scalar=scalar,
                              n_classes=None if scalar else 2 * k + 1)
    return acc, mse, lam


def pilot():
    """Adım 1: kol başına (g, amp) seçimi — YALNIZCA doğrulama; kademeli tie-break (1-4)."""
    if not os.path.exists(RAW_NPZ):
        build_raw_arms()
    log("\n=== ADIM 1: KOL BAŞINA (g, amp) SEÇİMİ (pilot, %d tohum, YALNIZCA doğrulama; "
        "test kullanılmaz) ===" % SEEDS_PILOT)
    rows, summary = [], []
    for arm in ARMS:
        W = load_arm(arm, "norm")
        data = pilot_data(W.shape[0])
        table = {}
        for g in G_GRID7:
            for amp in AMP_GRID:
                accs = [acc_at(W, P, Win, CRIT_K, CRIT_H, g, amp, seed)[0]
                        for (seed, P, Win) in data]
                table[(g, amp)] = float(np.mean(accs))
                rows.append(dict(arm=arm, g=g, amp=amp, crit_k=CRIT_K, crit_h=CRIT_H,
                                 val_acc=table[(g, amp)], n=len(accs)))
                log("  %-10s g=%-5.1f amp=%.1f  k=%d H=%d doğrulama=%.4f"
                    % (arm, g, amp, CRIT_K, CRIT_H, table[(g, amp)]))
        best = max(table.values())
        cand = sorted([k for k, v in table.items() if best - v < TIE_TOL])
        rung, note = 1, ""
        if len(cand) > 1:
            log("  %-10s BASAMAK 1 EŞİTLİK: %d aday %s" % (arm, len(cand), cand))
            tie = {}
            for (g, amp) in cand:
                accs = [acc_at(W, P, Win, TIE_K, TIE_H, g, amp, seed)[0]
                        for (seed, P, Win) in data]
                tie[(g, amp)] = float(np.mean(accs))
                rows.append(dict(arm=arm, g=g, amp=amp, crit_k=TIE_K, crit_h=TIE_H,
                                 val_acc=tie[(g, amp)], tie_rung=2))
            cand = sorted([k for k, v in tie.items() if max(tie.values()) - v < TIE_TOL])
            rung = 2
            if len(cand) > 1:
                log("  %-10s BASAMAK 2 EŞİTLİK: %d aday" % (arm, len(cand)))
                mse = {}
                for (g, amp) in cand:
                    vals = [acc_at(W, P, Win, CRIT_K, CRIT_H, g, amp, seed, scalar=True)[1]
                            for (seed, P, Win) in data]
                    mse[(g, amp)] = float(np.mean(vals))
                    rows.append(dict(arm=arm, g=g, amp=amp, crit_mse=mse[(g, amp)],
                                     tie_rung=3))
                cand = sorted([k for k, v in mse.items() if v - min(mse.values()) < TIE_TOL])
                rung = 3
                if len(cand) > 1:
                    rung = 4
                    log("  %-10s BASAMAK 3 EŞİTLİK: %d aday -> basamak 4 (en yüksek g)"
                        % (arm, len(cand)))
                    cand = [max(cand, key=lambda t: t[0])]
        if len(cand) > 1:
            note = "seçim ölçütü ayırt edici değil"
            cand = [max(cand, key=lambda t: t[0])]
        g_sel, amp_sel = cand[0]
        edge = g_sel in G_EDGE
        summary.append(dict(arm=arm, g=g_sel, amp=amp_sel, tie_rung=rung,
                            grid_edge=bool(edge), val_acc_at_sel=table[(g_sel, amp_sel)],
                            note=note))
        log("  %-10s SEÇİLDİ: g=%.1f amp=%.1f (tie-break basamağı %d%s)%s"
            % (arm, g_sel, amp_sel, rung, ", IZGARA SINIRI" if edge else "", note))
        # tanı: seçilen g'de aktif oran/doygunluk (seçim ölçütü DEĞİL; tohum 0, k=10 H=0)
        P54 = R.make_sequences(TRAIN_N + VAL_N + TEST_N, np.random.RandomState(20000), 10, 8)
        Win0 = R.make_win(W.shape[0], N_IN, np.random.RandomState(90000))
        out = R.simulate(W, Win0, P54, 10, [R.GAP * 9], g_sel, amp_sel)
        X = out[0].T
        act = float(np.mean(np.abs(X).max(axis=0) > 0.1))
        sat = float(np.mean(np.abs(X) > 0.9))
        summary[-1].update(active_frac=act, sat=sat)
        log("  %-10s tanı (seçilen g'de): aktif_oran=%.3f doygunluk=%.4f" % (arm, act, sat))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "pilot_grid.csv"), index=False)
    pd.DataFrame(summary).to_csv(os.path.join(OUT, "frozen_config.csv"), index=False)
    log("  donmuş konfigürasyon -> frozen_config.csv (TIE_TOL=%g)" % TIE_TOL)
    return summary


def task_t2(W, Win, seed, g, amp):
    """Jaeger MC (gecikme 1..%d); tek akış (2000 adım); λ yalnızca validasyonda."""
    rng = np.random.RandomState(30000 + seed)
    n = T2_LEN + T2_MAXLAG + 1
    u = rng.choice([-1.0, 1.0], size=n)
    N = W.shape[0]
    X = np.zeros((N, 1))
    states = np.empty((n, N))
    for t in range(n):
        v = u[t]
        drive = (g * (W @ X)) if W.nnz else np.zeros_like(X)
        drive = drive + amp * (Win @ np.array([[max(v, 0.0)], [max(-v, 0.0)]]))
        X = (1.0 - R.A_COEF) * X + R.A_COEF * np.tanh(drive)
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
    for lam in R.LAMBDA_REL:
        alpha = np.linalg.solve(K + lam * scale * I, u[tr.start - 1:tr.stop - 1][:, None])
        val = r2((Kva @ alpha)[:, 0], u[va.start - 1:va.stop - 1])
        if val > best:
            best, lam_best = val, lam
    mc, per_lag = 0.0, []
    for d in range(1, T2_MAXLAG + 1):
        alpha = np.linalg.solve(K + lam_best * scale * I, u[tr.start - d:tr.stop - d][:, None])
        r2d = r2((Kte @ alpha)[:, 0], u[te.start - d:te.stop - d])
        per_lag.append(dict(lag=d, r2=r2d))
        mc += r2d
    return mc, per_lag, lam_best


def run_seed(arm, seed, g, amp):
    """Adım 2: bir kol × tohum için T1 (+ T2: yalnızca DEEP) + tanılar; tohum başına CSV."""
    W = load_arm(arm, "norm")
    N = W.shape[0]
    rng = np.random.RandomState(20000 + seed)
    P = R.make_sequences(TRAIN_N + VAL_N + TEST_N, rng, 10, 8)
    assert len({tuple(x) for x in P.tolist()}) == len(P), "dizi cakismasi var"
    Win = R.make_win(N, N_IN, np.random.RandomState(90000 + seed))
    rows = []
    for k in K_GRID:
        rt = [R.GAP * (k - 1) + H for H in H_GRID]
        out = R.simulate(W, Win, P, k, rt, g, amp)
        sums = P[:, :k].sum(axis=1)
        y = (sums + k).astype(np.int64)
        for hi, H in enumerate(H_GRID):
            X = out[hi].T
            r = R.ridge_eval(X[:TRAIN_N], y[:TRAIN_N], X[TRAIN_N:TRAIN_N + VAL_N],
                             y[TRAIN_N:TRAIN_N + VAL_N], X[TRAIN_N + VAL_N:],
                             y[TRAIN_N + VAL_N:], np.random.RandomState(60000 + seed * 1000
                                                                       + k * 100 + H),
                             n_classes=2 * k + 1)
            reach = np.unique(y)
            rows.append(dict(arm=arm, seed=seed, task="T1", k=k, H=H, acc=r["test"],
                             val=r["val"], lam=r["lam"], reachable=len(reach),
                             chance=1.0 / len(reach)))
            if k == 10 and H == 0:
                d = R.state_diag(X)
                rows.append(dict(arm=arm, seed=seed, task="diag", k=10, H=0, acc=np.nan, **d))
    if arm in DEEP:
        mc, per_lag, lam = task_t2(W, Win, seed, g, amp)
        rows.append(dict(arm=arm, seed=seed, task="T2", acc=mc, lam=lam))
        for pl in per_lag:
            rows.append(dict(arm=arm, seed=seed, task="T2_lag", k=pl["lag"], acc=pl["r2"]))
    path = os.path.join(OUT, "%s_seed%02d.csv" % (arm, seed))
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def runall(nseeds, arms=None):
    cfg = {r.arm: (float(r.g), float(r.amp))
           for _, r in pd.read_csv(os.path.join(OUT, "frozen_config.csv")).iterrows()}
    arms = arms or list(ARMS)
    t00 = time.time()
    for arm in arms:
        g, amp = cfg[arm]
        for seed in range(nseeds):
            t0 = time.time()
            p = run_seed(arm, seed, g, amp)
            log("  %-10s seed%02d (g=%.1f amp=%.1f) -> %s (%.0fs, toplam %.0f dk)"
                % (arm, seed, g, amp, os.path.basename(p), time.time() - t0,
                   (time.time() - t00) / 60))
    log("runall bitti (%.0f dk)" % ((time.time() - t00) / 60))


def load_all():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "*_seed[0-9][0-9].csv")))
    if not fs:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)


def merge():
    df = load_all()
    if df.empty:
        log("merge: CSV yok")
        return None
    cfg = pd.read_csv(os.path.join(OUT, "frozen_config.csv"))
    log("\n=== DONMUŞ KONFİGÜRASYON (Adım 1) ===")
    for _, r in cfg.iterrows():
        log("  %-10s g=%-5.1f amp=%.1f  tie-break basamağı=%d  ızgara_sınırı=%s  "
            "val_acc=%.4f  aktif_oran=%.3f  doygunluk=%.4f%s"
            % (r.arm, r.g, r.amp, r.tie_rung, r.grid_edge, r.val_acc_at_sel,
               r.active_frac, r.sat,
               (" | " + str(r.note)) if isinstance(r.note, str) else ""))
    t1 = df[df.task == "T1"].copy()
    rows = []
    for (arm, k, H), sub in t1.groupby(["arm", "k", "H"]):
        m, sd, c = R.ci95(sub.acc.values)
        rows.append(dict(arm=arm, k=int(k), H=int(H), mean=m, std=sd, ci95=c, n=len(sub),
                         chance=float(sub.chance.mean())))
    agg = pd.DataFrame(rows)
    agg.to_csv(os.path.join(OUT, "summary_T1.csv"), index=False)
    log("\n=== T1 DOĞRULUK-k EĞRİLERİ (ort ± %95 GA) — tabanlar: k=2→0,49 k=4→0,37 "
        "k=6→0,31 k=8→0,27 k=10→0,25 ('en sık sınıf') ===")
    for arm in agg.arm.unique():
        for H in (10, 20):
            s = agg[(agg.arm == arm) & (agg.H == H)].sort_values("k")
            log("  %-10s H=%-2d " % (arm, H) + " | ".join(
                "k%-2d: %.3f+-%.3f" % (r.k, r["mean"], r.ci95) for _, r in s.iterrows()))

    def cell(arm, k, H):
        s = agg[(agg.arm == arm) & (agg.k == k) & (agg.H == H)]
        return None if len(s) == 0 else (float(s["mean"].iloc[0]), float(s["ci95"].iloc[0]))

    log("\n=== BAŞARI ÖLÇÜTLERİ (7-1 ile AYNI; gevşetilmedi) ===")
    res = {}
    for H in H_GRID:
        c1, c5 = cell("A_gercek", 10, H), cell("A_w0", 10, H)
        if c1 is None or c5 is None:
            continue
        ok = bool(c1[0] >= 0.90 and R.disjoint(c1, c5))
        res["k10_H%d" % H] = ok
        log("  k=10 H=%-2d: A_gercek %.3f+-%.3f | A_w0 %.3f+-%.3f | GA ayrik=%s -> %s"
            % (H, c1[0], c1[1], c5[0], c5[1], R.disjoint(c1, c5),
               "GEÇTİ" if ok else "GEÇMEDİ"))
    res["tasima_k10_H10"] = bool(res.get("k10_H10", False))
    for arm in ("A_derece", "A_er"):
        c = cell(arm, 10, 10)
        c1 = cell("A_gercek", 10, 10)
        if c is None or c1 is None:
            continue
        better = bool(R.disjoint(c1, c) and c1[0] > c[0])
        log("  k=10 H=10: A_gercek %.3f+-%.3f vs %-9s %.3f+-%.3f -> A_gercek GA ayrık "
            "ÜSTÜN=%s" % (c1[0], c1[1], arm, c[0], c[1], better))
    log("\n=== BELLEK UZUNLUĞU (ilk <0,90) ===")
    mem = {}
    for arm in agg.arm.unique():
        s = agg[agg.arm == arm].sort_values(["k", "H"])
        below = s[s["mean"] < 0.90]
        mem[arm] = None if len(below) == 0 else (int(below.k.iloc[0]), int(below.H.iloc[0]))
        c2, c4 = cell(arm, 2, 10), cell(arm, 4, 10)
        log("  %-10s bellek_uzunlugu=%s | k=2 H=10: %.3f | k=4 H=10: %.3f"
            % (arm, mem[arm], c2[0] if c2 else np.nan, c4[0] if c4 else np.nan))
    return agg, res, mem, cfg, df


def hypotheses(agg, res, mem, cfg, df):
    """H7.7-H7.10 (aile: A_gercek vs {A_w0, A_derece, A_er}; Holm m=3)."""
    from scipy import stats
    sel = {r.arm: r for _, r in cfg.iterrows()}
    g7 = float(sel["A_gercek"].g)
    act7 = float(sel["A_gercek"].active_frac)
    log("\n=== HİPOTEZLER ===")
    log("  H7.7: A_gercek seçilen g=%.1f (>1,3 mü: %s) | seçilen g'de aktif_oran=%.3f "
        "(<%%10 mu: %s) -> %s"
        % (g7, g7 > 1.3, act7, act7 < 0.10,
           "DESTEK" if (g7 > 1.3 and act7 >= 0.10) else "ÇÜRÜDÜ"))

    def per_seed(arm, k, H):
        s = df[(df.task == "T1") & (df.arm == arm) & (df.k == k) & (df.H == H)]
        return s.set_index("seed").acc.sort_index()

    ref = per_seed("A_gercek", 10, 10)
    tests = []
    for arm in ("A_w0", "A_derece", "A_er"):
        o = per_seed(arm, 10, 10)
        common = ref.index.intersection(o.index)
        if len(common) < 3:
            continue
        rv, ov = ref.loc[common].values, o.loc[common].values
        t = stats.ttest_rel(rv, ov)
        tests.append(dict(test="A_gercek vs %s (k10,H10)" % arm,
                          diff=float(np.mean(rv - ov)), p_raw=float(t.pvalue),
                          n=len(common)))
    if tests:
        ps = np.array([t["p_raw"] for t in tests])
        adj = np.empty(len(ps))
        prev = 0.0
        for rank, i in enumerate(np.argsort(ps)):
            prev = max(prev, min(1.0, (len(ps) - rank) * ps[i]))
            adj[i] = prev
        for t, a in zip(tests, adj):
            t["p_holm"] = float(a)
        for t in sorted(tests, key=lambda x: x["p_raw"]):
            log("  %-30s fark=%+.4f p_ham=%.4f p_holm=%.4f -> %s"
                % (t["test"], t["diff"], t["p_raw"], t["p_holm"],
                   "AYRIŞIR" if t["p_holm"] < 0.05 else "ayrışamaz"))
        pd.DataFrame(tests).to_csv(os.path.join(OUT, "hypotheses.csv"), index=False)
        d = [t for t in tests if "A_derece" in t["test"]]
        if d:
            f = d[0]["diff"]
            log("  H7.8: (A_gercek - A_derece) 7-1'de ≈ -0.156; şimdi %+.3f | fark küçüldü mü: %s "
                "| yön hâlâ A_gercek ≤ A_derece: %s" % (f, abs(f) < 0.156, f <= 0))
    s = agg[(agg.arm == "A_gercek") & (agg.k == 10) & (agg.H == 10)]
    c10 = float(s["mean"].iloc[0]) if len(s) else np.nan
    log("  H7.9: k=10 H=10 A_gercek=%.3f (≥0,90 mı: %s) -> %s"
        % (c10, c10 >= 0.90, "ÇÜRÜDÜ" if c10 >= 0.90 else "DESTEK"))
    try:
        sp_df = pd.read_csv(os.path.join(OUT, "spec_summary.csv"))
        sm = sp_df[(sp_df.scope == sp_df.arm) & sp_df.slow_modes.notna()]
        log("\n  H7.10 (TANI, yön YOK): yavaş mod sayısı (ham W) ↔ bellek uzunluğu")
        for _, r in sm.iterrows():
            log("    %-10s yavas_mod=%s rho_raw=%.1f max_real=%.1f | bellek_uzunlugu=%s"
                % (r.arm, r.slow_modes, r.rho, r.max_real, mem.get(r.arm)))
        v = [(float(r.slow_modes), mem.get(r.arm)) for _, r in sm.iterrows()
             if mem.get(r.arm) is not None]
        if len(v) >= 3:
            from scipy.stats import spearmanr
            xs = [a for a, b in v]
            ys = [b[0] * 100 + b[1] for a, b in v]
            rho_s, p_s = spearmanr(xs, ys)
            log("    Spearman (n=%d): rho=%+.2f p=%.3f -> %s"
                % (len(v), rho_s, p_s, "ilişki var" if p_s < 0.05 else "ilişki gösterilemedi"))
    except Exception as exc:
        log("  H7.10 hesaplanamadı: %s" % exc)
    t2 = df[df.task == "T2"]
    if len(t2):
        log("\n=== T2 (Jaeger MC, gecikme 1..%d) ===" % T2_MAXLAG)
        for arm, sub in t2.groupby("arm"):
            m, sd, c = R.ci95(sub.acc.values)
            log("  %-10s MC=%.2f +- %.2f (sd %.2f) [üst sınır %d]"
                % (arm, m, c, sd, T2_MAXLAG))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "spec":
        spec()
    elif cmd == "pilot":
        pilot()
    elif cmd == "runall":
        runall(int(sys.argv[2]), sys.argv[3:] or None)
    elif cmd == "merge":
        out = merge()
        if out is not None:
            agg, res, mem, cfg, df = out
            hypotheses(agg, res, mem, cfg, df)
    else:
        log("kullanim: spec | pilot | runall <nseeds> [kollar...] | merge")


if __name__ == "__main__":
    main()
