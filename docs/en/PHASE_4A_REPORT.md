<!-- Machine translation of `numcog/RAPOR_FAZ_4A.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 153 numeric tokens present) -->

# RAPOR FAZ 4A — Ardışık hesap makinesi (mühendislik; iş bölümü açık)

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `776e964`).

## 1. İş bölümü (AÇIK)

`numcog/calculator.py`. **Sinek çekirdeği** (`FlyCore`) yalnızca tek adım `(n,op) → clip(n±1,0..N)`
yapar (Faz 3c mimarisi: coarse_kc + sürekli Gauss çıktı, MSE, kosinüs decode). **Kontrolcü**
(`CyborgFly`) sayaç, döngü, durma koşulu (güvenlik sınırı), durum geri beslemesi ve sonuç okumayı
taşır. **SİNEK DURUM TAŞIMAZ; KONTROLCÜ TAŞIR.** "Uçuş simülatörü" gibi yeniden adlandırma YOK.
add/subtract = b kez ±1 tick; multiply = b kez toplama; divide = tekrarlı çıkarma + kalan.
Operatör kodu Faz 3'teki gibi (iki ayrık ALPN alt kümesi), değiştirilmedi.

## 2. Kapasite ölçümü (H4a.1)

| N | eğitim doğruluğu (ort ± std) | çıkarım güveni | süre/tohum |
|---|---|---|---|
| 10 | **0.502 ± 0.189** | 0.984 | 0.18 s |
| 20 | 0.196 ± 0.125 | 0.981 | 0.19 s |
| 40 | 0.109 ± 0.091 | 0.977 | 0.28 s |
| 81 | 0.166 ± 0.064 | 0.957 | 0.37 s |

**H4a.1 ÇÜRÜDÜ:** hiçbir N %100'e ulaşmıyor; en iyi N=10'da bile %50. **Kapasite < 10.**
Not: güven %95+ iken doğruluk %50 — model **kendinden emin ama yanlış** (kosinüs decode yanlış
referansı %98 güvenle seçiyor).

## 3. Mekanizma — operatör yıkanıyor

`(n,op+)` ile `(n,op−)` KC kodlarının kosinüs benzerliği **0.88–0.98**; top-k=40'ın **38–39'u ortak**.
Yani operatör (ALPN, yalnızca 151 ortak KC'ye iner) sayı (VPN, 427 KC) karşısında çok zayıf;
top-k=40 global inhibisyon sayıyı seçer, operatörü dışlar. Sonuç: okuma katmanı (n,op+) ve (n,op−)
ayıramaz, ~"kimlik" (n→n) üretir. Bu, sürekli (MSE) çıktının nominal (argmax) çıktıdan daha kırılgan
olduğunu gösterir: Faz 3'ün nominal okuması küçük KC farklarını ayırabilmişti (eğitim 1.0), sürekli
regresyon aynı farkla "kimliğe" çöker.

## 4. Hesap makinesi (N=10) — ÇALIŞMIYOR

| metrik | değer |
|---|---|
| p (tek adım doğruluğu) | 0.502 ± 0.189 |
| multiply doğruluğu (81 çift) | **0.075 ± 0.079** |
| divide doğruluğu | 0.548 ± 0.099 (çoğu a<b→q=0 triviyal; 36/81=0.44 zaten 0) |
| ort. sinek çağrısı / işlem | 7.992 (divide'ın 50-iterasyon güvenlik sınırına takılması) |

**Terminal demosu (hata gözle görülür):**
```
add(3,2):      Tick 1: 3→3 (güven 0.98) · Tick 2: 3→3  → sonuç 3 (beklenen 5)
multiply(2,3): Tick 1: 0→1 · Tick 2..6: 1→1 ...        → sonuç 1 (beklenen 6)
```
+1 adımı 0→1'de çalışıyor ama n=1,2,3'te "kimliğe" takılıp kalıyor (adım adım ilerlemiyor).

## 5. Chain Breakdown (H4a.2) and Noise (H4a.3)

- **H4a.2 PARTIALLY FAILED:** chain accuracy drops to above p^k in small k's (error is not independent; "identity sticking" mode is not random walk, k≥12 drops to 0).  Example: at k=2 acc=0.360 vs p²=0.252; at k=4 0.185 vs 0.064; at k≥12 0.
- **H4a.3 FAILED:** noise curve is not monotonic — 0.0→0.500, 0.05→0.545 (**increasing**), 0.10→0.545, 0.20→0.409, 0.50→0.364, 1.0→0.273. Low noise breaks "identity" collapse and INCREASES accuracy; high noise corrupts.

## 6. Hypothesis Evaluation

| Hypothesis | Result |
|---|---|
| H4a.1 capacity: N≤20 %100, N=40/81 failure | **FAILED**: N=10 also %50; capacity <10 |
| H4a.2 chain ≈ p^k | **PARTIALLY**: deviates from p^k due to "sticking" mode |
| H4a.3 noise decreases monotonically | **FAILED**: low noise increases accuracy (not monotonic) |

## 7. Limitations

- The weakness of the operator (ALPN) channel is the main reason for this result; the operator code is fixed in advance and not modified (task: "operator code remains the same").
- The assignment of Number→VPN and operator→ALPN is arbitrary; only the VPN→KC/ALPN→KC wiring is realistic.
- The output range is 0..N; N≥81 was required for 9×9=81 but capacity is already <10.
- This is a simulation; not a live bee (see `LIMITATIONS.md`, Phase 6).

## 8. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/calculator.py
```
Output: `numcog/results_p4a/` (capacity.csv, calculator.csv, chain_vs_k.csv).

**DECISION:** The calculator does NOT WORK on this core (capacity <10; operator is washed out).
Waiting for Phase 4B (multiplication/division, direct path) or Phase 5 (halt — user confirmation).
