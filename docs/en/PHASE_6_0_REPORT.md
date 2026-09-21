<!-- Machine translation of `numcog/RAPOR_FAZ_6_0.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 319 numeric tokens present) -->

# RAPOR FAZ 6-0 — CX halka geometrisi keşfi (yalnızca ölçüm; DİNAMİK SİMÜLASYON YOK)

Tarih: 2026-09-20. Durum: tamamlandı. Hipotez ön-kayıtlı (**commit `13647d9`**, ölçümden ÖNCE).
Yeni kod: **`numcog/cx_geometry.py`**. Faz 0–5 dosyaları/sonuçları DEĞİŞTİRİLMEDİ.
**Eşzamanlı süreç ≤ 2** (bu fazda en fazla 1). **Dinamik simülasyon YAPILMADI.**

**Ön-kayıtta sabitlenen seçimler:** birincil konum sütunu **`soma_x/y/z`**; açı düzlemi = **EPG soma
noktalarının PCA'sının ilk iki bileşeni**; PEN açıları **aynı tabana izdüşüm**; EPG↔PEN bağlantısı
**yönsüz toplam**; wedge = **EPG medyan açısal aralığı (veriden)**. m = 3 → **Holm**.

---

## 1. Etiket/konum sayımı (Adım 1)

| küme | n | `soma_xyz` dolu | `pos_xyz` dolu | NaN |
|---|---|---|---|---|
| EPG | **51** (`EPG` 47 + `EPGt` 4) | **51** | 51 | 0 |
| PEN | **42** (`PEN_a(PEN1)` 20, `PEN_b(PEN2)` 22) | **42** | 42 | 0 |
| Delta7 | **42** | **42** | 42 | 0 |

Yan (side): EPG left 26 / right 25; PEN 21/21; Delta7 21/21. EPG'de `pos`↔`soma` mesafesi:
medyan **0.0**, ortalama 1.621,6, en büyük 40.699 → çoğu hücrede `pos` = `soma`.

**Nöropil payı** (CX kümesine dokunan 34.154 kenar, toplam 184.149 sinaps):
**EB %58,1**, **PB %24,1**, NO %10,2, GA_L %3,1, GA_R %2,4, FB %0,7, CRE_R %0,7, MB_ML_R %0,4.
→ PB+EB = **%82,2** (beklendiği gibi halka sisteminin merkezinde).

## 2. Açı ataması (Adım 2)

- **PCA (EPG somaları):** açıklanan varyans **PC1 = 0,601, PC2 = 0,398, PC3 = 0,0004**
  (kovaryans özdeğerleri 8,2e4 / 8,1e7 / 1,2e8). Yani EPG somaları **nereyse tam düzlemsel**
  (düzlem dışı varyans en büyüğün %0,04'ü) → 2B halka modeli **geometrik olarak iyi tanımlı**.
- EPG açıları: min 25,5°, medyan 149,2°, max 359,7°.
- Açısal aralıklar: **medyan 3,30°**, en küçük **0,01°**, **en büyük 77,79°** → tam tur YOK,
  **77,8°'lik bir boşluk** var.
- İkincil (`pos_xyz`) sürüm dosyalara yazıldı (`geometry_angles_pos.csv`), birincil sonuçlar onda
  da tekrarlandı (§4c).

## 3. H6.1–H6.3 (1000 örnek/null; Holm m=3)

| test | gözlenen | null (ort ± sd) | fark | z | p_ham | p_holm | sonuç |
|---|---|---|---|---|---|---|---|
| **H6.1** r_cv (halka) | **0,3357** | 0,5207 ± 0,0522 | −0,1849 | **−3,54** | 0,0010 | **0,0030** | r_cv **AYRIŞIR** |
| **H6.2** ρ (yerellik) | **+0,0537** | +0,0091 ± 0,0286 | +0,0446 | +1,56 | 0,1179 | 0,1179 | ayrisamaz |
| **H6.3** kayma (tanı) | **1,28°** | 65,84° ± 38,16° | **−64,56°** | −1,69 | **0,0340** | 0,0679 | ayrisamaz (Holm) |

- **H6.1 → INVALIDATED (combined criterion).** The pre-recorded criterion required the simultaneous provision of two components: (i) r_cv null 5. persentilinin altında → **SATISFIED** (p_lower = 0,0010, z = −3,54: the spread of the covariance-aligned ellipsoid is **clearly smaller** than → the lobes are a fine **ring shell**); (ii) the largest angular gap ≤ 60° → **NOT SATISFIED** (77,8°). → **Ring-like radial arrangement IS, but not a full circle**. (Additional descriptor: Rayleigh R = 0,208, Kuiper V = 0,216.)
- **H6.2 → INVALIDATED.** Spearman ρ between weight and angular distance = **+0,0537** (expected sign **< 0**); permutation p = 0,118 (Raw) / **0,236 (Holm)**. **Degree-conserved random link control:** ρ = **+0,0046 ± 0,0323** (20 samples) → the observed value is within ~1,5 sd of the control → **no local-neighborhood signal**.
- **H6.3 → INVALIDATED (diagnosis, no direction).** 42/42 PEN EPG input exists; the angular average of the EPG input with weighted angle between PEN soma angle and the |δ| average **79,7°**. Subtype difference: PEN_a = **+8,2°**, PEN_b = **+6,9°** → |difference| = **1,28°**; permutation null **65,84° ± 38,16°**. Upper tail p = **0,9870**; two-sided p_raw = **0,0340** → **Holm p_holm = 0,0679 ≥ 0,05** → no systematic sub-type shift according to the pre-recorded invalidation criterion. *(Note: the raw p value of 0,034 appearing is not "shift exists" but rather that the sub-types are more similar than expected from random subdivisions – this also does not become significant after Holm.)* **Application correction (transparency):** due to the fact that in the first `merge` condition H6.3 null was **radians**, while the observed was **degrees** there was a unit mismatch; the code was corrected (`np.degrees`) and the `merge` was rerun. This is not a pre-record/measurement change, but a unit error correction; the decisions did not change (the p_holm of H6.2 from 0,236 to 0,118, both are nonsignificant).

## 4. EXPLORATORY (post-pre-recorded; measurement/hypothesis not changed)

**(a) Left/right structure — description of the gap.** Left (26) angular spread: the largest gap **226,3°** → it is located in a spread ~134°; right (25): the largest gap **217,3°** → ~143°. The angular difference between the nearest right cell and each left cell: median 57,2°, > 5° in 26/26 cells → **two separated angular spreads occupy both hemispheres**; the left and right somas are not **mirror images (same angle pair)**. The 77,8° gap in the combined cluster is between the ends of these two spreads.

**(b) Number of wedge (slot) from data.** When clustering angles with the gap threshold: threshold 2° → **33 clusters** (mean 1,55 cells), threshold 5° → **18 clusters** (2,83), threshold 10° → **9 clusters** (5,67); **only the left side (5°) → 10 clusters**. The "equal tiling" estimate (median range 3,30°) **109** which is an artifact of the paired/overlapping cell structure → **a clean integer wedge number does not emerge from the data**.

**(c) `pos_xyz` sağlamlığı.** pos tabanlı: r_cv **0,3397** (soma 0,3357), g_max **77,5°** (77,8°),
R 0,194 (0,208), H6.2 ρ **+0,0571** (+0,0537) → **sonuçlar konum sütunu seçimine duyarlı değil**.

## 5. Adım 4 — KARAR (kod yok; yalnızca ölçülen sayılar)

**Halka simülasyonu için yeterli geometri var mı?** **Kısmen.**
- **Var:** EPG somaları neredeyse **düzlemsel** (düzlem dışı varyans %0,04) → 2B halka modeli iyi
  tanımlı; 51 EPG + 42 PEN için **açısal koordinat** ve **yönlü/yönsüz ağırlıklar** (663 + 698 kenar)
  mevcut.
- **Yok / eksik:** boşluk **77,8°** (tam tur kapsanmıyor); **EPG-girdi merkezi ile PEN soma açısı
  arasındaki |δ| ortalaması 79,7°** → bu koordinatlar **işlevsel halka konumları değil, soma
  konumlarıdır**; arborizasyon/sinaps koordinatı ve wedge/glomerül ROI etiketi bu veri sürümünde
  **yok** (Faz 5 §5).

**Kaç wedge çıkarılabildi (ölçümden)?** **Belirsiz ve eşiğe bağlı:** 9 (10° eşik) – 18 (5°) – 33 (2°)
küme; yalnız sol hemisferde 10. Hücre sayısı 51 (26 sol + 25 sağ). **Önceden varsayılan bir wedge
sayısı YOK**; "109" tahmini artefaktır. En savunulabilir aralık **~10–18 ayrılabilir açısal konum**.

**Elle ayarlanacak parametreler (geometri bunları VERMİYOR):** EPG→PEN ve PEN→EPG **kazançları**,
**inhibisyon** gücü/işareti (bu fazda nörotransmitter sütunları kullanılmadı), ağırlık
normalizasyonu, **EPG–PEN koordinatları arasındaki açı kayması** (ölçülen ~80°), zaman sabitleri
(veri yok) ve **wedge sayısı**. Yani **dinamik parametrelerin tamamı elle ayarlanacaktır**.

**Belirsizlik:** (i) soma ≠ halka konumu (~80° ölçülen uyumsuzluk); (ii) 77,8° kapsanmayan yay;
(iii) 9–33 arası slot belirsizliği; (iv) sinaps düzeyinde geometri yok; (v) wedge etiketi yok →
her wedge ataması **çıkarım**dır.

## 6. Adım 5 — ZORUNLU İFADE

> Bu koordinatlardan çıkarılan açılar **wedge etiketi DEĞİLDİR.** Bunlar `soma_x/y/z` (veya `pos`)
> koordinatlarından PCA ile **türetilmiş bir açısal koordinattır**; hiçbir wedge/glomerül/segment/ROI
> etiketi bu veri sürümünde **yoktur** (Faz 5 §5). Ayrıca açının **sıfır noktası ve yönü keyfîdir**
> (PCA eksen işaretleri veriden gelmez): açılar **döndürme ve yansımaya göre belirsiz**dir.
> İleride "wedge k" gibi bir ifade kullanılırsa bu **veri değil, türetilmiş koordinat** olur.

## 7. Sınırlılıklar

- **Soma ≠ halka konumu:** halka EB'deki **arborizasyonlarla** tanımlanır; bu veri sürümünde
  arborizasyon/sinaps koordinatı **yok** (Faz 5 §5). Bu ölçüm **soma** geometrisidir.
- **Açı çerçevesi keyfî:** PCA tabanı soma bulutundan türetildi → açının **sıfır noktası ve yönü**
  veriden gelmez; sonuçlar **döndürme ve yansıma** altında tanımlıdır. H6.2/H6.3 ilişkileri
  döndürmeye duyarsızdır, ama mutlak açı değerleri anlam taşımaz.
- **H6.1 null'u zayıf bir alternatiftir:** kovaryans-eşleşmiş **Gauss bulutu**; disk/torus gibi daha
  güçlü alternatifler denenmedi. Ayrıca somalar neredeyse düzlemsel olduğundan null fiilen 2B'dir.
- **77,8° boşluk ve sol/sağ ayrık yaylar** soma koordinatlarının özelliğidir; **EB halkasının**
  özelliği olduğu gösterilmedi.
- **H6.2 gücü sınırlı:** 693 çift, ρ küçük ve anlamsız; kontrol de etkisiz. "Etki yok" sonucu bu
  güçle söylenir (yokluk kanıtı değil).
- **H6.3'ün referansı keyfî:** δ, **iki farklı hücre tipinin soma açıları** arasındaki farktır; 79,7°
  ortalaması **işlevsel bir faz kayması değil**, koordinat uyumsuzluğudur.
- **Slot/wedge sayısı en kırılgan sayıdır:** eşiğe bağlı 9/18/33.
- **Dinamik simülasyon yapılmadı; işlev/hesaplama iddiası yok** (Faz 5 yorum kuralı).
- **Tek connectome örneği** (hemibrain 783) ve tek hemisfer çifti; bireysel/cinsiyet varyasyonu
  modellenmedi.
- **Çoklu karşılaştırma:** yalnızca ön-kayıtlı **m=3** ailesi Holm ile düzeltildi; **KEŞİFSEL**
  bölümdeki analizler düzeltilmedi ve doğrulayıcı kanıt sayılmaz.

## 8. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py labels        # Adım 1
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py geometry      # Adım 2
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py h61 0 1       # H6.1 (1000 örnek null)
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py h62           # H6.2 + kontrol
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py h63           # H6.3
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py merge         # Holm m=3 + karar sayıları
.venv/Scripts/python.exe -X utf8 numcog/cx_geometry.py explore       # KEŞİFSEL (a,b,c)
```

Tüm null'lar **deterministik tohum** kullanır (`RandomState(7000 + örnek_no)`); `h61` shard'lı
çalışabilir (`h61 <shard> <nsh>`), bu koşuda **1 süreç** (≤2 kuralı).

Çıktılar (`numcog/results_p6_0/`): `label_counts.csv`, `neuropil_share.csv`, `geometry_angles.csv`,
`geometry_angles_pos.csv`, `h61_observed.csv`, `h61_shard0.csv`, `h62_edges.csv`, `h62_null.csv`,
`h62_control.csv`, `h62_observed.csv`, `h63_delta.csv`, `h63_null.csv`, `h63_observed.csv`,
`mx_tests.csv`, `explore.csv`, `run.log`.

## 9. ÖZET (kapanış)

1. **Konum verisi tam:** EPG 51 (26 sol / 25 sağ; EPG 47 + EPGt 4), PEN 42 (PEN_a 20 / PEN_b 22),
   Delta7 42; `soma_xyz` ve `pos_xyz` **%100 dolu**, NaN yok. Nöropil: **EB %58,1 + PB %24,1 = %82,2**.
2. **Düzlemsellik güçlü:** PCA PC1 0,601 / PC2 0,398 / **PC3 0,0004** → somalar neredeyse tek düzlemde.
3. **H6.1 ÇÜRÜTÜLDÜ (birleşik):** radyal halka kabuğu **var** (r_cv 0,336 vs null 0,521, z = −3,54,
   p_holm = 0,003) ama **tam tur yok** (en büyük boşluk **77,8°** > 60°).
4. **H6.2 ÇÜRÜTÜLDÜ:** ρ = **+0,0537** (beklenen < 0), p_holm = 0,236; derece-korunmuş kontrol
   ρ = +0,0046 ± 0,0323 → **yerellik sinyali yok**.
5. **H6.3 ÇÜRÜTÜLDÜ:** alt tip kayması **1,28°** (null 65,84° ± 38,16°; p_holm = 0,0679) →
   **sistematik yön kayması yok**; ham iki-yanlı p = 0,034 ise alt tiplerin beklenenden **daha
   benzer** olduğunu gösterir (Holm sonrası anlamsız).
6. **Adım 4 kararı:** geometri **kısmen yeterli** (düzlemsel 2B koordinat + ağırlıklar var; boşluk,
   ~80° soma-koordinat uyumsuzluğu ve wedge etiketinin yokluğu var). **Temiz wedge sayısı veriden
   çıkmıyor** (eşiğe göre 9–18–33); dinamik parametrelerin (kazançlar, inhibisyon, zaman sabitleri,
   wedge sayısı, koordinat kayması) **tamamı elle ayarlanacak**. Belirsizlik yüksek.
7. **Adım 5:** türetilen açılar **wedge etiketi değildir**; **çıkarım**dır ve döndürme/yansımaya göre
   belirsizdir. Dinamik simülasyon yapılmadı; işlev iddiası yok.

# HARD RULES:
1. Keep every number, decimal, percent, seed count, commit hash, file name, path, unit and symbol EXACTLY as it is.
2. Keep the Markdown structure: headings, tables (same rows and columns), lists, code fences, blockquotes, bold/italic markers.
3. Do not add, remove or summarise anything. Translate every sentence and every table cell.
4. Do not translate code identifiers, CSV column names or file names.
5. Output ONLY the translation, no preamble, no notes, no explanation.

# HARD RULES:
1. Keep every number, decimal, percent, seed count, commit hash, file name, path, unit and symbol EXACTLY as it is.
2. Keep the Markdown structure: headings, tables (same rows and columns), lists, code fences, blockquotes, bold/italic markers.
3. Do not add, remove or summarise anything. Translate every sentence and every table cell.
4. Do not translate code identifiers, CSV column names or file names.
5. Output ONLY the translation, no preamble, no notes, no explanation.
