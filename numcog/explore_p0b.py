"""numcog/explore_p0b.py — Faz 0 odaklı ölçüm: VPN (super_class=visual_projection) → KC, MBIN, KC alt tipleri."""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ann = pd.read_csv(
    os.path.join(ROOT, "annotations_783.tsv"), sep="\t", low_memory=False,
    usecols=["root_id", "cell_class", "cell_sub_class", "super_class",
             "cell_type", "hemibrain_type", "side", "top_nt"])
ann["root_id"] = ann["root_id"].astype("int64")
conn = pd.read_feather(
    os.path.join(ROOT, "proofread_connections_783.feather"),
    columns=["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil"])

kc = set(int(r) for r in ann.root_id[
    ann.cell_class.astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)])
alpn = set(int(r) for r in ann.root_id[
    ann.cell_class.astype(str).str.fullmatch("ALPN", case=False, na=False)])
vpn_ids = set(int(r) for r in ann.root_id[
    ann.super_class.astype(str).str.fullmatch("visual_projection", case=False, na=False)])
vis_cls = set(int(r) for r in ann.root_id[
    ann.cell_class.astype(str).str.fullmatch("visual", case=False, na=False)])

in_kc = conn[conn.post_pt_root_id.isin(kc)]

def report(name, idset):
    e = in_kc[in_kc.pre_pt_root_id.isin(idset)]
    e3 = e[e.syn_count >= 3]
    print("%-38s neurons=%-6d edges(all)=%-7d syn(all)=%-7d edges(>=3)=%-6d syn(>=3)=%d"
          % (name, len(idset), len(e), int(e.syn_count.sum()), len(e3), int(e3.syn_count.sum())))
    if len(e):
        print("    per-edge syn: min=%d median=%g mean=%.2f max=%d"
              % (int(e.syn_count.min()), e.syn_count.median(), e.syn_count.mean(), int(e.syn_count.max())))

print("=== KC = %d, ALPN = %d, super_class=visual_projection = %d, cell_class=visual = %d ==="
      % (len(kc), len(alpn), len(vpn_ids), len(vis_cls)))
report("ALPN", alpn)
report("visual_projection (VPN, super_class)", vpn_ids)
report("visual (cell_class)", vis_cls)
report("visual_projection UNION visual", vpn_ids | vis_cls)

mbin = ann[ann.cell_class.astype(str).str.fullmatch("MBIN", case=False, na=False)]
print("\n=== MBIN neurons (cell_class=MBIN) ===")
print(mbin[["root_id", "cell_type", "hemibrain_type", "cell_sub_class", "top_nt", "side"]].to_string())

kcann = ann[ann.root_id.isin(kc)]
print("\n=== KC cell_sub_class (alt tip) dagilimi ===")
print(kcann.cell_sub_class.fillna("NA").value_counts().to_string())
print("\n=== KC hemibrain_type (top 15) ===")
print(kcann.hemibrain_type.fillna("NA").value_counts().head(15).to_string())

v_edges = in_kc[in_kc.pre_pt_root_id.isin(vpn_ids | vis_cls)]
if len(v_edges):
    v_edges = v_edges.merge(
        ann[["root_id", "cell_type", "cell_class", "super_class"]],
        left_on="pre_pt_root_id", right_on="root_id", how="left")
    print("\n=== KC'ye dokunan görsel nöronlar (all syn) ===")
    print(v_edges.groupby(["super_class", "cell_class", "cell_type"]).agg(
        n_edges=("syn_count", "size"), n_syn=("syn_count", "sum")).to_string())
else:
    print("\n=== KC'ye dokunan görsel nöron: 0 kenar ===")

# MBIN girdisi ayrıntısı: bu 4 nöron KC alt tiplerine nasıl dağılıyor
print("\n=== MBIN -> KC kenar sayısı / toplam sinaps ===")
mb_edges = in_kc[in_kc.pre_pt_root_id.isin(set(int(r) for r in mbin.root_id))]
print("edges=%d syn=%d" % (len(mb_edges), int(mb_edges.syn_count.sum())))
