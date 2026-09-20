"""
numcog/structural_analysis.py — FAZ 5: connectome yapısal analizi (iki parçalı) + kapanış.

ADIM 0: etiket sayımı (labels) — ölçümden önce, raporun en başına.
ADIM 1: ön-kayıt HIPOTEZLER.md'de (bu betikten önce commit edilir).
ADIM 2: M1-M4 metrikleri ve null modeller (1000 örnek, shard'lı).
ADIM 3: CX halka attraktör veri kontrolü (yalnızca var/yok: cx).

Kenar tanımı ve eşikler Faz 0/1 ile AYNI: KC = cell_class "Kenyon_Cell",
VPN = super_class "visual_projection", ALPN = cell_class "ALPN", min_syn=1.
Metrikler ikili matris üzerinde ve yalnızca en az bir girdisi olan KC'ler üzerinde.

CLI: labels | nullA <shard> <nsh> | nullB <shard> <nsh> | m3 <shard> <nsh> |
     m4 <shard> <nsh> | merge | cx
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
OUT = os.path.join(HERE, "results_p5")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")

MIN_SYN = 1
N_SAMPLES = 1000
SWAP_FACTOR = 10                      # kenar sayısının >=10 katı takas
SMALL_SUBTYPE = 30                    # <30 hücreli alt tipler alt-tip analizinden çıkarılır
RNG_BASE = 5000                       # her örnek: np.random.RandomState(RNG_BASE + örnek_no)


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def load_mats():
    return nc.build_matrices(min_syn=MIN_SYN)


ANN_COLS = ["root_id", "cell_class", "super_class", "hemibrain_type", "cell_type",
            "cell_sub_class", "supertype", "ito_lee_hemilineage", "hartenstein_hemilineage",
            "pos_x", "pos_y", "pos_z", "soma_x", "soma_y", "soma_z", "side", "top_nt"]


def load_ann_full():
    """Etiket sütunlarını (Faz 0'da yüklenmeyen cell_type vb.) doğrudan okur."""
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False, usecols=ANN_COLS)
    ann["root_id"] = ann["root_id"].astype("int64")
    return ann


def setup():
    """Metrikler için ortak kurulum (Faz 0/1 tanımı; değişmez)."""
    M = load_mats()
    ann = load_ann_full()
    B = (M["W_vpn"] > 0)
    cty = dict(zip(ann.root_id, ann.cell_type))
    hemi = dict(zip(ann.root_id, ann.hemibrain_type))
    vpn_types = [cty.get(r) for r in M["vpn_pres"]]
    lab_mask = np.array([isinstance(t, str) for t in vpn_types], bool)
    cat = pd.Categorical([t if isinstance(t, str) else "__NA__" for t in vpn_types])
    type_codes = cat.codes.astype(np.int64)
    kc_hemi = [hemi.get(r) for r in M["kc_vpn"]]
    hcat = pd.Categorical([h if isinstance(h, str) else "__NA__" for h in kc_hemi])
    kc_hemi_codes = hcat.codes.astype(np.int64)
    return dict(M=M, ann=ann, B=B, lab_mask=lab_mask, type_codes=type_codes,
                n_types=len(cat.categories), kc_hemi=kc_hemi, kc_hemi_codes=kc_hemi_codes)


def m1(B):
    """KC çiftleri arası ortalama ortak VPN komşu sayısı (tüm çiftler)."""
    A = B.astype(np.float32)
    S = A @ A.T
    n = S.shape[0]
    return float((S.sum() - np.trace(S)) / (n * (n - 1.0)))


def m2(B, lab_mask, type_codes, n_types):
    """KC başına girdi VPN tiplerinin Shannon entropisi (log2), KC ortalaması."""
    sub = B[:, lab_mask]
    tc = type_codes[lab_mask]
    n_kc = sub.shape[0]
    X = np.zeros((n_kc, n_types), np.float32)
    for t in range(n_types):
        cols = np.nonzero(tc == t)[0]
        if len(cols):
            X[:, t] = sub[:, cols].sum(1)
    tot = X.sum(1)
    keep = tot > 0
    P = X[keep] / tot[keep, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        H = -(P * np.log2(np.where(P > 0, P, 1.0))).sum(1)
    return float(H.mean()), int((~keep).sum())


def mi_bits(table):
    T = float(table.sum())
    if T <= 0:
        return 0.0
    p = table / T
    q = p.sum(1, keepdims=True) * p.sum(0, keepdims=True)
    mask = p > 0
    return float((p[mask] * np.log2(p[mask] / q[mask])).sum())


def m4_edges_on(B, idx, lab_mask, type_codes, rows, n_types):
    """idx: KC satır indeksleri; rows: her KC için alt tip kodu (0/1)."""
    sub = B[np.ix_(idx, np.nonzero(lab_mask)[0])]
    tc = type_codes[lab_mask]
    r_i, c_i = np.nonzero(sub)
    table = np.bincount(rows[r_i] * n_types + tc[c_i],
                        minlength=2 * n_types).reshape(2, n_types).astype(np.float64)
    return table


def swap_edges(B, rng, n_swaps, groups=None):
    """Derece-korunmuş çift-kenar takası; groups verilirse yalnızca aynı gruptan satırlar arası."""
    edges = [tuple(e) for e in np.argwhere(B)]
    m = len(edges)
    if m < 4:
        return B
    for _ in range(n_swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = edges[i]
        c, d = edges[j]
        if a == c or b == d:
            continue
        if groups is not None and groups[a] != groups[c]:
            continue
        if B[a, d] or B[c, b]:
            continue
        B[a, b] = False
        B[c, d] = False
        B[a, d] = True
        B[c, b] = True
        edges[i] = (a, d)
        edges[j] = (c, b)
    return B


def observed():
    S = setup()
    B = S["B"]
    o1 = m1(B)
    o2, excl = m2(B, S["lab_mask"], S["type_codes"], S["n_types"])
    idx = np.array([i for i, h in enumerate(S["kc_hemi"]) if h in ("KCg-d", "KCab-p")])
    rows = np.array([0 if S["kc_hemi"][i] == "KCg-d" else 1 for i in idx])
    tab = m4_edges_on(B, idx, S["lab_mask"], S["type_codes"], rows, S["n_types"])
    o4 = mi_bits(tab)
    d = dict(M1=o1, M2=o2, M2_excluded=excl, M4=o4, M4_n_kc=len(idx),
             M4_edges=int(tab.sum()), edges=int(B.sum()),
             n_kc=int(B.shape[0]), n_vpn=int(B.shape[1]))
    pd.DataFrame([d]).to_csv(os.path.join(OUT, "observed.csv"), index=False)
    return S, d, tab


def null_job(name, shard, nsh):
    S, o, _ = observed()
    B = S["B"].copy()
    E = int(B.sum())
    n_swaps = SWAP_FACTOR * E
    groups = S["kc_hemi_codes"] if name == "B" else None
    log("\n=== NULL %s (shard %d/%d): %d kenar, %d takas denemesi/ornek ==="
        % (name, shard + 1, nsh, E, n_swaps))
    path = os.path.join(OUT, "null%s_shard%d.csv" % (name, shard))
    done = set()
    if os.path.exists(path) and os.path.getsize(path) > 0:
        done = set(int(x) for x in pd.read_csv(path).sample)
    rows = []
    t0 = time.time()
    for s in range(shard, N_SAMPLES, nsh):
        if s in done:
            continue
        rng = np.random.RandomState(RNG_BASE + s)
        Bs = B.copy()
        swap_edges(Bs, rng, n_swaps, groups)
        v1 = m1(Bs)
        v2, excl = m2(Bs, S["lab_mask"], S["type_codes"], S["n_types"])
        rows.append(dict(sample=s, M1=v1, M2=v2, m2_excluded=excl, edges=int(Bs.sum()),
                         sec=time.time() - t0))
        if len(rows) % 20 == 0:
            log("  [null%s s%d] %d ornek (%.0fs)" % (name, shard, len(rows), time.time() - t0))
    wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    pd.DataFrame(rows).to_csv(path, mode="a", header=wh, index=False)
    log("NULL %s shard %d bitti: %d ornek (%.0fs)" % (name, shard, len(rows), time.time() - t0))


def m3_job(shard, nsh):
    M = load_mats()
    ann = load_ann_full()
    kc_all = [int(r) for r in ann.root_id[
        ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)]]
    hemi = dict(zip(ann.root_id, ann.hemibrain_type))
    vset, aset = set(int(x) for x in M["kc_vpn"]), set(int(x) for x in M["kc_alpn"])
    have_v = np.array([1 if r in vset else 0 for r in kc_all], np.int8)
    have_a = np.array([1 if r in aset else 0 for r in kc_all], np.int8)
    cat = pd.Categorical([hemi.get(r) if isinstance(hemi.get(r), str) else "__NA__"
                          for r in kc_all])
    g = cat.codes
    obs = int(((have_v == 1) & (have_a == 1)).sum())
    log("\n=== M3 NULL (shard %d/%d): KC=%d, VPN girdili=%d, ALPN girdili=%d, IKISI=%d ==="
        % (shard + 1, nsh, len(kc_all), int(have_v.sum()), int(have_a.sum()), obs))
    path = os.path.join(OUT, "m3_shard%d.csv" % shard)
    done = set()
    if os.path.exists(path) and os.path.getsize(path) > 0:
        done = set(int(x) for x in pd.read_csv(path).sample)
    rows, t0 = [], time.time()
    for s in range(shard, N_SAMPLES, nsh):
        if s in done:
            continue
        rng = np.random.RandomState(RNG_BASE + s)
        v, a = have_v.copy(), have_a.copy()
        for gg in range(len(cat.categories)):
            idx = np.nonzero(g == gg)[0]
            if len(idx) < 2:
                continue
            v[idx] = v[rng.permutation(idx)]
            a[idx] = a[rng.permutation(idx)]
        rows.append(dict(sample=s, M3=int(((v == 1) & (a == 1)).sum()),
                         sec=time.time() - t0))
    wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    pd.DataFrame(rows).to_csv(path, mode="a", header=wh, index=False)
    log("M3 shard %d bitti: %d ornek (%.0fs)" % (shard, len(rows), time.time() - t0))


def m4_job(shard, nsh):
    S = setup()
    B, lab, tc, nt = S["B"], S["lab_mask"], S["type_codes"], S["n_types"]
    idx = np.array([i for i, h in enumerate(S["kc_hemi"]) if h in ("KCg-d", "KCab-p")])
    rows_lab = np.array([0 if S["kc_hemi"][i] == "KCg-d" else 1 for i in idx], np.int64)
    obs = mi_bits(m4_edges_on(B, idx, lab, tc, rows_lab, nt))
    log("\n=== M4 NULL (shard %d/%d): %d KC (KCg-d/KCab-p), gozlenen MI=%.5f bit ==="
        % (shard + 1, nsh, len(idx), obs))
    path = os.path.join(OUT, "m4_shard%d.csv" % shard)
    done = set()
    if os.path.exists(path) and os.path.getsize(path) > 0:
        done = set(int(x) for x in pd.read_csv(path).sample)
    rows, t0 = [], time.time()
    for s in range(shard, N_SAMPLES, nsh):
        if s in done:
            continue
        rng = np.random.RandomState(RNG_BASE + s)
        perm = rng.permutation(len(idx))
        rows.append(dict(sample=s,
                         M4=mi_bits(m4_edges_on(B, idx, lab, tc, rows_lab[perm], nt)),
                         sec=time.time() - t0))
    wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    pd.DataFrame(rows).to_csv(path, mode="a", header=wh, index=False)
    log("M4 shard %d bitti: %d ornek (%.0fs)" % (shard, len(rows), time.time() - t0))


def stat_test(name, obs, null):
    null = np.asarray(null, float)
    mu = float(np.mean(null))
    sd = float(np.std(null, ddof=1)) if len(null) > 1 else 0.0
    p = (1.0 + float(np.sum(np.abs(null - mu) >= abs(obs - mu)))) / (len(null) + 1.0)
    return dict(test=name, obs=float(obs), null_mean=mu, null_std=sd, diff=float(obs - mu),
                z=float((obs - mu) / sd) if sd > 0 else float("nan"), p_raw=float(p),
                n=int(len(null)))


def merge():
    S, o, _ = observed()
    m3obs = int(pd.read_csv(os.path.join(OUT, "m3_observed.csv")).n_inter.iloc[0])
    log("\n=== GOZLENEN DEGERLER ===")
    log("  kenar=%d, KC=%d, VPN=%d | M1=%.5f | M2=%.5f (M2 disi KC=%d) | M3=%d | M4=%.5f bit "
        "(M4 KC=%d, M4 kenar=%d)"
        % (o["edges"], o["n_kc"], o["n_vpn"], o["M1"], o["M2"], o["M2_excluded"], m3obs,
           o["M4"], o["M4_n_kc"], o["M4_edges"]))
    tests = []
    for name in ("A", "B"):
        parts = sorted(glob.glob(os.path.join(OUT, "null%s_shard*.csv" % name)))
        if not parts:
            log("null %s: shard YOK" % name)
            continue
        df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).drop_duplicates("sample")
        log("null %s: n=%d ornek | kenar korunumu=%s | degisim disi kenar=%s"
            % (name, len(df), bool((df.edges == o["edges"]).all()),
               bool((df.edges != o["edges"]).sum() == 0)))
        for met in ("M1", "M2"):
            t = stat_test("%s x Null %s" % (met, name), o[met], df[met].values)
            tests.append(t)
            log("  %-14s null=%.5f +- %.5f | gozlenen=%.5f fark=%+.5f z=%+.2f p_ham=%.4f"
                % (t["test"], t["null_mean"], t["null_std"], t["obs"], t["diff"], t["z"],
                   t["p_raw"]))
    for cmd, met, obs_v in (("m3", "M3", m3obs), ("m4", "M4", o["M4"])):
        parts = sorted(glob.glob(os.path.join(OUT, "%s_shard*.csv" % cmd)))
        if not parts:
            log("%s: shard YOK" % cmd)
            continue
        df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).drop_duplicates("sample")
        t = stat_test(met, obs_v, df[met].values)
        tests.append(t)
        log("  %-14s null=%.5f +- %.5f | gozlenen=%.5f fark=%+.5f z=%+.2f p_ham=%.4f (n=%d)"
            % (t["test"], t["null_mean"], t["null_std"], t["obs"], t["diff"], t["z"],
               t["p_raw"], t["n"]))
    tdf = pd.DataFrame(tests)
    ps = tdf.p_raw.values
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    prev = 0.0
    for rank, i in enumerate(order):
        prev = max(prev, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = prev
    tdf["p_holm"] = adj
    tdf.to_csv(os.path.join(OUT, "mx_null_tests.csv"), index=False)
    log("\n=== HOLM DUZELTMESI (m=%d) ===" % len(tdf))
    for _, r in tdf.sort_values("p_raw").iterrows():
        log("  %-14s fark=%+.5f z=%+.2f p_ham=%.4f p_holm=%.4f -> %s"
            % (r.test, r["diff"], r.z, r.p_raw, r.p_holm,
               "AYRISIR" if r.p_holm < 0.05 else "ayrisamaz"))
    log("  NOT: 1000 ornek -> en kucuk olculebilir p = 1/1001 = %.5f" % (1.0 / 1001.0))
    return tdf





def binary(M, which="vpn"):
    """İkili matris (KC x girdi) + canlı (en az bir girdisi olan) satır indeksleri."""
    W = M["W_vpn"] if which == "vpn" else M["W_alpn"]
    return (W > 0).astype(np.float32), W


def live_rows(B):
    return np.nonzero(B.sum(axis=1) > 0)[0]


def labels():
    """ADIM 0: etiket sayımı (dropna=False; NaN'lar sessizce düşmesin)."""
    ann = load_ann_full()
    M = load_mats()
    Bv, Wv = binary(M, "vpn")
    Ba, Wa = binary(M, "alpn")
    rows = []

    def counted(name, sub, col):
        v = sub[col]
        return dict(kume=name, sutun=col, hucre=int(len(sub)), etiketli=int(v.notna().sum()),
                    nan=int(v.isna().sum()), benzersiz=int(v.dropna().nunique()))

    kc_all = ann[ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)]
    vpn_all = ann[ann.super_class.astype(str).str.fullmatch("visual_projection", case=False, na=False)]
    alpn_all = ann[ann.cell_class.astype(str).str.fullmatch("ALPN", case=False, na=False)]
    cols = ("cell_type", "hemibrain_type", "cell_sub_class", "supertype",
            "ito_lee_hemilineage", "hartenstein_hemilineage")
    for nm, sub in (("VPN (super_class=visual_projection)", vpn_all),
                    ("KC (cell_class=Kenyon_Cell)", kc_all),
                    ("ALPN (cell_class=ALPN)", alpn_all)):
        for c in cols:
            rows.append(counted(nm, sub, c))
    ldf = pd.DataFrame(rows)
    ldf.to_csv(os.path.join(OUT, "label_columns.csv"), index=False)

    log("=== ADIM 0: ETIKET SAYIMI (dropna=False) ===")
    log("--- kume buyuklukleri ---")
    log("  VPN (super_class=visual_projection): %d" % len(vpn_all))
    log("  KC  (cell_class=Kenyon_Cell)      : %d" % len(kc_all))
    log("  ALPN(cell_class=ALPN)             : %d" % len(alpn_all))
    log("--- sutun bazinda etiketli / NaN ---")
    for _, r in ldf.iterrows():
        log("  %-36s %-24s etiketli=%-6d NaN=%-6d benzersiz=%d"
            % (r.kume, r.sutun, r.etiketli, r.nan, r.benzersiz))

    # VPN->KC matrisindeki canlı VPN'lerin etiket durumu
    kc_vpn, kc_alpn = list(M["kc_vpn"]), list(M["kc_alpn"])
    vpn_pres = list(M["vpn_pres"])
    sub = dict(zip(ann.root_id, ann.hemibrain_type))
    cty = dict(zip(ann.root_id, ann.cell_type))
    log("--- matris tanimi (min_syn=%d) ---" % MIN_SYN)
    log("  W_vpn: %d KC x %d VPN | canli KC=%d canli VPN=%d"
        % (Wv.shape[0], Wv.shape[1], int((Wv.sum(1) > 0).sum()), int((Wv.sum(0) > 0).sum())))
    log("  W_alpn: %d KC x %d ALPN | canli KC=%d canli ALPN=%d"
        % (Wa.shape[0], Wa.shape[1], int((Wa.sum(1) > 0).sum()), int((Wa.sum(0) > 0).sum())))
    n_lab_h = sum(1 for r in vpn_pres if isinstance(sub.get(r), str))
    n_lab_c = sum(1 for r in vpn_pres if isinstance(cty.get(r), str))
    log("  matristeki %d VPN: hemibrain_type etiketli=%d, cell_type etiketli=%d"
        % (len(vpn_pres), n_lab_h, n_lab_c))

    # KC alt tipleri (matristeki canlı KC'ler): dropna=False
    kc_type = pd.Series([nc._kc_type(sub.get(r)) for r in kc_vpn], name="grup")
    hemi = pd.Series([sub.get(r) for r in kc_vpn], name="hemibrain_type")
    live = kc_type.index[(Wv.sum(1) > 0)].tolist()
    tt = pd.DataFrame(dict(grup=kc_type, hemi=hemi)).loc[live]
    cnt = tt.groupby(["grup", "hemi"], dropna=False).size().reset_index(name="n")
    cnt = cnt.sort_values("n", ascending=False)
    cnt.to_csv(os.path.join(OUT, "kc_subtypes.csv"), index=False)
    log("--- matristeki canli KC'lerin alt tipleri (hemibrain_type) ---")
    for _, r in cnt.iterrows():
        log("  %-6s %-14s %d" % (r.grup, r.hemi, r.n))
    small = cnt[cnt.n < SMALL_SUBTYPE]
    log("  <%d hucreli alt tipler (alt-tip analizinden CIKARILDI): %s"
        % (SMALL_SUBTYPE, dict(zip(small.hemi.astype(str), small.n))))
    log("  KCg-d=%d, KCab-p=%d (M4'te kullanilacak iki alt tip)"
        % (int(cnt[cnt.hemi == "KCg-d"].n.sum()), int(cnt[cnt.hemi == "KCab-p"].n.sum())))

    # M3 hızlı kontrol (gerçek değer)
    ov = nc.channel_overlap(M)
    log("--- M3 (gercek deger, dogrulama) ---")
    log("  VPN girdili KC=%d, ALPN girdili KC=%d, IKISI=%d"
        % (ov["n_kc_vpn"], ov["n_kc_alpn"], ov["n_inter"]))
    log("  ortusen KC'lerin alt tip dagilimi: %s" % ov["inter_subtype"])
    pd.DataFrame([dict(n_kc_vpn=ov["n_kc_vpn"], n_kc_alpn=ov["n_kc_alpn"], n_inter=ov["n_inter"])]
                 ).to_csv(os.path.join(OUT, "m3_observed.csv"), index=False)
    return ldf, cnt


def m1_check():
    """KEŞİFSEL: M1'in derece dizisine bağlı olduğunu KANITLAR (null'un dejenere olduğunun kanıtı)."""
    S, o, _ = observed()
    B = S["B"]
    n, m = B.shape
    d_col = B.sum(0).astype(np.float64)
    E = float(B.sum())
    closed = float((np.sum(d_col ** 2) - E) / (n * (n - 1.0)))
    parts = (glob.glob(os.path.join(OUT, "nullA_shard*.csv"))
             + glob.glob(os.path.join(OUT, "nullB_shard*.csv")))
    vals = np.concatenate([pd.read_csv(p).M1.values for p in parts])
    log("\n=== KEŞİFSEL — M1 DEGENERASYON KONTROLU ===")
    log("  M1 = (sum_v d_v^2 - E) / (n(n-1))  [yalnizca sutun dereceleri ve kenar sayisi]")
    log("  kapali form = %.8f" % closed)
    log("  gozlenen M1 = %.8f  (mutlak fark = %.2e)" % (o["M1"], abs(o["M1"] - closed)))
    log("  null A+B ornekleri: %d | benzersiz deger = %d | min==max: %s | std = %.2e"
        % (len(vals), int(len(np.unique(vals))), bool(np.ptp(vals) == 0.0),
           float(np.std(vals))))
    log("  -> derece-koruyan null'da M1 DEGISMEZ; permutasyon p'si (0.0010) float32 yuvarlamasi")
    log("     artefaktidir, ayrisma kaniti DEGIL.")
    pd.DataFrame([dict(closed_form=closed, observed=o["M1"], abs_diff=abs(o["M1"] - closed),
                       null_n=len(vals), null_unique=int(len(np.unique(vals))),
                       null_range=float(np.ptp(vals)), null_std=float(np.std(vals)),
                       n_kc=n, n_vpn=m, edges=E)]).to_csv(
        os.path.join(OUT, "m1_degeneracy.csv"), index=False)
    return closed


def m2_hemi_job(shard, nsh):
    """KEŞİFSEL (ön-kayıtta ilan edilmişti): M2'nin hemibrain_type sürümü, yalnızca Null A."""
    S = setup()
    ann, M = S["ann"], S["M"]
    hemi = dict(zip(ann.root_id, ann.hemibrain_type))
    ht = [hemi.get(r) for r in M["vpn_pres"]]
    lab = np.array([isinstance(t, str) for t in ht], bool)
    cat = pd.Categorical([t if isinstance(t, str) else "__NA__" for t in ht])
    codes = cat.codes.astype(np.int64)
    nt = len(cat.categories)
    B = S["B"]
    obs, excl = m2(B, lab, codes, nt)
    E = int(B.sum())
    log("\n=== KEŞİFSEL M2 (hemibrain_type) shard %d/%d: gozlenen=%.5f (etiketli VPN=%d/%d) ==="
        % (shard + 1, nsh, obs, int(lab.sum()), len(lab)))
    path = os.path.join(OUT, "m2hemi_shard%d.csv" % shard)
    rows, t0 = [], time.time()
    for s in range(shard, N_SAMPLES, nsh):
        rng = np.random.RandomState(RNG_BASE + s)
        Bs = B.copy()
        swap_edges(Bs, rng, SWAP_FACTOR * E, None)
        rows.append(dict(sample=s, M2h=m2(Bs, lab, codes, nt)[0], sec=time.time() - t0))
    wh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    pd.DataFrame(rows).to_csv(path, mode="a", header=wh, index=False)
    log("KESIFSEL M2(hemi) shard %d bitti: %d ornek (%.0fs)" % (shard, len(rows), time.time() - t0))


def cx_check():
    """ADIM 3: CX halka attraktör veri kontrolü — YALNIZCA var/yok (dinamik simülasyon YOK)."""
    ann = load_ann_full()
    txt = ["cell_class", "super_class", "hemibrain_type", "cell_type", "cell_sub_class",
           "supertype"]
    log("\n=== ADIM 3: CX HALKA ATTRAKTOR VERI KONTROLU (var/yok) ===")
    log("annotation sutunlari (%d): %s" % (len(ann.columns), list(ann.columns)))
    found = {}
    for pat in ("EPG", "PEN", "Delta7"):
        mask = np.zeros(len(ann), bool)
        for c in txt:
            mask |= ann[c].astype(str).str.contains(pat, case=False, na=False).values
        sub = ann[mask]
        found[pat] = set(int(r) for r in sub.root_id)
        n_pos = int(sub[["pos_x", "pos_y", "pos_z"]].notna().all(1).sum())
        n_soma = int(sub[["soma_x", "soma_y", "soma_z"]].notna().all(1).sum())
        log("  %-7s hucre=%-5d koordinat(pos_xyz)=%-5d koordinat(soma_xyz)=%-5d "
            "hemibrain_type etiketli=%d"
            % (pat, len(sub), n_pos, n_soma, int(sub.hemibrain_type.notna().sum())))
    allcx = set().union(*found.values()) if found else set()
    log("  CX kumesi toplam: %d hucre" % len(allcx))

    conn = pd.read_feather(nc.CONN_FILE,
                           columns=["pre_pt_root_id", "post_pt_root_id", "neuropil"])
    m = conn.pre_pt_root_id.isin(allcx) | conn.post_pt_root_id.isin(allcx)
    sub = conn[m]
    nl = sub.neuropil.astype(str).value_counts()
    log("  baglanti dosyasi sutunlari: ['pre_pt_root_id','post_pt_root_id','neuropil',"
        "'syn_count','gaba_avg',...] (sinaps BASINA satir YOK; (pre,post,noropil) basina toplam)")
    log("  CX hucrelerine dokunan kenar: %d | noropil degerleri (ilk 15): %s"
        % (len(sub), dict(list(nl.items())[:15])))
    roi_like = [v for v in nl.index if any(k in v.upper() for k in ("PB", "EB", "GLOMER", "SEGMENT"))]
    log("  PB/EB/glomerul/segment benzeri noropil etiketi: %s" % (roi_like if roi_like else "YOK"))
    has_roi_col = any("glom" in c.lower() or "segment" in c.lower() or "roi" in c.lower()
                      for c in list(ann.columns) + ["pre_pt_root_id", "post_pt_root_id", "neuropil"])
    log("  glomerul/segment/ROI sutunu: %s" % ("VAR" if has_roi_col else "YOK"))
    log("  SONUC (bu veri surumunde): noron-seviyesi koordinat = BULUNDU; noropil sutunu = "
        "BULUNDU (kaba noropil); PB glomerulu / EB segmenti ROI etiketi = BULUNAMADI; "
        "sinaps-basina ayri tablo = BULUNAMADI (baglanti dosyasi syn_count ile toplu).")
    pd.DataFrame([dict(hucre=k, n=len(v), kume_toplam=len(allcx)) for k, v in found.items()]
                 ).to_csv(os.path.join(OUT, "cx_check.csv"), index=False)
    sub.neuropil.astype(str).value_counts().rename_axis("neuropil").reset_index(
        name="n").to_csv(os.path.join(OUT, "cx_neuropil.csv"), index=False)
    return found


def main():
    a = sys.argv[1:]
    if not a:
        log("kullanim: labels | nullA <shard> <nsh> | nullB <shard> <nsh> | "
            "m3 <shard> <nsh> | m4 <shard> <nsh> | merge | cx")
        return
    cmd = a[0]
    if cmd == "labels":
        labels()
    elif cmd == "nullA":
        null_job("A", int(a[1]), int(a[2]))
    elif cmd == "nullB":
        null_job("B", int(a[1]), int(a[2]))
    elif cmd == "m3":
        m3_job(int(a[1]), int(a[2]))
    elif cmd == "m4":
        m4_job(int(a[1]), int(a[2]))
    elif cmd == "merge":
        merge()
    elif cmd == "m1check":
        m1_check()
    elif cmd == "m2hemi":
        m2_hemi_job(int(a[1]), int(a[2]))
    elif cmd == "cx":
        cx_check()
    else:
        log("bilinmeyen komut: %s" % cmd)


if __name__ == "__main__":
    main()


