"""
numcog/cx_geometry.py — FAZ 6-0: CX halka geometrisi keşfi (YALNIZCA ÖLÇÜM).

DİNAMİK SİMÜLASYON YOK. Faz 0–5 dosyaları/sonuçları DEĞİŞTİRİLMEZ.
Ön-kayıt: HIPOTEZLER.md (commit `13647d9`).

Sabit seçimler (ön-kayıtta yazılı): birincil konum sütunu `soma_x/y/z`; açı düzlemi = EPG soma
noktalarının PCA'sının ilk iki bileşeni; PEN açıları aynı tabana izdüşümle; EPG↔PEN bağlantısı
yönsüz toplam; wedge ≈ EPG medyan açısal aralığı (veriden).

CLI: labels | geometry | h61 <shard> <nsh> | h62 | h63 | merge
"""
from __future__ import annotations
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

import number_coding as nc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_p6_0")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

N_PERM = 1000
RNG_BASE = 7000
PRIMARY = ("soma_x", "soma_y", "soma_z")
SECONDARY = ("pos_x", "pos_y", "pos_z")
ANN_COLS = ["root_id", "cell_class", "super_class", "hemibrain_type", "cell_type", "supertype",
            "side", "pos_x", "pos_y", "pos_z", "soma_x", "soma_y", "soma_z"]


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def labels():
    """ADIM 1: etiket/konum sayımı (NaN sayılır) + nöropil EB/PB payı."""
    ann, epg, pen, d7 = load_cx()
    rows = []
    for pat, sub in (("EPG", epg), ("PEN", pen), ("Delta7", d7)):
        for col, tag in ((PRIMARY, "soma_xyz"), (SECONDARY, "pos_xyz")):
            ok = sub[list(col)].notna().all(axis=1)
            rows.append(dict(kume=pat, sutun=tag, hucre=len(sub), dolu=int(ok.sum()),
                             nan=int((~ok).sum())))
    ldf = pd.DataFrame(rows)
    ldf.to_csv(os.path.join(OUT, "label_counts.csv"), index=False)
    log("=== ADIM 1: KONUM/ETIKET SAYIMI ===")
    for _, r in ldf.iterrows():
        log("  %-7s %-9s hucre=%-4d dolu=%-4d nan=%d" % (r.kume, r.sutun, r.hucre, r.dolu, r.nan))
    for pat, sub in (("EPG", epg), ("PEN", pen), ("Delta7", d7)):
        log("  %-7s hemibrain_type: %s | side: %s"
            % (pat, dict(sub.hemibrain_type.value_counts()),
               dict(sub.side.value_counts())))
    d = np.sqrt(((epg[list(PRIMARY)].values - epg[list(SECONDARY)].values) ** 2).sum(1))
    log("  EPG pos<->soma mesafesi: medyan=%.1f ort=%.1f max=%.1f" %
        (np.median(d), d.mean(), d.max()))

    ids = set(int(r) for r in list(epg.root_id) + list(pen.root_id) + list(d7.root_id))
    conn = pd.read_feather(nc.CONN_FILE,
                           columns=["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil"])
    m = conn.pre_pt_root_id.isin(ids) | conn.post_pt_root_id.isin(ids)
    sub = conn[m]
    tot = float(sub.syn_count.sum())
    nl = sub.groupby(sub.neuropil.astype(str), observed=True).syn_count.sum(
        ).sort_values(ascending=False)
    log("  CX kumesine dokunan kenar=%d, toplam sinaps=%.0f" % (len(sub), tot))
    log("  noropil payi (sinaps): " + ", ".join(
        "%s=%.1f%%" % (k, 100 * v / tot) for k, v in list(nl.items())[:8]))
    pd.DataFrame(dict(neuropil=list(nl.index), synapses=list(nl.values))).to_csv(
        os.path.join(OUT, "neuropil_share.csv"), index=False)
    return ldf


def pca_frame(P, Q=None):
    """P'den (n,3) PCA; ilk iki bileşen düzlemi. Q verilirse aynı merkez/tabana izdüşürülür."""
    mu = P.mean(0)
    X = P - mu
    _, sv, Vt = np.linalg.svd(X, full_matrices=False)
    basis = Vt[:2]
    out = {}
    for tag, Z in (("P", P), ("Q", Q)):
        if Z is None:
            continue
        Y = (np.asarray(Z, float) - mu) @ basis.T
        out[tag] = dict(Y=Y, r=np.hypot(Y[:, 0], Y[:, 1]),
                        ang=np.arctan2(Y[:, 1], Y[:, 0]))
    out.update(mu=mu, basis=basis, sv=sv)
    return out


def ring_stats(Y):
    r = np.hypot(Y[:, 0], Y[:, 1])
    ang = np.arctan2(Y[:, 1], Y[:, 0])
    n = len(ang)
    a = np.sort(ang % (2 * np.pi))
    gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]]))
    u = a / (2 * np.pi)
    i = np.arange(1, n + 1)
    V = float((i / n - u).max() + (u - (i - 1) / n).max())
    return dict(r_cv=float(r.std(ddof=1) / r.mean()), r_mean=float(r.mean()),
                r_std=float(r.std(ddof=1)), g_max_deg=float(np.degrees(gaps.max())),
                R=float(abs(np.exp(1j * ang).mean())), kuiper_V=V)


def _rank(v):
    v = np.asarray(v, float)
    order = np.argsort(v, kind="mergesort")
    r = np.empty(len(v), float)
    r[order] = np.arange(1, len(v) + 1, dtype=float)
    sv = v[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = r[order[i:j + 1]].mean()
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = _rank(x), _rank(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / den) if den > 0 else float("nan")


def circmean(ang):
    a = np.asarray(ang, float)
    return float(np.angle(np.exp(1j * a).mean()))


def circdiff(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    return (d + np.pi) % (2 * np.pi) - np.pi


def geometry():
    """ADIM 2: EPG soma PCA açıları (birincil) + PEN izdüşümü."""
    ann, epg, pen, d7 = load_cx()
    P = epg[list(PRIMARY)].values.astype(float)
    Q = pen[list(PRIMARY)].values.astype(float)
    G = pca_frame(P, Q)
    ev = (G["sv"] ** 2) / np.sum(G["sv"] ** 2)
    log("\n=== ADIM 2: ACI ATAMASI (birincil: soma_xyz, PCA ilk iki bilesen) ===")
    log("  EPG n=%d | aciklanan varyans: PC1=%.3f PC2=%.3f PC3=%.3f"
        % (len(P), ev[0], ev[1], ev[2]))
    a = np.sort(np.degrees(G["P"]["ang"]) % 360)
    gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
    log("  EPG aci: min=%.1f medyan=%.1f max=%.1f | aralik: medyan=%.2f min=%.2f max=%.2f (derece)"
        % (a.min(), np.median(a), a.max(), np.median(gaps), gaps.min(), gaps.max()))
    log("  (wedge = medyan aralik = %.2f derece -> esit tiling tahmini = %.1f wedge)"
        % (np.median(gaps), 360.0 / np.median(gaps)))
    g = pd.DataFrame(dict(kume="EPG", root_id=epg.root_id.values,
                          subtype=epg.hemibrain_type.values,
                          x=P[:, 0], y=P[:, 1], z=P[:, 2],
                          pc1=G["P"]["Y"][:, 0], pc2=G["P"]["Y"][:, 1],
                          r=G["P"]["r"], angle_deg=np.degrees(G["P"]["ang"]) % 360))
    h = pd.DataFrame(dict(kume="PEN", root_id=pen.root_id.values,
                          subtype=pen.hemibrain_type.values,
                          x=Q[:, 0], y=Q[:, 1], z=Q[:, 2],
                          pc1=G["Q"]["Y"][:, 0], pc2=G["Q"]["Y"][:, 1],
                          r=G["Q"]["r"], angle_deg=np.degrees(G["Q"]["ang"]) % 360))
    pd.concat([g, h], ignore_index=True).to_csv(os.path.join(OUT, "geometry_angles.csv"),
                                                index=False)
    P2 = epg[list(SECONDARY)].values.astype(float)
    G2 = pca_frame(P2, pen[list(SECONDARY)].values.astype(float))
    pd.DataFrame(dict(root_id=epg.root_id.values,
                      angle_deg_pos=np.degrees(G2["P"]["ang"]) % 360,
                      r_pos=G2["P"]["r"])).to_csv(
        os.path.join(OUT, "geometry_angles_pos.csv"), index=False)
    log("  ikincil (KESIFSEL) pos_xyz acilari: geometry_angles_pos.csv")
    return G


def h61(shard=0, nsh=1):
    """H6.1: halka benzeri mi? (r_cv + en buyuk bosluk) — kovaryans-eslesmis elipsoid null."""
    ann, epg, pen, d7 = load_cx()
    P = epg[list(PRIMARY)].values.astype(float)
    G = pca_frame(P)
    obs = ring_stats(G["P"]["Y"])
    pd.DataFrame([dict(**obs, n=len(P))]).to_csv(
        os.path.join(OUT, "h61_observed.csv"), index=False)
    mu = P.mean(0)
    S = np.cov(P.T)
    ev, EV = np.linalg.eigh(S)                  # S = EV diag(ev) EV^T (tekil olabilir)
    Ls = EV @ np.diag(np.sqrt(np.maximum(ev, 0.0)))   # S = Ls Ls^T
    n = len(P)
    path = os.path.join(OUT, "h61_shard%d.csv" % shard)
    log("\n=== H6.1 (shard %d/%d): gozlenen r_cv=%.4f r_mean=%.1f g_max=%.1f deg R=%.3f V=%.3f ==="
        % (shard + 1, nsh, obs["r_cv"], obs["r_mean"], obs["g_max_deg"], obs["R"],
           obs["kuiper_V"]))
    log("  kovaryans ozdegerleri: %s (tekil mi: %s)"
        % (np.round(ev, 3), bool(ev.min() <= 1e-9 * max(ev.max(), 1e-12))))
    rows, t0 = [], time.time()
    for s in range(shard, N_PERM, nsh):
        rng = np.random.RandomState(RNG_BASE + s)
        Z = rng.normal(size=(n, 3))
        Z = Z - Z.mean(0)
        wz, EVz = np.linalg.eigh(np.cov(Z.T))
        Zw = Z @ (EVz @ np.diag(1.0 / np.sqrt(np.maximum(wz, 1e-300)))) @ EVz.T  # birim kov.
        Nul = mu + Zw @ Ls.T                                                     # tam S
        st = ring_stats(pca_frame(Nul)["P"]["Y"])
        st["sample"] = s
        rows.append(st)
        if len(rows) % 100 == 0:
            log("  [h61 s%d] %d ornek (%.0fs)" % (shard, len(rows), time.time() - t0))
    wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    pd.DataFrame(rows).to_csv(path, mode="a", header=wh, index=False)
    log("H6.1 shard %d bitti: %d ornek (%.0fs)" % (shard, len(rows), time.time() - t0))


def _swap_bipartite(B, rng, n_swaps):
    """Derece-korunmus cift-kenar takasi (satir ve sutun dereceleri korunur)."""
    edges = [tuple(e) for e in np.argwhere(B)]
    m = len(edges)
    if m < 4:
        return B
    for _ in range(n_swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = edges[i]
        c, d = edges[j]
        if a == c or b == d or B[a, d] or B[c, b]:
            continue
        B[a, b] = False
        B[c, d] = False
        B[a, d] = True
        B[c, b] = True
        edges[i] = (a, d)
        edges[j] = (c, b)
    return B


def circmean_w(ang, w):
    a = np.asarray(ang, float)
    w = np.asarray(w, float)
    return float(np.angle((w * np.exp(1j * a)).sum()))


def build_weights(epg, pen):
    """Yonsuz EPG<->PEN agirlik matrisi (satir=EPG, sutun=PEN)."""
    epg_ids = [int(r) for r in epg.root_id]
    pen_ids = [int(r) for r in pen.root_id]
    ei = {r: i for i, r in enumerate(epg_ids)}
    pi = {r: i for i, r in enumerate(pen_ids)}
    conn = pd.read_feather(nc.CONN_FILE,
                           columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
    se, sp = set(epg_ids), set(pen_ids)
    e1 = conn[conn.pre_pt_root_id.isin(se) & conn.post_pt_root_id.isin(sp)]
    e2 = conn[conn.pre_pt_root_id.isin(sp) & conn.post_pt_root_id.isin(se)]
    W = np.zeros((len(epg_ids), len(pen_ids)), float)
    for a, b, w in zip(e1.pre_pt_root_id.values, e1.post_pt_root_id.values, e1.syn_count.values):
        W[ei[int(a)], pi[int(b)]] += float(w)
    for a, b, w in zip(e2.pre_pt_root_id.values, e2.post_pt_root_id.values, e2.syn_count.values):
        W[ei[int(b)], pi[int(a)]] += float(w)
    return W, e1, e2


def h62():
    """H6.2: EPG<->PEN agirligi acisal uzaklikla azaliyor mu? (Spearman + permutasyon + kontrol)"""
    ann, epg, pen, d7 = load_cx()
    G = pca_frame(epg[list(PRIMARY)].values.astype(float),
                  pen[list(PRIMARY)].values.astype(float))
    th_e, th_p = G["P"]["ang"], G["Q"]["ang"]
    W, e1, e2 = build_weights(epg, pen)
    ii, jj = np.nonzero(W > 0)
    w = W[ii, jj]
    dth = np.abs(circdiff(th_e[ii], th_p[jj]))
    rho = spearman(w, dth)
    log("\n=== H6.2: EPG<->PEN yerellik ===")
    log("  EPG->PEN kenar=%d (agirlik=%.0f) | PEN->EPG kenar=%d (agirlik=%.0f)"
        % (len(e1), e1.syn_count.sum(), len(e2), e2.syn_count.sum()))
    log("  yonsuz cift=%d, agirlik toplami=%.0f | Spearman rho(W, |dtheta|) = %.4f (beklenen < 0)"
        % (len(w), w.sum(), rho))
    pd.DataFrame(dict(epg_root_id=[int(epg.root_id.values[i]) for i in ii],
                      pen_root_id=[int(pen.root_id.values[j]) for j in jj],
                      w=w, dtheta_deg=np.degrees(dth))).to_csv(
        os.path.join(OUT, "h62_edges.csv"), index=False)
    rows = []
    t0 = time.time()
    for s in range(N_PERM):
        rng = np.random.RandomState(RNG_BASE + s)
        tp = rng.permutation(th_e)
        rows.append(dict(sample=s, rho=spearman(w, np.abs(circdiff(tp[ii], th_p[jj])))))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "h62_null.csv"), index=False)
    null = np.array([r["rho"] for r in rows])
    p = (1.0 + float(np.sum(np.abs(null) >= abs(rho)))) / (N_PERM + 1.0)
    log("  permutasyon (EPG acilari, n=%d): ort=%.4f sd=%.4f | p(iki-yanli)=%.4f (%.0fs)"
        % (N_PERM, null.mean(), null.std(ddof=1), p, time.time() - t0))

    # kontrol: derece-korunmus rasgele baglanti (20 ornek)
    C = (W > 0)
    rng = np.random.RandomState(RNG_BASE + 4242)
    ctrl = []
    for t in range(20):
        Cs = _swap_bipartite(C.copy(), rng, 10 * int(C.sum()))
        vals = w.copy()
        rng.shuffle(vals)
        i2, j2 = np.nonzero(Cs)
        ctrl.append(spearman(vals, np.abs(circdiff(th_e[i2], th_p[j2]))))
    ctrl = np.array(ctrl)
    pd.DataFrame(dict(kontrol_ornek=np.arange(20), rho=ctrl)).to_csv(
        os.path.join(OUT, "h62_control.csv"), index=False)
    log("  KONTROL (derece-korunmus rastgele baglanti, 20 ornek): rho ort=%.4f sd=%.4f "
        "(gozlenen %.4f)" % (ctrl.mean(), ctrl.std(ddof=1), rho))
    pd.DataFrame([dict(obs_rho=rho, p_perm=p, n_perm=N_PERM, n_pairs=len(w),
                       ctrl_mean=float(ctrl.mean()), ctrl_std=float(ctrl.std(ddof=1)),
                       epg2pen_edges=len(e1), pen2epg_edges=len(e2))]).to_csv(
        os.path.join(OUT, "h62_observed.csv"), index=False)
    return rho, p, ctrl.mean()


def load_cx():
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann["root_id"] = ann["root_id"].astype("int64")
    h = ann.hemibrain_type.astype(str)
    return (ann, ann[h.str.startswith("EPG")].copy(), ann[h.str.startswith("PEN")].copy(),
            ann[h.str.startswith("Delta7")].copy())


def h63():
    """H6.3 (tani, yon yok): PEN_a vs PEN_b — EPG acisina gore sistematik yon kaymasi."""
    ann, epg, pen, d7 = load_cx()
    G = pca_frame(epg[list(PRIMARY)].values.astype(float),
                  pen[list(PRIMARY)].values.astype(float))
    th_e, th_p = G["P"]["ang"], G["Q"]["ang"]
    W, e1, e2 = build_weights(epg, pen)
    sub = pen.hemibrain_type.astype(str).values
    delta = np.full(len(pen), np.nan)
    for j in range(len(pen)):
        col = W[:, j]
        m = col > 0
        if m.sum() == 0:
            continue
        delta[j] = circdiff(circmean_w(th_e[m], col[m]), th_p[j])
    ok = ~np.isnan(delta)
    a = ok & np.array([s.startswith("PEN_a") for s in sub])
    b = ok & np.array([s.startswith("PEN_b") for s in sub])
    ma, mb = circmean(delta[a]), circmean(delta[b])
    stat = abs(circdiff(ma, mb))
    span = (delta[ok] + np.pi) % (2 * np.pi) - np.pi
    log("\n=== H6.3: PEN alt tip yon kaymasi (tani) ===")
    log("  EPG girdisi olan PEN: %d / %d (PEN_a %d, PEN_b %d)"
        % (int(ok.sum()), len(pen), int(a.sum()), int(b.sum())))
    log("  |delta| ort=%.1f deg (delta = EPG-girdi agirlikli aci - PEN soma acisi)"
        % np.degrees(np.abs(span)).mean())
    log("  dairesel ortalama: PEN_a=%+.1f deg (n=%d), PEN_b=%+.1f deg (n=%d)"
        % (np.degrees(ma), int(a.sum()), np.degrees(mb), int(b.sum())))
    log("  |PEN_a - PEN_b| = %.1f derece" % np.degrees(stat))
    pd.DataFrame(dict(root_id=pen.root_id.values, subtype=sub, delta_deg=np.degrees(delta),
                      pen_angle_deg=np.degrees(th_p) % 360)).to_csv(
        os.path.join(OUT, "h63_delta.csv"), index=False)
    lab = np.array([0 if s.startswith("PEN_a") else (1 if s.startswith("PEN_b") else -1)
                    for s in sub])
    idx = np.nonzero(ok & (lab >= 0))[0]
    dl = delta[idx]
    grp = lab[idx]
    rows = []
    for s in range(N_PERM):
        rng = np.random.RandomState(RNG_BASE + s)
        g = rng.permutation(grp)
        rows.append(dict(sample=s,
                         stat=abs(circdiff(circmean(dl[g == 0]), circmean(dl[g == 1])))))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "h63_null.csv"), index=False)
    null = np.array([r["stat"] for r in rows])
    p = (1.0 + float(np.sum(null >= stat))) / (N_PERM + 1.0)
    log("  permutasyon (alt tip etiketleri, n=%d): ort=%.1f deg sd=%.1f | p=%.4f"
        % (N_PERM, np.degrees(null.mean()), np.degrees(null.std(ddof=1)), p))
    pd.DataFrame([dict(obs_shift_deg=float(np.degrees(stat)), p_perm=p, n_perm=N_PERM,
                       n_pen_a=int(a.sum()), n_pen_b=int(b.sum()),
                       mean_abs_delta_deg=float(np.degrees(np.abs(span)).mean()))]).to_csv(
        os.path.join(OUT, "h63_observed.csv"), index=False)
    return float(np.degrees(stat)), p


def stat_test(name, obs, null, side="both"):
    null = np.asarray(null, float)
    mu = float(null.mean())
    sd = float(null.std(ddof=1)) if len(null) > 1 else 0.0
    if side == "lower":
        p = (1.0 + float(np.sum(null <= obs))) / (len(null) + 1.0)
    else:
        p = (1.0 + float(np.sum(np.abs(null - mu) >= abs(obs - mu)))) / (len(null) + 1.0)
    return dict(test=name, obs=float(obs), null_mean=mu, null_std=sd, diff=float(obs - mu),
                z=float((obs - mu) / sd) if sd > 0 else float("nan"), p_raw=float(p),
                n=int(len(null)))


def merge():
    obs61 = pd.read_csv(os.path.join(OUT, "h61_observed.csv")).iloc[0]
    parts = sorted(glob.glob(os.path.join(OUT, "h61_shard*.csv")))
    n61 = pd.concat([pd.read_csv(p) for p in parts],
                    ignore_index=True).drop_duplicates("sample")
    t61 = stat_test("H6.1 r_cv (halka)", float(obs61.r_cv), n61.r_cv.values, side="lower")
    o62 = pd.read_csv(os.path.join(OUT, "h62_observed.csv")).iloc[0]
    n62 = pd.read_csv(os.path.join(OUT, "h62_null.csv"))
    t62 = stat_test("H6.2 rho (yerellik)", float(o62.obs_rho), n62.rho.values)
    o63 = pd.read_csv(os.path.join(OUT, "h63_observed.csv")).iloc[0]
    n63 = pd.read_csv(os.path.join(OUT, "h63_null.csv"))
    t63 = stat_test("H6.3 kayma (tani)", float(o63.obs_shift_deg),
                    np.degrees(n63.stat.values))     # null radyandan dereceye (birim uyumu)
    tdf = pd.DataFrame([t61, t62, t63])
    ps = tdf.p_raw.values
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    prev = 0.0
    for rank, i in enumerate(order):
        prev = max(prev, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = prev
    tdf["p_holm"] = adj
    tdf.to_csv(os.path.join(OUT, "mx_tests.csv"), index=False)
    log("\n=== GOZLEMLER ===")
    log("  H6.1: r_cv=%.4f (null ort=%.4f sd=%.4f) | g_max=%.1f deg | R=%.3f | Kuiper V=%.3f"
        % (t61["obs"], t61["null_mean"], t61["null_std"], obs61.g_max_deg, obs61.R,
           obs61.kuiper_V))
    log("  H6.2: rho=%+.4f (null ort=%+.4f) | KONTROL (derece-korunmus) rho ort=%+.4f sd=%.4f"
        % (t62["obs"], t62["null_mean"], o62.ctrl_mean, o62.ctrl_std))
    log("  H6.3: kayma=%.1f deg (null ort=%.1f deg +- %.1f) | |delta| ort=%.1f deg"
        % (t63["obs"], t63["null_mean"], t63["null_std"], o63.mean_abs_delta_deg))
    log("\n=== HOLM (m=3) ===")
    for _, r in tdf.sort_values("p_raw").iterrows():
        log("  %-20s fark=%+.4f z=%+.2f p_ham=%.4f p_holm=%.4f -> %s"
            % (r.test, r["diff"], r.z, r.p_raw, r.p_holm,
               "AYRISIR" if r.p_holm < 0.05 else "ayrisamaz"))
    log("  NOT: 1000 ornek -> p >= 1/1001 = %.5f" % (1.0 / 1001.0))

    ann, epg, pen, d7 = load_cx()
    P = epg[list(PRIMARY)].values.astype(float)
    a = np.sort(np.degrees(pca_frame(P)["P"]["ang"]) % 360)
    gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
    med = float(np.median(gaps))
    nd = pd.read_csv(os.path.join(OUT, "h63_delta.csv"))
    log("\n=== ADIM 4 KARAR SAYILARI (yalnizca olcumden) ===")
    log("  n_EPG=%d | medyan aralik=%.2f deg -> esit tiling wedge tahmini=%.1f"
        % (len(a), med, 360.0 / med))
    log("  en buyuk bosluk=%.1f deg -> bu bosluga dusen 'eksik' wedge=%.1f"
        % (gaps.max(), gaps.max() / med))
    log("  PEN: %d (PEN_a %d, PEN_b %d) | Delta7: %d | EPG girdili PEN: %d"
        % (len(pen), int(pen.hemibrain_type.astype(str).str.startswith("PEN_a").sum()),
           int(pen.hemibrain_type.astype(str).str.startswith("PEN_b").sum()), len(d7),
           int((~nd.delta_deg.isna()).sum())))
    return tdf


def explore():
    """KEŞİFSEL: (a) sol/sağ yapısı, (b) veriden slot (küme) sayısı, (c) pos_xyz sağlamlığı."""
    ann, epg, pen, d7 = load_cx()
    P = epg[list(PRIMARY)].values.astype(float)
    Q = pen[list(PRIMARY)].values.astype(float)
    G = pca_frame(P, Q)
    ang = np.degrees(G["P"]["ang"]) % 360
    side = epg.side.astype(str).values
    log("\n=== KEŞİFSEL (a): SOL/SAĞ YAPISI ===")
    for sd in ("left", "right"):
        a = np.sort(ang[side == sd])
        gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
        log("  %-5s n=%-3d aci araligi [%.1f, %.1f] | medyan aralik=%.2f | en buyuk bosluk=%.1f"
            % (sd, len(a), a.min(), a.max(), np.median(gaps), gaps.max()))
    # sol-sag eslesme: her sol hucreye en yakin sag hucrenin aci farki
    L, R = ang[side == "left"], ang[side == "right"]
    d = [np.degrees(np.abs(circdiff(np.radians(L[i]), np.radians(R)))).min() for i in range(len(L))]
    d = np.array(d)
    log("  sol->en yakin sag aci farki: medyan=%.2f deg, <%d deg olan: %d/%d"
        % (np.median(d), 5, int((d < 5).sum()), len(L)))

    log("\n=== KEŞİFSEL (b): VERIDEN SLOT (WEDGE) SAYISI ===")
    a = np.sort(ang)
    gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
    for thr in (2.0, 5.0, 10.0):
        cuts = np.nonzero(gaps > thr)[0]
        ncl = len(cuts)
        log("  esik %.0f deg -> kume sayisi=%d (ort. kume buyuklugu=%.2f)"
            % (thr, ncl, len(a) / ncl))
    log("  sol taraf tek basina: kume sayisi (esik 5 deg) = %d"
        % len(np.nonzero(np.diff(np.concatenate([np.sort(L), [np.sort(L)[0] + 360]])) > 5.0)[0]))

    log("\n=== KEŞİFSEL (c): pos_xyz SAGLAMLIGI (birincil metrikler pos ile) ===")
    P2 = epg[list(SECONDARY)].values.astype(float)
    st2 = ring_stats(pca_frame(P2)["P"]["Y"])
    log("  pos_xyz: r_cv=%.4f g_max=%.1f deg R=%.3f" % (st2["r_cv"], st2["g_max_deg"], st2["R"]))
    Q2 = pen[list(SECONDARY)].values.astype(float)
    G2 = pca_frame(P2, Q2)
    W, e1, e2 = build_weights(epg, pen)
    ii, jj = np.nonzero(W > 0)
    rho2 = spearman(W[ii, jj], np.abs(circdiff(G2["P"]["ang"][ii], G2["Q"]["ang"][jj])))
    log("  pos_xyz: H6.2 rho=%.4f (birincil soma ile %.4f)" % (rho2, spearman(
        W[ii, jj], np.abs(circdiff(np.radians(ang[ii]),
                                   np.radians(np.degrees(G["Q"]["ang"]) % 360)[jj])))))
    pd.DataFrame([dict(soma_r_cv=float(ring_stats(G["P"]["Y"])["r_cv"]),
                       pos_r_cv=float(st2["r_cv"]),
                       soma_g_max=float(ring_stats(G["P"]["Y"])["g_max_deg"]),
                       pos_g_max=float(st2["g_max_deg"]),
                       lr_near_median_deg=float(np.median(d)),
                       lr_near_lt5deg=int((d < 5).sum()), n_left=len(L), n_right=len(R))]).to_csv(
        os.path.join(OUT, "explore.csv"), index=False)
    return st2


def main():
    a = sys.argv[1:]
    if not a:
        log("kullanim: labels | geometry | h61 <shard> <nsh> | h62 | h63 | merge")
        return
    cmd = a[0]
    if cmd == "labels":
        labels()
    elif cmd == "geometry":
        geometry()
    elif cmd == "h61":
        h61(int(a[1]), int(a[2]))
    elif cmd == "h62":
        h62()
    elif cmd == "h63":
        h63()
    elif cmd == "merge":
        merge()
    elif cmd == "explore":
        explore()
    else:
        log("bilinmeyen komut: %s" % cmd)


if __name__ == "__main__":
    main()


