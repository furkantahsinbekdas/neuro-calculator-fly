# RAPOR FAZ 3 — Toplama/çıkarma (n±1), operatör = koku, sayı = görsel

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `81a90f1`); veri düzeltmesi
ayrıca kayıtlı (commit `7a15a4a`).

## 1. Yöntem

`numcog/arithmetic.py`. Sayı σ=1.5 Gauss (VPN, 265), operatör iki ayrık rastgele ALPN alt kümesi
(32 birim, tohum başına), KC = W_vpn·g(n) + W_alpn·op (aynı 427 hücre, top-k=40), çıktı 0..10
(11 sınıf, şans %9.1) çok-sınıflı delta kuralı (lr=0.01, 1000 epoch, tam batch). 7 kol, 20 tohum.

**Veri düzeltmesi (ölçüm sırasında):** ön-kayıtlı "dönüşümlü op" bölümü (her n tek op'la)
n-paritesi↔op korelasyonu yarattı ve tüm kollar TEST_KOMBINASYON=0 verdi (op yok sayıldı).
Bu bir veri kusurudur (hipotez değişikliği değil); düzeltme: n=1,2,3 İKİ op'la eğitilir
(op kullanımı zorlanır), TEST_KOMBINASYON = n=4,5,6'nın eksik op'u. Ayrıntı HIPOTEZLER.md'de.

## 2. Özet (ortalama ± std, %95 GA, n=20)

| kol | eğitim | combo (tam) | combo_mag (±1) | newn (tam) | newn_mag |
|---|---|---|---|---|---|
| hash | 1.000 | 0.067 ± 0.137 | 0.183 | 0.008 ± 0.037 | 0.017 |
| coarse_direct | **0.778** ± 0.000 | 0.000 | 0.667 | 0.167 ± 0.000 | 0.333 |
| coarse_kc (gerçek) | **1.000** ± 0.000 | 0.000 | **1.000** | 0.142 ± 0.061 | 0.300 |
| coarse_kc karıştırılmış | 1.000 | 0.000 | 1.000 | 0.167 ± 0.000 | 0.333 |
| coarse_kc ortak-çıkarılmış | **0.667** ± 0.000 | 0.000 | 1.000 | 0.167 ± 0.000 | 0.333 |
| coarse_kc örtüşme-kontrol | 1.000 | 0.000 | 1.000 | 0.142 ± 0.061 | 0.308 |
| termometre (DIŞ YARDIM) | 1.000 | 0.000 | 0.900 ± 0.157 | 0.083 ± 0.085 | 0.200 |

`combo_mag` = tahmin ∈ {n+1, n−1} (büyüklük doğru, yön serbest). Şans = %9.1.

## 3. Hipotez sonuçları

- **H3.1 DESTEKLENDİ:** coarse_direct EĞİTİM = 0.778 < 1.0. Toplamsal (doğrusal) okuma
  (n,op) konjunksiyonunu çözemez — çünkü "n+1 mi n−1 mi" (n ile op'un ÇARPIMSAL) birleşimidir;
  doğrusal okuma yalnızca a·n + b·op toplar. Ölçülen değer 0.778 (9 örneğin 7'si).
- **H3.2 KISMEN ÇÜRÜDÜ:** eğitim doğruluğu coarse_kc (1.0) > coarse_direct (0.778) ✓; AMA
  TEST_KOMBINASYON ikisinde de 0.000 — coarse_kc combo'da coarse_direct'i GEÇMİYOR. KC katmanı
  konjunksiyonu EZBERLİYOR ama genel "op→±1" KURALINI öğrenmiyor (aşağıda).
- **H3.3 DESTEKLENDİ:** ortak 151 KC çıkarılınca eğitim 1.0 → **0.667** (anlamlı düşüş, GA
  örtüşmüyor). Ortak (VPN∩ALPN) KC'ler konjunksiyonun gerçekleştiği yer.
- **H3.4 DESTEKLENDİ:** karıştırılmış (1.0) ve örtüşme-kontrol (1.0), gerçekten (1.0) ayırt
  edilemez — Faz 1-2 eğilimi sürüyor: kablolamanın KİMLİĞİ değil, VARLIĞI yetiyor.
- **H3.5 ÇÜRÜDÜ:** TEST_YENI_N gerçek-kod kollarında şansın BİRAZ üstünde (0.14–0.17) ve
  Kol 7 (termometre) DAHA İYİ DEĞİL (0.083, daha düşük). Termometre kodu ekstrapolasyonu
  düzeltmiyor çünkü asıl darboğaz operatör kanalı + eğitimsiz çıktı sınıflarıdır.

## 4. Asıl bulgu — konjunksiyon ezberi, kural değil

`coarse_kc` TEST_KOMBINASYON'da **büyüklüğü hep doğru** (combo_mag=1.0) ama **yönü hep yanlış**
(combo=0.0). Yani tek op'la gördüğü n için (ör. n=4 op+→5) diğer op'u (n=4 op−→3) TAHMİN EDEMİYOR;
ezberlediği tek sonucu veriyor. n=1,2,3'te iki op'u ayırt edebiliyor (eğitim 1.0) ama bu ayırt,
"op− → −1" gibi soyut bir kurala GENELLEŞMİYOR — KC katmanı (n×op) KONJUNKTİF özellik üretir,
görülmemiş konjunksiyonlar temsil edilmez. Kontrol: "sadece-n" de combo=0.0 (aynı şekilde op'u
yok sayar). Yani model (n,op)→sonuç TABLOSUNU ezberliyor; "+1/−1" işlemini kural olarak
öğrenmiyor. Bu, H3.2'nin "kural öğrenir" beklentisini çürüten esas bulgudur.

## 5. Aktif ortak KC payı (top-k=40 içinde)

coarse_kc 0.311 · karıştırılmış 0.318 · ortak-çıkarılmış 0.000 · örtüşme-kontrol 0.271 ·
termometre 0.336. Ortak KC'ler aktif kodun ~%31'ini oluşturuyor; çıkarılınca 0'a iniyor ve
eğitim 0.667'e düşüyor (H3.3'ün mekanik izi).
## 6. Kontroller

- Rastgele etiket: hash/coarse_direct/coarse_kc combo=0.03–0.05, newn≈0.01–0.02 (şans) → öğrenme
  gerçek sinyalden.
- "sadece-n" (op yok say): combo=0.000, newn=0.167 — op'suz model combo'yu hiç çözemez.

## 7. Sınırlılıklar

- **Çıktı sınıfı karıştırıcısı:** TEST_COMBO ((5,+)→6) ve TEST_YENI_N (sonuç 8,9,10) eğitimde
  hiç görülmemiş çıktı sınıflarını içerir; çok-sınıflı okuma bu sınıflar için ağırlık öğrenmediğinden
  doğruluk yapay olarak düşer. TEST_NEWN'in ~0.14'ü büyük ölçüde bu karıştırıcıdandır.
- **Sayı→VPN ve operatör→ALPN atamaları keyfîdir;** gerçek olan yalnızca VPN→KC / ALPN→KC
  aşağı akış kablolamasıdır.
- **Kol 7 bir DIŞ YARDIMdır** (elle tasarlanmış termometre kodu); sonucu bağlamanın bir
  yeteneği olarak YORUMLANAMAZ.
- "glomerül alt kümeleri" için glomerül etiketleri elimizde olmadığından, rastgele ayrık ALPN
  alt kümeleri kullanıldı (proxy).
- 6 yerine 9 eğitim örneği (veri düzeltmesi sonrası); TEST_COMBO 3 çiftle sınırlı.
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 8. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/arithmetic.py
```
Çıktı: `numcog/results_p3/` (arms_raw.csv, summary.csv, per_pair.csv).

**KARAR:** Faz 3b (±2/±3 ve +1→+2 transfer) yalnızca istenirse; aksi halde FAZ 4 için bekleniyor
(dur — kullanıcı onayı).

