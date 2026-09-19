"""numcog/explore_p0c.py — Faz 0 kesin ölçüm: VPN->KC vs ALPN->KC, KC alt tipi + neuropil dagilimi."""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_p0")
ann = pd.read_csv(
    os.path.join(ROOT, "annotations_783.tsv"), sep="\t", low_memory=False,
    usecols=["root_id", "cell_class", "cell_sub_class", "super_class",
             "cell_type", "hemibrain_type", "side", "top_nt"])
ann["root_id"] = ann["root_id"].astype("int64")
conn = pd.read_feather(
    os.path.join(ROOT, "proofread_connections_783.feather"),
    columns=["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil"])

def ids(mask):
    return set(int(r) for r in ann.root_id[mask])

kc = ids(ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False))
alpn = ids(ann.cell_class.astype(str).str.fullmatch("ALPN", case=False, na=False))
vp = ids(ann.super_class.astype(str).str.fullmatch("visual_projection", case=False, na=False))

def st(name):
    s = "" if (name is None or (isinstance(name, float) and np.isnan(name))) else str(name)
    if s.startswith("KCa'b'"):
        return "apbp"
    if s.startswith("KCab"):
        return "ab"
    if s.startswith("KCg"):
        return "g"
    return "other"

sub = dict(zip(ann.root_id, ann.hemibrain_type.apply(st)))

in_kc = conn[conn.post_pt_root_id.isin(kc)]

def measure(name, idset, csv_name):
    e = in_kc[in_kc.pre_pt_root_id.isin(idset)].copy()
    e3 = e[e.syn_count >= 3]
    e["sub"] = e.post_pt_root_id.map(sub)
    print("### %s" % name)
    print("n_pre=%d  n_edges=%d  n_syn=%d  n_post_kc=%d"
          % (e.pre_pt_root_id.nunique(), len(e), int(e.syn_count.sum()),
             e.post_pt_root_id.nunique()))
    print("per-edge syn: min=%d med=%g mean=%.2f max=%d"
          % (int(e.syn_count.min()), e.syn_count.median(), e.syn_count.mean(),
             int(e.syn_count.max())))
    print(">=3 : n_edges=%d  n_syn=%d" % (len(e3), int(e3.syn_count.sum())))
    print("KC subtype (n_edges / n_syn / n_kc):")
    print(e.groupby("sub").agg(
        n_edges=("syn_count", "size"), n_syn=("syn_count", "sum"),
        n_kc=("post_pt_root_id", "nunique")).to_string())
    print("neuropil:")
    print(e.neuropil.value_counts().head(8).to_string())
    print()
    e[["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil", "sub"]].to_csv(
        os.path.join(OUT, csv_name), index=False)
    return e

measure("ALPN -> KC", alpn, "alpn2kc_edges.csv")
vpn_edges = measure("VPN (super_class=visual_projection) -> KC", vp, "vpn2kc_edges.csv")

vpa = ann[ann.root_id.isin(vp)]
print("### VPN neuronlarinin cell_class dagilimi (top 12)")
print(vpa.cell_class.fillna("NA").value_counts().head(12).to_string())

# H0.4 kontrolu: KC'ye dokunan VPN nöron sayisi vs 685 ALPN
print("\nKC'ye dokunan VPN noron sayisi: %d (toplam VPN %d)" % (
    vpn_edges.pre_pt_root_id.nunique(), len(vp)))
