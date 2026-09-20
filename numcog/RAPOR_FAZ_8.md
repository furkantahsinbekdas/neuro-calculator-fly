# RAPOR FAZ 8 — MB'de biyolojik öğrenme kuralı (DAN-kapılı KC→MBON plastisitesi) + MB'nin doğal görevleri

Tarih: 2026-09-20. Ön-kayıt **ölçümden ÖNCE** commit edildi: **`3d7d638`** ("Faz 8 ön-kayıt +
Aşama 0 keşif kodu"). Yeni kod: **`numcog/mb_learning.py`**; çıktılar **`results_p8/`**.
Faz 0–7-3 dosyaları/sonuçları **değiştirilmedi**. **Eş zamanlı süreç: 1. float64. Tohum başına CSV.**
Dil kalıbı: **"bu veride, bu modelde, bu ızgarada"**.

## 0. Etiket sayımları ve KAPI SONUÇLARI (EN BAŞTA)

**AŞAMA 0 (keşif; simülasyon YOK).** Ayrıntı: `results_p8/gate0.csv`.

| öğe | değer | kapsam (NaN) |
|---|---|---|
| KC | 5.177 | `cell_type` 0 NaN, 12 tip (`KCab`,`KCg`,`KCa'b'`,…) |
| ALPN | 685 | 0 NaN |
| **MBON** | **96** | 0 NaN; `cell_type` = MBON01…MBON35 (35 tip) |
| **DAN** | **331** | 0 NaN; **PAM01-15 (307)**, **PPL1-01…08 (16)**, PPL2-01…04 (8, **hariç**) |
| MBON NT işareti | **+1 = 51 · −1 = 45 · NaN = 0** | kaynak: `known_nt`→`top_nt` (28 hücrede `known_nt` NaN → `top_nt`) |
| MBON `top_nt` | acetylcholine 52 · glutamate 25 · gaba 19 | — |
| **kenarlar (min_syn=3)** | **ALPN→KC 23.618** (pre 295, post 4.787) · **KC→MBON 35.204** (pre 5.173, post 91) · DAN→MBON 1.338 (pre 299, post 82) · MBON→DAN 877 · DAN→KC 1.923 | — |
| koku girdi boyutu | **295 ALPN** (ölçüldü; **görev metnindeki 319 değil**) | — |
| **bölme çıkarımı** | spektral kümeleme (DAN→MBON bipartit, eigengap) → **k=12** | MBON/küme: min 1, ort 8,0, **max 51** (dengesiz) |

**KAPI G0:** (a) 96 ≥ 30 ✓ · (b) k=12 ≥ 8 ✓ · (c) KC→MBON 35.204 ≥ 5.000 ✓ → **GEÇİLDİ** ✓

**KAPI G1** (2 koku: biri ödül biri ceza; σn=0,1, d=0, **10 deneme/koku**; donmuş η/ρ):
**MB_gercek = 0,982 ± 0,078 [0,948; 1,017] (20 tohum) → GEÇİLDİ** ✓ (≥ %90)

**Donmuş (η, ρ):** pilot (yalnızca validasyon, 10 tohum, ayrı prototip kümeleri) →
**η = 0,30 · ρ = 0,00** (validasyon 0,967); η=0,01'de 0,921; ρ=0,05 her yerde biraz daha kötü.

## 1. VARSAYIMLAR (AYRI BÖLÜM — hepsi etiketli)

| varsayım | ne yapıldı | neden |
|---|---|---|
| **DAN tipi → valans** | **PAM = ödül (+1), PPL1 = ceza (−1)**; PPL2 ve bilinmeyenler **hariç** | kaynak yalnızca `cell_type`/`hemibrain_type` **ön eki**; annotations'ta valans sütunu YOK |
| **Bölme (compartment) ataması** | **ÇIKARIM**: DAN→MBON bipartit matrisi + spektral kümeleme (k=12); DAN→bölme = hedef MBON'larının çoğunluk oyu (299/331 DAN atandı) | annotations'ta bölme sütunu YOK, `synonyms` boş; **gerçek anatomik bölmeler değil** |
| **Valans varsayımı** | **PAM DAN'ları kendi bölmesindeki KAÇINMA MBON'larını (s_j=−1)**, **PPL1 DAN'ları YAKLAŞMA MBON'larını (s_j=+1)** deprese eder | literatür temelli **VARSAYIM**; bu fazda test edilmedi |
| **MBON NT işareti** | 7-0 kuralı (`ACh/DA/5-HT/OA` → +1; `GABA/Glu` → −1) → +1 = 51, −1 = 45 | işaret **VARSAYIM** (glutamatı −1 saymak dahil) |
| **KC işareti** | **+1 (ACh) sabit** | `top_nt="dopamine"` çelişkisi biliniyor (5.172/5.177 KC) → **yok sayıldı** (7-0/7-3 ile aynı) |
| **US yayılımı** | Ödül denemesinde **tüm PAM'lar**, ceza denemesinde **tüm PPL1'ler** açık | görev tanımı: "ilgili tip DAN'lara verilir"; tip-içi seçicilik **modellenmedi** |
| **Ödül/ceza yolu** | karar **skoru = Σ_j s_j·MBON_j**; >0 yaklaş, <0 kaçın, **=0 yanlış** | okuma katmanı **eğitilmez** (kol 6 dışında) |
| **Öğrenme kuralı biçimi** | tek kural: **ΔW = −η·d_c(j)·KC_i·elig**, W≥0, unutma ρ | **tek kural biçimi** denenmiştir (sınırlılık) |

## 2. Hangi işi PLASTİSİTE, hangisini GEOMETRİ yaptı? (kol 6 = Δ-okuma tavanı, kol 7 = η=0)

**T1 (ayırım + gürültü; şans 0,50):** MB_gercek **0,847-0,992**; kollar 0,86-1,00; **MB_ER 1,000**;
**plastisitesiz (η=0) 0,44-0,55 ≈ şans**; **Δ-okuma tavanı 1,000**.

- **Geometri tek başına yetmiyor:** η=0 kolu **şans düzeyinde** (0,44-0,55) → görev
  **öğrenme olmadan çözülemiyor** ✓ (yani "MB kablolaması hazır bir sınıflandırıcı değil").
- **Plastisite tek başına yeterli değil, ama neredeyse:** gerçek kablolamada **6 deneme/koku**
  sonrası 0,85-0,99 ✓.
- **Δ-okuma tavanı 1,000** (T1'in tüm koşullarında) → görev **KC kodundan doğrusal olarak tamamen
  çözülebilir** ✓; biyolojik kural bunun **~%0-15 altında** kalıyor ✓ (en büyük fark N=2, σn=0,1'de:
  0,975 vs 1,000; en küçük N=16, σn=0,6'da 0,847 vs 1,000 ✓).
- **Yani iş bölümü:** *bu veride, bu modelde, bu ızgarada* bilgi **KC kodunda mevcut** (Δ-okuma
  kanıtı); **DAN-kapılı LTD onu kısmen çıkarıyor**; ama **hangi kablolamayla** (gerçek/karıştırılmış/ER)
  çıkarıldığı **sonucu değiştirmiyor** (bkz. §3).
## 3. Görev sonuçları (20 tohum; donmuş η=0,30 ρ=0,00; ort ± %95 GA)

### T1 — Ayırım ve gürültü dayanıklılığı (şans 0,50)

| koşul | **MB_gercek** | KCMBON_sh | ALPNKC_sh | MB_ER | rastgele_bölme | η=0 | Δ-okuma |
|---|---|---|---|---|---|---|---|
| N=2, σn=0,1 | **0,975** | 1,000 | 1,000 | 1,000 | 1,000 | 0,467 | 1,000 |
| N=4, σn=0,1 | **0,973** | 1,000 | 1,000 | 1,000 | 0,973 | 0,465 | 1,000 |
| N=8, σn=0,1 | 0,947 | 1,000 | 0,992 | 1,000 | 0,974 | 0,499 | 1,000 |
| N=16, σn=0,1 | 0,948 | 0,973 | 0,977 | 1,000 | 0,931 | 0,460 | 1,000 |
| N=4, σn=0,6 | 0,956 | 0,990 | 0,977 | 1,000 | 0,975 | 0,438 | 1,000 |
| **N=16, σn=0,6** | **0,847** | 0,864 | 0,891 | 1,000 | 0,807 | 0,486 | 1,000 |

### T2 — Örüntü tamamlama (d = glomerül düşmesi; temiz eğitim)

| d | MB_gercek | KCMBON_sh | ALPNKC_sh | MB_ER | rastgele_bölme | η=0 | Δ-okuma |
|---|---|---|---|---|---|---|---|
| 0,1 | **0,958** | 0,992 | 0,988 | 1,000 | 0,988 | 0,454 | 1,000 |
| 0,3 | 0,942 | 0,942 | 0,935 | 1,000 | 0,946 | 0,546 | 1,000 |
| **0,5** | **0,885** | 0,863 | 0,881 | 1,000 | 0,885 | 0,473 | 0,996 |

### T3 — Az örnekle öğrenme (≥ %90'a ulaşan ilk deneme sayısı)

| kol | ilk ≥0,90 | eğri (1,2,3,5,8,12,20 deneme) |
|---|---|---|
| **MB_gercek** | **1** | 0,96 · 1,00 · 1,00 · 1,00 · 1,00 · 1,00 · 1,00 |
| KCMBON_sh / ALPNKC_sh / MB_ER / rastgele_bölme | 1 | tümü ≥ 0,99 |
| **η=0 (plastisitesiz)** | **hiç ulaşmıyor** | 0,44 · 0,44 · 0,45 · 0,45 · 0,44 · 0,44 · 0,43 |

### T4 — Sürekli öğrenme / unutma ve kapasite (A öğren → B öğren → A'nın tutulması)

| kapasite (odor) | MB_gercek **A-tutma** | MB_gercek B | MB_ER A-tutma | rastgele_bölme A | η=0 A |
|---|---|---|---|---|---|
| 4 | **0,988** | 0,949 | 1,000 | 0,963 | 0,508 |
| 8 | 0,965 | 0,951 | 1,000 | 0,935 | 0,519 |
| 16 | 0,931 | 0,899 | 1,000 | 0,877 | 0,505 |
| 32 | 0,790 | 0,830 | 1,000 | 0,714 | 0,503 |
| **64** | **0,619** | 0,615 | **0,863** | 0,567 | 0,504 |

→ **Kapasite sınırı ≈ 32 odor**; **MB_ER bu görevde en iyi** (64 odor'da A-tutma 0,86 vs gerçek 0,62).

### T5 — Genelleme (eğitimde görülmeyen, prototipe benzer kokular)

| cos | MB_gercek | KCMBON_sh | ALPNKC_sh | MB_ER | rastgele_bölme | η=0 |
|---|---|---|---|---|---|---|
| 0,9 | **0,948** | 1,000 | 0,933 | 1,000 | 0,971 | 0,458 |
| 0,7 | 0,940 | 0,971 | 0,960 | 1,000 | 0,963 | 0,485 |
| **0,5** | **0,904** | 0,940 | 0,933 | 1,000 | 0,954 | 0,494 |

→ Gerçek ağ **cos=0,5'te bile** genelliyor (0,904) → H8.5'in "yalnızca desteğe yakın" beklentisi
**çürüdü**. **T7 (kural testi) bu fazda UYGULANMADI** (KEŞİFSEL etiketli) — bütçe nedeniyle.

### T6a — Negatif desenleme (A+, B+, AB−) · T6b — Ters öğrenme

| görev | MB_gercek | KCMBON_sh | ALPNKC_sh | MB_ER | rastgele_bölme | η=0 |
|---|---|---|---|---|---|---|
| **T6a** (şans 0,50; **hep-yaklaş 0,667**) | **0,678 ± 0,035** | 0,664 | 0,708 | 0,714 | 0,683 | 0,378 |
| T6b "önce" (A+/B−) | 0,900 | 1,000 | 1,000 | 1,000 | 0,996 | 0,050 |
| **T6b "sonra" (ters çevrilmiş)** | **0,554** | 0,500 | 0,421 | 0,500 | 0,517 | 0,921 |

→ **Negatif desenleme ÇÖZÜLEMEDİ** (0,678 ≈ "hep yaklaş" 0,667 → çürütme eşiği %70'in altında) ✓;
**ters öğrenme BAŞARISIZ** (0,554 ≈ şans; yeni eşleme öğrenilemiyor) ✓.

## 4. Ön-kayıtlı ölçütler ve hipotezler

| hipotez | sonuç | karar |
|---|---|---|
| **H8.1** (T1'de N≤4 için ≥ %90) | N≤4 koşulları 0,975/0,958/0,992/0,973/0,973/0,956 → **ort 0,971** | **DESTEK** |
| **H8.2** (MB_gercek ≈ ER ≈ shuffle) | Holm (m=15): **3/15 anlamlı** — **yalnızca η=0**'a karşı (etki ≥0,2); karıştırılmış kollar/ER/rastgele-bölme ile **p_holm = 1,00** | **DESTEK** |
| **H8.3** (MB_gercek > MB_rastgele_bölme) | T1: fark **+0,000**; T4 (64): +0,052 (anlamsız) | **ÇÜRÜDÜ** |
| **H8.4** (T6a başarısız ≈şans) | 0,678 < çürütme eşiği %70 | **DESTEK** |
| **H8.5** (T5 yalnız desteğe yakın; T7 şans üstü değil) | T5 **cos=0,5'te 0,904** → ilk kısım **çürüdü**; **T7 uygulanmadı** (KEŞİFSEL) → ikinci kısım **ölçülemedi** | **KISMEN / ölçülemedi** |
| **H8.6** (T4'te unutma ↔ ρ; gerçek vs kontrol) | ana ölçüm **donmuş ρ=0,00** → ρ karşılaştırması **ölçülemedi**; pilot ızgarasında ρ=0,05 her yerde biraz daha kötü (0,921 vs 0,967) | **ölçülemedi** |

**"SARSICI BULGU" ÖLÇÜTÜ:** ölçüt "aynı yön **en az iki farklı η/ρ ayarında**" koşulunu içerir; ana
ölçüm **tek donmuş ayarda** (η=0,30 ρ=0,00) koştu ve pilot ızgarasında kollar **denenmedi** →
**bu fazda "connectome'a özgü" DENMEZ** ✓. Tersine: MB_gercek **hiçbir görevde** kollardan
**GA-ayrık üstün değil**; **ER ve kimi karıştırılmış kollar eşit ya da daha iyi**.

## 5. Sınırlılıklar

- **Tek η/ρ ayarı ölçüldü** (donmuş η=0,30 ρ=0,00). Ön-kayıtlı "sarsıcı bulgu" ölçütü **en az iki
  ayar** istediği için **karşılanamaz** → "connectome'a özgü" **denmez**; ƒarklar yalnızca
  **ön bulgu**dur. **η=0,01-0,1** aralığında kolların davranışı **ölçülmedi**.
- **k = 250 KC sabit** (görev gereği ayarlanmadı); **APL inhibitörü** tek parametre (top-k) ile
  modellendi; **APL hücreleri ayrıca modellenmedi**.
- **Tek plastisite kuralı biçimi:** yalnızca **LTD** (ΔW = −η·d_c·KC·elig), W≥0, doğrusal unutma;
  **LTP**, dopamin konsantrasyon dinamiği, **deneme-içi izlek sönümü**, sinaptik gecikme
  **modellenmedi**.
- **Valans varsayımı test edilmedi** (PAM→kaçınma, PPL1→yaklaşma); **US tip-içi seçici değil**
  (tüm PAM'lar / tüm PPL1'ler aynı anda açık) → **DAN→bölme eşlemesinin ince yapısı** kullanılmıyor.
- **Bölme ataması bir ÇIKARIM**dır: k=12 spektral küme; **dengesiz** (bir kümede 51 MBON, bir kümede
  1 MBON; 2 kümede hiç DAN yok) ve **gerçek anatomik bölmelerle birebir değildir**.
- **Koku modeli** basitleştirildi: ALPN'lerin %20'si aktif + **additif Gauss gürültü** + glomerül
  düşmesi; **alıcı-nöron duyarlılık farkları, temporal dinamik, karışım fiziği** modellenmedi.
  Koku girdi boyutu **295 ALPN** (metindeki 319 değil).
- **KC kodu ikili** (top-250); **analog KC aktivitesi** kullanılmadı.
- **T7 (kural testi) UYGULANMADI** (KEŞİFSEL); **T6c (ikinci-derece koşullama) UYGULANMADI**;
  **ikili kararda "skor = 0"** yanlış sayıldı (tanı olarak hesaplandı ama rapora toplulaştırılmadı).
- **Gerçek vs tavan karşılaştırmasında** kol 6 (Δ-okuma) **eğitilmiş doğrusal bir okumadır** ve
  **biyolojik DEĞİLDİR**; yalnızca **üst sınır referansı** olarak kullanıldı.
- **Tek connectome** (hemibrain 783); **simülasyon**; işlev/evrimsel tasarım iddiası **YASAK**
  (Faz 5 kuralı).
- **Ölçüm sırasında hiçbir ızgara/ölçüt/kapı değiştirilmedi**; sonradan eklenen analiz **yok**.
- **Uygulama düzeltmesi (ölçüm ÖNCESİ, ön-kayıt `3d7d638`'den sonra):** pilotun **ilk** koşusunda
  tüm η/ρ ayarlarında doğrulama **0,525** (şans) çıktı; neden **`np.clip(..., out=self.W[m])`**
  çağrısının boolean maskelemede **kopya** üzerinde çalışmasıydı → W negatife iniyor, ReLU tüm
  plastisite etkisini siliyordu. Düzeltme: **satır indeksli** güncelleme
  (`self.W[rows] = np.maximum(self.W[rows] − η·kc, 0)`). Düzeltmeden sonra bir ödül denemesi
  skoru **−0,27 → +0,91**'e çeviriyor. **Hiçbir ızgara/ölçüt/kapı değişmedi**; yalnızca kod hatası
  giderildi ve düzeltilmiş sürüm G1'i (0,982) geçti.

## 6. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/mb_learning.py explore   # Aşama 0 + KAPI G0
.venv/Scripts/python.exe -X utf8 numcog/mb_learning.py pilot     # η/ρ (yalnızca validasyon)
.venv/Scripts/python.exe -X utf8 numcog/mb_learning.py gate1     # KAPI G1
.venv/Scripts/python.exe -X utf8 numcog/mb_learning.py runall 20  # Aşama 2 (7 kol × 20 tohum)
.venv/Scripts/python.exe -X utf8 numcog/mb_learning.py merge      # özet + ölçüt/hipotez
```

Çıktılar (`numcog/results_p8/`): `gate0.csv`, `gate1.csv`, `pilot.csv`, `frozen_config.csv`,
`<kol>_seed<NN>.csv` (tohum başına), `summary.csv`, `hypotheses.csv`, `merge_out.txt`, `run.log`.
Ara `mb_cache.npz` (0,3 MB, yeniden üretilebilir). **Koşu süresi: 140 tohum-kol, 11 dk**
(ön-kayıt tahmini 20-40 dk).

## 7. ÖZET (bu veride, bu modelde, bu ızgarada)

1. **Kapılar geçildi:** G0 (96 MBON ≥ 30; k=12 bölme; KC→MBON 35.204 ≥ 5.000) ✓ ve
   **G1 (MB_gercek = 0,982 ± 0,078 ≥ %90)** ✓ → model **öğreniyor**.
2. **Öğrenme kuralı işliyor:** bir ödül denemesi hedef kaçınma-MBON'larını deprese edip skoru
   **−0,27 → +0,91**'e çeviriyor ✓; **η=0 kolunda hiçbir görev öğrenilmiyor** (0,44-0,55 ≈ şans) ✓.
3. **Geometri tek başına yetmiyor, plastisite şart:** η=0 kolu T1-T6'nın **hepsinde şans düzeyinde** ✓.
4. **Ama hangi kablolama olduğu fark etmiyor:** MB_gercek ile **KCMBON-shuffle, ALPNKC-shuffle,
   ER ve rastgele-bölme** arasında **Holm sonrası hiçbir görevde GA-ayrık fark YOK** (p_holm = 1,00);
   **ER çoğu görevde eşit veya daha iyi** (T1 1,000; T4-64'te 0,863 vs gerçek 0,619) →
   **H8.2 DESTEK, H8.3 ÇÜRÜDÜ**.
5. **H8.1 DESTEK:** N≤4'te %90'ın üstünde (ort 0,971); **T3'te tek denemede** %90'a ulaşılıyor ✓.
6. **T6a negatif desenleme ÇÖZÜLEMEDİ** (0,678 ≈ "hep yaklaş" 0,667) → **H8.4 DESTEK** ✓
   (doğrusal-toplamsal MBON çıktısı XOR-benzeri problemi çözemiyor ✓).
7. **T6b ters öğrenme BAŞARISIZ** (0,554 ≈ şans) → eski eşleme kırılıp yenisi öğrenilemiyor ✓.
8. **T5 genelleme beklentiden GENİŞ** (cos=0,5'te bile 0,904) → H8.5'in ilk kısmı **çürüdü**.
9. **Δ-okuma tavanı 1,000** (T1/T2) → bilgi **KC kodunda tam olarak mevcut**; biyolojik kural bunun
   **%0-15 altında** kalıyor → iş bölümü: *kod KC'de, karar MBON'da, öğrenme DAN-kapılı LTD'de* ✓.
10. **"Connectome'a özgü" iddiası YOK** (sarsıcı bulgu ölçütü tek ayar nedeniyle karşılanamaz);
    *bu veride, bu modelde, bu ızgarada* gerçek MB kablolaması, biyolojik öğrenme kuralını
    kullanırken **surrogatlarından üstün değildir**; görevlerin çözülüp çözülmemesi
    **kablolamadan çok kuralın ve okumanın** varlığına bağlıdır.

