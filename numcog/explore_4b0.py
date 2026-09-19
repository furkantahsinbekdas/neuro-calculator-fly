"""
numcog/explore_4b0.py — FAZ 4B-0: çarpma ölçümü (Faz 4A-2 çekirdeği, N=40) + central complex keşfi.

Yeni model kodu YOK; yalnızca keşif ve küçük ölçüm. Mevcut modüller import edilir, değiştirilmez.
"""
from __future__ import annotations
import os

import numpy as np
import pandas as pd

import number_coding as nc
import operator_diagnosis as od
import calculator as cal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "results_p4b0")
ANN_FILE = os.path.join(ROOT, "annotations_783.tsv")
CONN_FILE = os.path.join(ROOT, "proofread_connections_783.feather")
N_CORE = 40
N_SEEDS = 20


# --------------------------------------------------------------------------- #
# A) Çarpma ölçümü
# --------------------------------------------------------------------------- #
def part_a():
    mats = od.load_sets()
    rows = []
    err_steps = {}
    for seed in range(N_SEEDS):
        core = od.NominalFlyCore(N_CORE, seed, mats)
        for a in range(1, 10):
            for b in range(1, 10):
                n = 0
                bad = 0
                for _ in range(b):
                    for _ in range(a):
                        before = n
                        n, _ = core.step(n, '+')
                        if n != core._result(before, '+'):
                            bad += 1
                            err_steps[before] = err_steps.get(before, 0) + 1
                rows.append(dict(seed=seed, a=a, b=b, got=n, want=a * b, ok=int(n == a * b),
                                 prod=a * b, in_range=int(a * b <= N_CORE), bad_steps=bad))
    return pd.DataFrame(rows), err_steps


def part_a_report(df, err_steps):
    print("=== A) CARPMA (N=%d nominal cekirdek, %d tohum) ===" % (N_CORE, N_SEEDS))
    s6 = df[(df.a <= 6) & (df.b <= 6)]
    ps6 = s6.groupby("seed").ok.mean()
    print("(i) a,b 1..6 (carpim<=36): %d cift  acc=%.3f +- %.3f"
          % (len(s6), ps6.mean(), ps6.std(ddof=1)))
    inr = df[df.in_range == 1]
    outr = df[df.in_range == 0]
    pin = inr.groupby("seed").ok.mean()
    pout = outr.groupby("seed").ok.mean()
    print("(ii) aralik ICI (<=%d): %d cift  acc=%.3f +- %.3f" % (N_CORE, len(inr), pin.mean(), pin.std(ddof=1)))
    print("     aralik DISI (>%d): %d cift  acc=%.3f +- %.3f" % (N_CORE, len(outr), pout.mean(), pout.std(ddof=1)))
    print("(iii) hatali +1 adim girdileri (n), toplam %d hata:" % sum(err_steps.values()))
    for n in sorted(err_steps):
        print("      n=%d: %d" % (n, err_steps[n]))
    if err_steps:
        vals = np.sort(np.array(list(err_steps.values())))[::-1]
        k = min(5, len(vals))
        print("      konsantrasyon: en yogun %d n, hatalarin %.0f%%'ini tutar" % (k, 100 * vals[:k].sum() / vals.sum()))
    pd.DataFrame([dict(n=n, count=c) for n, c in sorted(err_steps.items())]).to_csv(
        os.path.join(OUT, "multiply_error_steps.csv"), index=False)
# --------------------------------------------------------------------------- #
# B) Central complex keşfi
# --------------------------------------------------------------------------- #
CX_PATS = ("EPG", "PEN", "Delta7")


def part_b():
    ann = pd.read_csv(ANN_FILE, sep="\t", low_memory=False)
    print("\n=== B) CENTRAL COMPLEX KESFI ===")
    print("anotasyon satiri: %d" % len(ann))
    for col in ("cell_type", "hemibrain_type", "supertype", "cell_sub_class", "cell_class", "top_nt"):
        if col in ann.columns:
            v = ann[col].fillna("NA").astype(str)
            print("  %-16s bos=%6d / %d" % (col, int((v == "NA").sum()), len(v)))

    ct = ann["cell_type"].fillna("NA").astype(str)
    ht = ann["hemibrain_type"].fillna("NA").astype(str)
    types = {}
    for pat in CX_PATS:
        m = ct.str.contains(pat, case=False, regex=False)
        types[pat] = set(int(r) for r in ann.root_id[m])
        print("\n-- %s: %d hucre (cell_type)" % (pat, len(types[pat])))
        print(ct[m].value_counts().to_string())
        mh = ht.str.contains(pat, case=False, regex=False)
        print("   hemibrain_type kesisim: %d" % len(set(int(r) for r in ann.root_id[mh]) & types[pat]))
        if "top_nt" in ann.columns:
            sub = ann[ann.root_id.isin(types[pat])]
            print("   top_nt: %s" % sub.top_nt.fillna("NA").value_counts().to_dict())

    conn = pd.read_feather(CONN_FILE, columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
    print("\nkenar yuklendi: %d" % len(conn))

    def edges(A, B):
        e = conn[conn.pre_pt_root_id.isin(A) & conn.post_pt_root_id.isin(B)]
        return dict(n=len(e), syn=int(e.syn_count.sum()),
                    med=float(e.syn_count.median()) if len(e) else 0.0,
                    npre=int(e.pre_pt_root_id.nunique()) if len(e) else 0)

    print("\n-- baglanti matrisleri (pre -> post) --")
    pairs = [("EPG", "PEN"), ("EPG", "Delta7"), ("PEN", "EPG"), ("PEN", "Delta7"),
             ("Delta7", "EPG"), ("Delta7", "PEN"), ("EPG", "EPG"), ("PEN", "PEN"), ("Delta7", "Delta7")]
    rows = []
    for a_, b_ in pairs:
        r = edges(types[a_], types[b_])
        rows.append(dict(pre=a_, post=b_, **r))
        print("  %-8s -> %-8s kenar=%5d sinaps=%7d medyan=%g pre_noron=%d"
              % (a_, b_, r["n"], r["syn"], r["med"], r["npre"]))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cx_edges.csv"), index=False)

    # wedge numaralari (EPG tiplerinde)
    print("\n-- EPG wedge numaralari --")
    epg_names = ct[ct.str.contains("EPG", case=False, regex=False)]
    w = epg_names.str.extract(r"EPG[_\s]*(\d+)")[0].dropna().astype(int)
    print("   benzersiz wedge=%d  min=%d max=%d" % (w.nunique(), w.min(), w.max()) if len(w) else "   wedge numarasi ayiklanamadi")
    print("   ornek tip adlari:", sorted(epg_names.unique())[:12])

    # halka: wedge sirasina gore komsuluk (tip adlarindan)
    if len(w):
        dfw = pd.DataFrame(dict(root_id=epg_names.index, wedge=w.values))  # index hizali degil; guvenli yol:
    return ann, types


def main():
    os.makedirs(OUT, exist_ok=True)
    df, err = part_a()
    df.to_csv(os.path.join(OUT, "multiply.csv"), index=False)
    part_a_report(df, err)
    part_b()
    print("\nBITTI. Cikti: %s" % OUT)


if __name__ == "__main__":
    main()

