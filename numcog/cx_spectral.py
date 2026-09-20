"""
numcog/cx_spectral.py — FAZ 6-0b: koordinattan bağımsız halka testi (spektral, YALNIZCA ÖLÇÜM).

DİNAMİK SİMÜLASYON YOK. Faz 0–6-0 dosyaları/sonuçları DEĞİŞTİRİLMEZ.
Ön-kayıt: HIPOTEZLER.md (commit `193f21c`).

Girdi (Faz 4B-0 kenar tanımı; min_syn eşiği yok):
  W = EPG(51) x PEN(42) ağırlık; M = [[0,W],[W^T,0]] (93x93, BİRİNCİL);
  S = W W^T (51x51, köşegen sıfır, KO-ANALİZ).
Yöntem: normalize edilmemiş Laplasyen L = D - A, ilk iki nontrivial özvektör -> 2B gömme.
Ölçütler: r_cv, Kuiper V, en büyük açısal boşluk (hepsi döndürmeye duyarsız).

CLI: labels | embed | tests | bonus | merge
"""
from __future__ import annotations
import glob
import os
import sys
import time

import numpy as np
import pandas as pd

import number_coding as nc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p6_0b")
P60 = os.path.join(HERE, "results_p6_0")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

N_NULL = 1000
RNG_BASE = 8000
SWAP_FACTOR = 10
GAP_FULL = 60.0
ANN_COLS = ["root_id", "hemibrain_type", "cell_type", "supertype", "synonyms", "side"]


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def load_cx():
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann["root_id"] = ann["root_id"].astype("int64")
    h = ann.hemibrain_type.astype(str)
    return ann, ann[h.str.startswith("EPG")].copy(), ann[h.str.startswith("PEN")].copy()


def build_W(epg, pen):
    """Faz 4B-0 ile aynı: pre in EPG, post in PEN (eşik yok), ağırlık = syn_count toplamı."""
    epg_ids = [int(r) for r in epg.root_id]
    pen_ids = [int(r) for r in pen.root_id]
    ei = {r: i for i, r in enumerate(epg_ids)}
    pi = {r: i for i, r in enumerate(pen_ids)}
    conn = pd.read_feather(nc.CONN_FILE,
                           columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
    e = conn[conn.pre_pt_root_id.isin(set(epg_ids)) & conn.post_pt_root_id.isin(set(pen_ids))]
    W = np.zeros((len(epg_ids), len(pen_ids)), float)
    for a, b, w in zip(e.pre_pt_root_id.values, e.post_pt_root_id.values, e.syn_count.values):
        W[ei[int(a)], pi[int(b)]] += float(w)
    return W, e, epg_ids, pen_ids


def build_mats(W):
    n1, n2 = W.shape
    M = np.zeros((n1 + n2, n1 + n2), float)
    M[:n1, n1:] = W
    M[n1:, :n1] = W.T
    S = W @ W.T
    np.fill_diagonal(S, 0.0)
    return M, S


def embed_stats(A, label=""):
    """Laplasyen L = D - A; 2B gömme = en küçük İKİ SIFIR-DIŞI özvektör (birincil).

    Not: ön-kayıt "ilk iki nontrivial özvektör" diyordu; veride graf BAĞLI DEĞİL (λ=0 birden çok kez),
    bu yüzden "nontrivial" = **sıfırdan farklı** olarak uygulanır ve TÜM sıfır özvektörleri atlanır
    (aynı kural gözlenen ve tüm null örneklerine uygulanır). Ön-kayıttaki literal sürüm (indis 1,2)
    de 'literal' anahtarlarıyla raporlanır.
    """
    n = A.shape[0]
    d = A.sum(1)
    L = np.diag(d) - A
    ev, EV = np.linalg.eigh(L)
    tol = 1e-9 * max(abs(ev[-1]), 1e-12)
    n_zero = int(np.sum(ev <= tol))
    i_prim = [n_zero, n_zero + 1]
    out = dict(label=label, n=n, n_zero=n_zero, n_comp=n_zero, lam=[float(x) for x in ev[:6]],
               lam2=float(ev[1]), lam3=float(ev[2]), EV=EV, ev=ev, i_prim=i_prim)
    for tag, idx in (("", i_prim), ("literal", [1, 2])):
        if idx[1] >= n:
            continue
        coords = EV[:, idx]
        cm = coords.mean(0)
        Y = coords - cm
        r = np.hypot(Y[:, 0], Y[:, 1])
        ang = np.arctan2(Y[:, 1], Y[:, 0])
        a = np.sort(ang % (2 * np.pi))
        gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]]))
        u = a / (2 * np.pi)
        ii = np.arange(1, n + 1)
        Vk = float((ii / n - u).max() + (u - (ii - 1) / n).max())
        r_cv = float(r.std(ddof=1) / r.mean()) if r.mean() > 0 else float("nan")
        out[tag + "r_cv"] = r_cv
        out[tag + "r_mean"] = float(r.mean())
        out[tag + "g_max_deg"] = float(np.degrees(gaps.max()))
        out[tag + "kuiper_V"] = Vk
        out[tag + "ang"] = ang
        out[tag + "r"] = r
        out[tag + "idx"] = idx
    out["degen"] = bool(abs(ev[2] - ev[1]) <= 1e-9 * max(abs(ev[2]), 1e-12))
    return out


def _swap(C, rng, n_swaps):
    """Derece-korunmus cift-kenar takasi (EPG satir / PEN sutun dereceleri korunur)."""
    edges = [tuple(x) for x in np.argwhere(C)]
    m = len(edges)
    if m < 4:
        return C
    for _ in range(n_swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = edges[i]
        c, d = edges[j]
        if a == c or b == d or C[a, d] or C[c, b]:
            continue
        C[a, b] = False
        C[c, d] = False
        C[a, d] = True
        C[c, b] = True
        edges[i] = (a, d)
        edges[j] = (c, b)
    return C


def embed():
    ann, epg, pen = load_cx()
    W, e, epg_ids, pen_ids = build_W(epg, pen)
    M, S = build_mats(W)
    sm = embed_stats(M, "M(93x93)")
    ss = embed_stats(S, "S(51x51)")
    log("\n=== ADIM 2: GÖMME (Laplasyen; birincil = en küçük iki SIFIR-DIŞI özvektör) ===")
    for st in (sm, ss):
        log("  %-11s n=%-3d sifir ozdeger=%d (bagli bilesen) | BIRINCIL r_cv=%.4f r_mean=%.4f "
            "g_max=%.1f deg Kuiper V=%.3f | LITERAL(indis1,2) r_cv=%.4f g_max=%.1f"
            % (st["label"], st["n"], st["n_zero"], st["r_cv"], st["r_mean"], st["g_max_deg"],
               st["kuiper_V"], st["literalr_cv"], st["literalg_max_deg"]))
        log("      lam1..6=%s | ozvektor indisleri: birincil=%s literal=%s"
            % (np.round(st["lam"], 4), st["i_prim"], st["literalidx"]))
    rows = []
    for st, ids, kume in ((sm, epg_ids + pen_ids, ["EPG"] * len(epg_ids) + ["PEN"] * len(pen_ids)),
                          (ss, epg_ids, ["EPG"] * len(epg_ids))):
        i0, i1 = st["i_prim"]
        for i, rid in enumerate(ids):
            rows.append(dict(embed=st["label"], kume=kume[i], root_id=rid,
                             x=st["EV"][i, i0], y=st["EV"][i, i1], r=st["r"][i],
                             angle_deg=np.degrees(st["ang"][i]) % 360))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "embedding_coords.csv"), index=False)
    pd.DataFrame([dict(embed=st["label"], n=st["n"], n_zero=st["n_zero"], r_cv=st["r_cv"],
                       r_mean=st["r_mean"], g_max_deg=st["g_max_deg"], kuiper_V=st["kuiper_V"],
                       literal_r_cv=st["literalr_cv"], literal_g_max_deg=st["literalg_max_deg"],
                       literal_kuiper_V=st["literalkuiper_V"], i_prim=str(st["i_prim"]),
                       lam2=st["lam2"], lam3=st["lam3"], degen=st["degen"])
                  for st in (sm, ss)]).to_csv(os.path.join(OUT, "embedding_observed.csv"),
                                              index=False)
    pd.DataFrame([dict(embed=st["label"], i=i, lam=v)
                  for st in (sm, ss) for i, v in enumerate(st["lam"])]).to_csv(
        os.path.join(OUT, "embedding_eigenvalues.csv"), index=False)
    return sm, ss, (M, S, W, epg_ids, pen_ids)


def tests():
    ann, epg, pen = load_cx()
    W, e, epg_ids, pen_ids = build_W(epg, pen)
    M, S = build_mats(W)
    sm = embed_stats(M, "M(93x93)")
    ss = embed_stats(S, "S(51x51)")
    C = (W > 0)
    E = int(C.sum())
    dv, da = C.sum(1).copy(), C.sum(0).copy()
    log("\n=== ADIM 3: NULL (derece-korunmuş rastgele bağlantı, %d örnek) ===" % N_NULL)
    log("  kenar=%d, takas denemesi/ornek=%d | gözlenen: M r_cv=%.4f g_max=%.1f | "
        "S r_cv=%.4f g_max=%.1f"
        % (E, SWAP_FACTOR * E, sm["r_cv"], sm["g_max_deg"], ss["r_cv"], ss["g_max_deg"]))
    path = os.path.join(OUT, "null_samples.csv")
    rows, t0 = [], time.time()
    for s in range(N_NULL):
        rng = np.random.RandomState(RNG_BASE + s)
        Cs = _swap(C.copy(), rng, SWAP_FACTOR * E)
        assert (Cs.sum(1) == dv).all() and (Cs.sum(0) == da).all(), "derece korunmadi"
        vals = W[C].copy()
        rng.shuffle(vals)
        Ws = np.zeros_like(W)
        Ws[Cs] = vals
        Ms, Ss = build_mats(Ws)
        a = embed_stats(Ms)
        b = embed_stats(Ss)
        rows.append(dict(sample=s, m_r_cv=a["r_cv"], m_gmax=a["g_max_deg"], m_V=a["kuiper_V"],
                         m_nzero=a["n_zero"], s_r_cv=b["r_cv"], s_gmax=b["g_max_deg"],
                         s_V=b["kuiper_V"], s_nzero=b["n_zero"],
                         m_lit_r_cv=a["literalr_cv"], m_lit_gmax=a["literalg_max_deg"],
                         s_lit_r_cv=b["literalr_cv"], s_lit_gmax=b["literalg_max_deg"]))
        if (s + 1) % 200 == 0:
            log("  %d/%d örnek (%.0fs)" % (s + 1, N_NULL, time.time() - t0))
    pd.DataFrame(rows).to_csv(path, index=False)
    log("null bitti (%.0fs) | derece korunumu assert edildi" % (time.time() - t0))
    return sm, ss


def labels():
    ann, epg, pen = load_cx()
    log("=== ADIM 1: ETIKET/NaN SAYIMI ===")
    for nm, sub in (("EPG", epg), ("PEN", pen)):
        log("  %-4s n=%d | hemibrain_type: %s" % (nm, len(sub), dict(
            sub.hemibrain_type.value_counts())))
    W, e, epg_ids, pen_ids = build_W(epg, pen)
    rows = []
    for nm, ids, s in (("EPG", epg_ids, epg), ("PEN", pen_ids, pen)):
        tt = s.set_index("root_id").reindex(ids)
        rows.append(dict(kume=nm, n=len(ids),
                         hemibrain_type_nan=int(tt.hemibrain_type.isna().sum()),
                         cell_type_nan=int(tt.cell_type.isna().sum())))
    # wedge etiketi var mi? (tip adlarinda sayi)
    import re
    allnames = pd.concat([epg.cell_type, epg.hemibrain_type, epg.synonyms,
                          pen.cell_type, pen.hemibrain_type, pen.synonyms])
    withnum = [x for x in allnames.unique().tolist() if isinstance(x, str) and re.search(r"\d", x)]
    epg_names = [x for x in (list(epg.cell_type.unique()) + list(epg.hemibrain_type.unique()))
                 if isinstance(x, str)]
    epg_num = [x for x in epg_names if re.search(r"\d", x)]
    other_num = [x for x in withnum if not x.startswith("PEN_")]
    log("  NaN: %s" % rows)
    log("  EPG tip adlarinda SAYI: %s -> wedge/glomerul etiketi %s"
        % (epg_num if epg_num else "YOK", "VAR" if epg_num else "YOK"))
    log("  (sayi iceren TUM etiketler: %s -> bunlar PEN alt tip adlari, wedge degil)" % withnum)
    log("  W: %d x %d | kenar=%d, sinaps=%.0f, sifir olmayan hucre: EPG %d / PEN %d"
        % (W.shape[0], W.shape[1], len(e), W.sum(), int((W.sum(1) > 0).sum()),
           int((W.sum(0) > 0).sum())))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "label_counts.csv"), index=False)
    return W, epg_ids, pen_ids


def circ_corr(a, b):
    """Jammalamadaka-Sarma dairesel korelasyonu (isaret ozvektor isaretine bagli)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ab = np.angle(np.exp(1j * a).mean())
    bb = np.angle(np.exp(1j * b).mean())
    sa = np.sin(a - ab)
    sb = np.sin(b - bb)
    den = np.sqrt((sa ** 2).sum() * (sb ** 2).sum())
    return float((sa * sb).sum() / den) if den > 0 else float("nan")


def bonus():
    """BONUS (on-kayitli, yon beklentisi yok): gomme acisi ile Faz 6-0 soma acisi uyumu."""
    ann, epg, pen = load_cx()
    W, e, epg_ids, pen_ids = build_W(epg, pen)
    M, S = build_mats(W)
    sm = embed_stats(M, "M(93x93)")
    ss = embed_stats(S, "S(51x51)")
    soma = pd.read_csv(os.path.join(P60, "geometry_angles.csv"))
    soma_epg = soma[soma.kume == "EPG"].set_index("root_id").angle_deg
    log("\n=== BONUS: gömme açısı vs Faz 6-0 soma açısı (dairesel korelasyon) ===")
    rows = []
    for st, off in ((sm, 0), (ss, 0)):
        th = st["ang"][off:off + len(epg_ids)]
        ph = np.radians([float(soma_epg.loc[r]) for r in epg_ids])
        rc = circ_corr(th, ph)
        rows.append(dict(embed=st["label"], n_epg=len(epg_ids), circ_corr=rc,
                         abs_circ_corr=abs(rc)))
        log("  %-11s |r_c| = %.4f (isaret ozvektor yonune bagli, |r_c| raporlanir)"
            % (st["label"], abs(rc)))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "bonus_circular_corr.csv"), index=False)
    return rows


def stat_lower(obs, null):
    null = np.asarray(null, float)
    p = (1.0 + float(np.sum(null <= obs))) / (len(null) + 1.0)
    return dict(obs=float(obs), null_mean=float(null.mean()),
                null_std=float(null.std(ddof=1)), p_raw=float(p), n=int(len(null)))


def merge():
    obs = pd.read_csv(os.path.join(OUT, "embedding_observed.csv"))
    nul = pd.read_csv(os.path.join(OUT, "null_samples.csv"))
    mo = obs[obs.embed.str.startswith("M")].iloc[0]
    so = obs[obs.embed.str.startswith("S")].iloc[0]
    t1 = stat_lower(mo.r_cv, nul.m_r_cv.values)
    t2 = stat_lower(mo.g_max_deg, nul.m_gmax.values)
    log("\n=== GOZLEMLER (birincil M, 93x93) ===")
    log("  H6b.1 r_cv=%.4f (null %.4f +- %.4f)" % (t1["obs"], t1["null_mean"], t1["null_std"]))
    log("  H6b.2 g_max=%.1f deg (null %.1f +- %.1f)" % (t2["obs"], t2["null_mean"],
                                                        t2["null_std"]))
    ps = np.array([t1["p_raw"], t2["p_raw"]])
    order = np.argsort(ps)
    adj = np.empty(2)
    prev = 0.0
    for rank, i in enumerate(order):
        prev = max(prev, min(1.0, (2 - rank) * ps[i]))
        adj[i] = prev
    tdf = pd.DataFrame([dict(test="H6b.1 r_cv (M)", **t1, p_holm=adj[0]),
                        dict(test="H6b.2 g_max (M)", **t2, p_holm=adj[1])])
    log("\n=== HOLM (m=2) ===")
    for _, r in tdf.iterrows():
        extra = ""
        if r.test.startswith("H6b.2"):
            extra = " | g_max<60 deg: %s" % ("SAGLANDI" if r["obs"] < GAP_FULL else "SAGLANMADI")
        log("  %-16s p_ham=%.4f p_holm=%.4f -> %s%s"
            % (r.test, r.p_raw, r.p_holm, "AYRISIR" if r.p_holm < 0.05 else "ayrisamaz", extra))
    log("  NOT: 1000 ornek -> p >= 1/1001 = %.5f" % (1.0 / 1001.0))

    s1 = stat_lower(so.r_cv, nul.s_r_cv.values)
    s2 = stat_lower(so.g_max_deg, nul.s_gmax.values)
    log("\n=== KO-ANALIZ (S, 51x51; Holm ailesine DAHIL DEGIL) ===")
    log("  S r_cv=%.4f (null %.4f +- %.4f) p_ham=%.4f" % (s1["obs"], s1["null_mean"],
                                                          s1["null_std"], s1["p_raw"]))
    log("  S g_max=%.1f deg (null %.1f +- %.1f) p_ham=%.4f | g_max<60: %s"
        % (s2["obs"], s2["null_mean"], s2["null_std"], s2["p_raw"],
           "SAGLANDI" if s2["obs"] < GAP_FULL else "SAGLANMADI"))
    pd.DataFrame([dict(test="H6b.1 r_cv (S, ko-analiz)", **s1),
                  dict(test="H6b.2 g_max (S, ko-analiz)", **s2)]).to_csv(
        os.path.join(OUT, "co_analysis_S.csv"), index=False)
    tdf.to_csv(os.path.join(OUT, "mx_tests.csv"), index=False)

    # karar sayilari: gomme acilarindan kume (slot) sayisi
    co = pd.read_csv(os.path.join(OUT, "embedding_coords.csv"))
    log("\n=== ADIM 4 KARAR SAYILARI (gommeden) ===")
    for lbl, sub in co.groupby("embed"):
        a = np.sort(sub.angle_deg.values)
        gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
        for thr in (2.0, 5.0, 10.0):
            ncl = max(1, int(np.sum(gaps > thr)))
            log("  %-11s esik %4.0f deg -> %d kume (n=%d, ort. %.2f hucre)"
                % (lbl, thr, ncl, len(a), len(a) / ncl))
        log("  %-11s medyan aralik=%.2f deg | en buyuk bosluk=%.1f deg"
            % (lbl, float(np.median(gaps)), float(gaps.max())))
    return tdf


def explore():
    """KEŞİFSEL: bağlı bileşenler (kim kimde), null'ların bileşen yapısı, literal-birincil karşılaştırma."""
    ann, epg, pen = load_cx()
    W, e, epg_ids, pen_ids = build_W(epg, pen)
    M, S = build_mats(W)
    log("\n=== KEŞİFSEL: BAĞLI BİLEŞENLER (sıfır özdeğer = bileşen sayısı) ===")
    side = {int(r): s for r, s in zip(epg.root_id, epg.side)}
    for lbl, A, ids, kume in (("M(93x93)", M, epg_ids + pen_ids,
                               ["EPG"] * len(epg_ids) + ["PEN"] * len(pen_ids)),
                              ("S(51x51)", S, epg_ids, ["EPG"] * len(epg_ids))):
        n = A.shape[0]
        adj = (A > 0)
        comp = -np.ones(n, int)
        c = 0
        for i in range(n):
            if comp[i] >= 0:
                continue
            stack = [i]
            comp[i] = c
            while stack:
                u = stack.pop()
                for v in np.nonzero(adj[u])[0]:
                    if comp[v] < 0:
                        comp[v] = c
                        stack.append(v)
            c += 1
        log("  %s: %d bilesen" % (lbl, c))
        for k in range(c):
            sel = np.nonzero(comp == k)[0]
            sides = {}
            for i in sel:
                if kume[i] == "EPG":
                    s = side.get(int(ids[i]), "?")
                    sides[s] = sides.get(s, 0) + 1
            log("    bilesen %d: %d hucre (%s) | EPG taraf dagilimi: %s"
                % (k, len(sel), {kk: int(np.sum(np.array(kume)[sel] == kk))
                                 for kk in ("EPG", "PEN")}, sides))
        pd.DataFrame(dict(embed=lbl, node=kume, root_id=ids, comp=comp)).to_csv(
            os.path.join(OUT, "components_%s.csv" % lbl.split("(")[0]), index=False)
    nul = pd.read_csv(os.path.join(OUT, "null_samples.csv"))
    log("  null (n=%d): M sifir-ozdeger ort=%.3f | 2 bilesen orani=%.3f | "
        "S sifir-ozdeger ort=%.3f | 2 bilesen orani=%.3f"
        % (len(nul), nul.m_nzero.mean(), float((nul.m_nzero == 2).mean()),
           nul.s_nzero.mean(), float((nul.s_nzero == 2).mean())))
    log("  literal(indis1,2) vs birincil: M r_cv %.4f vs %.4f | S r_cv %.4f vs %.4f"
        % (nul.m_lit_r_cv.mean(), nul.m_r_cv.mean(), nul.s_lit_r_cv.mean(), nul.s_r_cv.mean()))
    pd.DataFrame([dict(m_nzero_mean=float(nul.m_nzero.mean()),
                       m_two_comp_frac=float((nul.m_nzero == 2).mean()),
                       s_nzero_mean=float(nul.s_nzero.mean()),
                       s_two_comp_frac=float((nul.s_nzero == 2).mean()),
                       m_lit_rcv_mean=float(nul.m_lit_r_cv.mean()),
                       s_lit_rcv_mean=float(nul.s_lit_r_cv.mean()))]).to_csv(
        os.path.join(OUT, "explore.csv"), index=False)


def main():
    a = sys.argv[1:]
    if not a:
        log("kullanim: labels | embed | tests | bonus | merge | explore")
        return
    cmd = a[0]
    if cmd == "labels":
        labels()
    elif cmd == "embed":
        embed()
    elif cmd == "tests":
        tests()
    elif cmd == "bonus":
        bonus()
    elif cmd == "merge":
        merge()
    elif cmd == "explore":
        explore()
    else:
        log("bilinmeyen komut: %s" % cmd)


if __name__ == "__main__":
    main()

