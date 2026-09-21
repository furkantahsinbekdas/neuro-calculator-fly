<!-- Machine translation of `numcog/RAPOR_FAZ_3c.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 178 numeric tokens present) -->

# RAPOR FAZ 3c — Kural öğrenimi: sürekli/topolojik çıktı

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `3b05762`).

## 1. Yöntem

`numcog/rule_learning.py`. Çıktı, girdi ile aynı topolojik kaba kodla temsil edilir: hedef
t ∈ 0..10 → eksen [0,10] üzerinde Gauss (σ=1.5) ya da Termometre vektörü (265 birim). Kayıp
MSE; lr=0.01, 500 epoch, tam batch, erken durma yok. Decode = üretilen vektörün 0..10 ideal
vektörlerine kosinüs argmax. Ana metrik kesin eşleşme, yan metrik ±1. 6 kol × 20 tohum.
Veri: eğitim 10 çift (hedefler 0..8, bitişik), TEST_KOMBINASYON = G1 (1) + G2 (3),
TEST_YENI_N = 4 (n=8,9). Asserts (parite korelasyonu yok, sızıntı yok, G2 izolasyonu, hedefler
bitişik) geçti.

## 2. Özet (ortalama ± std, %95 GA, n=20)

| kol | eğitim | G1 | **G2 (kural)** | G2 ±1 | newn | newn ±1 | op-flip |
|---|---|---|---|---|---|---|---|
| coarse_direct | 0.900 ± 0.000 | 0.000 | **0.000** | 0.000 | 0.250 | 0.750 | 0.222 |
| coarse_kc_gercek | 0.965 ± 0.067 | 0.000 | **0.000** | 0.000 | 0.087 | 0.650 | 0.294 |
| coarse_kc_shuffled | 0.965 ± 0.067 | 0.000 | **0.000** | 0.000 | 0.175 | 0.738 | 0.294 |
| coarse_kc_ablasyon | **0.400** ± 0.000 | 0.000 | **0.000** | 0.000 | 0.188 | 0.812 | **0.000** |
| coarse_kc_ortusme_kontrol | 1.000 ± 0.000 | 0.000 | **0.000** | 0.000 | 0.113 | 0.650 | 0.333 |
| coarse_kc_gercek_termometre | 0.900 ± 0.000 | 0.000 | **0.000** | 0.000 | 0.250 | 0.750 | 0.222 |

Taban çizgileri (G2): hep-n+1 exact=0.000 tol=0.000 · kimlik exact=0.000 tol=1.000 ·
rastgele exact=0.091 tol=0.273.

## 3. H3c.1 (kural) — ÇÜRÜDÜ

Grup 2'de (izole/kural testi) **tüm kollar 0.000** — coarse_kc_gercek dahil. Üstelik ±1
tolerans da 0.000: model op− için n+1'i (ezberlediği op+ sonucunu) üretiyor, hedeften 2 uzakta
kalıyor. Yani model n=1,2,3'te (iki op görülmüş) kaydırmayı yapabiliyor ama **"op− → sola
kaydır" kuralını görülmemiş konjunksiyonlara (n=5,6,7 op−) GENELLEYEMİYOR**. %95 GA [0,0], en
iyi taban çizgisinin (rastgele 0.091, kimlik tol 1.0) ALTINDA. **Kural iddiası çürüdü**; sürekli
çıktı, Faz 3'teki "ezber vs kural" başarısızlığını düzeltmedi.

**Not (güç):** Grup 2 = 3 öğe < 6 → istatistiksel güç DÜŞÜK (ön-kayıtta belirtildiği gibi).

## 4. H3c.3 (biyolojik katkı) — KISMEN DESTEKLENDİ

- Eğitimde coarse_kc_gercek (0.965 [0.936,0.994]) > coarse_direct (0.900 [0.900,0.900]);
  GA'lar örtüşmüyor → anlamlı üstünlük var (eğitimde).
- Ablasyon: ortak 151 KC çıkarılınca eğitim 0.965 → **0.400** (GA örtüşmüyor) → anlamlı çöküş.
  op-flip de 0.294 → **0.000**: ortak hücreler op'un (konjunksiyonun) yaşadığı yer.
- AMA: karıştırılmış (0.965) ve rastgele-örtüşme-kontrol (1.000) gerçekten ayırt edilemez, hatta
  rastgele-örtüşme DAHA iyi. Yani katkı, ortak hücrelerin KİMLİĞİnden değil, ~151 multimodal
  hücrenin VARLIĞINDAN geliyor (Faz 1-3 eğilimi sürüyor).

## 5. H3c.2 (ekstrapolasyon sınırı) — DESTEKLENDİ

TEST_YENI_N kesin doğruluğu düşük (0.087–0.250). coarse_kc_gercek [0.034,0.141], ulaşılabilir
hedef şansını (≈1/9≈0.111) İÇERİYOR → çürütme eşiği sağlandı (başarısızlık beklendiği gibi).
**Ulaşılabilirlik:** eğitim hedefleri 0..8; TEST_NEWN hedefleri {9,7,10,8} — 9 ve 10 yapısal
olarak ulaşılamaz (readout g(9)/g(10)'u hiç üretmeyi öğrenmedi). "Ölü birim" (maks aktivasyon
<0.01) 0 çıktı (σ=1.5 kuyrukları geniş); asıl sınır birim değil, **hedef ARALIĞI**dır.

## 6. Ek ölçümler

- **Op-duyarlılık (op-flip):** model op çevrilince yönünü yalnızca %22–33 oranında değiştiriyor
  (ablasyon: %0). Yani model çoğu n için op'u YOK SAYIYOR — kural öğrenmediğinin doğrudan ölçüsü.
- **Rastgele etiket kontrolü (coarse_kc_gercek):** g2_exact=0.083, newn=0.050 (şans). Gerçek
  görevdeki G2=0.000 rastgele etiketin ALTINDA → model sistematik yanlış (ezberlediği n+1'i
  üretiyor), gürültü değil.
- **Termometre çıktı:** eğitim 0.900, G2 0.000 — Gauss çıktıyla aynı. Çıktı kodunun türü
  başarısızlığı değiştirmiyor (darboğaz çıktı değil, operatör kanalı + konjunktif kodlama).

## 7. Sınırlılıklar

- **Grup 2 = 3 öğe** (istatistiksel güç düşük); kural iddiası yine de net çürüdü (0.000, ±1 de 0).
- Sayı→VPN ve operatör→ALPN atamaları keyfîdir; gerçek olan yalnızca VPN→KC / ALPN→KC kablolaması.
- **Termometre çıktı bir DIŞ YARDIMdır** (elle tasarlanmış); sonucu bağlamanın yeteneği olarak
  yorumlanamaz.
- "Glomerül alt kümeleri" için glomerül etiketi yok; rastgele ayrık ALPN alt kümeleri kullanıldı.
- TEST_NEWN'in 9/10 hedefleri ulaşılamaz (hedef aralığı 0..8); bu, H3c.2'nin yapısal sınırıdır.
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 8. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/rule_learning.py
```
Çıktı: `numcog/results_p3c/` (arms_raw.csv, summary.csv).

**KARAR:** FAZ 4 için bekleniyor (dur — kullanıcı onayı).
