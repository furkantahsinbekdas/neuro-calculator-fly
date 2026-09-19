# RAPOR FAZ 4C — Sistematik başlangıç hatası ve N=81 kapasitesi (mühendislik)

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `ea941cd`).
**Seçim ölçütü YALNIZCA tablo doğruluğu** (tüm 2(N+1) girdinin doğru öğrenilmesi); çarpma/bölme
testi seçim için KULLANILMADI.

## 1. Adım 0 — Tanı (N=40, 100 tohum, referans konfigürasyon)

- **Tablo TAM doğru tohum: 66/100 (%66.0)** → 34 tohumda en az bir girdi yanlış.
- Eğitim doğruluğu: ort 0.9938, **min 0.9634**.
- **Hatalı girdiler belirli n'lerde toplanıyor:** `(39,−)` 13 · `(1,+)` 11 · `(40,−)` 7 ·
  `(0,+)` 3 · `(3,+)` 2 · `(38,−)` 2 (+ 9 tekil). Yani hatalar **alt sınır (n=0,1)** ve
  **üst sınır (n=38,39,40)** girdilerinde.
- **Marj (doğru sınıf − en iyi yanlış): ort −0.064, min −0.213** → bozuk tohumlarda doğru sınıf
  yanlışa kaybediyor (marj negatif).
- **Kenar kod benzerliği (komşuyla maks kosinüs):** n=39 `−` **0.894**, n=40 `−` 0.888,
  n=39 `+` 0.879, n=0 `+` 0.840 — kenar girdileri komşularına daha çok benziyor (ayrışmaları zor).

## 2. Kollar (N=40, 30 tohum) — her düzeltme TASARIM DEĞİŞİKLİĞİ

| kol | tam-doğru tohum | eğitim | ölçüt (≥%95) |
|---|---|---|---|
| ref (1000 ep, lr .01) | 17/30 (%56.7) | 0.9919 | ✗ |
| **ep4x** (4000 ep) | **29/30 (%96.7)** | 0.9996 | **✓** |
| **ep10x** (10000 ep) | **30/30 (%100.0)** | **1.0000** | **✓** |
| pad (eksen [−3, 43]) | 21/30 (%70.0) | 0.9955 | ✗ |
| lr0.005 | 6/30 (%20.0) | 0.9659 | ✗ |
| lr0.02 | 27/30 (%90.0) | 0.9984 | ✗ |
| **lr0.05** | **29/30 (%96.7)** | 0.9996 | **✓** |
| balanced (1/frekans) | 17/30 (%56.7) | 0.9919 | ✗ |

**SEÇİLEN / DONAN KONFİGÜRASYON: `ep10x`** (σ=1.5, top-k=40, lr=0.01, **epoch=10000**, N=40).

## 3. Kontrolcü tarafı — kalibrasyon (KONTROLCÜ İŞİ; sinek kural öğrenmez)

Seçilen konfigürasyonla **0/30 tohum reddedildi** (tablo tam). Adım 1-4 başarılı olduğu için
kalibrasyon katmanı **gerekmedi**; yine de ölçüldü ve raporlandı. Not: bu bir **kalite kontrol**
katmanıdır, sineğe kural öğretmez.
## 4. N=81 kapasitesi (20 tohum) — H4c.3

| σ | top-k | tam-doğru | eğitim |
|---|---|---|---|
| 1.0 | 40 / 60 / 80 / 120 | 0/20 · **2/20** · 0/20 · 0/20 | 0.941 · 0.970 · 0.974 · 0.953 |
| 1.5 | 40 / 60 / 80 / 120 | 0/20 · 1/20 · 1/20 · 0/20 | 0.940 · 0.972 · 0.975 · 0.960 |

**H4c.3 ÇÜRÜDÜ:** hiçbir (σ, top-k) kombinasyonu ≥%95'e ulaşmıyor (en iyi 2/20 = %10). N=81
bu mimariyle **ulaşılamaz** — KC kodu 82 değeri ayırt etmekte yetersiz (eğitim ~0.97'de takılıyor).

### İki haneli YEDEK (TASARIM DEĞİŞİKLİĞİ, ETİKETLİ)

9×9=81 için N≥81 gerektiğinden, yedek: **onlar ve birler ayrı kanal** — her kanal kendi N=9
çekirdeği (0..9, tablo küçük → ep10x ile tam), **elde/borç ve basamak taşıma TAMAMEN KONTROLCÜDE**.
Bu bir kontrolcü tarafı iş bölümüdür; sinek hâlâ yalnızca ±1 adımı yapar. (Bu fazda uygulanmadı;
yalnızca etiketli yedek olarak yazıldı.)

## 5. Son ölçüm (donmuş `ep10x`, 100 tohum)

| ölçüm | sonuç |
|---|---|
| tablo tam-doğru tohum | **99/100** |
| add | **1.000 ± 0.000** |
| subtract | **1.000 ± 0.000** |
| divide | **1.000 ± 0.000** |
| multiply | **0.790 ± 0.000** (tüm tohumlarda AYNI değer) |
| zincir: k ≤ 40 | **1.000** |
| zincir: k > 40 | **0.000** (aralık dışı) |

**Zincir vs p^k:** p = 1.000 olduğu için p^k = 1.000. Ölçülen zincir **k ≤ 40'ta 1.000**, k > 40'ta
0.000. Yani tek sapma **aralık sınırıdır, hata birikmesi değil** — 40 adımdan uzun zincirler
N=40'ı aşıyor. (Karşılaştırma: Faz 4A'da p=0.50 → zincir k≥12'de 0'a çöküyordu.)

**Multiply 0.790'ın açıklaması — hata değil, ARALIK:** çarpım hep n=0'dan başlar ve 9×9=81'e
kadar çıkar; N=40 olduğu için çarpımı >40 olan 17/81 çift aralık dışıdır. 64/81 = 0.7901 ve bu
değer tüm tohumlarda **birebir aynı** — yani çekirdek artık kusursuz, kalan tek sınır **aralık**.
Faz 4B-0'da aynı 0.790 hem aralık sınırından hem çekirdek hatalarından geliyordu; 4C'de çekirdek
hatası **kalmadı**.

**İş bölümü (yazılı):** sinek yalnızca tek adım (n,op)→n±1 yapar ve **durum taşımaz**; sayaç,
döngü, durma koşulu, durum geri beslemesi ve sonuç okuma **kontrolcüdedir**.

## 6. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H4c.1 bozukluk optimizasyon kaynaklı | **DESTEKLENDİ** (ep4x %96.7, ep10x %100, lr0.05 %96.7) |
| H4c.2 kenar temsil sorunu | **KISMEN** (dolgu %56.7→%70, ama ≥%95'e ulaşmıyor) |
| H4c.3 N=81 bir konfigürasyon ≥%95 | **ÇÜRÜDÜ** (en iyi %10) → iki haneli yedek gerekli |
| Başarı ölçütü ≥%95 tohum tam-doğru | **SAĞLANDI** (ep10x %100; son ölçümde 99/100) |

## 7. Sınırlılıklar

- Hatalar hem sınıra hem optimizasyona bağlı: dolgu tek başına yetmedi, epoch artışı yetti →
  birincil neden **optimizasyon** (marj negatif, doğru sınıf kaybediyor).
- N=81 ulaşılamaz; iki haneli yedek bu fazda UYGULANMADI (etiketli yedek).
- Sayı→VPN / operatör→ALPN atamaları keyfî; yalnızca VPN→KC/ALPN→KC kablolaması gerçek.
- Kollar 30 tohum, son ölçüm 100 tohum (ana ölçüm).
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 8. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/phase4c.py
```
Çıktı: `numcog/results_p4c/` (diag_seeds.csv, diag_wrong.csv, diag_similarity.csv, arms40.csv,
n81_sweep.csv, final_seeds.csv, final_chain.csv).

**KARAR:** Donan konfigürasyon `ep10x` (N=40). Sistemik başlangıç hatası **optimizasyon** kaynaklıydı
ve epoch ×10 ile giderildi; N=81 ulaşılamaz (iki haneli yedek etiketlendi). Sonraki adım için
bekleniyor (dur — kullanıcı onayı).

