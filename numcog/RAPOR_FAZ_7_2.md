# RAPOR FAZ 7-2 — Adil rejim testi: kol başına g seçimi + spektrum tanısı

Tarih: 2026-09-20. Ön-kayıt **ölçümden ÖNCE** commit edildi: **`137b034`**
("Faz 7-2 ek ön-kayıt + tasarım tabanları"). Yeni kod: **`numcog/reservoir_fair.py`**;
çıktılar **`results_p7_2/`**. Faz 0–7-1 dosyaları/sonuçları **değiştirilmedi** (7-1 dizinine yazılmadı).
**Eş zamanlı süreç: 1. float64. Seyrek W × yoğun durum matrisi. Tohum başına ayrı CSV.**
Dil kalıbı: **"bu veride, bu modelde, bu ızgarada"**.

> ### ⚠ TASARIM DEĞİŞİKLİĞİ BEYANI
> Bu faz **bir TASARIM DEĞİŞİKLİĞİDİR** ve **7-1 sonuçları görüldükten sonra** yazılmıştır
> (7-1: "ağ durumu taşıyor" geçmedi; gerçek alt ağ surrogatlarından **daha kötü**; rejim
> "neredeyse ölü": aktivite 0,0033, aktif %2,4; nedeni ρ_raw farkı: gerçek **635**, derece-shuffle **116**).
> Test edilen hipotez: **tüm kollar aynı g'de koştuğu için karşılaştırma adil değil miydi?**
> Bu yüzden 7-2 **doğrulayıcı değil, keşifsel-yeniden-test** niteliğindedir; **başarı ölçütleri
> (≥%90, GA ayrıklığı, T3 yok, bölme) 7-1 ile AYNIDIR ve GEVŞETİLMEMİŞTİR.**

## 0. Parametreler ve etiketler (EN BAŞTA)

| öğe | değer | kaynak |
|---|---|---|
| alt ağ / model | A = CX çekirdek (EB/PB/FB/NO), **N=4.236, E=298.441**; a=0,5; tanh; W işaretli (NT **varsayım**), **ρ=1**; I1 giriş (k=50 nöron/kanal) | 7-0/7-1 (kilitli) |
| bölme | **eğitim 300 / validasyon 120 / test 120** (dizi çakışması yok, assert) | 7-1 ile aynı |
| okuma | dual ridge, λ yalnızca validasyonda, gürültü 1e-3×std | 7-1 ile aynı |
| T1 | k ∈ {2,4,6,8,10}, **H ∈ {0,10,20}** (H=40 **yok**) | 7-2 |
| T2 | Jaeger MC, gecikme **1..40**; yalnızca A_gercek + A_w0 | 7-2 |
| **T3** | **bu fazda YOK** (7-1'de okuma sınırı görüldü) | 7-2 (bilinçli daraltma) |
| kollar (4) | A_gercek, A_derece (derece-shuffle), A_er (Erdős–Rényi), A_w0 | 7-2 |
| **donmuş (g, amp) — kol başına** | A_gercek **40,0 / 1,0** · A_derece **20,0 / 1,0** · A_er **20,0 / 1,0** · A_w0 **40,0 / 0,5** | Adım 1 pilotu (yalnızca doğrulama) |
| tie-break basamağı | A_gercek **1** · A_derece **3** · A_er **1** · A_w0 **4** | ön-kayıtlı 4 basamak |
| ızgara sınırı | **A_gercek (g=40) ve A_w0 (g=40)**: raporlandı, **ızgara genişletilmedi** | ön-kayıt |
| şans / "en sık sınıf" tabanı | k=2: 0,333/0,492 · k=4: 0,200/0,371 · k=6: 0,143/0,310 · k=8: 0,111/0,265 · k=10: 0,111/**0,248** | `design_baselines.txt` (**ölçümden önce**) |
| tohum | Adım 1 pilotu 10; **Adım 2 ölçümü 20** | 7-2 |

## 1. Adım 0 — Spektrum ve bileşen tanısı (ham W, normalizasyondan ÖNCE)

**Tutarlılık kontrolü (7-1 ile birebir):** A_gercek **E=298.441, ρ_raw=634.99**; A_derece
ρ_raw=115.80; A_er E=310.545, ρ_raw=125.85 ✓ (aynı kurulum tohumları kullanıldı).
**ARPACK** (`eigs(which='LM', k=50, maxiter=5000)`) — tüm kollarda **yakınsadı** ✓.

| kol | ρ (ARPACK) | en büyük gerçek kısım | **"yavaş mod"** (\|λ\|/ρ ≥ 0,90) | izole hücre | GB bileşen | en büyük GB |
|---|---|---|---|---|---|---|
| **A_gercek** | 634,99 | 275,1 | **1** | 0 | **239** | 3710 / 4236 |
| A_derece | 114,01 | 110,4 | **50** (50/50!) | 0 | 162 | 4075 / 4236 |
| A_er | 125,85 | 125,8 | **1** | 0 | 2 | 4235 / 4236 |
| A_w0 | 0 | 0 | 0 | **4236** | 4236 | 1 |

- **En büyük GB bileşen üzerinde tekrar:** ρ ve yavaş-mod sayıları **değişmedi** (baskın dinamik
  en büyük GB bileşenden geliyor) ✓; en büyük GB: A_gercek 3710, A_derece 4075, A_er 4235, A_w0 1.
- **İzole hücre yok** (A_gercek/A_derece/A_er'de 0; A_w0'da tanım gereği 4236).
- **Yapısal okuma:** gerçek W'nin spektrumu **tepede izole** (ilk 50 özdeğerden yalnızca **1**'i ρ'nun
  %10 bandında) ve **239 güçlü bağlı bileşene** parçalanmış; derece-shuffle'ın spektrumu ise
  **tepede düz** (50/50 mod bandda) ve **162 bileşenli**; ER **tek parça** (2 bileşen).
  *Yani bu veride, bu modelde, bu ızgarada* gerçek connectome "**birkaç baskın mod + parçalı
  bağlantı**" imzası taşıyor; aynı ağırlık çokluğunun karıştırılmış sürümü "**düz tepeli, daha
  bütünleşik**" bir imza taşıyor.
- **Not (dürüstlük):** A_derece için ARPACK ρ=114,01 ile güç iterasyonu ρ_raw=**115,80** arasında
  **~%1,5 fark** var; normalizasyonda 7-1 ile tutarlılık için **güç iterasyonu** değeri kullanıldı
  (7-1'in `arms_cache` değeri). Bu fark raporlanır; sonuçlar bu seçime karşı duyarlı olabilir.

**Aktivite yeniden üretimi (7-1 donmuş g=1,30; amp=0,5; tohum 0; TEK simülasyon istisnası):**

| kol | aktif nöron oranı | 7-1 (30 tohum ort.) | tutarlı |
|---|---|---|---|
| A_gercek | 0,024 | 0,024 | ✓ |
| A_derece | 0,641 | 0,651 | ✓ |
| A_er | 0,930 | 0,931 | ✓ |
| A_w0 | 0,024 | 0,024 | ✓ |

→ 7-1 tanısı **yeniden üretildi** ✓ (gerçek ağ "neredeyse ölü", surrogatları canlı).

## 2. Adım 1 — Kol başına g seçimi (pilot, yalnızca doğrulama)

Ölçüt: **T1, k=6, H=10** kesin doğrulama doğruluğu (10 tohum ort.), kademeli tie-break ile.

| kol | **seçilen (g, amp)** | tie-break basamağı | ızgara sınırı | val (k6,H10) | **aktif oran** | **doygunluk** |
|---|---|---|---|---|---|---|
| **A_gercek** | **g=40,0 · amp=1,0** | 1 | **EVET (g=40)** | **0,9892** | **0,690** | 0,271 |
| A_derece | g=20,0 · amp=1,0 | **3** (skaler MSE) | hayır | 1,0000 | 0,976 | 0,653 |
| A_er | g=20,0 · amp=1,0 | 1 | hayır | 0,7700 | 1,000 | 0,952 |
| A_w0 | g=40,0 · amp=0,5 | **4** (en yüksek g) | **EVET** | 0,3242 | 0,024 | 0,000 |

- **A_gercek'in seçilen g'si ızgaranın ÜST UCUNDADIR (40)** → ön-kayıt gereği "**ızgara sınırı**"
  diye raporlanır ve **ızgara GENİŞLETİLMEDİ** (g>40 denenmedi).
- **A_derece**'de basamak 1 ve 2 **tam eşitlikle** (1,0000; 8 aday) tıkandı → seçim **basamak 3**'te
  (skaler regresyon validasyon MSE'si) çözüldü ✓; **A_w0**'da tüm 18 aday eşitti (W=0 → g anlamsız)
  → **basamak 4** (en yüksek g) düştü, **beklenen** davranış ✓.
- **Aktivite tanısı (seçim ölçütü DEĞİL):** 7-1'de gerçek ağ **%2,4 aktif** ve "neredeyse ölü"ydü;
  adil g seçimiyle **%69 aktif** (ve tanh sınırında %27 doygun) — surrogatlar ise **%98-100 aktif**
  ve **%65-95 doygun**.

## 3. Adım 2 — Donmuş konfigürasyonla ölçüm (20 tohum)

**T1 doğruluk–k eğrileri (ort ± %95 GA).** Tabanlar (ölçümden önce): k=2 0,492 · k=4 0,371 ·
k=6 0,310 · k=8 0,265 · k=10 0,248 ("en sık sınıf").

| kol | H | k=2 | k=4 | k=6 | k=8 | **k=10** |
|---|---|---|---|---|---|---|
| **A_gercek** | 10 | 1,000±0,000 | **1,000±0,000** | **0,990±0,008** | **0,710±0,017** | 0,227±0,019 |
| **A_gercek** | 20 | 1,000 | 1,000 | **0,996±0,006** | 0,711±0,018 | 0,215±0,022 |
| A_gercek | 0 | 1,000 | 0,980±0,016 | 0,752±0,029 | 0,548±0,017 | 0,255±0,023 |
| A_derece | 10 | 1,000 | 1,000 | 0,999±0,002 | 0,680±0,020 | 0,210±0,022 |
| A_er | 10 | 1,000 | 0,910±0,048 | 0,741±0,067 | 0,517±0,037 | 0,259±0,014 |
| A_w0 | 10 | 0,558±0,051 | 0,384±0,016 | 0,294±0,016 | 0,267±0,014 | 0,226±0,019 |

### 7-1 → 7-2 karşılaştırması (aynı ölçütler, aynı bölme, aynı okuma)

| ölçüm | 7-1 (tek g=1,30) | **7-2 (kol başına g)** |
|---|---|---|
| A_gercek k=4, H=10 | 0,780 | **1,000** |
| A_gercek k=6, H=10 | 0,478 | **0,990** |
| A_gercek k=8, H=10 | 0,327 | **0,710** |
| A_gercek k=10, H=10 | 0,252 | 0,227 |
| **A_gercek − A_derece (k=10,H=10)** | **−0,156** | **+0,017** |
| A_gercek − A_derece (k=8,H=10) | −0,082 | **+0,030** |
| aktif nöron oranı (A_gercek) | 0,024 | **0,690** |
| T2 (Jaeger MC, A_gercek) | 10,85 (gecikme 0-60) | **2,12** (gecikme 1-40) |

→ **Adil g seçimi, gerçek alt ağın k ≤ 8'deki durum taşımasını büyük ölçüde düzeltiyor ve
surrogatlarla aradaki farkı KAPATIYOR** (k=6'da −0,156 → −0,009; k=8'de −0,082 → **+0,030**).
**Ancak k=10'da hiçbir kol taban çizgisinin üstüne çıkamıyor** (0,21-0,26 vs taban 0,248) ve
**MC bellek kapasitesi bu rejimde düşüyor** (10,85 → 2,12): doğrusal bellek ile nominal durum
taşıma **aynı yönde hareket etmiyor**.

### Başarı ölçütleri (7-1 ile AYNI; gevşetilmedi)

| ölçüt | sonuç | karar |
|---|---|---|
| **"Ağ durumu taşıyor"** (k=10, H=10 ≥0,90 VE A_w0'dan GA ayrık) | 0,227±0,019 vs 0,226±0,019 | **GEÇMEDİ** |
| aynı ölçüt H=0 / H=20 | 0,255 / 0,215 | **GEÇMEDİ** |
| **"Connectome'a özgü"** (A_derece VE A_er'den GA ayrık üstünlük) | vs A_derece: −0,017 (ayrışamaz); vs A_er: **−0,032 (A_er ÜSTÜN, p_holm=0,044)** | **GEÇMEDİ** |
| **Bellek uzunluğu** (ilk <0,90) | A_gercek **(6, 0)** · A_derece (6,0) · A_er (4,0) · A_w0 (2,0) | 7-1'de A_gercek (4,0) idi |

### Hipotezler (eşleşmiş t-testi; Holm m=3)

| hipotez | sonuç (k=10, H=10) | karar |
|---|---|---|
| **H7.7** (seçilen g > 1,3 **ve** aktif oran ≫ %2,4) | g=**40** > 1,3 ✓; aktif **0,690** ≥ %10 ✓ | **DESTEK** |
| **H7.8** (fark küçülür; yön hâlâ A_gercek ≤ A_derece) | −0,156 → **+0,017** (küçüldü ✓) ama **yön tersine döndü**; çürütme eşiği **GA ayrıklığı sağlanmadı** (p_holm=0,338) | **KISMEN** (fark küçüldü; çürütülmedi) |
| **H7.9** (k=10,H=10'da ≥%90 **sağlanmaz**) | 0,227 | **DESTEK** |
| **H7.10** (TANI, yön yok: yavaş mod ↔ bellek uzunluğu) | A_gercek 1 yavaş mod ↔ (6,0); A_derece **50** yavaş mod ↔ (6,0); A_er 1 ↔ (4,0); Spearman rho=+0,83 **p=0,167 (n=4)** | **ilişki gösterilemedi** |

- **Holm sonuçları:** A_gercek vs **A_er**: −0,032 (p_holm=**0,044**) → ayrışır (**A_er üstün**);
  vs A_derece: +0,017 (p_holm=0,338) → ayrışamaz; vs **A_w0**: +0,001 (p_holm=0,921) → ayrışamaz.
  Yani adil g seçimiyle gerçek ağ, **no-recurrence kontrolüyle istatistiksel olarak ayırt edilemez**
  hale geliyor (k=10'da), ama surrogatlarından da **üstün değil**.
- **T2 (Jaeger MC, gecikme 1-40):** A_gercek **2,12±0,21**, A_w0 **0,35±0,03** (üst sınır 40).
  Bu rejimde (g=40) gerçek ağ **düşük** MC'ye sahip — 7-1'de (g=1,30, gecikme 1-60) 10,85 idi.


## 4. Hangi işi ağın, hangisini okumanın yaptığı (A_gercek vs A_w0)

- **Kontrolcü yalnızca ±1 darbesi gönderir; sayaç TUTMAZ** — toplamı taşımak ağın işidir.
- **No-recurrence kontrolü (A_w0):** k=2'de **0,558**; k=4 **0,384**; k=6 **0,294**; k=8 **0,267**;
  k=10 **0,226** → okuma, **tekrarlama olmadan**, yalnızca sızıntılı izden bu kadar çıkarabiliyor
  (k=2 tabanı 0,492 → A_w0 **tabanın biraz üstünde**, k≥4'te taban düzeyi).
- **Gerçek ağ (A_gercek, g=40):** k=2 **1,000**; k=4 **1,000**; **k=6 0,990**; k=8 **0,710**;
  k=10 **0,227**.
- → **Tekrarlamanın katkısı k ≤ 8'de BÜYÜK** (k=6'da +0,70; k=8'de +0,44), **k=10'da SIFIR**
  (+0,001, p=0,92). 7-1'de bu katkı k=10'da +0,025 kadardı.
- **T2 (Jaeger MC):** A_gercek **2,12** vs A_w0 **0,35** (gecikme 1-40; üst sınır 40) → tekrarlama
  **doğrusal bellek de ekliyor**, ama bu rejimde (yüksek g, doygun) 7-1'in düşük-g rejiminden
  (MC 10,85) **daha az**. **Doğrusal bellek ile nominal durum taşıma aynı yönde hareket etmiyor**:
  yüksek g nominal görevi k≤8'de düzeltirken MC'yi düşürüyor.
- **İdeal sayaç (7-1'de tanımlı, DIŞ YARDIM, üst sınır = 1,000):** bu fazda **koşmadı**; hesap
  kontrolcüde tam yapılabilir, ağın işi onu taşımaktı.

## 5. Sınırlılıklar

- **TASARIM DEĞİŞİKLİĞİ (en önemli sınır):** bu faz **7-1 sonuçları görüldükten sonra** tasarlandı →
  sonuçlar **doğrulayıcı değil, keşifsel-yeniden-test**tir; çoklu-karşılaştırma/HARKing riski
  raporlanır ve **azaltılamaz**. Ölçütler 7-1 ile aynı tutulmuş ve **gevşetilmemiştir**.
- **"Adil" seçim kolları AYNI rejimde karşılaştırmıyor:** her kol **kendi** doğrulama-optimal (g, amp)
  değerinde koşar (en iyi durum karşılaştırması). Seçilen rejimler çok farklı: aktif oran %69 (gerçek)
  - %100 (ER), doygunluk %27 - %95.
- **Seçim ölçütü tek koşuldur (k=6, H=10)** → k=10 için **optimal olduğu garanti değildir**; özellikle
  yüksek g (40) k=10'da doygunluğa yol açmış olabilir.
- **Izgara sınırı:** A_gercek'in seçilen g'si **40 = ızgaranın üst ucu**; g>40 **denenmedi**
  (ön-kayıt gereği genişletilmedi) → "daha yüksek g'de farklı olabilir" olasılığı **kapatılamadı**.
- **T3 yok** (bilinçli daraltma) → kural/ekstrapolasyon bu fazda test edilmedi.
- **T4 yok**; T2 yalnızca 2 kolda (A_gercek, A_w0).
- **Doygun rejim:** seçilen g'lerde tanh ağır doygunlukta (%27-95) → "durum taşıma" bir ölçüde
  **doygunluğa bağlı kodlama** olabilir; bu, ön-kayıtın istediği tanı olarak raporlanır.
- **Spektrum:** ARPACK ρ'si A_derece için güç iterasyonundan **%1,5 farklı** (114,01 vs 115,80);
  normalizasyonda güç iterasyonu kullanıldı. En büyük ~50 özdeğer **alt küme**dir (tüm spektrum değil).
- **Tek connectome** (hemibrain 783); **giriş nöron seçimi keyfî**; **NT işaretleri VARSAYIM**;
  **simülasyon**; işlev/evrimsel tasarım iddiası **YASAK** (Faz 5 kuralı).
- **Ölçüm sırasında hiçbir ızgara/ölçüt değiştirilmedi**; bu rapordaki *tüm* sayılar ön-kayıtlı
  tasarımdan gelir; sonradan eklenen analiz **yok**.

## 6. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/reservoir_fair.py spec      # Adım 0 (ARPACK + aktivite)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_fair.py pilot     # Adım 1 (kol başına g)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_fair.py runall 20 # Adım 2 (20 tohum)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_fair.py merge     # özet + hipotezler
```

Çıktılar (`numcog/results_p7_2/`): `arms_raw_meta.csv`, `spec_summary.csv`, `spec_eigs.csv`,
`activity_g130.csv`, `pilot_grid.csv`, `frozen_config.csv`, `<kol>_seed<NN>.csv` (tohum başına),
`summary_T1.csv`, `hypotheses.csv`, `design_baselines.txt`, `merge_out.txt`, `run.log`.
Ara `arms_raw_cache.npz` (~4,7 MB, yeniden üretilebilir) commit edilmedi.

## 7. ÖZET (bu veride, bu modelde, bu ızgarada)

1. **"Adil rejim" hipotezinin cevabı: KISMEN EVET.** Kol başına g seçilince gerçek alt ağ
   **k ≤ 8'de durum taşıyor**: k=4 **1,000**, k=6 **0,990**, k=8 **0,710** (7-1'de aynı koşullar
   0,780 / 0,478 / 0,327 idi) ve **sızıntılı-giriş kontrolü A_w0'dan büyük farkla ayrışıyor**
   (k=6: 0,990 vs 0,294). **7-1'in "gerçek ağ surrogatlardan kötü" sonucu büyük ölçüde BİR REJİM
   ARTEFAKTIYDI**: fark k=6'da **−0,156 → −0,009**, k=8'de −0,082 → **+0,030**.
2. **Ama "connectome'a özgü üstünlük" iddiası yine DOĞMUYOR:** A_derece ile ayrışamaz (p_holm=0,34),
   A_er k=10'da **üstün** (0,259 vs 0,227; p_holm=0,044).
3. **k=10'da HİÇBİR kol taban çizgisini geçemiyor** (0,21-0,26 vs taban **0,248**) →
   **"ağ durumu taşıyor" ölçütü (k=10, H=10, ≥%90) yine GEÇMEDİ**; **H7.9 destek**, **H7.7 destek**
   (g=40 ≫ 1,3, aktif oran %69), **H7.8 kısmen** (fark küçüldü ama yön tersine döndü ve çürütme
   eşiği olan GA ayrıklığı sağlanmadı), **H7.10: yavaş mod ↔ bellek ilişkisi gösterilemedi**.
4. **Adil g'nin bedeli:** seçilen yüksek g'lerde rejim **ağır doygun** (%27-95) ve **T2 bellek
   kapasitesi düşüyor** (A_gercek MC 10,85 → **2,12**) → nominal durum taşıma ile doğrusal bellek
   **aynı yönde hareket etmiyor**.
5. **Spektrum tanısı:** gerçek W **tepede izole** (ilk 50 özdeğerden 1'i ρ'nun %10 bandında) ve
   **239 güçlü bağlı bileşene** parçalı; derece-shuffle **düz tepeli** (50/50) ve 162 bileşenli;
   ER **tek parça** (2 bileşen). **İzole hücre yok**; en büyük GB üzerinde analiz **aynı** sonucu verdi.
6. **Aktivite yeniden üretimi:** 7-1 tanısı birebir doğrulandı (gerçek %2,4 aktif, surrogatlar
   %65-93) ✓ — yani 7-1'in "ölü rejim" tanısı **doğru**ydu ve 7-2 onu **düzeltti**.
7. **Genel sonuç:** *bu veride, bu modelde, bu ızgarada* gerçek CX çekirdeği, **doğru ölçeklenmiş
   bir rejimde** kısa dizileri (k≤6-8) **taşıyabiliyor**, ama (i) bu başarı surrogatlarından
   **üstün değil**, (ii) **k=10'da kayboluyor** ve (iii) seçilen g **ızgaranın ucunda** — yani
   "connectome'a özgü bir bellek avantajı" bu fazda da **gösterilemedi**.

