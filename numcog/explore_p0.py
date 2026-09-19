"""
numcog/explore_p0.py — FAZ 0: veri keşfi (ölçer, değiştirmez).

Soru: FlyWire v783'te görsel projeksiyon nöronu (VPN) → Kenyon hücresi (KC) bağlantısı
var mı? Varsa sayı, sinaptik ağırlık dağılımı ve KC alt tipleri (αβ / α'β' / γ) bazında
raporla; yoksa ALPN dışında hangi duyusal projeksiyon nöronları KC'lere bağlanıyor listele.

Yalnızca okur: flysim.py / cognitive_matrix.py / sniff.py import edilmez, veri dosyaları
doğrudan pandas ile okunur (ölçüm o üç modülün değişikliğinden bağımsız olsun diye).
Çıktılar numcog/results_p0/ altına CSV olarak yazılır.
"""
from __future__ import annotations
import os
import re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))   # .../flyputer/numcog
ROOT = os.path.dirname(HERE)                        # .../flyputer
CONN_FILE = os.path.join(ROOT, "proofread_connections_783.feather")
ANN_FILE = os.path.join(ROOT, "annotations_783.tsv")
OUT = os.path.join(HERE, "results_p0")


def kc_subtype(name):
    """Best-effort KC alt tipi: αβ='ab', α'β'='apbp', γ='g'. Ham isimler de ayrıca basılır."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return "?"
    s = str(name)
    if re.match(r"^KCa['’]?b['’]", s) or re.match(r"^KCa\.b\.", s):
        return "apbp"
    if s.startswith("KCab"):
        return "ab"
    if s.startswith("KCg"):
        return "g"
    if s.startswith("KC"):
        return "other"
    return "?"


def main():
    os.makedirs(OUT, exist_ok=True)

    print("== anotasyon yükleniyor ==")
    ann = pd.read_csv(
        ANN_FILE, sep="\t", low_memory=False,
        usecols=["root_id", "flow", "super_class", "cell_class",
                 "cell_sub_class", "cell_type", "hemibrain_type", "side"])
    ann["root_id"] = ann["root_id"].astype("int64")
    print("anotasyon satırı:", len(ann))

    print("\n== taksonomi census (sınıf düzeyi sütunlar) ==")
    for c in ["flow", "super_class", "cell_class", "cell_sub_class"]:
        vc = ann[c].fillna("NA").astype(str).value_counts()
        print("\n--- %s (%d benzersiz) ---" % (c, len(vc)))
        print(vc.head(30).to_string())

    print("\n== KC / ALPN kümeleri ==")
    kc_mask = ann["cell_class"].astype(str).str.fullmatch("Kenyon_Cell", case=False, na=False)
    alpn_mask = ann["cell_class"].astype(str).str.fullmatch("ALPN", case=False, na=False)
    kc_ids = set(int(r) for r in ann.root_id[kc_mask])
    alpn_ids = set(int(r) for r in ann.root_id[alpn_mask])
    print("KC = %d nöron,  ALPN = %d nöron" % (len(kc_ids), len(alpn_ids)))

    kc_ann = ann[kc_mask]
    print("\n--- KC hemibrain_type (top 30) ---")
    print(kc_ann["hemibrain_type"].fillna("NA").value_counts().head(30).to_string())
    print("\n--- KC cell_type (top 30) ---")
    print(kc_ann["cell_type"].fillna("NA").value_counts().head(30).to_string())

    # KC alt tipi eşlemesi: hemibrain_type, dolu değilse cell_type.
    kc_ann = kc_ann.copy()
    kc_ann["_subname"] = kc_ann["hemibrain_type"].fillna(kc_ann["cell_type"])
    kc_ann["_subtype"] = kc_ann["_subname"].apply(kc_subtype)
    sub = kc_ann["_subtype"].value_counts()
    print("\n--- KC alt tipi (best-effort: ab/apbp/g/other/?) ---")
    print(sub.to_string())
    kc_subtype_map = dict(zip(kc_ann.root_id.astype("int64"), kc_ann["_subtype"]))
    print("\n== bağlantı verisi yükleniyor (yalnızca gerekli sütunlar) ==")
    conn = pd.read_feather(
        CONN_FILE,
        columns=["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil"])
    print("kenar satırı:", len(conn))

    # KC'lerin presinaptik girdi bileşimi (tüm sinaps sayıları) — belirleyici tablo.
    print("\n== KC presinaptik girdi bileşimi (post ∈ KC) ==")
    in_kc = conn[conn["post_pt_root_id"].isin(kc_ids)]
    del conn
    in_kc = in_kc.merge(
        ann[["root_id", "cell_class", "cell_sub_class", "super_class"]],
        left_on="pre_pt_root_id", right_on="root_id", how="left").drop(columns="root_id")
    g = in_kc.groupby("cell_class").agg(
        n_pre=("pre_pt_root_id", "nunique"),
        n_edges=("syn_count", "size"),
        n_syn=("syn_count", "sum"))
    g = g.sort_values("n_syn", ascending=False)
    print("\n--- tüm kenarlar (top 30 cell_class, sinaptik toplam sırasıyla) ---")
    print(g.head(30).to_string())
    g.to_csv(os.path.join(OUT, "kc_input_composition_all.csv"))

    g3 = in_kc[in_kc.syn_count >= 3].groupby("cell_class").agg(
        n_pre=("pre_pt_root_id", "nunique"),
        n_edges=("syn_count", "size"),
        n_syn=("syn_count", "sum")).sort_values("n_syn", ascending=False)
    print("\n--- syn_count ≥ 3 (sniff.circuit eşiği; top 30) ---")
    print(g3.head(30).to_string())
    g3.to_csv(os.path.join(OUT, "kc_input_composition_ge3.csv"))

    # ALPN→KC referansı
    alpn2kc = in_kc[in_kc.pre_pt_root_id.isin(alpn_ids)]
    print("\n== ALPN→KC (referans) ==")
    print("nöron(pre)=%d  kenar=%d  toplam sinaps=%d  medyan=%g  ortalama=%g" % (
        alpn2kc.pre_pt_root_id.nunique(), len(alpn2kc), alpn2kc.syn_count.sum(),
        alpn2kc.syn_count.median(), alpn2kc.syn_count.mean()))

    # VPN adayları: cell_class/cell_sub_class içinde görsel anahtarları.
    vis_key = ann["cell_class"].astype(str).str.contains("visual|vpn|optic", case=False, na=False)
    vis_key |= ann["cell_sub_class"].astype(str).str.contains("visual|vpn|optic", case=False, na=False)
    vis = ann[vis_key]
    print("\n== VPN/görsel adayları (cell_class/cell_sub_class içinde visual|vpn|optic) ==")
    print("aday nöron:", len(vis))
    print(vis["cell_class"].fillna("NA").value_counts().head(20).to_string())
    print("\ncell_sub_class dağılımı:")
    print(vis["cell_sub_class"].fillna("NA").value_counts().head(20).to_string())

    if len(vis):
        vis_ids = set(int(r) for r in vis.root_id)
        vpn2kc = in_kc[in_kc.pre_pt_root_id.isin(vis_ids)]
        print("\n== VPN/görsel → KC (ölçüm) ==")
        print("nöron(pre)=%d  kenar=%d  toplam sinaps=%d  medyan=%g  ortalama=%g  max=%g" % (
            vpn2kc.pre_pt_root_id.nunique(), len(vpn2kc), vpn2kc.syn_count.sum(),
            vpn2kc.syn_count.median(), vpn2kc.syn_count.mean(), vpn2kc.syn_count.max()))
        print("\nsinaps/kenar dağılımı (VPN→KC):")
        print(vpn2kc.syn_count.value_counts().sort_index().to_string())
        if len(vpn2kc):
            vpn2kc["_subtype"] = vpn2kc.post_pt_root_id.map(kc_subtype_map)
            print("\nKC alt tipi bazında VPN→KC:")
            agg = vpn2kc.groupby("_subtype").agg(
                n_edges=("syn_count", "size"), n_syn=("syn_count", "sum"),
                n_kc=("post_pt_root_id", "nunique"), n_vpn=("pre_pt_root_id", "nunique"))
            print(agg.to_string())
            vpn2kc[["pre_pt_root_id", "post_pt_root_id", "syn_count", "neuropil", "_subtype"]].to_csv(
                os.path.join(OUT, "vpn2kc_edges.csv"), index=False)
        print("\nneuropil dağılımı (VPN→KC):")
        print(vpn2kc["neuropil"].value_counts().head(15).to_string())

    print("\n== BİTTİ == (CSV'ler: %s)" % OUT)


if __name__ == "__main__":
    main()

