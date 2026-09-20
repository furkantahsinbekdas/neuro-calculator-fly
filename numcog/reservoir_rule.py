"""
numcog/reservoir_rule.py — FAZ 7-3: KURAL/EKSTRAPOLASYON TESTİ (T3), 6 adımlık rejimde.

Ön-kayıt: HIPOTEZLER.md "Faz 7-3 ek ön-kayıt" (ÖLÇÜMDEN ÖNCE commit). Faz 0–7-2 dosyaları/
sonuçları DEĞİŞTİRİLMEZ; bu modül `results_p7_1/`, `results_p7_2/` dizinlerine **YAZMAZ**.
Model 7-2 ile aynı (a=0,5; tanh; işaretli W, ρ=1; I1 girişi; gürültü 1e-3×std).
**Donmuş (g, amp) 7-2'den alınır; YENİ ızgara YOK.**
Çıktı: `results_p7_3/`. float64. Tohum başına ayrı CSV.

T3'e ÖZEL SAPMA: darbeler arası aralık her darbede {4,5,6}'dan RASTGELE (jitter);
7-1/7-2'deki sabit 5 adımdan sapmadır (s=±6 için ≥50 FARKLI test öğesi üretmek için).

CLI: selftest | runall <nseeds> | merge
"""
from __future__ import annotations
import os
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import reservoir_run as R          # saf yardımcılar (load_signs, build_subnet, make_win...)
import reservoir_fair as F         # kolların (norm) yeniden kurulumu; 7-2 çıktılarına yazmaz

OUT = os.path.join(HERE, "results_p7_3")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

# --- 7-2'de DONMUŞ konfigürasyon (yeni ızgara YOK) ---
FROZEN = {"A_gercek": (40.0, 1.0), "A_derece": (20.0, 1.0),
          "A_er": (20.0, 1.0), "A_w0": (40.0, 0.5)}
FROZEN_SRC = "results_p7_2/frozen_config.csv (7-2 Adım 1; ızgara sınırı: A_gercek g=40)"
ARMS = ("A_gercek", "A_derece", "A_er", "A_w0")

K_PULSE = 6
JITTER = (4, 5, 6)
CAP = 8
H_PRIMARY = 10
H_LIST = (0, 10, 20)
EVEN_S = (-6, -4, -2, 0, 2, 4, 6)
S1_TRAIN = (-2, 0, 2)
S1_TEST_NEAR = (-4, 4)
S1_TEST_FAR = (-6, 6)
S2_TRAIN = (-4, -2, 0, 2, 4)
S2_TEST = (-6, 6)
TRAIN_N, VAL_N = 300, 150
TEST_PER_S = 60
PAT_POOL, PAT_TRAIN, PAT_VAL = 1000, 650, 50      # PAT_POOL - (PAT_TRAIN+PAT_VAL) = %30 test
PCA_COMP = 30
SEEDS_MAIN = 20
N_IN = 50


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---------------------------------------------------------------- dizi üreteci (jitter)
def n_plus(s):
    """k=6 ve net toplam s için (+1) sayısı."""
    assert (K_PULSE + s) % 2 == 0 and abs(s) <= K_PULSE, s
    return (K_PULSE + s) // 2


def gen_patterns(rng, s, n, seen):
    """s toplamı için n BENZERSİZ (işaret, jitter) örüntüsü (seen global tekillik kümesi)."""
    out = []
    while len(out) < n:
        p = n_plus(s)
        signs = np.ones(K_PULSE, np.int8)
        neg = rng.permutation(K_PULSE)[:K_PULSE - p]
        signs[neg] = -1
        jit = np.array([JITTER[rng.randint(3)] for _ in range(K_PULSE - 1)], np.int8)
        key = (tuple(signs.tolist()), tuple(jit.tolist()))
        if key in seen:
            continue
        seen.add(key)
        out.append((signs, jit))
    return out


def gen_mixed(rng, n, seen, s_values=EVEN_S, weights=None):
    """Karışık s dağılımıyla n örüntü (T3-P havuzu)."""
    sv = list(s_values)
    w = np.array(weights, float) if weights is not None else np.ones(len(sv))
    w = w / w.sum()
    out = []
    while len(out) < n:
        s = sv[rng.choice(len(sv), p=w)]
        out.extend(gen_patterns(rng, s, 1, seen))
    return out


def pulse_times(seq):
    """(işaretler, jitter) -> darbe zamanları (uzunluk k) ve son darbe zamanı."""
    signs, jit = seq
    t = [0]
    for i in range(K_PULSE - 1):
        t.append(t[-1] + int(jit[i]))
    return t


def build_U(seqs, T):
    """Girdi matrisi (2, T, B): kanal 0 = +1, kanal 1 = -1 darbeleri."""
    U = np.zeros((2, T, len(seqs)), np.float64)
    for j, seq in enumerate(seqs):
        signs, _ = seq
        for i, t in enumerate(pulse_times(seq)):
            U[0, t, j] = 1.0 if signs[i] > 0 else 0.0
            U[1, t, j] = 1.0 if signs[i] < 0 else 0.0
    return U


def simulate_jit(W, Win, seqs, H_list, g, amp):
    """Jitter'lı darbelerle toplu simülasyon. Döner (len(H_list), N, n_seq) —
    her dizi için okuma zamanı KENDİ son darbesinden +H sonradır."""
    N = W.shape[0]
    B = len(seqs)
    ends = [pulse_times(s)[-1] for s in seqs]
    T = max(e + max(H_list) for e in ends) + 1
    U = build_U(seqs, T)
    read_map = {}
    for j, e in enumerate(ends):
        for hi, H in enumerate(H_list):
            read_map.setdefault(e + H, []).append((j, hi))
    outs = np.empty((len(H_list), N, B), np.float64)
    X = np.zeros((N, B), np.float64)
    for t in range(T):
        d = (W @ X) if W.nnz else np.zeros_like(X)
        drive = g * d + amp * (Win @ U[:, t, :])
        X = (1.0 - R.A_COEF) * X + R.A_COEF * np.tanh(drive)
        for (j, hi) in read_map.get(t, ()):
            outs[hi][:, j] = X[:, j]
    return outs


def seq_signs(seqs):
    return np.array([s[0] for s in seqs], np.int8)


def seq_sums(seqs):
    return np.array([int(np.sum(s[0])) for s in seqs], np.int64)


def ridge_predict(Xtr, ytr, Xva, yva, Xte, rng, scalar=True, classes=None):
    """Dual ridge; λ YALNIZCA validasyonda. Döner (lam, val_ölçüt, tahmin_test)."""
    sd = float(Xtr.std())
    Xtr = Xtr + rng.normal(0.0, R.NOISE_REL * sd, Xtr.shape)
    Xva = Xva + rng.normal(0.0, R.NOISE_REL * sd, Xva.shape)
    K = Xtr @ Xtr.T
    scale = float(np.mean(np.diag(K))) or 1.0
    if scalar:
        T = ytr.astype(np.float64)[:, None]
    else:
        T = np.zeros((len(ytr), len(classes)))
        idx = {c: i for i, c in enumerate(classes)}
        T[np.arange(len(ytr)), [idx[int(v)] for v in ytr]] = 1.0
    Kva, Kte = Xva @ Xtr.T, Xte @ Xtr.T
    I = np.eye(len(K))
    best = None
    for lam in R.LAMBDA_REL:
        alpha = np.linalg.solve(K + lam * scale * I, T)
        pv = Kva @ alpha
        if scalar:
            crit = float(np.mean((pv[:, 0] - yva) ** 2))          # MSE (en düşük iyi)
            if best is None or crit < best[0]:
                best = (crit, lam, alpha)
        else:
            crit = -float(np.mean([classes[int(np.argmax(p))] == int(y)
                                   for p, y in zip(pv, yva)]))
            if best is None or crit < best[0]:
                best = (crit, lam, alpha)
    crit, lam, alpha = best
    pt = Kte @ alpha
    if scalar:
        return lam, float(crit), pt[:, 0]
    idx = np.array([classes[int(np.argmax(p))] for p in pt])
    return lam, float(-crit), idx


def pca_residual(Xtr, Xte, k=PCA_COMP):
    """Xte durumlarının, Xtr'nin PCA alt uzayına göreli artık uzaklığı (ölçek-bağımsız)."""
    mu = Xtr.mean(axis=0, keepdims=True)
    Ztr = Xtr - mu
    _, _, Vt = np.linalg.svd(Ztr, full_matrices=False)
    V = Vt[:k]
    Z = Xte - mu
    res = Z - (Z @ V.T) @ V
    den = np.linalg.norm(Z, axis=1)
    return np.linalg.norm(res, axis=1) / (den + 1e-30)


def stuck_frac(pred, s_train_max):
    """Tahminlerin eğitim aralığının UCUNDA takılı kalma oranı (verilen öğeler üzerinde)."""
    pred = np.asarray(pred, float)
    if len(pred) == 0:
        return np.nan
    return float(np.mean(np.abs(pred) <= s_train_max))


def make_split(rng, s_train, n_train, n_val, test_s, n_test):
    """(eğitim, val, test listeleri, hedef s dizisi) — örüntüler GLOBAL BENZERSİZ."""
    seen = set()
    per = max(n_train // len(s_train), 1)
    tr = []
    for s in s_train:
        tr += gen_patterns(rng, s, per, seen)
    tr = tr[:n_train]
    perv = max(n_val // len(s_train), 1)
    va = []
    for s in s_train:
        va += gen_patterns(rng, s, perv, seen)
    va = va[:n_val]
    te, tg = [], []
    for s in test_s:
        got = gen_patterns(rng, s, n_test, seen)
        te += got
        tg += [s] * len(got)
    return tr, va, te, np.array(tg, np.int64)


def eval_condition(arm, seed, split, H, train_H, Xtr, ytr, Xva, yva, Xte, tg, smax):
    """Bir (bölme, H) koşulu için okumalar + tanılar → satır listesi."""
    rng = np.random.RandomState(70000 + seed * 100 + int(H) * 7 + (0 if split == "S1" else
                                                                  1 if split == "S2" else 2))
    lam, vmse, pred = ridge_predict(Xtr, ytr, Xva, yva, Xte, rng, scalar=True)
    pred_even = 2.0 * np.round(pred / 2.0)                      # en yakın ÇİFT tam sayı
    classes = sorted(set(ytr.tolist()))
    lam2, vacc, nom = ridge_predict(Xtr, ytr, Xva, yva, Xte, rng, scalar=False,
                                    classes=classes)
    prv = pca_residual(Xtr, Xte)
    sat = float(np.mean(np.abs(Xte) > 0.9))
    act = float(np.mean(np.abs(Xte).max(axis=0) > 0.1))
    rows = []

    def pack(ts, m):
        p, q = pred_even[m], tg[m]
        slope = np.nan
        if len(q) > 1 and float(np.ptp(q)) > 0:      # sabit hedefte eğim tanımsız (tekil sistem)
            slope = float(np.polyfit(q.astype(float), pred[m], 1)[0])
        return dict(arm=arm, seed=seed, split=split, H=int(H), train_H=int(train_H),
                    target_s=ts, n=int(m.sum()),
                    acc_exact=float(np.mean(q == p)),
                    acc_within2=float(np.mean(np.abs(q - p) <= 2)),
                    acc_nominal=float(np.mean(nom[m] == q)),
                    pred_mean=float(np.mean(pred[m])),
                    pred_slope=slope,
                    stuck=stuck_frac(pred[m], smax) if np.isfinite(smax) else np.nan,
                    pca_res=float(np.mean(prv[m])), sat=sat, active=act, lam=float(lam),
                    lam_nom=float(lam2), val_mse=float(vmse), val_acc_nom=float(vacc))

    rows.append(pack("ALL", np.ones(len(tg), bool)))
    for s in sorted(set(tg.tolist())):
        rows.append(pack(int(s), tg == s))
    return rows


def run_seed(arm, seed):
    """Faz 7-3: T3-S1, T3-S2, T3-P, T3-H (okuma aktarımı) — tohum başına CSV."""
    g, amp = FROZEN[arm]
    W = F.load_arm(arm, "norm")
    N = W.shape[0]
    rng = np.random.RandomState(20000 + seed)
    Win = R.make_win(N, N_IN, np.random.RandomState(90000 + seed))
    rows = []
    # --- S1 / S2
    sets = {}
    tr, va, te, tg = make_split(rng, S1_TRAIN, TRAIN_N, VAL_N,
                                S1_TEST_NEAR + S1_TEST_FAR, TEST_PER_S)
    sets["S1"] = (tr, va, te, tg, 2)
    tr, va, te, tg = make_split(rng, S2_TRAIN, TRAIN_N, VAL_N, S2_TEST, TEST_PER_S)
    sets["S2"] = (tr, va, te, tg, 4)
    for name in ("S1", "S2"):
        tr, va, te, tg, smax = sets[name]
        seqs = tr + va + te
        assert len({(tuple(s[0].tolist()), tuple(s[1].tolist())) for s in seqs}) == len(seqs)
        out = simulate_jit(W, Win, seqs, H_LIST, g, amp)
        ntr, nva = len(tr), len(va)
        Xall = [out[hi].T for hi in range(len(H_LIST))]
        for hi, H in enumerate(H_LIST):
            X = Xall[hi]
            rows += eval_condition(arm, seed, name, H, H, X[:ntr], seq_sums(tr),
                                   X[ntr:ntr + nva], seq_sums(va), X[ntr + nva:], tg, smax)
        # T3-H (KEŞİFSEL): okuma H=10'da eğitilir, H=0 ve H=20'de test edilir
        h10 = H_LIST.index(H_PRIMARY)
        for H in H_LIST:
            if H == H_PRIMARY:
                continue
            rows += eval_condition(arm, seed, "H_xfer", H, H_PRIMARY,
                                   Xall[h10][:ntr], seq_sums(tr),
                                   Xall[h10][ntr:ntr + nva], seq_sums(va),
                                   Xall[H_LIST.index(H)][ntr + nva:], tg, smax)
    # --- P (örüntü tutma; İNTERPOLASYON kontrolü)
    pool = gen_mixed(rng, PAT_POOL, set())
    rng.shuffle(pool)
    trP = pool[:PAT_TRAIN]
    vaP = pool[PAT_TRAIN:PAT_TRAIN + PAT_VAL]
    teP = pool[PAT_TRAIN + PAT_VAL:]
    tgP = seq_sums(teP)
    seqs = trP + vaP + teP
    out = simulate_jit(W, Win, seqs, H_LIST, g, amp)
    for hi, H in enumerate(H_LIST):
        X = out[hi].T
        rows += eval_condition(arm, seed, "P", H, H, X[:PAT_TRAIN], seq_sums(trP),
                               X[PAT_TRAIN:PAT_TRAIN + PAT_VAL], seq_sums(vaP),
                               X[PAT_TRAIN + PAT_VAL:], tgP, np.nan)
    path = os.path.join(OUT, "%s_seed%02d.csv" % (arm, seed))
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def runall(nseeds, arms=None):
    arms = arms or list(ARMS)
    t00 = time.time()
    for arm in arms:
        for seed in range(nseeds):
            t0 = time.time()
            p = run_seed(arm, seed)
            log("  %-10s seed%02d (g=%.1f amp=%.1f) -> %s (%.0fs, toplam %.0f dk)"
                % (arm, seed, FROZEN[arm][0], FROZEN[arm][1], os.path.basename(p),
                   time.time() - t0, (time.time() - t00) / 60))
    log("runall bitti (%.0f dk)" % ((time.time() - t00) / 60))


def design_baselines():
    """ÖLÇÜMDEN ÖNCE tasarım tabanları: şans + 'en sık sınıf' (model ölçümü DEĞİL)."""
    import collections
    acc = collections.defaultdict(collections.Counter)
    n_seed = 0
    p_test_s = []
    for seed in range(SEEDS_MAIN):
        rng = np.random.RandomState(20000 + seed)     # run_seed ile AYNI akış
        n_seed += 1
        tr, va, te, tg = make_split(rng, S1_TRAIN, TRAIN_N, VAL_N,
                                    S1_TEST_NEAR + S1_TEST_FAR, TEST_PER_S)
        acc["S1|ALL"].update(tg.tolist())
        acc["S1|far"].update(tg[np.abs(tg) == 6].tolist())
        tr, va, te, tg = make_split(rng, S2_TRAIN, TRAIN_N, VAL_N, S2_TEST, TEST_PER_S)
        acc["S2|ALL"].update(tg.tolist())
        pool = gen_mixed(rng, PAT_POOL, set())
        p_test_s += seq_sums(pool[PAT_TRAIN + PAT_VAL:]).tolist()
    acc["P|ALL"].update(p_test_s)
    rows = []
    log("\n=== TASARIM TABANLARI (ölçümden ÖNCE; %d tohum; model ölçümü DEĞİL) ===" % n_seed)
    for key in sorted(acc):
        c = acc[key]
        tot = sum(c.values())
        sp, sub = key.split("|")
        rows.append(dict(split=sp, subset=sub, n=tot, n_distinct=len(c),
                         chance=1.0 / len(c), majority=max(c.values()) / tot,
                         s_dist=str(dict(sorted(c.items())))))
        log("  %-9s n=%-6d sınıf=%d şans=%.4f en_sık_sınıf=%.4f  %s"
            % (key, tot, len(c), 1.0 / len(c), max(c.values()) / tot,
               dict(sorted(c.items()))))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "design_baselines.csv"), index=False)
    return pd.DataFrame(rows)


def load_all():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "*_seed[0-9][0-9].csv")))
    if not fs:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)


def _agg(df, split, H, target="ALL", train_H=None):
    m = (df.split == split) & (df.H == H) & (df.target_s.astype(str) == str(target))
    if train_H is not None:
        m &= (df.train_H == train_H)
    s = df[m]
    out = []
    for arm, sub in s.groupby("arm"):
        mean, sd, ci = R.ci95(sub.acc_exact.values)
        out.append(dict(arm=arm, mean=mean, sd=sd, ci95=ci, n=len(sub),
                        stuck=float(sub.stuck.mean()), pca_res=float(sub.pca_res.mean()),
                        sat=float(sub.sat.mean()), active=float(sub.active.mean()),
                        pred_mean=float(sub.pred_mean.mean()),
                        within2=float(sub.acc_within2.mean()),
                        nom=float(sub.acc_nominal.mean()),
                        pred_slope=float(sub.pred_slope.mean())
                        if sub.pred_slope.notna().any() else np.nan))
    return pd.DataFrame(out)


def _agg_far(df, H):
    """S1'in |s|=6 (uzak) öğeleri üzerinde kol bazlı özet."""
    s = df[(df.split == "S1") & (df.H == H) & (df.target_s.astype(str).isin(["-6", "6"]))]
    out = []
    for arm, sub in s.groupby("arm"):
        v = sub.acc_exact.values
        out.append(dict(arm=arm, mean=float(v.mean()), sd=float(v.std(ddof=1)),
                        ci95=1.96 * float(v.std(ddof=1)) / np.sqrt(len(v)), n=len(v),
                        stuck=float(sub.stuck.mean()), pca_res=float(sub.pca_res.mean()),
                        sat=float(sub.sat.mean()), active=float(sub.active.mean()),
                        pred_mean=float(sub.pred_mean.mean()),
                        within2=float(sub.acc_within2.mean()),
                        nom=float(sub.acc_nominal.mean()),
                        pred_slope=float(sub.pred_slope.mean())
                        if sub.pred_slope.notna().any() else np.nan))
    return pd.DataFrame(out)

def merge():
    df = load_all()
    if df.empty:
        log("merge: CSV yok")
        return None
    log("\n=== DONMUŞ KONFİGÜRASYON (7-2'den alındı; YENİ IZGARA YOK) ===")
    for a, (g, amp) in FROZEN.items():
        log("  %-10s g=%.1f amp=%.1f   [%s]" % (a, g, amp, FROZEN_SRC))
    try:
        bl = pd.read_csv(os.path.join(OUT, "design_baselines.csv"))
    except Exception:
        bl = design_baselines()
    base = {(r.split, r.subset): (float(r.chance), float(r.majority))
            for _, r in bl.iterrows()}
    report = []
    log("\n=== T3-S1 / T3-S2 (BİRİNCİL: H=%d; kesin = skaler + en yakın ÇİFT tam sayı) ==="
        % H_PRIMARY)
    for split, far in (("S1", False), ("S1", True), ("S2", False)):
        a = _agg_far(df, H_PRIMARY) if far else _agg(df, split, H_PRIMARY, "ALL")
        ck = base.get((split, "far" if far else "ALL"), (np.nan, np.nan))
        etiket = "uzak |s|=6" if far else ("yalnız s=±6" if split == "S2" else "ALL")
        log("  %s %s (şans=%.3f, en sık sınıf=%.3f):" % (split, etiket, ck[0], ck[1]))
        for _, r in a.iterrows():
            log("    %-10s kesin=%.3f+-%.3f | ±2=%.3f | nominal=%.3f | pred_ort=%+.2f | "
                "takılı=%.2f | PCA_artık=%.3f | doygun=%.3f aktif=%.3f"
                % (r.arm, r["mean"], r.ci95, r.within2, r.nom, r.pred_mean, r.stuck,
                   r.pca_res, r.sat, r.active))
            report.append(dict(split=split, subset="far" if far or split == "S2" else "ALL",
                               chance=ck[0], majority=ck[1],
                               **{k: r[k] for k in ("arm", "mean", "sd", "ci95", "n", "stuck",
                                                    "pca_res", "sat", "active", "pred_mean",
                                                    "within2", "nom")}))
    pd.DataFrame(report).to_csv(os.path.join(OUT, "summary_T3.csv"), index=False)
    log("\n  Hedef-bazlı ayrıntı (H=%d, kesin doğruluk):" % H_PRIMARY)
    for split in ("S1", "S2"):
        for t in ("-6", "-4", "4", "6"):
            a = _agg(df, split, H_PRIMARY, target=t)
            if len(a) == 0:
                continue
            log("    %s s=%-3s " % (split, t) + " | ".join(
                "%s %.3f" % (r.arm, r["mean"]) for _, r in a.iterrows()))
    log("\n=== İKİNCİL: H=0 ve H=20 (okuma yine kendi H'sinde eğitilir) ===")
    for H in (0, 20):
        for split in ("S1", "S2"):
            a = _agg(df, split, H, "ALL")
            log("  %s H=%-2d: " % (split, H) + " | ".join(
                "%s %.3f+-%.3f" % (r.arm, r["mean"], r.ci95) for _, r in a.iterrows()))
    log("\n=== T3-P (örüntü tutma; İNTERPOLASYON kontrolü — KURAL KANITI DEĞİL) ===")
    aP = _agg(df, "P", H_PRIMARY, "ALL")
    ckP = base.get(("P", "ALL"), (np.nan, np.nan))
    for _, r in aP.iterrows():
        log("  %-10s kesin=%.3f+-%.3f | ±2=%.3f | nominal=%.3f | takılı=%.3f (şans %.3f)"
            % (r.arm, r["mean"], r.ci95, r.within2, r.nom, r.stuck, ckP[0]))
    log("\n=== T3-H (KEŞİFSEL: okuma H=%d'de eğitildi, başka H'de test) ===" % H_PRIMARY)
    for H in (0, 20):
        a = _agg(df, "S2", H, "ALL", train_H=H_PRIMARY)
        log("  S2 H=%-2d (okuma H=%d'de): " % (H, H_PRIMARY) + " | ".join(
            "%s %.3f+-%.3f" % (r.arm, r["mean"], r.ci95) for _, r in a.iterrows()))
    log("\n=== İDEAL SAYAÇ (DIŞ YARDIM; simüle EDİLMEDİ) ===")
    log("  Durum doğrudan net toplam olduğunda kesin doğruluk tanım gereği = 1,000 (üst sınır);")
    log("  bu bir REFERANSTIR, ağ ölçümü DEĞİLDİR (7-1/7-2 ile aynı etiket).")
    return df, base

def hypotheses(df, base):
    """Ön-kayıtlı ölçütler + H7.11-H7.14 (Holm m=6: A_gercek vs {A_w0,A_derece,A_er} × 2 alt küme)."""
    from scipy import stats

    def g1(a, arm):
        r = a[a.arm == arm]
        return None if len(r) == 0 else r.iloc[0]

    def per_seed_far(arm):
        s = df[(df.split == "S1") & (df.H == H_PRIMARY) & (df.arm == arm)
               & (df.target_s.astype(str).isin(["-6", "6"]))]
        return s.groupby("seed").acc_exact.mean().sort_index()

    def per_seed(arm, split):
        s = df[(df.split == split) & (df.H == H_PRIMARY) & (df.arm == arm)
               & (df.target_s.astype(str) == "ALL")]
        return s.groupby("seed").acc_exact.mean().sort_index()

    far, s2 = _agg_far(df, H_PRIMARY), _agg(df, "S2", H_PRIMARY, "ALL")
    ck_f, ck_s = base[("S1", "far")], base[("S2", "ALL")]
    log("\n=== ÖN-KAYITLI ÖLÇÜTLER ===")
    for tag, a, ck in (("T3-S1 uzak |s|=6", far, ck_f), ("T3-S2 (s=±6)", s2, ck_s)):
        g, w = g1(a, "A_gercek"), g1(a, "A_w0")
        ok = bool((g["mean"] - g.ci95 > ck[1]) and (g["mean"] - g.ci95 > w["mean"] + w.ci95)
                  and (g["mean"] >= 0.50))
        log("  \"Kural/ekstrapolasyon\" (%s): A_gercek %.3f+-%.3f | en sık sınıf %.3f | "
            "A_w0 %.3f+-%.3f -> %s" % (tag, g["mean"], g.ci95, ck[1], w["mean"], w.ci95,
                                       "GEÇTİ" if ok else "GEÇMEDİ"))
        for arm in ("A_derece", "A_er"):
            o = g1(a, arm)
            log("  \"Connectome'a özgü kural\" (%s) vs %-9s %.3f+-%.3f -> GA ayrık üstün=%s"
                % (tag, arm, o["mean"], o.ci95,
                   bool(g["mean"] - g.ci95 > o["mean"] + o.ci95)))
    log("\n=== HİPOTEZLER ===")
    for tag, a in (("T3-S1 uzak", far), ("T3-S2", s2)):
        g = g1(a, "A_gercek")
        log("  H7.11 (%s): A_gercek takılı_oranı=%.3f (≥0,5 mi: %s), kesin=%.3f -> %s"
            % (tag, g.stuck, g.stuck >= 0.5, g["mean"],
               "DESTEK (çöktü)" if g.stuck >= 0.5 else "belirsiz"))
    P = _agg(df, "P", H_PRIMARY, "ALL")
    gp = g1(P, "A_gercek")
    log("  H7.12 (T3-P A_gercek ≥0,90): %.3f -> %s"
        % (gp["mean"], "DESTEK" if gp["mean"] >= 0.90 else "ÇÜRÜDÜ"))
    log("  H7.13 (A_gercek ≈ A_derece ≈ A_er):")
    tests = []
    for tag, fn in (("S1_far", per_seed_far), ("S2", lambda x: per_seed(x, "S2"))):
        ref = fn("A_gercek")
        for arm in ("A_w0", "A_derece", "A_er"):
            o = fn(arm)
            common = ref.index.intersection(o.index)
            if len(common) < 3:
                continue
            rv, ov = ref.loc[common].values, o.loc[common].values
            t = stats.ttest_rel(rv, ov)
            tests.append(dict(subset=tag, test="A_gercek vs %s" % arm,
                              diff=float(np.mean(rv - ov)), p_raw=float(t.pvalue),
                              n=len(common)))
    if tests:
        ps = np.array([t["p_raw"] for t in tests])
        adj = np.empty(len(ps))
        prev = 0.0
        for rank, i in enumerate(np.argsort(ps)):
            prev = max(prev, min(1.0, (len(ps) - rank) * ps[i]))
            adj[i] = prev
        for t, a2 in zip(tests, adj):
            t["p_holm"] = float(a2)
        for t in sorted(tests, key=lambda x: x["p_raw"]):
            log("    %-8s %-22s fark=%+.4f p_ham=%.4f p_holm=%.4f -> %s"
                % (t["subset"], t["test"], t["diff"], t["p_raw"], t["p_holm"],
                   "AYRIŞIR" if t["p_holm"] < 0.05 else "ayrışamaz"))
        pd.DataFrame(tests).to_csv(os.path.join(OUT, "hypotheses.csv"), index=False)
    pts = [(float(r.pca_res), 1.0 - float(r["mean"])) for _, r in
           pd.concat([far, s2]).iterrows()]
    if len(pts) >= 4:
        rho, p = stats.spearmanr([x for x, _ in pts], [y for _, y in pts])
        log("  H7.14 (TANI, yön yok): PCA artık uzaklığı ↔ ekstrapolasyon hatası "
            "Spearman rho=%+.2f p=%.3f (n=%d) -> %s"
            % (rho, p, len(pts), "ilişki var" if p < 0.05 else "ilişki gösterilemedi"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "baselines":
        design_baselines()
    elif cmd == "runall":
        runall(int(sys.argv[2]), sys.argv[3:] or None)
    elif cmd == "merge":
        out = merge()
        if out is not None:
            df, base = out
            hypotheses(df, base)
    else:
        log("kullanim: baselines | runall <nseeds> [kollar...] | merge")


if __name__ == "__main__":
    main()

