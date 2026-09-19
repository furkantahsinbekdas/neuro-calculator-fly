"""
numcog/number_coding.py — FAZ 1: sayı kodlama katmanı.

1-9 sayılarını üç kodla temsil eder ve ölçer:
  * hash          : sayının deterministik hash'i (yapısız taban çizgisi).
  * coarse_direct : 265 VPN üzerinde Gauss ayarlı kaba kod (KC katmanı YOK).
  * coarse_kc     : aynı kaba kod + gerçek VPN->KC matrisi (427 KC) + aktivasyon kuralı.

Yalnızca ÖLÇER (flysim/cognitive_matrix/sniff import edilmez). VPN->KC matrisi
Faz 0 kararına göre gerçek kablolamadan (>=3 sinaps) kurulur. Sayı->VPN ataması
keyfîdir; gerçek olan yalnızca aşağı akış VPN->KC kablolamasıdır.
"""
from __future__ import annotations
import os
import json
import hashlib

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONN_FILE = os.path.join(ROOT, "proofread_connections_783.feather")
ANN_FILE = os.path.join(ROOT, "annotations_783.tsv")
OUT = os.path.join(HERE, "results_p1")

NUMBERS = list(range(1, 10))          # 1..9
SIGMAS = (0.5, 1.0, 1.5)
ACT_THRESH = 0.5                      # "aktif VPN" eşiği (Gauss aktivasyonu)
COUNT_KS = (2, 3, 4)                  # eş-zamanlı VPN sayısı (coincidence)
SYN_KS = (2, 3, 4)                    # sinaps-ağırlıklı toplam eşiği
TOPK_KS = (5, 10, 20, 40)             # APL-benzeri top-k
N_PERMS = 20                          # VPN->sayı-ekseni permütasyon sayısı

_CACHE = {}


def _load():
    if "ann" not in _CACHE:
        ann = pd.read_csv(
            ANN_FILE, sep="\t", low_memory=False,
            usecols=["root_id", "cell_class", "super_class", "hemibrain_type"])
        ann["root_id"] = ann["root_id"].astype("int64")
        _CACHE["ann"] = ann
        conn = pd.read_feather(
            CONN_FILE,
            columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
        _CACHE["conn"] = conn
    return _CACHE["ann"], _CACHE["conn"]


def build_matrices(min_syn=3):
    """Gerçek VPN->KC (W_vpn) ve ALPN->KC (W_alpn) matrislerini kur.

    Girdi uzayı Faz 0'daki '265 VPN' (en az 1 kenarı olan) ve '685 ALPN'dir; kenarlar
    min_syn'den küçükse 0'a çekilir (sniff.circuit'in >=3 eşiğiyle aynı mantık).
    """
    ann, conn = _load()
    kc = set(int(r) for r in ann.root_id[
        ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)])
    alpn = sorted(int(r) for r in ann.root_id[
        ann.cell_class.astype(str).str.fullmatch("ALPN", case=False, na=False)])
    vpn = sorted(int(r) for r in ann.root_id[
        ann.super_class.astype(str).str.fullmatch("visual_projection", case=False, na=False)])

    sub = dict(zip(ann.root_id, ann.hemibrain_type))

    def build(pre_set):
        e = conn[(conn.pre_pt_root_id.isin(pre_set)) &
                 (conn.post_pt_root_id.isin(kc))]
        e = e[e.syn_count >= min_syn]
        posts = sorted(set(int(r) for r in e.post_pt_root_id))
        pres = sorted(set(int(r) for r in e.pre_pt_root_id))
        pi = {r: i for i, r in enumerate(pres)}
        qi = {r: i for i, r in enumerate(posts)}
        W = np.zeros((len(posts), len(pres)), dtype=np.float32)
        for pre, post, w in zip(e.pre_pt_root_id.values,
                                e.post_pt_root_id.values, e.syn_count.values):
            W[qi[int(post)], pi[int(pre)]] += float(w)
        return W, pres, posts

    W_vpn, vpn_pres, kc_vpn = build(set(vpn))
    W_alpn, alpn_pres, kc_alpn = build(set(alpn))
    return {
        "min_syn": min_syn,
        "W_vpn": W_vpn, "vpn_pres": vpn_pres, "kc_vpn": kc_vpn,
        "W_alpn": W_alpn, "alpn_pres": alpn_pres, "kc_alpn": kc_alpn,
        "subtype": sub, "n_kc_all": len(kc),
    }


# --------------------------------------------------------------------------- #
# yardımcılar: kosinüs, sıra, Spearman
# --------------------------------------------------------------------------- #
def rankdata(a):
    sorter = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=np.float64)
    ranks[sorter] = np.arange(1, len(a) + 1)
    # bağlar için ortalama sıra (kosinus gerçel değer olduğundan nadiren gerekir)
    u, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    for j in np.where(cnt > 1)[0]:
        idx = np.where(inv == j)[0]
        ranks[idx] = ranks[idx].mean()
    return ranks


def spearman(x, y):
    rx, ry = rankdata(np.asarray(x, float)), rankdata(np.asarray(y, float))
    if np.std(rx) < 1e-12 or np.std(ry) < 1e-12:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def sim_matrix(codes):
    """codes: (N, D) -> NxN kosinüs benzerlik matrisi."""
    N = len(codes)
    S = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            S[i, j] = cosine(codes[i], codes[j])
    return S


def rho_from_sim(S, numbers):
    """Spearman ρ(kosinüs benzerlik, |n-m|) — köşegen dışı çiftler üzerinde."""
    sims, dists = [], []
    N = S.shape[0]
    for i in range(N):
        for j in range(i + 1, N):
            sims.append(S[i, j])
            dists.append(abs(numbers[i] - numbers[j]))
    return spearman(sims, dists)
# --------------------------------------------------------------------------- #
# kodlayıcılar
# --------------------------------------------------------------------------- #
def gauss_codes(n_vpn, sigma, seed):
    """A[9, n_vpn]: n -> Gauss aktivasyon. VPN->sayı-ekseni ataması tohumlu permütasyon;
    pozisyonlar linspace(1,9,n_vpn), unit->pozisyon eşlemesi karılmış."""
    rng = np.random.RandomState(seed)
    positions = np.linspace(1.0, 9.0, n_vpn)
    perm = rng.permutation(n_vpn)
    pos = positions[perm]                      # pos[i] = VPN i'nin tercih ettiği sayı
    A = np.zeros((9, n_vpn), dtype=np.float32)
    for n in NUMBERS:
        d = n - pos
        A[n - 1] = np.exp(-(d * d) / (2.0 * sigma * sigma))
    return A, pos


def hash_codes(dim, active, seed=0):
    """B[9, dim]: deterministik, yapısız seyrek ikili kod (hash taban çizgisi)."""
    B = np.zeros((9, dim), dtype=np.float32)
    for n in NUMBERS:
        key = ("%d|%d" % (n, seed)).encode()
        rng = np.random.RandomState(int.from_bytes(hashlib.sha256(key).digest()[:4], "little"))
        idx = rng.choice(dim, size=active, replace=False)
        B[n - 1, idx] = 1.0
    return B


# --------------------------------------------------------------------------- #
# KC aktivasyon kuralları (iki kol: sabit eşik + top-k)
# --------------------------------------------------------------------------- #
def binary_active(A_row):
    return A_row > ACT_THRESH


def activate_count(A_row, W):
    """Eş-zamanlı aktif VPN partner SAYISI (coincidence, ağırlıksız)."""
    act = binary_active(A_row)
    partner = (W > 0).astype(np.float32)
    return partner @ act.astype(np.float32)          # [n_kc]


def activate_syn(A_row, W):
    """Aktif partnerlerin sinaps TOPLAMI (sinaps-ağırlıklı)."""
    act = binary_active(A_row)
    return W @ act.astype(np.float32)                # [n_kc]


def activate_weighted(A_row, W):
    """Gerçel ağırlıklı toplam (top-k skoru)."""
    return W @ A_row.astype(np.float32)


def kc_codes(A, W, fire_fn):
    """9 sayı -> KC kod matrisi (9, n_kc), verilen ateşleme kuralıyla."""
    return np.array([fire_fn(A[n], W) for n in range(9)], dtype=np.float32)


# --------------------------------------------------------------------------- #
# ölçüm yardımcıları
# --------------------------------------------------------------------------- #
def code_metrics(codes):
    N = codes.shape[0]
    active = (codes > 0).sum(axis=1)
    S = sim_matrix(codes)
    rho = rho_from_sim(S, NUMBERS)
    off = [S[i, j] for i in range(N) for j in range(N) if i != j]
    adj = [S[i, i + 1] for i in range(N - 1)]
    return {
        "rho": rho,
        "active_median": float(np.median(active)),
        "active_min": int(active.min()),
        "active_per_num": [int(a) for a in active],
        "max_off_cos": float(max(off)),
        "max_adj_cos": float(max(adj)),
        "sim": S,
    }
def degree_preserving_shuffle(W, seed, swaps=200000):
    """Degree-preserving karıştırma: çift-kenar takası (row/column dereceleri korunur),
    sonra sinaps ağırlıkları kenar destek kümesi üzerine rastgele dağıtılır."""
    rng = np.random.RandomState(seed)
    nk, nv = W.shape
    B = (W > 0).astype(np.int8)
    edges = [tuple(e) for e in zip(*np.nonzero(B))]
    m = len(edges)
    for _ in range(swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = edges[i]
        c, d = edges[j]
        if a == c or b == d:
            continue
        if B[a, d] or B[c, b]:
            continue
        B[a, b] = 0
        B[c, d] = 0
        B[a, d] = 1
        B[c, b] = 1
        edges[i] = (a, d)
        edges[j] = (c, b)
    vals = W[W > 0].copy()
    rng.shuffle(vals)
    Wsh = np.zeros_like(W)
    Wsh[B > 0] = vals
    return Wsh


def topk_codes(A, W, k):
    """Her sayı için en yüksek aktivasyonlu k KC (bağlar dahil olabilir)."""
    out = []
    for n in range(9):
        score = activate_weighted(A[n], W)
        thr = np.sort(score)[-k] if k <= len(score) else score.min()
        out.append(score >= thr)
    return np.array(out, dtype=np.float32)


# --------------------------------------------------------------------------- #
# iki sayı birlikte sunumu (VPN aktivasyon düzeyinde, henüz öğrenme yok)
# --------------------------------------------------------------------------- #
def two_number_modes(n_vpn, sigma, seed=0):
    """(i) ayrı popülasyonlar: iki yarıya ayrılmış VPN kümesi; (ii) konjunktif: aynı
    küme üzerinde çarpım. Döndürür: her mod için 81 sıralı çift kodu (9*9, n_vpn)."""
    half1 = n_vpn // 2
    A1, _ = gauss_codes(half1, sigma, seed)             # n1 -> H1 (yarım 1)
    A2, _ = gauss_codes(n_vpn - half1, sigma, seed + 1)  # n2 -> H2 (yarım 2)
    Afull, _ = gauss_codes(n_vpn, sigma, seed + 2)       # tam küme (konjunktif için)

    sep = np.zeros((81, n_vpn), dtype=np.float32)
    con = np.zeros((81, n_vpn), dtype=np.float32)
    for n1 in NUMBERS:
        for n2 in NUMBERS:
            r = (n1 - 1) * 9 + (n2 - 1)
            sep[r, :half1] = A1[n1 - 1]
            sep[r, half1:] = A2[n2 - 1]
            con[r] = Afull[n1 - 1] * Afull[n2 - 1]      # konjunktif (çarpım)
    return sep, con


def recover(codes, refs, labels):
    """codes: (N,D); refs: (9,D) tek-sayı referansları; labels: (N,) gerçek indeks (0..8).
    Her kodun argmax-kosinüs referansı gerçek etiketle eşleşiyorsa doğru. Doğruluk döndürür."""
    ok = 0
    for c, lab in zip(codes, labels):
        sims = np.array([cosine(c, r) for r in refs])
        ok += int(np.argmax(sims) == lab)
    return ok / len(codes)


def _pair_labels():
    return np.array([(n1 - 1) * 9 + (n2 - 1) for n1 in NUMBERS for n2 in NUMBERS])


def sweep(W, nk, nv, seed=0):
    rows = []
    for sigma in SIGMAS:
        A, _ = gauss_codes(nv, sigma, seed)
        m = code_metrics(A)
        m.update(kind="coarse_direct", sigma=sigma, rule="direct", param=0)
        rows.append(m)
        for k in COUNT_KS:
            c = kc_codes(A, W, lambda a, w: activate_count(a, w) >= k)
            m = code_metrics(c)
            m.update(kind="coarse_kc", sigma=sigma, rule="count", param=k)
            rows.append(m)
        for t in SYN_KS:
            c = kc_codes(A, W, lambda a, w: activate_syn(a, w) >= t)
            m = code_metrics(c)
            m.update(kind="coarse_kc", sigma=sigma, rule="syn", param=t)
            rows.append(m)
        for k in TOPK_KS:
            c = topk_codes(A, W, k)
            m = code_metrics(c)
            m.update(kind="coarse_kc", sigma=sigma, rule="topk", param=k)
            rows.append(m)
    for active in (5, 10, 20):
        B = hash_codes(nk, active, seed=0)
        m = code_metrics(B)
        m.update(kind="hash", sigma=0.0, rule="hash", param=active)
        rows.append(m)
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "sim"} for r in rows])
    return df


def perm_stats(W, nk, nv, n_perms=N_PERMS):
    """VPN->sayı-ekseni atama permütasyonları arasında ρ (ortalama ± std)."""
    rows = []
    for sigma in SIGMAS:
        rhos = []
        for seed in range(n_perms):
            A, _ = gauss_codes(nv, sigma, seed)
            rhos.append(code_metrics(A)["rho"])
        rows.append(dict(kind="coarse_direct", sigma=sigma, rule="direct", param=0,
                         n=n_perms, rho_mean=float(np.mean(rhos)),
                         rho_std=float(np.std(rhos, ddof=1))))
    for sigma in SIGMAS:
        for rule in ("count", "syn", "topk"):
            for param in (COUNT_KS if rule == "count" else SYN_KS if rule == "syn" else TOPK_KS):
                rhos = []
                for seed in range(n_perms):
                    A, _ = gauss_codes(nv, sigma, seed)
                    if rule == "count":
                        c = kc_codes(A, W, lambda a, w: activate_count(a, w) >= param)
                    elif rule == "syn":
                        c = kc_codes(A, W, lambda a, w: activate_syn(a, w) >= param)
                    else:
                        c = topk_codes(A, W, param)
                    rhos.append(code_metrics(c)["rho"])
                rows.append(dict(kind="coarse_kc", sigma=sigma, rule=rule, param=param,
                                 n=n_perms, rho_mean=float(np.mean(rhos)),
                                 rho_std=float(np.std(rhos, ddof=1))))
    # hash permütasyon duyarlılığı (tohum varyansı)
    for active in (10,):
        rhos = []
        for seed in range(n_perms):
            B = hash_codes(nk, active, seed)
            rhos.append(code_metrics(B)["rho"])
        rows.append(dict(kind="hash", sigma=0.0, rule="hash", param=active,
                         n=n_perms, rho_mean=float(np.mean(rhos)),
                         rho_std=float(np.std(rhos, ddof=1))))
    return pd.DataFrame(rows)
def run_two_number(nv, sigma=1.0, seed=0):
    """İki sayının birlikte sunumu: (i) ayrı popülasyonlar vs (ii) konjunktif çarpım.
    Her mod için n1/n2 kurtarma doğruluğu + 81 çift kodun kosinüs yapısı."""
    sep, con = two_number_modes(nv, sigma, seed)
    half1 = nv // 2
    ref1, _ = gauss_codes(half1, sigma, seed)
    ref2, _ = gauss_codes(nv - half1, sigma, seed + 1)
    reffull, _ = gauss_codes(nv, sigma, seed + 2)
    labels = _pair_labels()
    n1lbl = labels // 9
    n2lbl = labels % 9
    acc_sep_n1 = recover(sep[:, :half1], ref1, n1lbl)
    acc_sep_n2 = recover(sep[:, half1:], ref2, n2lbl)
    acc_con_n1 = recover(con, reffull, n1lbl)
    acc_con_n2 = recover(con, reffull, n2lbl)

    def stats(S):
        off = [S[i, j] for i in range(81) for j in range(81) if i != j]
        return float(np.mean(off)), float(np.max(off))

    S_sep, S_con = sim_matrix(sep), sim_matrix(con)
    return {
        "acc_sep_n1": acc_sep_n1, "acc_sep_n2": acc_sep_n2,
        "acc_con_n1": acc_con_n1, "acc_con_n2": acc_con_n2,
        "sep_mean_off": stats(S_sep)[0], "sep_max_off": stats(S_sep)[1],
        "con_mean_off": stats(S_con)[0], "con_max_off": stats(S_con)[1],
    }


def _kc_type(name):
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return "?"
    s = str(name)
    if s.startswith("KCa'b'"):
        return "apbp"
    if s.startswith("KCab"):
        return "ab"
    if s.startswith("KCg"):
        return "g"
    return "other"


def channel_overlap(M):
    """Hem VPN->KC hem ALPN->KC girdisi alan KC'ler: sayı, alt tip, her iki matristeki toplam ağırlık."""
    from collections import Counter
    vset, aset = set(M["kc_vpn"]), set(M["kc_alpn"])
    inter = sorted(vset & aset)
    cnt = Counter(_kc_type(M["subtype"].get(r)) for r in inter)
    vi = {r: i for i, r in enumerate(M["kc_vpn"])}
    ai = {r: i for i, r in enumerate(M["kc_alpn"])}
    vpn_syn = float(M["W_vpn"][[vi[r] for r in inter]].sum())
    alpn_syn = float(M["W_alpn"][[ai[r] for r in inter]].sum())
    return {
        "n_kc_vpn": len(vset), "n_kc_alpn": len(aset), "n_inter": len(inter),
        "inter_subtype": dict(cnt), "vpn_syn_onto_inter": vpn_syn,
        "alpn_syn_onto_inter": alpn_syn,
    }


def make_plots(df, W, nk, nv, best_row):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ρ çubuk grafiği
    fig, ax = plt.subplots(figsize=(11, 4.5))
    labels = df.apply(lambda r: "%s σ=%.1f %s=%s" % (r.kind, r.sigma, r.rule, r.param), axis=1)
    ax.bar(range(len(df)), df.rho, color=["#888" if k == "hash" else "#c44" if k == "coarse_kc"
                                          else "#44c" for k in df.kind])
    ax.axhline(-0.5, ls="--", c="k", lw=1, label="U1 eşiği (ρ=-0.5)")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_ylabel("Spearman ρ (benzerlik vs |n-m|)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "rho_by_config.png"), dpi=120)
    plt.close(fig)

    # aktif KC ortancası
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(range(len(df)), df.active_median,
           color=["#888" if k == "hash" else "#c44" if k == "coarse_kc" else "#44c" for k in df.kind])
    ax.axhline(5, ls="--", c="k", lw=1, label="U2 eşiği (ortanca ≥ 5)")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_ylabel("aktif KC (ortanca)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "active_kc_by_config.png"), dpi=120)
    plt.close(fig)

    # benzerlik ısı haritaları
    A, _ = gauss_codes(nv, 1.0, 0)
    for name, codes in [("coarse_direct", A), ("coarse_kc_best", None)]:
        if codes is None:
            rule, param = best_row["rule"], best_row["param"]
            if rule == "count":
                codes = kc_codes(A, W, lambda a, w: activate_count(a, w) >= param)
            elif rule == "syn":
                codes = kc_codes(A, W, lambda a, w: activate_syn(a, w) >= param)
            else:
                codes = topk_codes(A, W, param)
        S = sim_matrix(codes)
        fig, ax = plt.subplots(figsize=(4.5, 4))
        im = ax.imshow(S, vmin=0, vmax=1, cmap="viridis")
        ax.set_xticks(range(9)); ax.set_xticklabels(range(1, 10))
        ax.set_yticks(range(9)); ax.set_yticklabels(range(1, 10))
        ax.set_title("%s (kosinus benzerligi)" % name)
        fig.colorbar(im)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "sim_%s.png" % name), dpi=120)
        plt.close(fig)
def main():
    os.makedirs(OUT, exist_ok=True)
    M = build_matrices(min_syn=1)          # tüm kanıtlanmış kenarlar -> 265 VPN x 427 KC
    W = M["W_vpn"]
    nk, nv = W.shape
    n_live_kc = int((W.sum(axis=1) > 0).sum())
    n_live_vpn = int((W.sum(axis=0) > 0).sum())
    print("VPN->KC matrisi: %d KC x %d VPN | canli KC=%d, canli VPN=%d (min_syn=%d)"
          % (nk, nv, n_live_kc, n_live_vpn, M["min_syn"]))
    print("ALPN->KC matrisi: %d KC x %d ALPN" % M["W_alpn"].shape)
    M3 = build_matrices(min_syn=3)
    print("Not: >=3 sinaps alt matrisi = %d KC x %d VPN (sniff.circuit esigi)" % M3["W_vpn"].shape)

    df = sweep(W, nk, nv, seed=0)
    df.to_csv(os.path.join(OUT, "sweep.csv"), index=False)
    print("\n=== SWEEP ===")
    print(df[["kind", "sigma", "rule", "param", "rho", "active_median",
              "active_min", "max_off_cos", "max_adj_cos"]].to_string(index=False))

    ps = perm_stats(W, nk, nv)
    ps.to_csv(os.path.join(OUT, "perm_stats.csv"), index=False)
    print("\n=== PERMUTASYON VARyANSI (rho, mean +- std, n=%d) ===" % N_PERMS)
    print(ps.to_string(index=False))

    print("\n=== KONTROL: gercek VPN->KC vs degree-preserving karistirma ===")
    Wsh = degree_preserving_shuffle(W, seed=12345)
    ctrl_rows = []
    for sigma in (0.5, 1.0, 1.5):
        A, _ = gauss_codes(nv, sigma, 0)
        for rule, param in [("count", 2), ("topk", 20)]:
            if rule == "count":
                cr = kc_codes(A, W, lambda a, w: activate_count(a, w) >= param)
                cs = kc_codes(A, Wsh, lambda a, w: activate_count(a, w) >= param)
            else:
                cr = topk_codes(A, W, param)
                cs = topk_codes(A, Wsh, param)
            mr, ms = code_metrics(cr), code_metrics(cs)
            ctrl_rows.append(dict(sigma=sigma, rule=rule, param=param,
                                  rho_real=mr["rho"], rho_shuffled=ms["rho"],
                                  active_median_real=mr["active_median"],
                                  active_median_shuffled=ms["active_median"]))
    ctrl = pd.DataFrame(ctrl_rows)
    ctrl.to_csv(os.path.join(OUT, "control_shuffle.csv"), index=False)
    print(ctrl.to_string(index=False))

    tn = run_two_number(nv, sigma=1.0, seed=0)
    pd.DataFrame([tn]).to_csv(os.path.join(OUT, "two_number.csv"), index=False)
    print("\n=== IKI SAYI (ayri pop. vs konjunktif) ===")
    print(json.dumps(tn, indent=2))

    ov = channel_overlap(M)
    ov_df = pd.DataFrame([{
        "n_kc_vpn": ov["n_kc_vpn"], "n_kc_alpn": ov["n_kc_alpn"],
        "n_inter": ov["n_inter"], "vpn_syn_onto_inter": ov["vpn_syn_onto_inter"],
        "alpn_syn_onto_inter": ov["alpn_syn_onto_inter"],
        **{"inter_" + k: v for k, v in ov["inter_subtype"].items()}}])
    ov_df.to_csv(os.path.join(OUT, "channel_overlap.csv"), index=False)
    print("\n=== KANAL ORTUSMESI (VPN + ALPN -> KC) ===")
    print(json.dumps(ov, indent=2))

    kc = df[df.kind == "coarse_kc"].copy()
    kc["u1"] = kc.rho <= -0.5
    kc["u2"] = (kc.active_min >= 1) & (kc.active_median >= 5)
    kc["u3"] = kc.max_off_cos < 0.95
    kc["usable"] = kc.u1 & kc.u2 & kc.u3
    print("\n=== KULLANILABILIRLIK (U1 & U2 & U3) ===")
    print(kc[["sigma", "rule", "param", "rho", "active_median", "active_min",
              "max_off_cos", "u1", "u2", "u3", "usable"]].to_string(index=False))
    n_usable = int(kc.usable.sum())
    print("kullanilabilir yapilandirma: %d / %d" % (n_usable, len(kc)))
    best_row = None
    if n_usable:
        best_row = kc[kc.usable].sort_values("rho").iloc[0]
        print("EN IYI: sigma=%.1f rule=%s param=%d rho=%.3f"
              % (best_row.sigma, best_row.rule, best_row.param, best_row.rho))
    else:
        print("HICBIR coarse_kc yapilandirmasi U1&U2&U3'u saglamadi -> yedek (b).")

    make_plots(df, W, nk, nv, best_row if best_row is not None else dict(rule="topk", param=20))

    print("\n=== HASH TABAN CIZGISI ===")
    print(df[df.kind == "hash"][["param", "rho", "active_median", "max_off_cos"]].to_string(index=False))
    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()





