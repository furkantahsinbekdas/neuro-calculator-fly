"""
numcog/mb_learning.py — FAZ 8: MB'de BİYOLOJİK ÖĞRENME KURALI (DAN-kapılı KC→MBON plastisitesi)
ve MB'nin doğal görevleri.

Ön-kayıt: HIPOTEZLER.md "Faz 8 ön-kayıt" (ÖLÇÜMDEN ÖNCE commit; kapı ölçütleri ve hipotezler dahil).
Faz 0–7-3 dosyaları/sonuçları DEĞİŞTİRİLMEZ. Çıktı: `results_p8/`.
float64 (gerekli yerlerde float32 ağırlıklar), SEYREK matrisler, tohum başına ayrı CSV,
tüm shuffle'lar tohumlu. Eş zamanlı süreç: 1.
**KC işareti +1 (ACh) SABİT** — `top_nt="dopamine"` etiket çelişkisi biliniyor (7-0/7-3).

Dil: "bu veride, bu modelde, bu ızgarada".

CLI: explore | pilot | gate1 | runall <nseeds> [kollar...] | merge
"""
from __future__ import annotations
import os
import re
import sys
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.cluster.vq import kmeans2

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import number_coding as nc

OUT = os.path.join(HERE, "results_p8")
os.makedirs(OUT, exist_ok=True)
LOGF = os.path.join(OUT, "run.log")
CACHE = os.path.join(OUT, "mb_cache.npz")

# --- hücre kümeleri ve kenar tanımları (7-0/7-1 ile aynı min_syn) ---
MIN_SYN = 3
KC_SIGN = 1.0                      # ACh; top_nt='dopamine' çelişkisi biliniyor
N_ALPN_EXPECTED = 319              # koku kodlama girdi boyutu (aktif ALPN)
TOP_K_KC = 250                     # APL-benzeri global inhibisyon (SABİT)
ACTIVE_RATE = 0.20                 # prototip aktif oranı
N_PROTO_DEFAULT = 8
N_TRIALS_TRAIN = 6
N_TRIALS_TEST = 6
SIGMA_N = (0.1, 0.3, 0.6)
DROPOUT = (0.1, 0.3, 0.5)
ETA_GRID = (0.01, 0.03, 0.1, 0.3)
RHO_GRID = (0.0, 0.01, 0.05)
SEEDS_PILOT = 10
SEEDS_MAIN = 20
K_COMP_MIN, K_COMP_MAX = 8, 20     # bölme küme sayısı aralığı (ön-kayıtlı)


def log(msg):
    print(msg, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def load_ann():
    ann = pd.read_csv(nc.ANN_FILE, sep="\t", low_memory=False)
    ann["root_id"] = ann["root_id"].astype("int64")
    return ann


def cell_sets(ann):
    cc = ann.cell_class.astype(str)
    def ids(pat):
        return np.array(sorted(int(r) for r in ann.root_id[
            cc.str.fullmatch(pat, case=False, na=False)]), dtype=np.int64)
    kc = ids("Kenyon_Cell")
    alpn = ids("ALPN")
    mbon = ids("MBON")
    dan = ids("DAN")
    return dict(kc=kc, alpn=alpn, mbon=mbon, dan=dan)


def mb_edges(conn, pre_set, post_set, min_syn=MIN_SYN):
    """(pre, post, syn) üçlüleri; min_syn altı 0'a çekilir (Faz 1 ile aynı tanım)."""
    e = conn[conn.pre_pt_root_id.isin(pre_set) & conn.post_pt_root_id.isin(post_set)]
    e = e[e.syn_count >= min_syn]
    return (e.pre_pt_root_id.to_numpy(np.int64), e.post_pt_root_id.to_numpy(np.int64),
            e.syn_count.to_numpy(np.float64))


def dan_type_map(ann, dan_ids):
    """DAN -> (tip, valans). PAM=ödül (+1), PPL1=ceza (-1), PPL2=diğer (0, hariç)."""
    a = ann[ann.root_id.isin(dan_ids)]
    out = {}
    for r, ct in zip(a.root_id.values, a.cell_type.astype(str).values):
        if ct.startswith("PAM"):
            out[int(r)] = (ct, 1)
        elif ct.startswith("PPL1"):
            out[int(r)] = (ct, -1)
        elif ct.startswith("PPL2"):
            out[int(r)] = (ct, 0)
        else:
            out[int(r)] = (ct, 0)
    return out


def nt_sign(s):
    """Faz 7-0 işaret kuralı: ACh/DA/5-HT/OA +1; GABA/Glu -1; diğer NaN."""
    if not isinstance(s, str) or not s.strip():
        return np.nan
    toks = [t.strip().lower() for t in re.split(r"[;,]", s)]
    toks = [t for t in toks if t and "negative" not in t]
    pos = {"acetylcholine", "dopamine", "serotonin", "octopamine"}
    neg = {"gaba", "glutamate"}
    p, n = any(t in pos for t in toks), any(t in neg for t in toks)
    return 1.0 if (p and not n) else (-1.0 if (n and not p) else np.nan)


def mbon_signs(ann, mbon_ids):
    """MBON NT işareti: known_nt -> top_nt (7-0 kuralı). NaN sayısı raporlanır."""
    a = ann[ann.root_id.isin(mbon_ids)]
    lut = {}
    for v in list(a.known_nt.dropna().unique()) + list(a.top_nt.dropna().unique()):
        lut.setdefault(v, nt_sign(v))
    sk = a.known_nt.map(lambda v: lut.get(v, np.nan))
    st = a.top_nt.map(lambda v: lut.get(v, np.nan))
    sig = np.where(sk.notna(), sk, st)
    d = dict(zip(a.root_id.astype(np.int64).tolist(), sig.tolist()))
    s = np.array([d.get(int(r), np.nan) for r in mbon_ids])
    return s


def spectral_compartments(M, kmin=K_COMP_MIN, kmax=K_COMP_MAX, seed=0):
    """MBON×DAN-tipi matrisinden spektral kümeleme; k, eigengap ile [kmin,kmax] aralığında."""
    X = np.asarray(M, np.float64)
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    nrm[nrm == 0] = 1.0
    Xn = X / nrm
    S = Xn @ Xn.T
    np.fill_diagonal(S, 0.0)
    d = S.sum(axis=1)
    d[d == 0] = 1e-12
    Dm = 1.0 / np.sqrt(d)
    L = np.eye(len(S)) - (S * Dm[:, None]) * Dm[None, :]
    w, V = np.linalg.eigh(L)
    gaps = np.diff(w[:kmax + 1])
    k = int(np.argmax(gaps[kmin - 1:kmax]) + kmin)
    Z = V[:, :k] * Dm[:, None]
    _, lab_raw = kmeans2(Z, k, minit="++", seed=seed, iter=200)   # scipy: (centroid, label)
    lab = np.asarray(lab_raw).astype(np.int64).ravel()
    assert lab.shape == (len(S),), "kumeleme etiketi sekli: %s" % (lab.shape,)
    return lab, k, w


def explore():
    """AŞAMA 0: etiket sayımları, kapsam, DAN→valans, bölme çıkarımı, kenar sayımları, KAPI G0."""
    ann = load_ann()
    cs = cell_sets(ann)
    kc, alpn, mbon, dan = cs["kc"], cs["alpn"], cs["mbon"], cs["dan"]
    log("=== AŞAMA 0: KEŞİF (simülasyon YOK) ===")
    log("  KC=%d | ALPN=%d | MBON=%d | DAN=%d" % (len(kc), len(alpn), len(mbon), len(dan)))
    a = ann.copy()
    a["cc"] = a.cell_class.astype(str)
    for name, ids in (("KC", kc), ("ALPN", alpn), ("MBON", mbon), ("DAN", dan)):
        sub = a[a.root_id.isin(ids)]
        for col in ("cell_type", "hemibrain_type", "known_nt", "top_nt"):
            log("  %-5s %-15s: NaN=%d/%d, %d farklı"
                % (name, col, int(sub[col].isna().sum()), len(sub), sub[col].nunique()))
    dmap = dan_type_map(ann, dan)
    types = pd.Series([v[0] for v in dmap.values()])
    val = pd.Series([v[1] for v in dmap.values()])
    log("\n  DAN tipi -> valans (KAYNAK: cell_type/hemibrain_type ÖN EKİ):")
    for t, v in sorted(set(zip(types, val))):
        log("    %-10s valans=%+d  n=%d" % (t, v, int(((types == t) & (val == v)).sum())))
    n_pam = int((val == 1).sum())
    n_ppl1 = int((val == -1).sum())
    n_other = int((val == 0).sum())
    log("    ödül(PAM)=%d  ceza(PPL1)=%d  diğer(PPL2/bilinmeyen)=%d (HARİÇ)"
        % (n_pam, n_ppl1, n_other))
    ms = mbon_signs(ann, mbon)
    log("\n  MBON NT işareti (known_nt -> top_nt): +1=%d, -1=%d, NaN=%d"
        % (int((ms == 1).sum()), int((ms == -1).sum()), int(np.isnan(ms).sum())))
    sub = ann[ann.root_id.isin(mbon)]
    log("    MBON top_nt: %s" % sub.top_nt.value_counts(dropna=False).to_dict())
    log("    MBON known_nt (ilk 6): %s"
        % sub.known_nt.value_counts(dropna=False).head(6).to_dict())
    conn = nc._load()[1]
    pres, posts, w = {}, {}, {}
    for tag, (P, Q) in (("ALPN->KC", (alpn, kc)), ("KC->MBON", (kc, mbon)),
                        ("DAN->MBON", (dan, mbon)), ("MBON->DAN", (mbon, dan)),
                        ("DAN->KC", (dan, kc))):
        e = conn[conn.pre_pt_root_id.isin(P) & conn.post_pt_root_id.isin(Q)]
        e = e[e.syn_count >= MIN_SYN]
        pres[tag] = e.pre_pt_root_id.to_numpy(np.int64)
        posts[tag] = e.post_pt_root_id.to_numpy(np.int64)
        w[tag] = e.syn_count.to_numpy(np.float64)
        log("  %-10s kenar=%-6d pre=%-5d post=%-5d sinaps: ort=%.1f med=%.0f max=%.0f"
            % (tag, len(w[tag]), len(np.unique(pres[tag])), len(np.unique(posts[tag])),
               w[tag].mean() if len(w[tag]) else 0, np.median(w[tag]) if len(w[tag]) else 0,
               w[tag].max() if len(w[tag]) else 0))
    n_alpn_used = len(np.unique(pres["ALPN->KC"]))
    log("  ALPN->KC'de kullanılan ALPN (pres) = %d (koku girdi boyutu)" % n_alpn_used)
    return (ann, cs, dmap, ms, conn, pres, posts, w, n_alpn_used)


def explore_gate(ctx):
    """Aşama 0 ikinci yarı: bölme çıkarımı (ÇIKARIM), DAN→bölme/valans, KAPI G0, önbellek."""
    ann, cs, dmap, ms, conn, pres, posts, w, n_alpn_used = ctx
    kc, alpn, mbon, dan = cs["kc"], cs["alpn"], cs["mbon"], cs["dan"]
    dtypes = sorted({v[0] for v in dmap.values() if v[1] != 0})
    di = {t: i for i, t in enumerate(dtypes)}
    mi = {int(r): i for i, r in enumerate(mbon)}
    M = np.zeros((len(mbon), len(dtypes)))
    for p, q, ww in zip(pres["DAN->MBON"], posts["DAN->MBON"], w["DAN->MBON"]):
        t = dmap.get(int(p), (None, 0))[0]
        if t in di and int(q) in mi:
            M[mi[int(q)], di[t]] += ww
    lab, k, _ = spectral_compartments(M, seed=0)
    cnt = np.bincount(lab, minlength=k)
    log("\n  BÖLME ÇIKARIMI (DAN→MBON bipartit matrisi, spektral kümeleme) — ETİKET: ÇIKARIM")
    log("    DAN tipi sayısı=%d, MBON=%d; k=%d (ön-kayıtlı aralık %d-%d); MBON/küme: "
        "min=%d ort=%.1f max=%d" % (len(dtypes), len(mbon), k, K_COMP_MIN, K_COMP_MAX,
                                    cnt.min(), cnt.mean(), cnt.max()))
    dan_comp = {}
    for p, q in zip(pres["DAN->MBON"], posts["DAN->MBON"]):
        dan_comp.setdefault(int(p), []).append(int(lab[mi[int(q)]]))
    dan_comp = {p: int(np.bincount(v).argmax()) for p, v in dan_comp.items()}
    per_comp = np.bincount(list(dan_comp.values()), minlength=k)
    log("    DAN→bölme: %d/%d DAN atandı; bölme başına DAN: %s"
        % (len(dan_comp), len(dan), per_comp.tolist()))
    log("    bölme başına DAN tipleri: %s" % [
        sorted({dmap[int(p)][0] for p, c in dan_comp.items() if c == cc})[:4]
        for cc in range(k)])
    g0 = dict(n_kc=len(kc), n_alpn=len(alpn), n_mbon=len(mbon), n_dan=len(dan),
              n_alpn_used=n_alpn_used, k_comp=k, n_kcmbon=len(w["KC->MBON"]),
              n_danmbon=len(w["DAN->MBON"]), n_mbondan=len(w["MBON->DAN"]),
              n_dankc=len(w["DAN->KC"]), n_mbon_sign=int((~np.isnan(ms)).sum()),
              n_pam=int(sum(1 for v in dmap.values() if v[1] == 1)),
              n_ppl1=int(sum(1 for v in dmap.values() if v[1] == -1)))
    g0["mbon_ge30"] = bool(len(mbon) >= 30)
    g0["comp_ge8"] = bool(k >= 8 and k <= K_COMP_MAX)
    g0["kcmbon_ge5000"] = bool(len(w["KC->MBON"]) >= 5000)
    g0["g0_gecildi"] = bool(g0["mbon_ge30"] and g0["comp_ge8"] and g0["kcmbon_ge5000"])
    log("\n=== KAPI G0 ===")
    log("  (a) ≥30 MBON etiketli: %d -> %s" % (g0["n_mbon"], g0["mbon_ge30"]))
    log("  (b) ≥8 bölme çıkarılabildi: k=%d -> %s" % (k, g0["comp_ge8"]))
    log("  (c) KC→MBON kenarı ≥5.000: %d -> %s" % (g0["n_kcmbon"], g0["kcmbon_ge5000"]))
    log("  >>> KAPI G0: %s" % ("GEÇİLDİ" if g0["g0_gecildi"] else "GEÇİLEMEDİ (DUR)"))
    pd.DataFrame([g0]).to_csv(os.path.join(OUT, "gate0.csv"), index=False)
    dkeys = sorted(dan_comp.keys())
    np.savez_compressed(
        CACHE,
        kc=kc, alpn=alpn, mbon=mbon, dan=dan,
        alpnkc_pre=pres["ALPN->KC"], alpnkc_post=posts["ALPN->KC"], alpnkc_w=w["ALPN->KC"],
        kcmbon_pre=pres["KC->MBON"], kcmbon_post=posts["KC->MBON"], kcmbon_w=w["KC->MBON"],
        danmbon_pre=pres["DAN->MBON"], danmbon_post=posts["DAN->MBON"], danmbon_w=w["DAN->MBON"],
        mbon_signs=ms, comp_lab=lab, comp_k=np.array([k]),
        dan_ids=np.array(dkeys, np.int64),
        dan_comp=np.array([dan_comp[p] for p in dkeys], np.int64),
        dan_val=np.array([dmap[p][1] for p in dkeys], np.int64),
        dan_type=np.array([dmap[p][0] for p in dkeys], dtype=object),
        dtypes=np.array(dtypes, dtype=object))
    log("  önbellek: %s (%.1f MB)" % (CACHE, os.path.getsize(CACHE) / 1e6))
    return g0


def cmd_explore():
    ctx = explore()
    g0 = explore_gate(ctx)
    if not g0["g0_gecildi"]:
        log("\nKAPI G0 GEÇİLEMEDİ -> RAPOR_FAZ_8_0.md yazılacak ve DUR.")
    return g0


# ============================== MODEL (kilitli) ==============================
def bipartite_shuffle(r, c, w, n_swaps, rng, n_row, n_col):
    """Derece-korunmuş çift-kenar takası (bipartit); ağırlıklar kenarla taşınır."""
    key = set(zip(r.tolist(), c.tolist()))
    R, C, W_ = r.copy(), c.copy(), w.copy()
    m = len(R)
    done = 0
    for _ in range(n_swaps):
        i, j = rng.randint(0, m, size=2)
        a, b = R[i], C[i]
        d, e = R[j], C[j]
        if a == d or b == e or (a, e) in key or (d, b) in key:
            continue
        key.discard((a, b)); key.discard((d, e))
        key.add((a, e)); key.add((d, b))
        R[i], C[i] = a, e
        R[j], C[j] = d, b
        W_[i], W_[j] = W_[j], W_[i]          # ağırlık da kenarla gider
        done += 1
    return R, C, W_


def er_edges(r, c, w, rng, n_row, n_col, factor=1.05):
    """Aynı yoğunlukta Erdős–Rényi (her iki katman için ayrı çağrılır)."""
    m = len(r)
    ne = int(m * factor)
    rr = rng.randint(0, n_row, size=ne)
    cc = rng.randint(0, n_col, size=ne)
    pp, inv = np.unique(np.stack([rr, cc], 1), axis=0, return_inverse=True)
    rr, cc = pp[:, 0], pp[:, 1]
    ww = rng.choice(w, size=len(rr), replace=True) if len(w) else np.ones(len(rr))
    return rr, cc, ww


def csr_from(pre, post, w, n_row, n_col, row_map=None, col_map=None):
    r = np.array([row_map[int(x)] for x in pre]) if row_map else pre
    c = np.array([col_map[int(x)] for x in post]) if col_map else post
    keys = r.astype(np.int64) * n_col + c.astype(np.int64)
    uk, inv = np.unique(keys, return_inverse=True)
    ww = np.zeros(len(uk))
    np.add.at(ww, inv.ravel(), w)
    rr = (uk // n_col).astype(np.int64)
    cc = (uk % n_col).astype(np.int64)
    M = sp.csr_matrix((ww, (rr, cc)), shape=(n_row, n_col))
    M.sort_indices()
    return M


def load_mb_cache():
    d = np.load(CACHE, allow_pickle=True)
    return d


def build_arm(arm, seed=0):
    """Bir kol için (W_ak: KC×ALPN, W_km: MBON×KC, bölme atamaları) üretir."""
    d = load_mb_cache()
    kc, alpn, mbon = d["kc"], d["alpn"], d["mbon"]
    ai = {int(x): i for i, x in enumerate(alpn)}
    ii = {int(x): i for i, x in enumerate(kc)}
    mi = {int(x): i for i, x in enumerate(mbon)}
    rng = np.random.RandomState(8000 + seed)
    ak_p, ak_q, ak_w = d["alpnkc_pre"], d["alpnkc_post"], d["alpnkc_w"]
    km_p, km_q, km_w = d["kcmbon_pre"], d["kcmbon_post"], d["kcmbon_w"]
    # ALPN->KC: satır = KC (post), sütun = ALPN (pre)
    r_ak = np.array([ii[int(x)] for x in ak_q])
    c_ak = np.array([ai[int(x)] for x in ak_p])
    # KC->MBON: satır = MBON (post), sütun = KC (pre)
    r_km = np.array([mi[int(x)] for x in km_q])
    c_km = np.array([ii[int(x)] for x in km_p])
    if arm == "MB_KCMBON_shuffle":
        r_km, c_km, km_w = bipartite_shuffle(r_km, c_km, km_w, 10 * len(r_km), rng,
                                             len(mbon), len(kc))
    elif arm == "MB_ALPNKC_shuffle":
        r_ak, c_ak, ak_w = bipartite_shuffle(r_ak, c_ak, ak_w, 10 * len(r_ak), rng,
                                             len(kc), len(alpn))
    elif arm == "MB_ER":
        r_km, c_km, km_w = er_edges(r_km, c_km, km_w, rng, len(mbon), len(kc))
        r_ak, c_ak, ak_w = er_edges(r_ak, c_ak, ak_w, rng, len(kc), len(alpn))
    W_ak = csr_from(r_ak, c_ak, ak_w, len(kc), len(alpn))
    W_km = csr_from(r_km, c_km, km_w, len(mbon), len(kc))
    signs = d["mbon_signs"].astype(np.float64)
    signs = np.where(np.isnan(signs), 0.0, signs)
    comp = d["comp_lab"].astype(np.int64)
    k = int(d["comp_k"][0])
    dan_ids, dan_comp, dan_val = d["dan_ids"], d["dan_comp"].astype(np.int64), \
        d["dan_val"].astype(np.int64)
    if arm == "MB_rastgele_bolme":
        dan_comp = rng.permutation(dan_comp)
        dan_val = rng.permutation(dan_val)
    return dict(W_ak=W_ak, W_km=W_km, signs=signs, comp=comp, k_comp=k,
                dan_ids=dan_ids, dan_comp=dan_comp, dan_val=dan_val,
                n_kc=len(kc), n_alpn=len(alpn), n_mbon=len(mbon))


def make_prototypes(n_proto, n_alpn, rng):
    """P prototip: ALPN'lerin %20'si aktif, genlikler Gamma."""
    P = np.zeros((n_proto, n_alpn), np.float64)
    na = max(int(ACTIVE_RATE * n_alpn), 1)
    for i in range(n_proto):
        act = rng.choice(n_alpn, size=na, replace=False)
        P[i, act] = rng.gamma(shape=2.0, scale=1.0, size=na)
    return P


def odor_trial(proto, rng, sigma_n, drop):
    x = proto + rng.normal(0.0, sigma_n, size=len(proto))
    np.clip(x, 0.0, None, out=x)
    a = np.where(proto > 0)[0]
    if drop > 0 and len(a):
        kk = int(round(drop * len(a)))
        if kk > 0:
            x[rng.choice(a, size=kk, replace=False)] = 0.0
    return x


def kc_code(W_ak, x, k=TOP_K_KC):
    """APL-benzeri global inhibisyon: en güçlü k KC aktif (ikili)."""
    d = W_ak @ x
    if k >= d.shape[0]:
        return (d > 0).astype(np.float64)
    thr = np.partition(d, -k)[-k]
    return (d >= thr).astype(np.float64)


class MB:
    """DAN-kapılı KC→MBON plastisitesi olan MB devresi (okuma katmanı YOK)."""

    def __init__(self, armd, eta, rho):
        self.W_ak = armd["W_ak"]
        W = np.asarray(armd["W_km"].todense(), np.float64)
        tot = W.sum(axis=1, keepdims=True)
        tot[tot == 0] = 1.0
        self.W0 = W / tot                      # MBON başına toplam normalize
        self.W = self.W0.copy()
        self.signs = armd["signs"]
        self.comp = armd["comp"]
        self.dan_comp = armd["dan_comp"]
        self.dan_val = armd["dan_val"]
        self.eta, self.rho = eta, rho
        self.tgt = {}
        for v in (1, -1):
            want = -v                          # PAM(+1) -> KAÇINMA(-1); PPL1(-1) -> YAKLAŞMA(+1)
            m = np.zeros(len(self.signs), bool)
            for c in np.unique(self.dan_comp[self.dan_val == v]):
                m |= (self.comp == c) & (self.signs == want)
            self.tgt[v] = m
        self.n_targets = {v: int(self.tgt[v].sum()) for v in (1, -1)}

    def mbons(self, kc):
        return np.maximum(self.W @ kc, 0.0)
    def score(self, kc):
        return float(self.signs @ self.mbons(kc))

    def learn(self, kc, valance):
        """US denemesi: ilgili DAN tipi açık -> hedef MBON satırlarında LTD + unutma."""
        m = self.tgt[int(valance)]
        if m.any() and self.eta > 0:
            rows = np.where(m)[0]
            self.W[rows] = np.maximum(self.W[rows] - self.eta * kc[None, :], 0.0)
        if self.rho > 0:
            self.W += self.rho * (self.W0 - self.W)


def trial_acc(mb, protos, valences, rng, sigma_n, drop, n_trials, learn=True,
              shift=None):
    """Bir koku kümesi üzerinde denemeler; doğruluk döner (deneme×koku ortalaması)."""
    ok, tot, ties = 0, 0, 0
    n = len(protos)
    for t in range(n_trials):
        for i in range(n):
            x = odor_trial(protos[i] + (shift[i] if shift is not None else 0.0), rng,
                           sigma_n, drop)
            kc = kc_code(mb.W_ak, x)
            s = mb.score(kc)
            if learn:
                mb.learn(kc, valences[i])
            else:
                tot += 1
                if s == 0.0:
                    ties += 1
                else:
                    ok += int(np.sign(s) == valences[i])
    return (ok / tot if tot else np.nan), ties


def proto_set(n, armd, rng):
    protos = make_prototypes(n, armd["n_alpn"], rng)
    val = np.array([1 if i % 2 == 0 else -1 for i in range(n)], np.int64)
    return protos, val


def run_condition(armd, seed, eta, rho, task, cond, **kw):
    """Bir görev/koşul için doğruluk (0-1)."""
    off = {"T1": 0, "T2": 100, "T3": 200, "T4": 300, "T5": 400, "T6a": 500,
           "T6b": 600, "G1": 700}.get(task, 800)
    rng = np.random.RandomState(100000 + off * 97 + seed * 13 + abs(hash(cond)) % 997)
    mb = MB(armd, eta, rho)
    if task in ("T1", "T2", "T3", "T5", "G1"):
        N = kw.get("N", 4)
        sigma = kw.get("sigma", 0.1)
        protos, val = proto_set(N, armd, rng)
        nt = kw.get("n_trials", N_TRIALS_TRAIN)
        if task == "T3":
            accs = []
            for ntr in (1, 2, 3, 5, 8, 12, 20):
                mb2 = MB(armd, eta, rho)
                trial_acc(mb2, protos, val, rng, sigma, 0.0, ntr, learn=True)
                a, _ = trial_acc(mb2, protos, val, rng, sigma, 0.0, N_TRIALS_TEST,
                                 learn=False)
                accs.append(a)
            return accs
        trial_acc(mb, protos, val, rng, sigma, 0.0, nt, learn=True)
        drop = kw.get("drop", 0.0)
        if task == "T5":
            cos = kw.get("cos", 0.7)
            novel = np.zeros_like(protos)
            for i in range(N):
                nv = protos[i] + rng.normal(0, 1, size=len(protos[i]))
                v0 = protos[i] - protos[i].mean()
                v1 = nv - nv.mean()
                nv = v0 / np.linalg.norm(v0) * cos + v1 / max(np.linalg.norm(v1), 1e-9) * \
                    np.sqrt(max(1 - cos ** 2, 0.0))
                nv = np.abs(nv)
                novel[i] = nv / max(nv.max(), 1e-9) * protos[i].max()
            a, _ = trial_acc(mb, novel, val, rng, sigma, drop, N_TRIALS_TEST, learn=False)
            return a
        a, _ = trial_acc(mb, protos, val, rng, sigma, drop,
                         kw.get("n_test", N_TRIALS_TEST), learn=False)
        return a
    if task == "T4":
        nA, nB = kw.get("nA", 8), kw.get("nB", 8)
        pA, vA = proto_set(nA, armd, rng)
        pB, vB = proto_set(nB, armd, np.random.RandomState(rng.randint(1 << 30)))
        trial_acc(mb, pA, vA, rng, 0.1, 0.0, N_TRIALS_TRAIN, learn=True)
        a_before, _ = trial_acc(mb, pA, vA, rng, 0.1, 0.0, N_TRIALS_TEST, learn=False)
        trial_acc(mb, pB, vB, rng, 0.1, 0.0, N_TRIALS_TRAIN, learn=True)
        a_after, _ = trial_acc(mb, pA, vA, rng, 0.1, 0.0, N_TRIALS_TEST, learn=False)
        b_after, _ = trial_acc(mb, pB, vB, rng, 0.1, 0.0, N_TRIALS_TEST, learn=False)
        if kw.get("which") == "B":
            return b_after
        return a_after if kw.get("which", "A") == "A" else a_before
    if task == "T6a":
        pA, _ = proto_set(1, armd, rng)
        pB, _ = proto_set(1, armd, np.random.RandomState(rng.randint(1 << 30)))
        mA = pA[0]
        mB = pB[0]
        mAB = np.maximum(mA, mB)
        mb = MB(armd, eta, rho)
        for _ in range(N_TRIALS_TRAIN):
            for x, v in ((mA, 1), (mB, 1), (mAB, -1)):
                kc = kc_code(mb.W_ak, odor_trial(x, rng, 0.1, 0.0))
                mb.learn(kc, v)
        ok, tot = 0, 0
        for _ in range(N_TRIALS_TEST):
            for x, v in ((mA, 1), (mB, 1), (mAB, -1)):
                kc = kc_code(mb.W_ak, odor_trial(x, rng, 0.1, 0.0))
                s = mb.score(kc)
                tot += 1
                ok += int(s != 0.0 and np.sign(s) == v)
        return ok / tot
    if task == "T6b":
        pA, pB = proto_set(1, armd, rng)[0], proto_set(1, armd,
                                                       np.random.RandomState(7))[0]
        mA, mB = pA[0], pB[0]
        mb = MB(armd, eta, rho)
        for _ in range(N_TRIALS_TRAIN):
            for x, v in ((mA, 1), (mB, -1)):
                mb.learn(kc_code(mb.W_ak, odor_trial(x, rng, 0.1, 0.0)), v)
        a1, _ = trial_acc(mb, np.stack([mA, mB]),
                          np.array([1, -1], np.int64), rng, 0.1, 0.0, N_TRIALS_TEST,
                          learn=False)
        for _ in range(N_TRIALS_TRAIN):          # ters çevir
            for x, v in ((mA, -1), (mB, 1)):
                mb.learn(kc_code(mb.W_ak, odor_trial(x, rng, 0.1, 0.0)), v)
        a2, _ = trial_acc(mb, np.stack([mA, mB]),
                          np.array([-1, 1], np.int64), rng, 0.1, 0.0, N_TRIALS_TEST,
                          learn=False)
        if kw.get("which") == "once":
            return a1
        return a2
    raise ValueError(task)


def delta_condition(armd, seed, task, cond, **kw):
    """Δ-okuma TAVANI (DIŞ REFERANS, biyolojik DEĞİL): KC -> valence doğrusal okuma."""
    rng = np.random.RandomState(200000 + seed * 17 + abs(hash(cond)) % 991)
    N = kw.get("N", 4)
    sigma = kw.get("sigma", 0.1)
    protos, val = proto_set(N, armd, rng)
    X, Y = [], []
    for _ in range(kw.get("n_trials", N_TRIALS_TRAIN)):
        for i in range(N):
            X.append(kc_code(armd["W_ak"], odor_trial(protos[i], rng, sigma, 0.0)))
            Y.append(float(val[i]))
    X = np.asarray(X)
    Y = np.asarray(Y)
    K = X @ X.T
    lam = 1e-3 * float(np.mean(np.diag(K)) or 1.0)
    alpha = np.linalg.solve(K + lam * np.eye(len(K)), Y)
    ok, tot = 0, 0
    for _ in range(kw.get("n_test", N_TRIALS_TEST)):
        for i in range(N):
            kc = kc_code(armd["W_ak"], odor_trial(protos[i], rng, sigma,
                                                  kw.get("drop", 0.0)))
            s = float(kc @ (X.T @ alpha))
            tot += 1
            ok += int(s != 0.0 and np.sign(s) == val[i])
    return ok / tot


def nc_safe_ci(v):
    v = np.asarray(v, float)
    m = float(v.mean())
    sd = float(v.std(ddof=1)) if len(v) > 1 else 0.0
    return m, sd, 1.96 * sd / np.sqrt(max(len(v), 1))


BIOLOGICAL = ("MB_gercek", "MB_KCMBON_shuffle", "MB_ALPNKC_shuffle", "MB_ER",
              "MB_rastgele_bolme", "plastisitesiz", "delta_okuma")
T1_SIGMAS = (0.1, 0.3, 0.6)
T1_NS = (2, 4, 8, 16)
T2_DROPS = (0.1, 0.3, 0.5)
T3_NTRIALS = (1, 2, 3, 5, 8, 12, 20)
T4_NS = (4, 8, 16, 32, 64)
T5_COS = (0.9, 0.7, 0.5)


def pilot():
    """η/ρ seçimi YALNIZCA validasyonda (10 tohum, ayrı prototip kümeleri)."""
    armd = build_arm("MB_gercek", 0)
    rows = []
    for eta in ETA_GRID:
        for rho in RHO_GRID:
            accs = [run_condition(armd, s, eta, rho, "T1", "val", N=4, sigma=0.1)
                    for s in range(SEEDS_PILOT)]
            rows.append(dict(eta=eta, rho=rho, val=float(np.mean(accs)), n=len(accs)))
            log("  pilot η=%.2f ρ=%.2f -> validasyon=%.3f" % (eta, rho, rows[-1]["val"]))
    pdf = pd.DataFrame(rows)
    pdf.to_csv(os.path.join(OUT, "pilot.csv"), index=False)
    b = pdf.sort_values("val", ascending=False).iloc[0]
    frozen = dict(eta=float(b.eta), rho=float(b.rho), val=float(b.val))
    pd.DataFrame([frozen]).to_csv(os.path.join(OUT, "frozen_config.csv"), index=False)
    log("  DONDU: η=%.2f ρ=%.2f (validasyon=%.3f; TEST kullanılmadı)"
        % (frozen["eta"], frozen["rho"], frozen["val"]))
    return frozen


def gate1():
    """AŞAMA 1: 2 koku, σn=0.1, d=0, 10 deneme/koku -> MB_gercek ≥ %90 (20 tohum)."""
    fr = pd.read_csv(os.path.join(OUT, "frozen_config.csv")).iloc[0]
    armd = build_arm("MB_gercek", 0)
    accs = [run_condition(armd, s, float(fr.eta), float(fr.rho), "G1", "g1",
                          N=2, sigma=0.1, n_trials=10, n_test=10)
            for s in range(SEEDS_MAIN)]
    m, sd, ci = nc_safe_ci(accs)
    ok = bool(m >= 0.90)
    log("\n=== KAPI G1 (η=%.2f ρ=%.2f) ===" % (fr.eta, fr.rho))
    log("  MB_gercek doğruluk = %.3f ± %.3f [%.3f, %.3f] (n=%d) -> %s"
        % (m, sd, m - ci, m + ci, len(accs), "GEÇİLDİ" if ok else "GEÇİLEMEDİ"))
    pd.DataFrame([dict(acc=m, sd=sd, ci95=ci, n=len(accs), gecti=ok,
                       eta=float(fr.eta), rho=float(fr.rho))]).to_csv(
        os.path.join(OUT, "gate1.csv"), index=False)
    if not ok:
        log("  KAPI G1 GEÇİLEMEDİ -> RAPOR_FAZ_8_1.md yazılacak ve DUR.")
    return ok



def run_arm_seed(arm, seed, eta, rho):
    """Bir kol × tohum: tüm görevler -> satır listesi."""
    rows = []
    if arm == "delta_okuma":
        base = build_arm("MB_gercek", 0)
        for N in T1_NS:
            for sg in T1_SIGMAS:
                rows.append(dict(arm=arm, seed=seed, task="T1", cond="N%d_s%.1f" % (N, sg),
                                 value=delta_condition(base, seed, "T1",
                                                       "d%d_%.1f" % (N, sg), N=N,
                                                       sigma=sg)))
        for d in T2_DROPS:
            rows.append(dict(arm=arm, seed=seed, task="T2", cond="d%.1f" % d,
                             value=delta_condition(base, seed, "T2", "d%.1f" % d, N=4,
                                                   sigma=0.1, drop=d)))
        return rows
    armd = build_arm("MB_gercek" if arm == "plastisitesiz" else arm, seed)
    e = 0.0 if arm == "plastisitesiz" else eta
    for N in T1_NS:
        for sg in T1_SIGMAS:
            rows.append(dict(arm=arm, seed=seed, task="T1", cond="N%d_s%.1f" % (N, sg),
                             value=run_condition(armd, seed, e, rho, "T1",
                                                 "N%d_%.1f" % (N, sg), N=N, sigma=sg)))
    for d in T2_DROPS:
        rows.append(dict(arm=arm, seed=seed, task="T2", cond="d%.1f" % d,
                         value=run_condition(armd, seed, e, rho, "T2", "d%.1f" % d,
                                             N=4, sigma=0.1, drop=d)))
    accs = run_condition(armd, seed, e, rho, "T3", "T3", N=4, sigma=0.1)
    for ntr, a in zip(T3_NTRIALS, accs):
        rows.append(dict(arm=arm, seed=seed, task="T3", cond="ntr%d" % ntr, value=a))
    for nA in T4_NS:
        rows.append(dict(arm=arm, seed=seed, task="T4", cond="nA%d_after" % nA,
                         value=run_condition(armd, seed, e, rho, "T4", "A%d" % nA,
                                             nA=nA, nB=8, which="A")))
        rows.append(dict(arm=arm, seed=seed, task="T4", cond="nA%d_B" % nA,
                         value=run_condition(armd, seed, e, rho, "T4", "B%d" % nA,
                                             nA=nA, nB=8, which="B")))
    for c in T5_COS:
        rows.append(dict(arm=arm, seed=seed, task="T5", cond="cos%.1f" % c,
                         value=run_condition(armd, seed, e, rho, "T5", "c%.1f" % c,
                                             N=4, sigma=0.1, cos=c)))
    rows.append(dict(arm=arm, seed=seed, task="T6a", cond="A+B+AB-",
                     value=run_condition(armd, seed, e, rho, "T6a", "t6a")))
    rows.append(dict(arm=arm, seed=seed, task="T6b", cond="once",
                     value=run_condition(armd, seed, e, rho, "T6b", "once", which="once")))
    rows.append(dict(arm=arm, seed=seed, task="T6b", cond="sonra",
                     value=run_condition(armd, seed, e, rho, "T6b", "sonra", which="after")))
    return rows


def merge():
    """Özet + ön-kayıtlı ölçütler + H8.1-H8.6 + 'sarsıcı bulgu' ölçütü."""
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "*_seed[0-9][0-9].csv")))
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    fr = pd.read_csv(os.path.join(OUT, "frozen_config.csv")).iloc[0]
    log("\n=== DONMUŞ KONFİGÜRASYON ===")
    log("  η=%.2f ρ=%.2f (pilot validasyon=%.3f; TEST kullanılmadı)"
        % (fr.eta, fr.rho, fr.val))
    rows = []
    for (task, cond), s in df.groupby(["task", "cond"]):
        for arm, sub in s.groupby("arm"):
            m, sd, ci = nc_safe_ci(sub.value.values)
            rows.append(dict(task=task, cond=cond, arm=arm, mean=m, sd=sd, ci95=ci,
                             n=len(sub)))
    agg = pd.DataFrame(rows)
    agg.to_csv(os.path.join(OUT, "summary.csv"), index=False)

    def g(task, cond, arm):
        s = agg[(agg.task == task) & (agg.cond == cond) & (agg.arm == arm)]
        return None if len(s) == 0 else (float(s["mean"].iloc[0]), float(s.ci95.iloc[0]))

    log("\n=== T1 AYIRIM + GÜRÜLTÜ (şans 0,50) ===")
    for cond in agg[agg.task == "T1"].cond.unique():
        log("  %-10s " % cond + " | ".join(
            "%s %.3f" % (a, g("T1", cond, a)[0]) for a in BIOLOGICAL
            if g("T1", cond, a) is not None))
    log("\n=== T2 ÖRÜNTÜ TAMAMLAMA (d) ===")
    for cond in sorted(agg[agg.task == "T2"].cond.unique()):
        log("  %-6s " % cond + " | ".join(
            "%s %.3f" % (a, g("T2", cond, a)[0]) for a in BIOLOGICAL
            if g("T2", cond, a) is not None))
    log("\n=== T3 AZ ÖRNEK (≥%90 için gereken deneme) ===")
    for arm in agg.arm.unique():
        s = agg[(agg.task == "T3") & (agg.arm == arm)].copy()
        s["ntr"] = s.cond.str.replace("ntr", "").astype(int)
        s = s.sort_values("ntr")
        first = s[s["mean"] >= 0.90]
        log("  %-20s ilk≥0,90: %s | eğri: %s" % (arm,
            (int(first.ntr.iloc[0]) if len(first) else None),
            " ".join("%d:%.2f" % (r.ntr, r["mean"]) for _, r in s.iterrows())))
    log("\n=== T4 SÜREKLİ ÖĞRENME (A-tutma / B) ===")
    for cond in sorted(agg[agg.task == "T4"].cond.unique()):
        log("  %-14s " % cond + " | ".join(
            "%s %.3f" % (a, g("T4", cond, a)[0]) for a in BIOLOGICAL
            if g("T4", cond, a) is not None))
    log("\n=== T5 GENELLEME (cos) ===")
    for cond in sorted(agg[agg.task == "T5"].cond.unique()):
        log("  %-8s " % cond + " | ".join(
            "%s %.3f" % (a, g("T5", cond, a)[0]) for a in BIOLOGICAL
            if g("T5", cond, a) is not None))
    log("\n=== T6a NEGATİF DESENLEME (şans 0,50; 'hep yaklaş' 0,667) ===")
    for a in BIOLOGICAL:
        r = g("T6a", "A+B+AB-", a)
        if r:
            log("  %-20s %.3f ± %.3f" % (a, r[0], r[1]))
    log("\n=== T6b TERS ÖĞRENME ===")
    for cond in ("once", "sonra"):
        log("  %-6s " % cond + " | ".join(
            "%s %.3f" % (a, g("T6b", cond, a)[0]) for a in BIOLOGICAL
            if g("T6b", cond, a) is not None))
    # --- ölçütler + Holm
    from scipy import stats

    def per_seed(task, cond, arm):
        return df[(df.task == task) & (df.cond == cond) & (df.arm == arm)
                  ].value.values

    log("\n=== ÖN-KAYITLI ÖLÇÜTLER ===")
    t1_low = [c for c in agg[agg.task == "T1"].cond.unique()
              if c.startswith(("N2_", "N4_"))]
    v = [g("T1", c, "MB_gercek")[0] for c in t1_low]
    log("  H8.1 (T1'de N≤4 için ≥0,90): ortalama=%.3f (koşullar %s) -> %s"
        % (np.mean(v), [round(x, 3) for x in v],
           "DESTEK" if np.mean(v) >= 0.90 else "ÇÜRÜDÜ"))
    tests = []
    for task in ("T1", "T2", "T6a"):
        conds = sorted(agg[agg.task == task].cond.unique())
        key = "N4_s0.1" if task == "T1" else (conds[0] if task == "T2" else conds[0])
        for arm2 in ("MB_KCMBON_shuffle", "MB_ALPNKC_shuffle", "MB_ER",
                     "MB_rastgele_bolme", "plastisitesiz"):
            a1, a2 = per_seed(task, key, "MB_gercek"), per_seed(task, key, arm2)
            if len(a1) < 3 or len(a2) < 3:
                continue
            t = stats.ttest_ind(a1, a2, equal_var=False)
            tests.append(dict(task=task, cond=key, test="MB_gercek vs %s" % arm2,
                              diff=float(np.mean(a1) - np.mean(a2)),
                              p_raw=float(t.pvalue), n=len(a1)))
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
            log("  %-5s %-30s fark=%+.3f p_holm=%.4f -> %s"
                % (t["task"], t["test"], t["diff"], t["p_holm"],
                   "AYRIŞIR" if t["p_holm"] < 0.05 else "ayrışamaz"))
        pd.DataFrame(tests).to_csv(os.path.join(OUT, "hypotheses.csv"), index=False)
        n_sig = sum(1 for t in tests if t["p_holm"] < 0.05)
        n_big = sum(1 for t in tests if t["p_holm"] < 0.05 and abs(t["diff"]) >= 0.2)
        log("  H8.2 (MB_gercek ≈ kollar): Holm sonrası %d/%d anlamlı; |fark|≥0,2 olan %d"
            % (n_sig, len(tests), n_big))
    r_a, r_b = g("T6a", "A+B+AB-", "MB_gercek"), g("T6a", "A+B+AB-", "MB_er")
    log("  H8.4 (T6a başarısız ≈şans): MB_gercek=%.3f (şans 0,50; hep-yaklaş 0,667) -> %s"
        % (r_a[0], "DESTEK (çözemedi)" if r_a[0] < 0.70 else "ÇÜRÜDÜ (çözdü)"))
    log("\n=== SARSICI BULGU ÖLÇÜTÜ (Holm GA-ayrık + etki≥0,2 + en az iki η/ρ ayarı) ===")
    log("  Ana ölçüm DONMUŞ tek ayarda (η=%.2f ρ=%.2f) koştu -> 'en az iki ayar' koşulu"
        % (fr.eta, fr.rho))
    log("  ana ölçümle SAĞLANAMAZ; pilot ızgarasında kollar denenmedi.")
    log("  -> bu fazda 'connectome'a özgü' DENMEZ; varsa yalnızca ÖN BULGU.")
    return agg, df


def runall(nseeds, arms=None):
    fr = pd.read_csv(os.path.join(OUT, "frozen_config.csv")).iloc[0]
    arms = arms or list(BIOLOGICAL)
    t00 = time.time()
    for arm in arms:
        for seed in range(nseeds):
            t0 = time.time()
            rows = run_arm_seed(arm, seed, float(fr.eta), float(fr.rho))
            pd.DataFrame(rows).to_csv(os.path.join(OUT, "%s_seed%02d.csv" % (arm, seed)),
                                      index=False)
            log("  %-20s seed%02d (%.0fs, toplam %.0f dk)"
                % (arm, seed, time.time() - t0, (time.time() - t00) / 60))
    log("runall bitti (%.0f dk)" % ((time.time() - t00) / 60))




def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "explore":
        cmd_explore()
    elif cmd == "pilot":
        pilot()
    elif cmd == "gate1":
        gate1()
    elif cmd == "runall":
        runall(int(sys.argv[2]), sys.argv[3:] or None)
    elif cmd == "merge":
        merge()
    else:
        log("kullanim: explore | pilot | gate1 | runall <nseeds> [kollar...] | merge")


if __name__ == "__main__":
    main()


