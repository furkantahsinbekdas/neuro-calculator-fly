<!-- Machine translation of `numcog/RAPOR_FAZ_6_0b.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 315 numeric tokens present) -->

# RAPOR FAZ 6-0b — Koordinattan bağımsız halka testi (spektral; yalnızca ölçüm)

Tarih: 2026-09-20. Durum: tamamlandı. Hipotez ön-kayıtlı (**commit `193f21c`**, ölçümden ÖNCE).
Yeni kod: **`numcog/cx_spectral.py`**. Faz 0–6-0 dosyaları/sonuçları DEĞİŞTİRİLMEDİ.
**Eşzamanlı süreç: 1. DİNAMİK SİMÜLASYON YAPILMADI.**

**Ön-kayıtta sabitlenenler:** kenar tanımı **Faz 4B-0 ile aynı** (sinaps tablosundan `pre ∈ EPG ∧
post ∈ PEN`, min_syn eşiği yok); **W** = 51×42 ağırlık; **M = [[0,W],[Wᵀ,0]]** (93×93) **BİRİNCİL**;
**S = W Wᵀ** (51×51, köşegen sıfır) **ko-analiz**; yöntem = normalize edilmemiş Laplasyen
`L = D − A` + **ilk iki nontrivial özvektör** ile 2B gömme; ölçütler = **r_cv**, **Kuiper V**,
**en büyük açısal boşluk g_max**; null = **derece-korunmuş rastgele bağlantı (1000)**; Holm **m=2**.

---

## 1. Etiket/NaN sayımı ve girdi

| küme | n | `hemibrain_type` | tip sütunlarında NaN |
|---|---|---|---|
| EPG | **51** | `EPG` 47, `EPGt` 4 | 0 |
| PEN | **42** | `PEN_b(PEN2)` 22, `PEN_a(PEN1)` 20 | 0 |

- **W:** 51×42; sinaps tablosunda **663 satır** → **582 benzersiz (EPG,PEN) çifti** → ikili yapıda
  **582 kenar**, toplam **6.852 sinaps**. **EPG→PEN çıkışı olan EPG: 50/51**; PEN girişi olan: 42/42.
- **Wedge/glomerül etiketi:** EPG tip adlarında **sayı YOK** (`EPG`, `EPGt`). Veri sürümündeki sayı
  içeren tek etiketler `PEN_a(PEN1)` / `PEN_b(PEN2)` — bunlar **PEN alt tip** adları, wedge değil.
  → **Bu veri sürümünde wedge/glomerül etiketi YOKTUR** (Faz 4B-0 H4b0.5 ve Faz 6-0 §6 ile aynı).

## 2. Gömme (Adım 2)

**Önce graf yapısı:** M ve S **BAĞLI DEĞİL** — **2 sıfır özdeğer** (λ1 = λ2 = 0). Keşifsel analiz
(§6) nedeni göstermiştir: **tek bir izole EPG hücresi** (hiç EPG→PEN çıkışı yok) + kalan **50 EPG
(25 sol + 25 sağ) + 42 PEN** ana bileşeni. Yani "2 bileşen" bir **hemisfer ayrımı DEĞİL**, izole
hücre artefaktıdır.

Bu nedenle **ön-kayıttaki "ilk iki nontrivial özvektör" ifadesi, gözlenen ve tüm null örneklerinde
TUTARLI biçimde, en küçük iki SIFIR-DIŞI özvektör olarak uygulanmıştır** (λ=0 sayısı 2 olduğu için
literal "indis 1,2" seçimi ikinci sıfır özvektörü = bileşen göstergesini içerirdi). Ön-kayıttaki
literal sürüm de aşağıda **aynen raporlanmıştır**; metrik/null/eşik değiştirilmemiştir.

| gömme | n | sıfır özdeğer | **BİRİNCİL r_cv** | r_mean | **g_max** | Kuiper V | LİTERAL(indis 1,2) r_cv / g_max |
|---|---|---|---|---|---|---|---|
| **M (93×93)** | 93 | 2 | **1,1538** | 0,0963 | **86,2°** | 0,421 | 1,7668 / 92,3° |
| S (51×51) | 51 | 2 | **1,6562** | 0,1031 | **87,1°** | 0,512 | 2,0597 / 93,7° |

λ dizisi (M): 0, 0, 6,54, 7,64, 9,26, 11,75 → **λ2 ≈ λ3 dejenerasyonu YOK**.

## 3. Testler (derece-korunmuş null, 1000 örnek)

Derece korunumu her örnekte **assert** edildi (EPG satır ve PEN sütun dereceleri birebir);
1000 örnek 56 s'de tamamlandı.

| test | gözlenen | null (ort ± sd) | z | p_ham | p_holm | sonuç |
|---|---|---|---|---|---|---|
| **H6b.1** r_cv (M) | **1,1538** | 2,8476 ± 0,4753 | **−3,56** | 0,0010 | **0,0020** | **AYRIŞIR** (literal ölçüt) |
| **H6b.2** g_max (M) | **86,2°** | 71,5 ± 19,4 | +0,76 | 0,6154 | 0,6154 | **ayrisamaz** |
| ko-analiz (S) r_cv | 1,6562 | 2,6755 ± 0,1859 | −5,48 | 0,0010 | — | ayrışır (ham p) |
| ko-analiz (S) g_max | 87,1° | 91,6 ± 14,6 | −0,31 | 0,2088 | — | ayrisamaz |

- **H6b.2 ÇÜRÜTÜLDÜ:** g_max = **86,2° ≥ 60°** ve null'a göre de aşırı değil (p_ham = 0,615;
  null'un kendi ortalaması 71,5 ± 19,4). **Tam tur çıkmıyor.**
- **H6b.1 literal ölçütü SAĞLANDI** (p_holm = 0,0020; gözlenen r_cv, derece-korunmuş null'un çok
  altında). **AMA bu "halka" demek DEĞİLDİR ve öyle yorumlanmamıştır:**
  - Gözlenen **r_cv = 1,15** iken Faz 6-0'ın soma tabanlı halka gömlezi **r_cv = 0,336**'dır
    (**~3,4× daha küçük**). r_cv ≈ 1,15 "ince halka kabuğu" değil, **iki-loblu/bulutsu** bir gömmedir
    (Laplasyen'in baş özvektörleri grafı bölmeye eğilimlidir; izole hücre de yapıyı zorlar).
  - Null'un r_cv'sinin daha da büyük olması (2,85 ± 0,48) yalnızca "rastgele bağlantı bu ölçütte
    daha ekstrem" demektir; **gözlenenin halka olduğunu göstermez**.
  - Bu nedenle ölçüt **biçimsel olarak** geçse de **içerik olarak** halka iddiası **desteklenmemiştir**.

## 4. BONUS: gömme açısı vs Faz 6-0 soma açısı

| gömme | |r_c| (dairesel korelasyon) |
|---|---|---|
| M (93×93, EPG alt kümesi) | **0,300** |
| S (51×51) | **0,322** |

Zayıf-pozitif uyum. **İşaret, özvektör yönü keyfî olduğu için raporlanmamıştır** (|r_c| verilir).

## 5. Adım 4 — KARAR (yalnızca ölçümden; kod yok)

**Gömmeden kaç wedge/slot çıkıyor?** Küme sayısı (boşluk eşiğiyle):

| gömme | 2° | 5° | 10° | medyan aralık | en büyük boşluk |
|---|---|---|---|---|---|
| M (93×93) | 18 | 10 | 7 | 0,34° | 86,2° |
| S (51×51) | 17 | 9 | 6 | 1,08° | 87,1° |

→ **Temiz bir wedge sayısı YOK**; değer eşiğe bağlı olarak **6–18** arasında geziyor. Medyan aralığın
çok küçük olması (0,34°/1,08°) gömmede **çok sayıda neredeyse çakışık nokta** olduğunu, boşluğun
86–87° olması ise **tam turun kapanmadığını** gösterir.

**Halka simülasyonu için yeterli geometri var mı?** **Bu veri sürümünde, bu yöntemle: HAYIR.**
- Gömme **bulutsu/iki-loblu** (r_cv 1,15 / 1,66); **halka koordinatı tanımlı değil**.
- **Tam tur yok** (H6b.2: g_max 86–87° ≥ 60°).
- Graf **izole bir EPG hücresi** yüzünden bölünüyor; baş özvektörler grafı bölmeye eğilimli.
- **Belirsizlik yüksek:** (i) halka koordinatının varlığı; (ii) wedge sayısı (6–18 arası);
  (iii) normalizasyon seçimi (normalize Laplasyen / rastgele-yürüyüş denenmedi — ön-kayıt yoktu);
  (iv) ikili yapı + ağırlık dağıtımı seçimi; (v) sinaps düzeyinde geometri ve wedge etiketi yok.

## 6. KEŞİFSEL (ön-kayıt sonrası; ölçüm/hipotez değiştirilmedi)

- **Bağlı bileşenler (neden 2?):** M: **bileşen 0 = 92 hücre (50 EPG + 42 PEN; EPG'nin 25'i sol,
  25'i sağ)**, **bileşen 1 = 1 izole EPG hücresi (sol)**. S: aynı — 50 EPG + 1 izole. → "2 bileşen"
  **hemisfer ayrımı değil**, **tek izole hücre** artefaktıdır (bu hücrenin EPG→PEN çıkışı yok:
  50/51 EPG).
- **Null'ların bileşen yapısı:** 1000 örnekte **tamamı 2 sıfır özdeğer** (2 bileşen) —
  derece-korunmuş takas izole hücreyi korur → gözlenen–null karşılaştırması **eşleşmiş**tir.
- **Literal (indis 1,2) vs birincil:** null ortalamaları M **3,545 vs 2,848**, S **2,976 vs 2,676**;
  gözlenen değerler iki sürümde de null'un altında → **sonucun yönü seçime bağlı değil**.
- **BONUS** (§4): |r_c| ≈ 0,30 (zayıf).

## 7. ZORUNLU İFADE

> Gömmeden çıkarılan açılar **wedge etiketi DEĞİLDİR**: bu veri sürümünde EPG tip adlarında
> **sayı/wedge/glomerül etiketi yoktur** (§1; Faz 4B-0 H4b0.5 ve Faz 6-0 §6 ile aynı). Açı,
> **bağlantı matrisinden türetilmiş bir koordinattır** ve **sıfır noktası ile yönü keyfîdir**
> (Laplasyen özvektörlerinin işareti ve döndürmesi veriden gelmez). H6b.1/H6b.2 ölçütleri
> döndürmeye duyarsızdır; **mutlak açı değerleri anlam taşımaz**.

## 8. Sınırlılıklar

- **H6b.1'in literal geçişi içerik olarak destek SAĞLAMAZ:** r_cv = 1,15 halka kabuğu değil,
  bulutsu gömmedir (Faz 6-0 halka değeri 0,336). Ölçüt "null'dan daha az ekstrem"den başka bir şey
  ölçmüyor; bu raporda **halka iddiası desteklenmiş sayılmadı**.
- **Gömme yöntemi tek:** yalnızca normalize edilmemiş Laplasyen + ilk iki sıfır-dışı özvektör.
  Normalize Laplasyen, rastgele-yürüyüş normalizasyonu, UMAP/t-SNE gibi alternatifler denenmedi.
- **İzole hücre** graf yapısını ve λ=0 sayısını etkiliyor; hücre dışlanarak yapılan bir analiz
  bu fazda **yapılmadı** (ön-kayıt dışı olurdu).
- **Girdi ikili yapı + ağırlık** kullanır; **ağırlık dağıtımı** (kenar başına sinaps) null'da
  rastgele yeniden dağıtılır — alternatif ağırlık modelleri (log, normalize) denenmedi.
- **Delta7 dışarıda:** ön-kayıt yalnızca EPG↔PEN matrisini sabitledi; Delta7 devreye alınmadı.
- **p tabanı:** 1000 örnek → p ≥ 1/1001; ayrım gücü **z** ve etki büyüklüğünden okunmalı.
- **Tek connectome** (hemibrain 783); bireysel/cinsiyet varyasyonu yok.
- **İşlev/hesaplama katkısı ve evrimsel tasarım iddiası YASAK** (Faz 5 yorum kuralı);
  **dinamik simülasyon yapılmadı**.
- **Uygulama düzeltmeleri (şeffaflık):** (i) `pd.DataFrame(generator)` hatası `embedding_observed.csv`'yi
  tek sütun olarak yazmıştı → `list(...)` ile düzeltildi (istatistik hesaplanmadan ÖNCE);
  (ii) `labels()`'ta `synonyms` NaN'ları `re.search`'i kırıyordu → düzeltildi; (iii) "ilk iki
  nontrivial özvektör" ifadesi, **2 sıfır özdeğer** nedeniyle "en küçük iki **sıfır-dışı**" olarak
  uygulandı (literal sürüm de raporlandı). **Metrik/null/eşik/hipotez değiştirilmedi.**

## 9. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py labels    # Step 1
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py embed     # Step 2
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py tests     # Step 3 (1000 null, ~56 s)
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py bonus     # bonus circular correlation
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py merge     # Holm m=2 + decision numbers
.venv/Scripts/python.exe -X utf8 numcog/cx_spectral.py explore   # EXPLORE
```

Null örnekleri **deterministic seed** uses (`RandomState(8000 + sample_no)`) → **single process**
(≤1 rule); degree conservation is asserted for each sample.

Outputs (`numcog/results_p6_0b/`): `label_counts.csv`, `embedding_coords.csv`,
`embedding_observed.csv`, `embedding_eigenvalues.csv`, `null_samples.csv`,
`bonus_circular_corr.csv`, `mx_tests.csv`, `co_analysis_S.csv`, `components_M.csv`,
`components_S.csv`, `explore.csv`, `run.log`.

## 10. ÖZET

1. **Input:** EPG 51, PEN 42; type columns have no NaNs; **663 synapse lines → 582 unique pairs**,
   6.852 synapses; EPG output having 50/51. **Wedge/glomerulus label NOT PRESENT** (numbers only in PEN subtype names: `PEN_a(PEN1)`, `PEN_b(PEN2)`).
2. **Graph is disconnected:** 1 **isolated EPG cell** (left) + principal component (50 EPG [25 left + 25 right] +
   42 PEN); λ=0 **twice** (in M and S). The null's **%100** are the same structure → comparison matched.
3. **Embedding (primary):** M r_cv **1.1538**, g_max **86.2°**; S r_cv 1.6562, g_max 87.1°.
   (Literal "indis 1,2" version: M 1.7668 / 92.3°; S 2.0597 / 93.7°.)
4. **H6b.1 (literal criterion) SEPARATE:** r_cv 1.1538 vs null 2.8476 ± 0.4753 (z = −3.56,
   p_holm = 0.0020). **But this is not a ring:** r_cv ≈ 1.15 blurry/two-lobule embedding (Phase 6-0
   soma based ring where r_cv = 0.336); criterion only means "less extreme than null" →
   **ring claim is not supported.**
5. **H6b.2 DISPROVED:** g_max **86.2° ≥ 60°** and not excessive compared to null (p_ham = 0.615) →
   **no full circle**.
6. **BONUS:** |r_c| = 0.300 (M) / 0.322 (S) → weak fit with soma angle; sign arbitrary.
7. **DECISION:** **in this data version, with this method** the ring coordinate does not come from the connectivity matrix;
   wedge number is not clean (**between the threshold 6–18**); dynamic simulation **was not performed**.
8. **Mandatory expression (§7):** derived angles are **not wedge labels**; **zero point and direction** are arbitrary (eigenvector sign/rotation does not come from the data).

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
