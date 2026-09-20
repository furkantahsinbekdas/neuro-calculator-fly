# RAPOR FAZ 7-1 — Connectome rezervuarında durum taşıma (asıl deney)

Tarih: 2026-09-20. Durum: koşu sürüyor / tamamlanacak. Ön-kayıt **ölçümden ÖNCE** commit edildi:
`36e52df` (Faz 7-1 ek ön-kayıt) + `5f816d2` (ölçülmüş bütçe) + `80fda08` (kollara göre tohum sayısı).
Faz 0–7-0 dosyaları/sonuçları DEĞİŞTİRİLMEDİ. Yeni kod: **`numcog/reservoir_run.py`**.
**Eşzamanlı süreç: 1. float64. Tohum başına ayrı CSV.** Dil kalıbı:
**"bu veride, bu modelde, bu ızgarada"**.

## 0. Parametreler ve etiketler (EN BAŞTA)

| öğe | değer | kaynak |
|---|---|---|
| alt ağ (birincil) | **A = CX çekirdek (EB/PB/FB/NO)** — N=4.236, E=**298.441** | 7-0 seçim kuralı |
| alt ağ (KEŞİFSEL) | **B = MB** (KC/MBON/DAN/APL/DPM) — N=5.608, E=523.784 | 7-0 (SCC sınırı bilinerek aşıldı) |
| model | `x_{t+1}=(1−a)x_t + a·tanh(g·W·x_t + B·u_t)`, **a=0,5** | 7-0 (kilitli) |
| W | işaretli (NT **VARSAYIM**), **Dale** (işaret pre-nöron başına), **ρ(W)=1'e normalize** | 7-0 |
| işaret kuralı | ACh/DA/5-HT/OA **+**; GABA/Glu **−**; `negative`/diğer → **imzasız** (kenar hariç) | 7-0 |
| giriş | 2 kanal (+1/−1), **tohumla rastgele k=50 nöron/kanal**, darbe 1 adım, aralık 5 adım | 7-1 |
| **donmuş (g, amp)** | **g = 1,30, amp = 0,5** (yalnızca validasyonda seçildi; TEST kullanılmadı) | pilot (10 tohum) |
| okuma | **dual (kernel) ridge**; λ ∈ {1e-6…1}×ort(diag K) yalnızca validasyonda; gürültü sd=1e-3×std | 7-1 |
| dizi bölmesi | **eğitim 300 / validasyon 120 / test 120** + 180 T3-ekstrapolasyon (dizi çakışması yok, assert) | 7-1 (bütçe) |
| T1 | k ∈ {2,4,6,8,10}, H ∈ {0,10,20,40}; okuma bekleme sonunda | 7-1 |
| T2 | Jaeger MC, gecikme 1..60, tek akış (2000 adım) | 7-1 |
| T3 | eğitim |s|≤6; test s ∈ {7,8,9,10} (her biri 50 dizi) + görülmemiş başlangıç durumu | 7-1 |
| T4 | iki başlangıçtan yakınsama, g ∈ {0,5;0,8;0,95;1,1;1,3} | 7-1 |
| tohum sayısı | A_gercek, A_w0: **30**; kontrol kolları: **15**; MB kolları: **10** | 7-1 (bütçe) |
| T2/T4 kapsamı | yalnızca **A_gercek, A_w0, B_gercek** | 7-1 (bütçe) |

**Kollar (9):** 1 A_gercek · 2 A_derece · 3 A_agirlik · 4 A_er · 5 A_w0 · 6 **ideal sayaç (DIŞ YARDIM,
üst sınır — simülasyon değil)** · 7 A_isaretperm · 8 A_dengeli · 9 KEŞİFSEL: B_gercek, B_derece,
B_dengeli. **Merkezleme varyantı ikincildir** (bu raporda birincil = merkezlemesiz).

## 1. Yöntem

- **Kolların kurulumu (`build`):** A ve B alt ağları 7-0 önbelleğinden; W'ler işaretli+Dale;
  derece-shuffle (çift-kenar takası, derece korunumlu), ağırlık-shuffle (topoloji sabit),
  Erdős–Rényi (aynı N ve yoğunluk), işaret-permutasyon (aynı +/− oranı), dengeli-işaret (%50 −).
  Her kol **ρ=1'e normalize** edildi (`meta`: `arms_meta.csv`).
- **Simülasyon:** seyrek CSR × **yoğun durum matrisi** (toplu, B=64 sütun); float64;
  aynı k içinde 4 H okuması tek yörüngeyi paylaşır; her k için ayrı yörünge (sonraki darbeler
  bekleme penceresini bozacağından).
- **Okuma:** dual ridge (kernel) — n < N olduğu için; λ validasyonda; gözlem gürültüsü 1e-3.
- **Ölçüm sırası:** pilot (validasyon) → **donmuş (g=1,30; amp=0,5)** → kollar × tohumlar → `merge`.



## 2. Sonuçlar — T1 (durum taşıma)

**Koşu:** 165 tohum-kol, **174 dk** (bütçe tahmini 3,3 saatti ✓). `summary_T1.csv` (k=10 satırları):

| kol | tohum | H=0 | H=10 | H=20 | H=40 |
|---|---|---|---|---|---|
| **A_gercek** | 30 | **0,249±0,015** | **0,252±0,013** | **0,257±0,016** | **0,246±0,013** |
| A_w0 (tekrarlama yok) | 30 | 0,230±0,013 | 0,227±0,014 | 0,233±0,013 | 0,240±0,013 |
| A_derece | 15 | 0,382±0,025 | 0,408±0,027 | 0,409±0,029 | 0,407±0,033 |
| A_agirlik | 15 | 0,437±0,026 | 0,392±0,034 | 0,355±0,035 | 0,313±0,023 |
| A_er | 15 | 0,337±0,023 | 0,263±0,016 | 0,229±0,015 | 0,223±0,020 |
| A_isaretperm | 15 | 0,464±0,045 | 0,449±0,050 | 0,439±0,058 | 0,359±0,056 |
| A_dengeli | 15 | 0,343±0,023 | 0,337±0,021 | 0,322±0,028 | 0,299±0,025 |
| B_gercek (KEŞİFSEL) | 10 | 0,240±0,025 | 0,222±0,026 | 0,237±0,023 | 0,229±0,025 |
| B_derece (KEŞİFSEL) | 10 | 0,309±0,038 | 0,280±0,033 | 0,266±0,046 | 0,242±0,022 |
| B_dengeli (KEŞİFSEL) | 10 | 0,235±0,030 | 0,248±0,025 | 0,237±0,020 | 0,223±0,019 |

Şans düzeyi k=10 için **ulaşılabilir sınıf sayısı 9** (cap=8 nedeniyle çift toplamlar) → **şans ≈ 0,111**.

**A_gercek doğruluk profili** (H=0): k=2 → **1,000**; k=4 → 0,764; k=6 → 0,433; k=8 → 0,321;
**k=10 → 0,249** (H=10/20/40 benzer; H=40'ta k=2 hâlâ 0,999).

### Başarı ölçütleri (7-0'ı sıkılaştıran)

| ölçüt | sonuç | karar |
|---|---|---|
| **"Ağ durumu taşıyor"** (k=10, H=10: ≥0,90 VE W=0'dan GA ayrık) | 0,252±0,013 vs 0,227±0,014 | **GEÇMEDİ** (<0,90; GA'lar ayrık değil) |
| aynı ölçüt H=0 / H=20 / H=40 | 0,249 / 0,257 / 0,246 | **GEÇMEDİ** |
| **"Connectome'a özgü"** (kol 2/3/4'ten GA ayrık üstünlük) | gerçek **daha düşük** (§2 hipotezler) | **GEÇMEDİ — ters yönde** |
| **"Kural/ekstrapolasyon"** (T3 şans üstü, ≥200 öğe) | kesin 0,177 (şans 0,25) | **GEÇMEDİ** |
| **Bellek uzunluğu** (ilk <%90) | **(k=4, H=0)** | — |

### Hipotezler (eşleşmiş t-testi, k=10/H=10; Holm m=6)

| karşılaştırma | fark (A_gercek − kol) | p_ham | p_holm | sonuç |
|---|---|---|---|---|
| vs **A_derece** | **−0,172** | 0,0000 | 0,0000 | **AYRIŞIR (shuffle DAHA İYİ)** |
| vs **A_isaretperm** | **−0,213** | 0,0000 | 0,0000 | **AYRIŞIR (daha iyi)** |
| vs **A_agirlik** | **−0,156** | 0,0000 | 0,0000 | **AYRIŞIR (daha iyi)** |
| vs **A_dengeli** | **−0,101** | 0,0000 | 0,0000 | **AYRIŞIR (daha iyi)** |
| vs **A_er** | **−0,027** | 0,0120 | 0,0120 | **AYRIŞIR (daha iyi)** |
| vs **A_w0** | **+0,025** | 0,0017 | 0,0034 | AYRIŞIR (gerçek hafifçe iyi) |

- **H7.1 (kol1 > kol5):** H=0'da +0,019, k=10/H=10'da **+0,025 (p_holm = 0,0034)** → **yön doğru ama
  etki çok küçük** (0,252 vs 0,227; **%90 ölçütünün çok altında**).
- **H7.2 (kol1 ≈ kol2-4):** **ÇÜRÜDÜ — ters yönde.** Gerçek alt ağ, **dört kontrolün dördünden de
  anlamlı biçimde DAHA KÖTÜ** (−0,03 ile −0,21; tümü p_holm < 0,05). Yani **bu veride, bu modelde,
  bu ızgarada connectome'a özgü üstünlük YOK**; tersine gerçek W, surrogatlarından daha az
  kullanılabilir durum dinamiği üretiyor.
- **H7.3 (T3 çöker):** **DESTEK.** Kesin 0,177 / ±1 0,256 (şans 0,25) → şans düzeyi ya da altı;
  görülmemiş başlangıç durumunda 0,015. **Doygunluk YOK** (0,0000) → çöküş 7-0'da öne sürülen
  "tanh doygunluğu" ile değil, **okumanın ekstrapole edememesiyle** açıklanır.
- **H7.4:** **k yönünde DESTEK** (dört H değerinde de monoton: 1,000 → 0,76 → 0,43 → 0,32 → 0,25);
  **H yönünde ÇÜRÜDÜ** (k=4,6,8,10'da monoton değil; ör. k=4: 0,764 → 0,780 → 0,765 → 0,625).
- **H7.5 (yön yok, kol 1 vs 7/8):** her ikisinde de **surrogatlar daha iyi** → **işaret VARSAYIMI**
  bu sonucun ana nedeni **değildir**.
- **H7.6 (yön yok, A vs B_MB):** 0,252 vs 0,222, **p = 0,068** → **ayrışamaz** (n_B=10; güç sınırlı).


## 3. Ağın yaptığı iş vs okumanın yaptığı iş (kol 5 vs kol 6)

- **İdeal sayaç (kol 6, DIŞ YARDIM):** durum doğrudan toplam olduğunda doğruluk **tanım gereği
  1,000**dir — yani hesap **kontrolcüde tam olarak yapılabilir**; ağın işi onu **taşımaktı**.
- **Kol 5 (W=0, yalnızca sızıntılı giriş):** k=10'da **0,23** → okuma, **tekrarlama olmadan**,
  yalnızca girdinin üstel izinden ~%23 çıkarabiliyor (k=2'de ~1,000).
- **Kol 1 (gerçek ağ):** k=10'da **0,25** → tekrarlamanın katkısı **~+0,02** (istatistiksel olarak
  ayrışıyor, ama küçük).
- **T2 (Jaeger MC):** gerçek ağ **10,85 ± 0,21**, W=0 **0,39 ± 0,02**, MB **7,11 ± 0,57** →
  **tekrarlama bellek kapasitesi EKLİYOR** (MC'de açık), ama bu kapasite **T1'in nominal okumasında
  kullanılamıyor**.
- **T4 (yankı-durum):** iki farklı başlangıçtan yörüngeler **yakınsıyor** (d_end = 0,0000; üç kolda da)
  → sistem **yankı-durum özelliğini sağlıyor** (kararlı, sönümlü dinamik).

## 4. Rejim tanısı ve "neden gerçek ağ daha kötü?"

| kol | doygunluk | ortalama aktivite | aktif nöron oranı | katılım oranı |
|---|---|---|---|---|
| **A_gercek** | 0,0000 | **0,0033** | **0,024** | 1,0 |
| A_w0 | 0,0000 | 0,0028 | 0,024 | 1,0 |
| A_derece | 0,0029 | **0,1644** | **0,651** | 1,8 |
| A_agirlik | 0,0000 | 0,0228 | 0,080 | 1,1 |
| A_isaretperm | 0,0002 | 0,0410 | 0,127 | 1,0 |
| A_er | 0,0379 | 0,4997 | 0,931 | 1,1 |
| B_gercek | 0,0000 | 0,0026 | 0,018 | 1,0 |

**Gerçek alt ağ "neredeyse ölü" bir rejimde** (aktivite 0,0033; nöronların yalnızca **%2,4'ü aktif**);
surrogatları ise **çok daha canlı** (A_derece %65, A_er %93 aktif) ve T1'de **daha iyi**.
Ölçülen neden **spektral normalleştirmedir**: ham spektral yarıçaplar **A_gercek 635**,
A_derece 116, A_agirlik 278, A_isaretperm 424, A_er 126, B_gercek 1.432. ρ=1'e normalleştirildiğinde
**ρ_raw'ı büyük olan matrisin tipik ağırlıkları küçülür** → tekrarlama sürücüsü zayıflar. Yani
gerçek connectome'un ağırlık dağılımı **birkaç güçlü mod tarafından domine ediliyor**; aynı ağırlık
çokluğunun karıştırılmış sürümleri bu modları kırıp **daha dengeli (ve bu görev için daha kullanışlı)
bir dinamik** üretiyor.

**Bu bir "connectome kötü" iddiası DEĞİLDİR:** bu, **tek bir normalleştirme seçiminin** (ρ=1,
ön-kayıtlı) sonucudur; başka bir normalleştirme (ör. ortalama ağırlık ya da farklı bir g ızgarası)
sıralamayı değiştirebilir ve bu fazda **denenmedi** (TASARIM DEĞİŞİKLİĞİ olurdu).

## 5. Sınırlılıklar

- **Tek connectome** (hemibrain 783); bireysel/cinsiyet varyasyonu yok.
- **NT işaretleri VARSAYIMDIR** (7 sınıf → ±1; histamin vb. işaretsiz). KC'lerde `top_nt`="dopamine"
  anomalisi (7-0 §0) etiket güvenilirliğini sınırlar.
- **Giriş nöron seçimi keyfîdir** (tohumla rastgele k=50/kanal); sonuçlar bu seçime bağlıdır ve
  **tohumlar arası dağılım** olarak raporlanır.
- **Model kilitli**: tek mimari (sızıntılı hız modeli, a=0,5, ρ=1 normalizasyon, tanh); başka
  normalizasyon/zaman sabiti/nöron modeli denenmedi (TASARIM DEĞİŞİKLİĞİ olurdu).
- **Izgara sınırlı**: g ∈ {0,5…1,3}, amp ∈ {0,5;1,0}; daha büyük g/amp **denenmedi** (pilot
  ızgaranın üst ucunu seçti → "ızgaranın dışında daha iyi olabilir" olasılığı **kapatılamadı**).
- **Veri bölmesi teknik bütçe nedeniyle küçültüldü** (300/120/120; gerekçe §0 ve ön-kayıt);
  bu okuma gücünü sınırlar ve **mutlak** doğrulukları etkiler (kollar arası karşılaştırma yine
  aynı bütçeyle yapılır ✓).
- **Tohum sayıları kollara göre farklı** (30/15/10) → kontrol kollarının GA'ları daha geniş;
  bu raporda her yerde belirtilir.
- **T2/T4 yalnızca 3 kol için** ölçüldü; diğer kollarda "ölçülmedi".
- **Spektral yarıçap** güç iterasyonuyla (float64) tahmin edildi; işaretli asimetrik matriste
  baskın özdeğer karmaşık olabilir (7-0 §5 notu geçerli).
- **Simülasyon**; canlı sinek değil. **İşlev/hesaplama katkısı ve evrimsel tasarım iddiası YASAK**
  (Faz 5 yorum kuralı).
- **Ölçüm sırasında hiçbir ölçüt/ızgara/bölme değiştirilmedi**; sonradan eklenen analizler
  **KEŞİFSEL** etiketlidir.

## 6. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/reservoir_run.py build
.venv/Scripts/python.exe -X utf8 numcog/reservoir_run.py pilot
.venv/Scripts/python.exe -X utf8 numcog/reservoir_run.py runall 30 A_gercek A_w0 \
    A_derece:15 A_agirlik:15 A_er:15 A_isaretperm:15 A_dengeli:15 \
    B_gercek:10 B_derece:10 B_dengeli:10
.venv/Scripts/python.exe -X utf8 numcog/reservoir_run.py merge
```

Çıktılar (`numcog/results_p7_1/`): `arms_meta.csv`, `pilot.csv`, `frozen_config.csv`,
`<kol>_seed<NN>.csv` (tohum başına), `summary_T1.csv`, `criteria.csv`, `hypotheses.csv`,
`merge_out.txt`, `run.log`. Ara `arms_cache.npz` (~12 MB, yeniden üretilebilir) commit edilmedi.

**Bütçe ölçüm betikleri** (ön-kayıtta atıf yapılan ms/adım değerlerinin kaynağı):
`numcog/_bench_csr.py` (CSR × yoğun, 9,8/14,9 ms), `_bench_var.py` (sort_indices etkisi),
`_bench_dense.py` (yoğun BLAS karşılaştırması), `_bench_spmv.py` (reduceat denemesi).

## 7. ÖZET (bu veride, bu modelde, bu ızgarada)

1. **Koşu:** 165 tohum-kol, **174 dk**; donmuş konfigürasyon **g = 1,30, amp = 0,5** (yalnızca
   validasyonla seçildi; test seçimde kullanılmadı ✓).
2. **"Ağ durumu taşıyor" ölçütü GEÇMEDİ.** A_gercek k=10'da **0,25** (H = 0/10/20/40 için 0,246–0,257);
   %90 eşiğinin çok altında ve W=0 kolundan **GA ayrık** değil. Yalnızca k=2'de **1,000**.
3. **"Connectome'a özgü" ölçütü GEÇMEDİ — ters yönde.** Gerçek alt ağ, **derece-shuffle (−0,17),
   işaret-permutasyon (−0,21), ağırlık-shuffle (−0,16), dengeli-işaret (−0,10) ve ER (−0,03)**
   kollarının **hepsinden anlamlı biçimde DAHA KÖTÜ** (tümü p_holm < 0,05).
4. **Neden (ölçülü):** gerçek W "neredeyse ölü" bir rejim üretiyor (aktivite 0,0033, aktif %2,4;
   surrogate A_derece'de %65). Nedeni **ρ=1 normalizasyonu + gerçek ağırlıkların ağır-kuyruklu
   olması** (ρ_raw: gerçek 635, derece-shuffle 116) → normalleştirme gerçek ağın tipik ağırlıklarını
   küçültüyor. **Bu tek normalizasyon seçiminin sonucudur** ("connectome kötü" değildir).
5. **Tekrarlama yine de bellek ekliyor:** T2 (Jaeger MC) **10,85** (gerçek) vs **0,39** (W=0) vs
   7,11 (MB); **T4** yankı-durum sağlanıyor (d_end = 0,0000). Yani kapasite **var**, ama **T1'in
   nominal okuması onu kullanamıyor**.
6. **H7.1:** yön doğru ama **etki küçük** (+0,025; 0,252 vs 0,227). **H7.2:** **çürüdü (ters yönde).**
   **H7.3:** **destek** (T3 şans düzeyi: 0,177 / şans 0,25; doygunluk YOK → çöküş doygunlukla değil,
   okumanın ekstrapole edememesiyle). **H7.4:** k yönünde **destek**, H yönünde **çürüdü**.
   **H7.5:** surrogatlar daha iyi → **işaret varsayımı ana neden değil.** **H7.6:** A vs MB
   **ayrışamaz** (p = 0,068; n_B = 10).
7. **İş bölümü:** kontrolcü yalnızca ±1 darbesi gönderir, **sayaç tutmaz**; okuma katmanı durumu
   sayıya çevirir. **İdeal sayaç (dış yardım) tanım gereği 1,000** → hesap kontrolcüde tam
   yapılabilir; **ağın taşıması** bu modelde/ızgarada **başarılamadı**.
8. **Giriş nöron seçimi keyfî** (tohumla rastgele), **NT işaretleri varsayım**, **tek connectome**,
   **simülasyon**. **Sonradan eklenen analiz yok** (her şey ön-kayıtlıydı; ölçüm sırasında hiçbir
   ölçüt/ızgara/bölme değiştirilmedi).

