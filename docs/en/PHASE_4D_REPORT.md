<!-- Machine translation of `numcog/RAPOR_FAZ_4D.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 140 numeric tokens present) -->

# RAPOR FAZ 4D — N=81 tablo kapasitesi, uzun optimizasyonla (KISA)

Tarih: 2026-09-19. Durum: tamamlandı. Hipotez ön-kayıtlı (commit `4505664`).
**Seçim ölçütü YALNIZCA tablo doğruluğu**; çarpma/bölme testi seçim için KULLANILMADI.

## 1. Yöntem

`numcog/phase4d.py`. N=81, σ=1.5; epoch ∈ {10000, 25000} × lr ∈ {0.01, 0.05} × top-k ∈ {40, 80}
= 8 hücre × 30 tohum. Ölçüt: tohumların ≥%95'i tabloyu %100 öğrenir. Mevcut modüller import
edildi, hiçbiri değiştirilmedi.

## 2. Izgara sonuçları (N=81, 30 tohum)

| epoch | lr | top-k | tam-doğru tohum | eğitim | süre |
|---|---|---|---|---|---|
| 10000 | 0.01 | 40 | 13/30 (%43.3) | 0.9953 | 179 s |
| 10000 | 0.01 | 80 | 15/30 (%50.0) | 0.9957 | 161 s |
| 10000 | 0.05 | 40 | 15/30 (%50.0) | 0.9961 | 137 s |
| 10000 | 0.05 | 80 | 17/30 (%56.7) | 0.9967 | 165 s |
| 25000 | 0.01 | 40 | 15/30 (%50.0) | 0.9961 | 497 s |
| 25000 | 0.01 | 80 | 17/30 (%56.7) | 0.9967 | 669 s |
| 25000 | 0.05 | 40 | 15/30 (%50.0) | 0.9961 | 339 s |
| **25000** | **0.05** | **80** | **18/30 (%60.0)** | 0.9967 | 364 s |

`results_p4d/grid81.csv`.

## 3. H4d.1 — ÇÜRÜDÜ

**Hiçbir hücre ≥%95'e ulaşmıyor**; en iyi hücre %60.0. Optimizasyonu 2.5× uzatmak (10000→25000)
neredeyse hiçbir şey değiştirmiyor: %56.7 → %60.0 (aynı lr/top-k'de 10000 zaten %56.7 veriyordu).
Eğitim doğruluğu **0.9961–0.9967'de plato** yapıyor — yani 164 girdinin ~%0.4–0.5'i HİÇ
öğrenilmiyor. Bu **optimizasyon değil, temsil/kapasite sınırı**dır: N=81'de KC kodu 82 değeri
tam ayıramıyor, birkaç girdi kalıcı olarak karışıyor. (N=40'ta ep10x ile bu sınır kayboluyordu;
N=81'de eşik aşıyor.)

**Karar (ön-kayıtlı):** başarısız → son ölçüm (100 tohum çarpma/bölme) YAPILMADI (pre-registered
koşul sağlanmadı). N=81 bu mimaride/ızgarada **ulaşılamaz**.

## 4. İki haneli YEDEK — TASARIM olarak etiketlendi (bu fazda UYGULANMADI)

9×9=81 için N≥81 gerektiğinden: **onlar ve birler ayrı kanal** — her kanal kendi N=9 çekirdeği
(0..9 tablosu küçük → 4C'de `ep10x` ile %100), **elde/borç ve basamak taşıma TAMAMEN KONTROLCÜDE**.
Sinek hâlâ yalnızca tek adım (n,op)→n±1 yapar; iki basamağı yöneten, taşımayı hesaplayan ve sonucu
birleştiren **kontrolcüdür**. Bu bir **kontrolcü tarafı iş bölümü**dür, sineğin yeteneği değil.

## 5. Sınırlılıklar

- Izgara yalnızca 8 hücre (epoch/lr/top-k); başka bir eksen (ör. daha büyük top-k, N=81 için özel
  kodlama, daha dar σ) denenmedi.
- Hücreler 137–669 s sürdü (uzun-optimizasyon ızgarası pahalı); 30 tohum.
- Sayı→VPN / operatör→ALPN atamaları keyfî; yalnızca kablolama gerçek.
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 6. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/phase4d.py
```
Output: `numcog/results_p4d/grid81.csv`.

**DECISION:** This grid N=81 could not be reached (plato %60, training ~0.997; not optimization but capacity limit). Marked as a two-digit backup design, NOT APPLIED. Waiting for next step (status — user confirmation).
