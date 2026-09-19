"""
numcog/phase4e.py — FAZ 4E: N=81 teşhisi, kalibrasyon ve shuffle kontrolü (kısa).

Adım 1: 4D en iyi hücrede (ep 25000, lr 0.05, top-k 80, sigma=1.5) teşhis + ayrılabilirlik.
Adım 2: gerçek / derece-korunmuş shuffle / örtüşme-kontrol.
Adım 3: YALNIZCA Adım 1 kenar hatası gösterirse küçük ızgara (eksen dolgusu x sigma).
Adım 4: kontrolcü kalibrasyonu (KONTROLCÜ İŞİ) + kabul edilen sineklerle hesap makinesi.

Seçim ölçütü YALNIZCA tablo doğruluğu; çarpma/bölme seçim için KULLANILMAZ.
Mevcut modüller import edilir, DEĞİŞTİRİLMEZ.
"""
from __future__ import annotations
import os
import time

import numpy as np
import pandas as pd

import number_coding as nc
import operator_diagnosis as od
import calculator as cal
import phase4c as p4c

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p4e")

N_BIG = 81
SIGMA = 1.5
BEST = dict(epochs=25000, lr=0.05, topk=80)     # 4D en iyi hücre
SEEDS = 30
SEEDS_FINAL = 100
EDGE = (0, 1, 80, 81)                            # kenar n değerleri
SHUF_SEED = 999
SHUF_SWAPS = 200000
SUCCESS = 0.95
PAD = (-3.0, float(N_BIG + 3))
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

_CACHE = {}


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def tcache(seed, mats, key, sigma, cfg):
    """p4c.table_eval'i (deterministik) önbelleğe al; aynı hesabı iki kez yapma."""
    ck = (seed, key, float(sigma), tuple(sorted(cfg.items())))
    if ck not in _CACHE:
        _CACHE[ck] = p4c.table_eval(N_BIG, seed, mats, sigma=sigma, **cfg)
    return _CACHE[ck]


def pairs_all():
    return [(n, op) for n in range(N_BIG + 1) for op in ('+', '-')]


def _cos(a, b):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(a @ b) / (na * nb)


def neighbor_sim(code, pairs, pos, i):
    """i. girdinin (n,op) komşu kodlarına kosinüs benzerliği (maks)."""
    n, op = pairs[i]
    js = []
    for nn in (n - 1, n + 1):
        if 0 <= nn <= N_BIG:
            js.append(pos[(nn, op)])
    js.append(pos[(n, '+' if op == '-' else '-')])
    c = code(n, op)
    return max(_cos(c, code(*pairs[j])) for j in js)


def onehot(y, k):
    T = np.zeros((len(y), k), dtype=np.float32)
    T[np.arange(len(y)), y] = 1.0
    return T


def wilson(k, n):
    """Başarı oranı için %95 Wilson aralığı (k/n)."""
    if n == 0:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2.0 * n)
    hw = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return float((c - hw) / d), float((c + hw) / d)



def step1(mats):
    log("\n=== ADIM 1: TANIS (N=%d, %d tohum, hucre=%s) ===" % (N_BIG, SEEDS, BEST))
    pairs = pairs_all()
    pos = {p: i for i, p in enumerate(pairs)}
    y = np.array([od.clip_result(n, op, N_BIG) for n, op in pairs])
    rows, wrongs, sims, seps = [], [], [], []
    for s in range(SEEDS):
        t0 = time.time()
        acc, wrong, code = tcache(s, mats, "real", SIGMA, BEST)
        rows.append(dict(seed=s, acc=acc, n_wrong=len(wrong), full=int(len(wrong) == 0)))
        if len(wrong) == 0:
            log("  tohum %2d: TAM-DOGRU (%.0fs)" % (s, time.time() - t0))
        else:
            log("  tohum %2d: %d hatali -> %s (%.0fs)"
                % (s, len(wrong), [(w["n"], w["op"], w["pred"]) for w in wrong], time.time() - t0))
        wrong_idx = {pos[(w["n"], w["op"])] for w in wrong}
        for w in wrong:
            wrongs.append(dict(seed=s, **w))
        X = np.array([code(n, op) for n, op in pairs], np.float32)
        for i, (n, op) in enumerate(pairs):
            sims.append(dict(seed=s, n=n, op=op, wrong=int(i in wrong_idx),
                             sim=neighbor_sim(code, pairs, pos, i)))
        r = int(np.linalg.matrix_rank(X))
        _, idx, inv = np.unique(X, axis=0, return_index=True, return_inverse=True)
        groups = {}
        for i, g in enumerate(inv):
            groups.setdefault(int(g), []).append(i)
        dup_conf = sum(len(ids) for ids in groups.values()
                       if len(ids) > 1 and len({int(y[i]) for i in ids}) > 1)
        T1 = onehot(y, N_BIG + 1)
        Wc = np.linalg.lstsq(X, T1, rcond=None)[0].T
        cf1 = float(np.mean((X @ Wc.T).argmax(1) == y))
        T2 = -np.ones_like(T1)
        T2[np.arange(len(y)), y] = 1.0
        Wc2 = np.linalg.lstsq(X, T2, rcond=None)[0].T
        cf2 = float(np.mean((X @ Wc2.T).argmax(1) == y))
        seps.append(dict(seed=s, dim=int(X.shape[1]), rank=r, n_uniq=int(len(idx)),
                         dup_conflict=int(dup_conf), cf_onehot=cf1, cf_pm1=cf2, delta_acc=acc))
    sdf = pd.DataFrame(rows)
    wdf = pd.DataFrame(wrongs) if wrongs else pd.DataFrame(
        columns=["seed", "n", "op", "pred", "true", "margin"])
    mdf = pd.DataFrame(sims)
    pdf = pd.DataFrame(seps)
    sdf.to_csv(os.path.join(OUT, "diag81_seeds.csv"), index=False)
    wdf.to_csv(os.path.join(OUT, "diag81_wrong.csv"), index=False)
    mdf.to_csv(os.path.join(OUT, "diag81_sim.csv"), index=False)
    pdf.to_csv(os.path.join(OUT, "diag81_sep.csv"), index=False)

    log("\n--- Adim 1 ozet ---")
    log("tablo TAM dogru tohum: %d/%d (%.1f%%)  egitim ort=%.4f min=%.4f"
        % (int(sdf.full.sum()), len(sdf), 100 * sdf.full.mean(), sdf.acc.mean(), sdf.acc.min()))
    log("hatali tohum: %d  toplam hatali girdi: %d"
        % (int((sdf.full == 0).sum()), len(wdf)))
    h1 = False
    if len(wdf):
        ncnt = wdf.groupby(["n", "op"]).size().reset_index(name="count").sort_values(
            "count", ascending=False)
        ncnt.to_csv(os.path.join(OUT, "diag81_ncount.csv"), index=False)
        log("hatali (n,op) ilk 12:\n" + ncnt.head(12).to_string(index=False))
        ncnt_n = wdf.groupby("n").size().sort_index()
        ncnt_n.to_frame("count").to_csv(os.path.join(OUT, "diag81_nhist.csv"))
        log("hatali girdilerin n dagilimi: %s"
            % ", ".join("%d:%d" % (k, v) for k, v in ncnt_n.items()))
        edge_wrong = int(wdf.n.isin(EDGE).sum())
        base = len(EDGE) * 2 / (2 * (N_BIG + 1))
        share = edge_wrong / len(wdf)
        h1 = bool(share >= 2 * base)
        log("KENAR (n in %s): %d/%d = %.1f%%  (taban %.2f%%) -> H4e.1 %s"
            % (list(EDGE), edge_wrong, len(wdf), 100 * share, 100 * base,
               "DESTEK" if h1 else "CURUTULDU"))
        log("kenar hatalarinin (n,op) dagilimi:\n" + wdf[wdf.n.isin(EDGE)]
            .groupby(["n", "op"]).size().to_string())
    log("komsu kod kosinus benzerligi: yanlis=%.3f  dogru=%.3f"
        % (mdf[mdf.wrong == 1].sim.mean(), mdf[mdf.wrong == 0].sim.mean()))
    rankfull = bool((pdf["rank"] == len(pairs)).all())
    noconf = bool((pdf["dup_conflict"] == 0).all())
    cfmin = float(pdf[["cf_onehot", "cf_pm1"]].min().min())
    h2 = bool(rankfull and noconf and cfmin >= 1.0)
    log("ayrilabilirlik: rank==%d (tum tohum) = %s | ozdes-kod catismasi = %d | kapali form min = %.4f"
        % (len(pairs), rankfull, int(pdf.dup_conflict.sum()), cfmin))
    log("kapali form (one-hot) ort=%.4f | delta kurali (ayni kodlar) ort=%.4f"
        % (pdf.cf_onehot.mean(), pdf.delta_acc.mean()))
    log("-> H4e.2 %s" % ("DESTEK" if h2 else "CURUTULDU"))
    return sdf, wdf, mdf, pdf, h1, h2


def step2(mats):
    log("\n=== ADIM 2: SHUFFLE KONTROLU (N=%d, %d tohum, hucre=%s) ===" % (N_BIG, SEEDS, BEST))
    t0 = time.time()
    Wsh = nc.degree_preserving_shuffle(mats["W_vpn"], SHUF_SEED, SHUF_SWAPS)
    log("derece-korunmus shuffle: seed=%d swaps=%d, kenar %d -> %d (%.0fs)"
        % (SHUF_SEED, SHUF_SWAPS, int((mats["W_vpn"] > 0).sum()), int((Wsh > 0).sum()),
           time.time() - t0))
    m_sh = dict(mats)
    m_sh["W_vpn"] = Wsh
    m_ov = dict(mats)
    m_ov["W_alpn_r"] = mats["W_alpn_r_rand"]
    rows = []
    for name, mm, key in (("real", mats, "real"), ("shuffled", m_sh, "shuf"),
                          ("overlap", m_ov, "ovl")):
        t0 = time.time()
        full, accs = 0, []
        for s in range(SEEDS):
            acc, wrong, _ = tcache(s, mm, key, SIGMA, BEST)
            accs.append(acc)
            full += int(len(wrong) == 0)
        lo, hi = wilson(full, SEEDS)
        rows.append(dict(arm=name, full=full, n=SEEDS, frac=full / SEEDS, ci_lo=lo, ci_hi=hi,
                         acc=float(np.mean(accs)), sec=time.time() - t0))
        log("  %-9s tam-dogru=%2d/%d (%.1f%%) GA95=[%.1f%%,%.1f%%] egitim=%.4f (%.0fs)"
            % (name, full, SEEDS, 100 * full / SEEDS, 100 * lo, 100 * hi, np.mean(accs),
               rows[-1]["sec"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "shuffle81.csv"), index=False)
    r = df[df.arm == "real"].iloc[0]
    sh = df[df.arm == "shuffled"].iloc[0]
    ov = df[df.arm == "overlap"].iloc[0]
    same = bool(sh.ci_lo <= r.frac <= sh.ci_hi)
    log("gercek %.1f%% vs shuffle %.1f%% (GA95 %.1f-%.1f) -> %s"
        % (100 * r.frac, 100 * sh.frac, 100 * sh.ci_lo, 100 * sh.ci_hi,
           "AYIRT EDILEMEDI" if same else "FARK VAR"))
    log("gercek %.1f%% vs ortusme-kontrol %.1f%% (GA95 %.1f-%.1f)"
        % (100 * r.frac, 100 * ov.frac, 100 * ov.ci_lo, 100 * ov.ci_hi))
    return df, same


def step3(mats):
    log("\n=== ADIM 3: KUCUK IZGARA (dolgu x sigma, %d tohum) ===" % SEEDS)
    cells = [(sg, pad) for sg in (1.0, 1.5, 2.0) for pad in (False, True)]
    rows = []
    for sg, pad in cells:
        kw = dict(BEST)
        if pad:
            kw["lo"], kw["hi"] = PAD
        full, accs = 0, []
        t0 = time.time()
        for s in range(SEEDS):
            acc, wrong, _ = tcache(s, mats, "real", sg, kw)
            accs.append(acc)
            full += int(len(wrong) == 0)
        lo, hi = wilson(full, SEEDS)
        rows.append(dict(sigma=sg, pad=int(pad), lo=kw.get("lo", 0.0),
                         hi=kw.get("hi", float(N_BIG)), full=full, frac=full / SEEDS,
                         ci_lo=lo, ci_hi=hi, acc=float(np.mean(accs)), sec=time.time() - t0))
        log("  sigma=%.1f dolgu=%-5s tam-dogru=%2d/%d (%.1f%%) GA95=[%.1f%%,%.1f%%] egitim=%.4f (%.0fs)"
            % (sg, bool(pad), full, SEEDS, 100 * full / SEEDS, 100 * lo, 100 * hi,
               np.mean(accs), rows[-1]["sec"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "grid81_4e.csv"), index=False)
    ok = df[df.frac >= SUCCESS]
    if len(ok):
        best = ok.sort_values(["frac", "acc"], ascending=False).iloc[0]
        frozen = dict(sigma=float(best.sigma), pad=bool(best.pad))
        log("DONDU: sigma=%.1f dolgu=%s (%.1f%%)" % (best.sigma, bool(best.pad), 100 * best.frac))
        return df, frozen
    log(">=%95 saglayan hucre YOK -> donma yok")
    return df, None


def step4(mats, frozen):
    if frozen is None:
        sigma, kw, tag = SIGMA, dict(BEST), "4D-en-iyi"
    else:
        sigma, kw = frozen["sigma"], dict(BEST)
        tag = "donmus-s%.1f-dolgu%d" % (frozen["sigma"], int(frozen["pad"]))
        if frozen["pad"]:
            kw["lo"], kw["hi"] = PAD
    log("\n=== ADIM 4: KONTROLCU KALIBRASYONU + HESAP MAKINESI ===")
    log("konfigurasyon: %s sigma=%.1f %s" % (tag, sigma, dict(BEST)))
    log("KONTROLCU ISI (etiketli): acilista 164 (n,op) girdisi sinanir; gecmeyen sinek REDDEDILIR.")
    acc_rows, accepted = [], []
    for s in range(SEEDS_FINAL):
        acc, wrong, _ = tcache(s, mats, tag, sigma, kw)
        acc_rows.append(dict(seed=s, acc=acc, n_wrong=len(wrong), accept=int(len(wrong) == 0)))
        if len(wrong) == 0:
            accepted.append(s)
    adf = pd.DataFrame(acc_rows)
    adf.to_csv(os.path.join(OUT, "calib81.csv"), index=False)
    nrej = SEEDS_FINAL - len(accepted)
    lo, hi = wilson(len(accepted), SEEDS_FINAL)
    log("%d tohum: kabul=%d (%.1f%%, GA95 %.1f-%.1f) | reddedilen=%d (%.1f%%, GA95 %.1f-%.1f)"
        % (SEEDS_FINAL, len(accepted), 100 * len(accepted) / SEEDS_FINAL, 100 * lo, 100 * hi,
           nrej, 100 * nrej / SEEDS_FINAL, 100 * (1 - hi), 100 * (1 - lo)))

    rows, chain = [], []
    for s in accepted:
        acc, wrong, code = tcache(s, mats, tag, sigma, kw)
        X = np.array([code(n, op) for n, op in pairs_all()], np.float32)
        y = np.array([od.clip_result(n, op, N_BIG) for n, op in pairs_all()])
        W, b = p4c.fit_fast(X, y, N_BIG + 1, kw.get("lr", 0.01), kw.get("epochs", 1000), s)
        core = p4c.Core(N_BIG, code, W, b)
        r = od.calc_measure(N_BIG, s, mats, core)
        rows.append(dict(seed=s, table=acc, add=r["add"], subtract=r["subtract"],
                         multiply=r["multiply"], divide=r["divide"]))
        chain.extend(r["chain"])
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "final81_seeds.csv"), index=False)
    if len(df):
        log("kabul edilen %d tohumda (N=%d; tum 9x9=%d <= 81 temsil edilebilir):"
            % (len(df), N_BIG, 81))
        for k in ("add", "subtract", "multiply", "divide"):
            m = float(df[k].mean())
            sd = float(df[k].std(ddof=1)) if len(df) > 1 else 0.0
            ci = 1.96 * sd / np.sqrt(len(df))
            log("  %-9s ort=%.4f +- %.4f  min=%.4f  GA95=[%.4f,%.4f]  dagilim=%s"
                % (k, m, sd, df[k].min(), m - ci, m + ci,
                   dict(df[k].value_counts().sort_index())))
        cdf = cal.chain_vs_k(chain, float(df["add"].mean()))
        cdf.to_csv(os.path.join(OUT, "final81_chain.csv"), index=False)
        log("zincir k vs p^k (ilk 4 / son 4):")
        log(cdf.head(4).to_string(index=False))
        log(cdf.tail(4).to_string(index=False))
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(LOGF, "w", encoding="utf-8"):
        pass
    log("FAZ 4E basladi (N=%d, hucre=%s, %d tohum)" % (N_BIG, BEST, SEEDS))
    t00 = time.time()
    mats = od.load_sets()
    sdf, wdf, mdf, pdf, h1, h2 = step1(mats)
    step2(mats)
    if h1:
        _, frozen = step3(mats)
    else:
        log("\n=== ADIM 3 ATLANDI: on-kayitli kosul (H4e.1 kenar hatasi) saglanmadi ===")
        frozen = None
    step4(mats, frozen)
    log("\ntoplam sure: %.0fs" % (time.time() - t00))
    log("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()


