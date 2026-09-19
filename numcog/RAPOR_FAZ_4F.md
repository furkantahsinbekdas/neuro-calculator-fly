# RAPOR FAZ 4F — N=81: dolgu + σ genişletme (KISA, ön-kayıtlı)

Tarih: 2026-09-20. Durum: tamamlandı. Hipotez ön-kayıtlı (commit `46128e2`).
**Seçim ölçütü YALNIZCA tablo doğruluğu**; çarpma/bölme seçim için KULLANILMADI.
Faz 0–4E dosyaları/sonuçları DEĞİŞTİRİLMEDİ.

## 1. Yöntem

`numcog/phase4f.py`. N=81; **dolgu sabit `lo=−3, hi=N+3`** (4E'nin en iyi dolgusu);
**σ ∈ {2.0, 2.5, 3.0, 4.0} × top-k ∈ {80, 120}** = 8 hücre × **30 tohum**; epoch 25000, lr 0.05.
Başarı eşiği: ≥%95 tohum %100 tablo. Her hücrede ayrıca **özdeş-kod + farklı-etiket çatışma sayısı**,
**rank** ve **float32 taşma (NaN) bayrağı** raporlandı.

**Koşu:** 8 hücre 8 paralel süreçte (tek iş parçacıklı) koştu; her tohum biter bitmez CSV'ye eklendi
(kesintiye dayanıklı). Paralellik yalnızca yürütüm biçimidir, sonuçları değiştirmez (bkz. §5 sağlama).

## 2. Izgara sonuçları (30 tohum/hücre)

| σ | top-k | tam-doğru | %95 GA | eğitim | kod çakışması (ort/top) | rank<164 | **taşma (NaN)** |
|---|---|---|---|---|---|---|---|
| **2.0** | **80** | **28/30 = %93.3** | [78.7, 98.2] | 0.9996 | 0.13 / **4** | 16/30 | 0 |
| 2.0 | 120 | 0/30 = %0.0 | [0.0, 11.4] | 0.0122 | 0.33 / 10 | 13/30 | **30/30** |
| 2.5 | 80 | 24/30 = %80.0 | [62.7, 90.5] | 0.9984 | 0.27 / 8 | 14/30 | 0 |
| 2.5 | 120 | 0/30 = %0.0 | [0.0, 11.4] | 0.0122 | 0.07 / 2 | 11/30 | **30/30** |
| 3.0 | 80 | 22/30 = %73.3 | [55.6, 85.8] | 0.9974 | 0.47 / 14 | 18/30 | 0 |
| 3.0 | 120 | 0/30 = %0.0 | [0.0, 11.4] | 0.0122 | 0.13 / 4 | 11/30 | **30/30** |
| 4.0 | 80 | 25/30 = %83.3 | [66.4, 92.7] | 0.9988 | 0.40 / 12 | 19/30 | 0 |
| 4.0 | 120 | 0/30 = %0.0 | [0.0, 11.4] | 0.0122 | 0.20 / 6 | 15/30 | **30/30** |

CSV: `results_p4f/grid81_4f_summary.csv` (ham satırlar: `grid81_4f.csv`).

## 3. H4f.1 — ÇÜRÜTÜLDÜ (top-k=80); top-k=120 ekseni ÖLÇÜLEMEDİ

**top-k = 80 σ dizisi: 0.933 → 0.800 → 0.733 → 0.833.** Monoton DEĞİL ve σ=3.0 ile σ=4.0,
σ=2.0'ın **altında** → ön-kayıtlı çürütme koşulu sağlandı: **H4f.1 ÇÜRÜTÜLDÜ.**

Yani 4E'de görülen "σ arttıkça iyileşme" trendi **σ=2.0'da bitiyor**; daha geniş σ zarar veriyor.
Mekanizma ölçümle uyumlu: **kod çakışması σ ile artıyor** (4 → 8 → 14 → 12 çatışma; σ=2.0 en düşük),
ve eğitim doğruluğu 0.9996 → 0.9974'e düşüyor. (σ=4.0'un 3.0'dan iyice olması çatışma sayısının
12'ye gerilemesiyle tutarlı.)

**top-k = 120 hücreleri kapasite bilgisi TAŞIMIYOR:** dört hücrede de **30/30 tohum float32
taşması** (W/b içinde NaN; eğitim doğruluğu şans düzeyi 0.0122 = 2/164). Bu bir kapasite sonucu
değil, **sayısal çöküş**tür: top-k=120 ile kodlar yoğun/benzer hale geliyor ve lr=0.05 + 25000 epoch
float32 delta kuralı ıraksıyor. Bu nedenle `h4f1.csv`'de top-k=120 satırı "monoton" görünse de
(0,0,0,0) bu **boş bir doğrulamadır** ve hipotez lehine sayılmaz.

## 4. Karar

**Hiçbir hücre ≥%95'e ulaşmadı** → **donma YOK** → ön-kayıtlı karar gereği **kalibrasyon kapısı
olmadan 100 tohum ölçümü YAPILMADI** (`frozen.json = null`). En iyi hücre yine **σ=2.0 + dolgu +
top-k=80 = %93.3**; yani **N=81'de tabloyu tüm tohumlarda %100 öğretmek bu ızgarada da başarılamadı**.
Kalibrasyon kapısı (4E) çözüm olarak kalır.

## 5. Sağlamalar (iki bağımsız doğrulama)

1. **4E ile birebir çakışma:** 4F'nin σ=2.0/top-k=80/dolgulu hücresi, 4E'nin `grid81_4e.csv`'deki
   aynı hücresiyle **birebir aynı**: `full=28`, eğitim `0.9995934959349594` (16 ondalık aynı).
2. **Ön-kayıtlı determinizm sağlaması:** 4E'de shard'lı koşup birleştirilen zincirden
   `RandomState(2026)` ile seçilen **3 tohum (15, 43, 71)** baştan çalıştırıldı; her biri **324
   zincir satırı, 0 farklı hücre → 3/3 BİREBİR AYNI** (`sanity_determinism.csv`).
   → 4E'nin paralel shard sonuçları güvenilir.

## 6. Sınırlılıklar

- **Izgara fiilen 4 hücre:** top-k=120 ekseninin tamamı sayısal taşma nedeniyle boş; "8 hücre"
  ifadesi biçimseldir, σ trendi yalnızca 4 noktayla (top-k=80) test edildi.
- **Sayısal taşma bir TASARIM sınırıdır, kapasite sınırı değil:** lr≥0.05 + 25000 epoch float32
  delta kuralı yoğun kodlarda ıraksıyor. Bu fazda **öğrenme kuralı/precision DEĞİŞTİRİLMEDİ**
  (değiştirmek "TASARIM DEĞİŞİKLİĞİ" olurdu). Yani "top-k=120 kötü" değil, "top-k=120 bu
  kuralla ölçülemedi".
- **"Bu ızgarada" kaydı:** σ ∈ {2.0…4.0} ve top-k ∈ {80,120} denendi; σ<2.0 kombinasyonları (4E'de
  σ=1.0/1.5 dolgulu %83.3), farklı dolgu genişlikleri, top-k ∈ (80,120) arası veya başka
  optimizasyon (epoch/lr) denenmedi. Bu nedenle sonuç "N=81 ulaşılamaz" değil,
  **"bu ızgarada ≥%95 yok"**tur.
- **Tek ölçüt tablo:** çarpma/bölme bu fazda hiç çalıştırılmadı (donma olmadı).
- **30 tohum** → GA genişliği ±10-15 puan; %93.3 ile %95 arasındaki fark istatistiksel olarak
  ayırt edilemez ama **ön-kayıtlı eşik %95 olduğu için karar değişmez**.
- Sayı→VPN / operatör→ALPN atamaları **keyfî**; yalnızca VPN→KC / ALPN→KC kablolaması gerçek veridir.
  Termometre kodu **dış yardımcı**dır.
- **Simülasyon**, canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).
- **Koşu koşulları:** makine ağır yüklüydü; hücreler 8 paralel süreçle koştu ve her satır anında
  diske yazıldı. Paralellik yürütüm detayıdır; **§5'teki iki sağlama sonuçların değişmediğini
  gösterir**.

## 7. Yeniden üretilebilirlik

```bash
cd flyputer
# 8 hücre (paralel; her biri kendi sürecinde):
for i in 0 1 2 3 4 5 6 7; do .venv/Scripts/python.exe -X utf8 numcog/phase4f.py cell $i & done
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py merge     # özet + H4f.1 + donma kararı
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py sanity    # 4E determinizm sağlaması
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py final 0 1 # (donma olmadığı için çalışmaz)
```

CSV: `results_p4f/` → `cell0_s0.csv … cell7_s0.csv`, `grid81_4f.csv`, `grid81_4f_summary.csv`,
`h4f1.csv`, `sanity_determinism.csv`, `frozen.json`, `run.log`.

## 8. KARAR (özet)

1. **H4f.1 ÇÜRÜTÜLDÜ (top-k=80):** σ dizisi 0.933 → 0.800 → 0.733 → 0.833; monoton değil ve
   σ=3.0/4.0 σ=2.0'ın altında. σ'yı büyütmek **yardımcı olmuyor, zarar veriyor**.
2. **Kod çakışması σ ile artıyor** (4 → 8 → 14 → 12), eğitim doğruluğu düşüyor → mekanizma tutarlı.
3. **top-k=120 ekseni float32 taşması** nedeniyle ölçülemedi (30/30 NaN) — kapasite kanıtı değil.
4. **Hiçbir hücre ≥%95 → donma yok, kalibrasyon kapısı olmadan 100 tohum ölçümü yapılmadı.**
   En iyi hücre yine **σ=2.0 + dolgu + top-k=80 = %93.3**.
5. **İki sağlama geçti:** 4E hücresiyle birebir aynı sayılar; 4E zincirinin 3 tohumu 3/3 birebir aynı.
6. **Sinek durum taşımaz, kontrolcü taşır.**

**Açık kalan (sonraki faz kararı):** N=81'de kalibrasyon kapısı olmadan tam kapsama
(i) ya sayısal stabiliteyi düzelterek (float64 / daha küçük lr / normalizasyon) aranmalı — bu bir
**TASARIM DEĞİŞİKLİĞİ**dir ve yeni ön-kayıt gerektirir; (ii) ya da **iki haneli yedek** uygulanmalı
(onlar/birler ayrı kanal, elde/borç kontrolcüde) — 4D'de tasarım olarak etiketlenmişti, hâlâ
uygulanmadı.

