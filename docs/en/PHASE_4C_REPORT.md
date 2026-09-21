<!-- Machine translation of `numcog/RAPOR_FAZ_4C.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 244 numeric tokens present) -->

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

### Two-Digit BACKUP (DESIGN CHANGE, LABELED)

9×9=81 for N≥81 required, backup: **ones and tens channel** — each channel has its own N=9
core (0..9, small table → ep10x full), **hand/borrow and carry OVERRIDDEN COMPLETELY**.
This is a controller side job division; the fly still only makes ±1 step. (This phase was not applied;
it was only written as a labeled backup.)

## 5. Last Measurement (frozen `ep10x`, 100 seeds)

| measurement | result |
|---|---|
| table full-accurate seed | **99/100** |
| add | **1.000 ± 0.000** |
| subtract | **1.000 ± 0.000** |
| divide | **1.000 ± 0.000** |
| multiply | **0.790 ± 0.000** (same value on all seeds) |
| chain: k ≤ 40 | **1.000** |
| chain: k > 40 | **0.000** (out of range) |

**Chain vs p^k:** p = 1.000, so p^k = 1.000. Measured chain **k ≤ 40 is 1.000**, k > 40 is
0.000. So the only deviation is **the range limit, not an error accumulation** — chains longer than 40
exceed N=40. (Comparison: Phase 4A with p=0.50 → the chain dropped to 0 in k≥12.)

**Explanation of Multiply 0.790 — not an error, but a RANGE:** the product always starts from n=0 and goes up to 9×9=81;
with N=40, the product >40 is 17/81 which is an out-of-range pair. 64/81 = 0.7901 and this
value is **exactly the same** on all seeds — so the core is now flawless, the remaining single limit is **the range**.
In Phase 4B-0, the same 0.790 came from both range limit and core errors; in 4C the core
error **disappeared**.

**Job Division (written):** the fly only makes a single step (n,op)→n±1 and **does not carry state**; the counter,
loop, stop condition, state feedback, and result reading is **in the controller**.

## 6. Hypothesis Evaluation

| Hypothesis | Result |
|---|---|
| H4c.1 malfunction caused by optimization | **SUPPORTED** (ep4x %96.7, ep10x %100, lr0.05 %96.7) |
| H4c.2 edge representation problem | **PARTIALLY** (padding %56.7→%70, but does not reach ≥%95) |
| H4c.3 N=81 is a configuration ≥%95 | **REFUTED** (best %10) → two-digit backup required |
| Success criterion ≥%95 seed full-accurate | **MET** (ep10x %100; 99/100 in last measurement) |

## 7. Limitations

- Errors are due to both the limit and optimization: padding alone was not enough, epoch increase was needed →
  the primary cause is **optimization** (negative margin, correct class is lost).
- N=81 cannot be reached; the two-digit backup was not applied in this phase (labeled backup).
- Number→VPN / operator→ALPN assignments are arbitrary; only the VPN→KC/ALPN→KC wiring is real.
- Arms 30 seeds, last measurement 100 seeds (main measurement).
- Simulation; not a live fly (see `LIMITATIONS.md`, Phase 6).

## 8. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/phase4c.py
```
Output: `numcog/results_p4c/` (diag_seeds.csv, diag_wrong.csv, diag_similarity.csv, arms40.csv,
n81_sweep.csv, final_seeds.csv, final_chain.csv).

**DECISION:** Hardware configuration `ep10x` (N=40). Systematic startup error was due to **optimization** and was removed with epoch ×10; N=81 could not be reached (two-digit backup labels were tagged). Waiting for the next step (stop — user confirmation).
