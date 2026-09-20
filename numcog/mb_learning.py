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


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "explore":
        cmd_explore()
    else:
        log("kullanim: explore | pilot | gate1 | runall <nseeds> [kollar...] | merge")


if __name__ == "__main__":
    main()


