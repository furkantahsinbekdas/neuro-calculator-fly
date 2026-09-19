# RAPOR FAZ 0 — Veri keşfi: VPN (görsel projeksiyon nöronu) → KC bağlantısı

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `364285d`,
`numcog/HIPOTEZLER.md`), ölçümler onlardan sonra yapıldı.

## 1. Yöntem

Ölçüm, `flysim.py` / `cognitive_matrix.py` / `sniff.py`'yi **import etmeden** veri
dosyalarını doğrudan pandas ile okur (o üç modülün değişikliğinden bağımsız kalsın diye):

- `proofread_connections_783.feather` → 16.847.997 kenar; sütunlar `pre_pt_root_id,
  post_pt_root_id, neuropil, syn_count, …`.
- `annotations_783.tsv` → 139.248 satır; `super_class, cell_class, cell_sub_class,
  cell_type, hemibrain_type, side, top_nt`.

Kümeler: `cell_class == "Kenyon_Cell"` (KC), `cell_class == "ALPN"`,
`super_class == "visual_projection"` (VPN). VPN→KC = `pre ∈ VPN ∧ post ∈ KC` kenarları.
Betikler: `numcog/explore_p0.py` (taksonomi + bileşim), `explore_p0b.py` (VPN + MBIN),
`explore_p0c.py` (kesin ölçüm), `explore_p0d.py` (KCg-d ayrıştırması). Ham kenarlar
`numcog/results_p0/*.csv`.

## 2. Kümeler

| Küme | Sayı |
|---|---|
| Kenyon_Cell (KC) | 5.177 |
| ALPN (koku) | 685 |
| super_class = visual_projection (VPN) | 8.038 |
| cell_class = visual | 11.391 |

KC alt tipleri (hemibrain_type): γ **2.489** (%48.1; KCg-m 2.189, KCg-d 295, KCg-s 5),
αβ **1.771** (%34.2; KCab-s 621, -m 619, -c 403, -p 128),
α'β' **917** (%17.7; KCa'b'-m 338, -ap2 298, -ap1 281).

## 3. Sonuç

### 3.1 VPN→KC var mı? (S1) — EVET, ama küçük ve γ-özel

| ölçüm | VPN→KC | ALPN→KC (referans) |
|---|---|---|
| nöron (pre) | **265** | 319 |
| hedef KC | **427** | 4.887 |
| kenar (tüm) | 2.035 | 28.144 |
| sinaps (tüm) | 13.867 | 329.394 |
| kenar (≥3) | 1.055 | 23.618 |
| sinaps (≥3) | 12.659 | 323.651 |
| sinaps/kenar: medyan · ortalama · max | 3 · 6.81 · 83 | 11 · 11.70 · 69 |

VPN→KC ≈ ALPN→KC'nin **%7'si (kenar), %4.2'si (sinaps)**. Gerçek ve ölçülebilir ama
küçük bir görsel kanal var.

### 3.2 KC alt tipi dağılımı (H0.2)

VPN→KC (sinaps payı): **γ %92.5** (12.833/13.867), αβ %7.4 (1.021), α'β' %0.1 (13).

Ham hemibrain_type ayrıştırması (hedef KC / sinaps / pay):

| KC tipi | hedef KC | sinaps | pay |
|---|---|---|---|
| **KCg-d (γ-d)** | 286 | 11.703 | **%84.4** |
| KCab-p (αβ-p) | 102 | 1.008 | %7.3 |
| KCg-m / KCg-s | ~35 | 1.130 | %8.1 |
| KCa'b' (α'β') | 2 | 13 | %0.1 |

Karşılaştırma — ALPN→KC geniş dağılır: αβ 1.709 KC, γ 2.263 KC, α'β' 915 KC.
VPN→KC ise **neredeyse yalnızca γ-d** (ve ikincil αβ-p) KC'lerine iner. H0.2 doğrulandı.

### 3.3 ALPN dışında KC'ye bağlanan duyusal projeksiyon nöronları (S2)

KC'lerin **tüm** presinaptik girdi bileşimi (`results_p0/kc_input_composition_all.csv`,
cell_class bazında, sinaps toplamıyla):

| cell_class | n_pre | kenar | sinaps | nitelik |
|---|---|---|---|---|
| Kenyon_Cell | 5.177 | 326.685 | 379.338 | KC→KC (yinelenen) |
| ALPN | 319 | 28.144 | 329.394 | **koku — tek asıl kodlama girdisi** |
| MBIN | 4 | 31.297 | 107.934 | APL(GABA)+DPM(dopamin) — **geri-besleme, duyusal değil** |
| DAN | 328 | 49.616 | 60.657 | dopaminerjik modülatör |
| MBON | 94 | 11.262 | 13.206 | çıktı/geri-besleme |
| LHCENT | 16 | 2.365 | 4.452 | lateral horn santrifüj |
| bilateral (VPN) | 69 | 106 | 211 | görsel VPN'ler (MTe/MeMe/aMe) |
| … CX/bilateral/LHLN/… | küçük | küçük | küçük | çeşitli |

**ALPN dışında KC'ye doğrudan bağlanan duyusal projeksiyon nöronu: yalnızca VPN**
(265 nöron, 13.9k sinaps, γ-d ağırlıklı). Gustatory (408) → **0 kenar**;
mechanosensory (2.668) → **0 kenar**. MBIN zannedildiği gibi duyusal değil: **APL + DPM**
(iki yarımküredeki MB-genişliğinde geri-besleme/modülatör nöron).

### 3.4 VPN→KC neuropil

VPN→KC kenarları ağırlıklı olarak **PLP** (687+653) ve **SCL/SLP** (~440) içinde; ana
kaliks **MB_CA** yalnızca 140 kenar. Bu, γ-d KC dendritlerinin yerleştiği aksesuar
kaliks/PLP bölgesiyle tutarlıdır (ana kaliks ALPN'lerindir: ALPN→KC'nin ~27.4k kenarı
MB_CA'da).
## 4. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H0.1 VPN→KC var, ALPN→KC'nin ~%1–10'u | **DESTEKLENDİ** (%7 kenar / %4.2 sinaps) |
| H0.2 görsel girdi γ-d'ye iner, α'β' çok az | **DESTEKLENDİ** (γ-d %84.4; α'β' %0.1) |
| H0.3 kenar medyanı ≤ ~10 | **DESTEKLENDİ** (medyan 3) |
| H0.4 KC'ye dokunan VPN < 685 | **DESTEKLENDİ** (265) |
| H0.5 strateji: H0.1 tutarsa (a) | **(a) seçildi, aşağıda** |

## 5. Giriş katmanı stratejisi (S3 — AÇIKÇA)

**STRATEJİ (a):** `coarse_kc`'de gerçek **VPN→KC matrisi** kullanılacak
(427 KC × 265 VPN; ≥3 sinaps eşiğiyle 1055 kenar). Görsel kanal gerçek bir devredir;
soyut bir "sayı kodu" değildir.

Ama ölçülen iki sınır, Faz 1'in **varsaymadan ölçmesi** gereken koşullar olarak
ön-kayda geçiyor (hedef değiştirmek değil, önceden yazılmış olasılık):

1. Matris küçük ve γ-d/αβ-p'ye özgü: 265 VPN → 427 KC, kenar medyanı 3. Eşik
   (coincidence ≥2/3/4) taramasında aktif KC sayısı çok düşük (hatta sıfır) kalabilir.
2. Eğer ölçüm, VPN→KC katmanının sayı kodlaması için kullanılamayacak kadar seyrek
   olduğunu gösterirse, önceden yazılmış **yedek (b)** devreye girer: kaba kodlama
   ALPN/PN girdisi üzerine uygulanır ve raporda "görsel kanal gerçek bir görsel devre
   değil, soyut bir sayı kodudur" denir. Bu, hipotez değiştirmek değil; H0.5'te
   önceden yazılmış koşullu yoldur.

## 6. Sınırlılıklar

- Bu bir **simülasyon/ölçüm**; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).
- VPN→KC temaslarının kompartman düzeyi (dendrit mi akson mu) elimizde yok — yalnızca
  neuropil var. PLP/SCL konumu γ-d dendrit bölgesiyle uyumlu ama kanıtlanmış dendritik
  girdi değil.
- 7.949/8.038 VPN `cell_class` düzeyinde boş (yalnız `super_class` işaretli); bu yüzden
  VPN tespiti `super_class == "visual_projection"` ile yapıldı.
- `syn_count` bağlantı gücünün tek vekilidir; sinaptik işaret (uyarıcı/baskılayıcı)
  ayrımı yapılmadı.

## 7. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/explore_p0.py      # taksonomi + bileşim
.venv/Scripts/python.exe -X utf8 numcog/explore_p0b.py     # VPN(super_class) + MBIN
.venv/Scripts/python.exe -X utf8 numcog/explore_p0c.py     # kesin VPN->KC / ALPN->KC
.venv/Scripts/python.exe -X utf8 numcog/explore_p0d.py     # KCg-d ayrıştırması
```
Ham çıktılar: `numcog/results_p0/` (kompozisyon + `vpn2kc_edges.csv` + `alpn2kc_edges.csv`).

**KARAR:** FAZ 1'e geçiş için bekleniyor (dur — kullanıcı onayı).

