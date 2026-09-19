"""numcog/explore_p0d.py — H0.2 inceltme: VPN->KC hedef KC'lerin ham hemibrain_type dagilimi."""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ann = pd.read_csv(
    os.path.join(ROOT, "annotations_783.tsv"), sep="\t", low_memory=False,
    usecols=["root_id", "super_class", "cell_class", "hemibrain_type"])
ann["root_id"] = ann["root_id"].astype("int64")

vpn2kc = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "results_p0", "vpn2kc_edges.csv"))
ht = dict(zip(ann.root_id, ann.hemibrain_type))
vpn2kc["ht"] = vpn2kc.post_pt_root_id.map(ht)
print("VPN->KC hedef KC'lerin hemibrain_type dagilimi (n_edges / n_syn / n_kc):")
g = vpn2kc.groupby("ht").agg(
    n_edges=("syn_count", "size"), n_syn=("syn_count", "sum"),
    n_kc=("post_pt_root_id", "nunique")).sort_values("n_syn", ascending=False)
print(g.to_string())
print("\ntoplam KCg-d hedef: %d, KCg-m: %d" % (
    int(g.loc["KCg-d", "n_kc"]) if "KCg-d" in g.index else 0,
    int(g.loc["KCg-m", "n_kc"]) if "KCg-m" in g.index else 0))
