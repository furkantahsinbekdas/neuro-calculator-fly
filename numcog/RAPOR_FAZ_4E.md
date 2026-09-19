# RAPOR FAZ 4E — N=81 teşhisi, kalibrasyon ve shuffle kontrolü (KISA)

Tarih: 2026-09-19/20. Durum: tamamlandı. Hipotez ön-kayıtlı (commit `2435393`).
**Seçim ölçütü YALNIZCA tablo doğruluğu**; çarpma/bölme seçim için KULLANILMADI.

## 0. Sabit hücre ve yöntem

N=81; 4D en iyi hücre **epoch 25000, lr 0.05, top-k 80, σ=1.5**; Adım 1–3'te 30 tohum, Adım 4'te 100.
`numcog/phase4e.py`; mevcut modüller import edildi, DEĞİŞTİRİLMEDİ. Faz 0–4D dosyaları/sonuçları
dokunulmadı.

**Koşu notu (dürüstlük):** Adım 1–3 ve Adım 4 kalibrasyonu tamamlandıktan sonra (kalibrasyon çıktısı
`calib81.csv` diske yazılmıştı) hesap makinesi döngüsünde terminal kesintisi oldu. Kalan kısım AYNI
deterministik kod yoluyla tamamlandı (`numcog/phase4e_step4_calc.py`, her tohumdan sonra CSV'ye ekleyen
yeniden-başlatılabilir sürüm). Ön-kayıt, konfigürasyon ve tohum listesi DEĞİŞMEDİ.

## 1. Adım 1 — Teşhis

### 1.1 Hangi (n,op) girdileri yanlış?

- Tablo **tam doğru tohum: 18/30 (%60.0)**; eğitim doğruluğu ort 0.9967, min 0.9695.
- **12 hatalı tohum, toplam 16 hatalı girdi** (164 girdinin ~%0.5'i).
- Hatalı (n,op) sayımı: **(1,+)=3, (80,−)=3, (81,−)=2**, (15,+)=1, (15,−)=1, (2,−)=1, (62,+)=1,
  (64,+)=1, (67,+)=1, (78,+)=1, (79,−)=1.
- Hatalı girdilerin n dağılımı: 1:3, 2:1, 15:2, 62:1, 64:1, 67:1, 78:1, 79:1, 80:3, 81:2.

### 1.2 Kenarda mı toplanıyor? → **H4e.1 DESTEK**

Kenar kümesi E = (n ∈ {0,1,80,81}) = 8/164 = %4.88 taban oranı. Hatalı 16 girdinin **8'i (%50.0)**
E'de → taban oranının **~10 katı**, ön-kayıtlı eşik (%9.76) fazlasıyla aşıldı.

Kenar hatalarının tam dağılımı: **(1,+)=3, (80,−)=3, (81,−)=2**. Üçü de sınırın **bir adım içi**
(1→2, 80→79, 81→80) — yani kenarda "içeri doğru tek adım" en kırılgan girdi. Kenarın kendisi
(0,−) ve (81,+) (kırpılan girdiler) hiç hata vermedi.

### 1.3 Hatalı girdilerin komşu kod kosinüs benzerliği

| grup | komşu kod kosinüs (maks) |
|---|---|
| yanlış girdiler | **0.998** |
| doğru girdiler | 0.902 |

Hatalı girdilerin kodu komşusuyla **neredeyse özdeş**. Bu, hatanın "öğrenme zorluğu" değil **kod
çakışması** olduğunu gösterir.

### 1.4 Ayrılabilirlik testi (aynı kodlar, kapalı form) → **H4e.2 ÇÜRÜTÜLDÜ**

| ölçüt | sonuç |
|---|---|
| rank(X) = 164 (30 tohum) | **HAYIR — 19/30 tohumda rank < 164** |
| özdeş kod + farklı etiket çatışması | **27 satır** (30 tohumda) |
| kapalı form (en küçük norm `lstsq`) doğruluk | ort **0.9967**, **min 0.9756** |
| delta kuralı (aynı kodlar) doğruluk | ort **0.9967** |

**H4e.2 çürüdü** (rank<164 VE özdeş-kod çatışması var VE kapalı form <1.000). Dahası:

> **Kapalı form = delta kuralı (0.9967 = 0.9967).** Yani yakınsamış en iyi doğrusal sınıflandırıcı,
> delta kuralının ulaştığından daha iyisini yapamıyor. Öğrenme kuralı/optimizasyon tavanı **değil**;
> tavan **kodlarda** (birkaç girdi için kod birebir çakışıyor, hiçbir okuma ayıramaz).

### 1.5 Mekanizma (yorum)

top-k=80 ile ±1 komşu kodları neredeyse aynı (0.998); eksen [0,N] iken kenarda Gauss komşusu
kırpıldığı için kenar girdileri ayırt edilemez hale geliyor ve birkaç iç nokta da çakışıyor. Bu,
Adım 3'te test edilen **eksen dolgusu**nun neden işe yaradığını açıklar.

## 2. Adım 2 — Shuffle kontrolü (30 tohum)

| kol | tam-doğru | %95 GA (Wilson) | eğitim |
|---|---|---|---|
| **gerçek** `W_vpn` | **18/30 (%60.0)** | [42.3, 75.4] | 0.9967 |
| derece-korunmuş shuffle (`seed=999`, 200000 takas; 1843→1843 kenar) | 22/30 (%73.3) | [55.6, 85.8] | 0.9980 |
| örtüşme-kontrol (`W_alpn_r_rand`) | 15/30 (%50.0) | [33.2, 66.8] | 0.9961 |

**Karar: AYIRT EDİLEMEDİ.** Gerçek kolun oranı (%60.0) shuffle kolunun %95 GA'sının **içinde** →
ön-kayıtlı yorum kuralı gereği "connectome'a özgü VPN→KC yapısının bu tabloda ölçülebilir katkısı
yok" yazılır. (Nominal olarak shuffle daha yüksek — %73.3 — ama GA'lar örtüşüyor; bu bir "shuffle daha
iyi" iddiası değil, gücün yetersizliğidir; bkz. Sınırlılıklar.)

## 3. Adım 3 — Küçük ızgara (H4e.1 desteklendiği için çalıştı; 6 hücre × 30 tohum)

| σ | dolgu [−3, N+3] | tam-doğru | %95 GA | eğitim |
|---|---|---|---|---|
| 1.0 | yok | 12/30 (%40.0) | [24.6, 57.7] | 0.9931 |
| 1.0 | **var** | 25/30 (%83.3) | [66.4, 92.7] | 0.9988 |
| 1.5 | yok | 18/30 (%60.0) | [42.3, 75.4] | 0.9967 |
| 1.5 | **var** | 25/30 (%83.3) | [66.4, 92.7] | 0.9980 |
| 2.0 | yok | 24/30 (%80.0) | [62.7, 90.5] | 0.9984 |
| 2.0 | **var** | **28/30 (%93.3)** | [78.7, 98.2] | **0.9996** |

- **Eksen dolgusu her σ'da büyük kazanç:** σ=1.0'da +43.3 puan, σ=1.5'te +23.3, σ=2.0'da +13.3.
- En iyi hücre **σ=2.0 + dolgu = %93.3** → ön-kayıtlı başarı eşiğinin (**%95**) ALTINDA.
- **DONMA YOK.** N=81'de tam tablo bu mimaride/ızgarada ulaşılamadı (ama yön net: dolgu + daha geniş σ).

## 4. Adım 4 — Kontrolcü kalibrasyonu (KONTROLCÜ İŞİ) + hesap makinesi

**Açılış kalibrasyon kapısı:** tüm 164 (n,op) girdisi sınanır; **herhangi biri yanlışsa sinek
REDDEDİLİR**. Bu bir **kalite kontrol**tür, kural öğrenme değildir.

| ölçüt | sonuç |
|---|---|
| taranan tohum | 100 |
| **kabul** | **54 (%54.0, GA95 [44.3, 63.4])** |
| **reddedilen** | **46 (%46.0, GA95 [36.6, 55.7])** |

**Kabul edilen 54 tohumda hesap makinesi (N=81; 1..9 tüm çiftler):**

| işlem | ort ± std | min | %95 GA | tohum doğruluk dağılımı |
|---|---|---|---|---|
| add | **1.0000 ± 0.0000** | 1.0000 | [1.0000, 1.0000] | {1.0: 54} |
| subtract | **1.0000 ± 0.0000** | 1.0000 | [1.0000, 1.0000] | {1.0: 54} |
| **multiply** | **1.0000 ± 0.0000** | 1.0000 | [1.0000, 1.0000] | {1.0: 54} |
| **divide** | **1.0000 ± 0.0000** | 1.0000 | [1.0000, 1.0000] | {1.0: 54} |

- N=81 olduğu için **9×9 = 81 tam temsil edilebilir** → 4C'deki N=40 **aralık artefaktı**
  (multiply 0.790) ortadan kalkar; kabul edilen sineklerde **tüm çarpma ve bölme %100**.
- 4C'den fark: orada donmuş konfigürasyon tüm tohumlarda tabloyu %100 öğretiyordu; burada
  **tablo %100 olmayan sinekler reddedilir** (kalibrasyon), kalanlar hatasızdır.
- **İş bölümü (değişmedi):** sinek yalnızca (n,op)→n±1 tek adımını yapar; **sayma, döngü, durma
  koşulu, basamak/taşıma ve kötü tabloyu reddetme KONTROLCÜDE**dir. **Sinek durum taşımaz, kontrolcü taşır.**

## 5. Zincir uzunluğu k vs p^k

`results_p4e/final81_chain.csv` (k = kontrolcünün tetiklediği sinek adımı sayısı). Kabul edilen
sineklerin tablosu %100 olduğundan zincirdeki her adım doğrudur.

## 6. Sınırlılıklar

- **"Ulaşılamaz" değil "bu ızgarada ulaşılamadı".** Yalnızca ön-kayıtlı 6 hücre denendi; σ>2.0,
  daha geniş dolgu veya özel kodlama denenmedi. Dolgu + σ artışının hâlâ monoton kazanç vermesi
  (%40→%83.3→%93.3) sınırın **yöntemsel değil ızgara-ekseni** olabileceğini düşündürür.
- **Shuffle kontrolünün gücü zayıf:** tek shuffle tohumu (999), 30 tohum; "AYIRT EDİLEMEDİ"
  sonucu "fark yok" kanıtı değil, **güç yetersizliği**dir ve shuffle kolu nominal olarak daha
  yüksektir (%73.3 vs %60.0).
- **Adım 4, Adım 3'ün değil 4D hücresinin konfigürasyonunu kullandı** (ön-kayıtlı kural: donma
  olmadığı için 4D hücresi). σ=2.0+dolgu dondurulsaydı kabul oranı muhtemelen daha yüksek olurdu;
  ama o hücre de %95'i geçmediği için donma yoktu.
- Kalibrasyon **46/100 tohumu reddetti** → sistemin %54'ü kullanılabilir. Reddedilenlerin başka
  tohumla yeniden eğitilmesi bir **kontrolcü politikasıdır** ve bu fazda uygulanmadı.
- Adım 1–3'ün tam-doğru oranı ≈ kalibrasyon kabul oranı (%60 vs %54) — ikisi aynı ölçüttür.
- Sayı→VPN ve operatör→ALPN atamaları **keyfî**; yalnızca VPN→KC / ALPN→KC kablolaması gerçek veridir.
  Termometre kodu **dış yardımcı**dır (biyolojik değil).
- **Simülasyon**, canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).
- **Koşu kesintisi:** Adım 4 hesap makinesi döngüsü yeniden çalıştırıldı (aynı deterministik kod
  yolu, `seed+1000` ile aynı ağırlık başlangıcı → aynı sonuç). Kalibrasyon çıktısı yeniden
  üretilmedi, kesintiden önceki `calib81.csv` kullanıldı.

## 7. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/phase4e.py             # Adım 1-3 + Adım 4 kalibrasyon
.venv/Scripts/python.exe -X utf8 numcog/phase4e_step4_calc.py   # Adım 4 hesap makinesi (resumable)
```

CSV: `results_p4e/` → `diag81_seeds.csv`, `diag81_wrong.csv`, `diag81_sim.csv`, `diag81_sep.csv`,
`diag81_ncount.csv`, `diag81_nhist.csv`, `shuffle81.csv`, `grid81_4e.csv`, `calib81.csv`,
`final81_seeds.csv`, `final81_chain.csv`, `run.log`.

## 8. KARAR (özet)

1. **H4e.1 DESTEK:** N=81 hataları kenarda toplanır (hatalı girdilerin %50'si, taban %4.88),
   ve tam da "sınırın bir adım içi" girdiler (1,+, 80,−, 81,−).
2. **H4e.2 ÇÜRÜTÜLDÜ:** kodlar tam ayrılamıyor; 27 özdeş-kod çatışması var ve **kapalı form =
   delta kuralı = 0.9967** → tavan kodda, öğrenme kuralında değil.
3. **Shuffle: AYIRT EDİLEMEDİ** (gerçek %60.0, shuffle GA95 [55.6, 85.8] içinde).
4. **Eksen dolgusu en güçlü iyileştirme** (σ=1.0: %40→%83.3); en iyi hücre %93.3 < %95 → **donma yok**.
5. **Kontrolcü kalibrasyonu ile N=81 hesap makinesi tam çalışıyor:** kabul edilen 54/100 tohumda
   1..9 tüm **çarpma ve bölme 1.0000** (4C'deki 0.790 aralık artefaktı yok).
6. **Sinek durum taşımaz, kontrolcü taşır.**

