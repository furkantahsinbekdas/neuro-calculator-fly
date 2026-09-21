<!-- Machine translation of `numcog/RAPOR_FAZ_4F.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 326 numeric tokens present) -->

# RAPOR FAZ 4F — N=81: dolgu + σ genişletme (KISA, ön-kayıtlı)

Tarih: 2026-09-20. Durum: tamamlandı. Hipotez ön-kayıtlı (commit `46128e2`).
**Seçim ölçütü YALNIZCA tablo doğruluğu**; çarpma/bölme seçim için KULLANILMADI.
Faz 0–4E dosyaları/sonuçları DEĞİŞTİRİLMEDİ.

## 1. Yöntem

`numcog/phase4f.py`. N=81; **dolgu sabit `lo=-3, hi=N+3`** (4E'nin en iyi dolgusu);
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

**No cells ever reached ≥%95** → **no freeze** → due to pre-recorded decision, **calibration door
was not opened for 100 seed measurements** (`frozen.json = null`). The best cell again **σ=2.0 + padding +
top-k=80 = %93.3**; therefore, **N=81 the table could not be taught to 100% in all seeds in this grid either**.
The calibration door (4E) remains as a solution.

## 5. Safeguards (two independent validations)

1. **One-to-one match with 4E:** The cell of 4F with σ=2.0/top-k=80/padded cell matches **exactly** the cell in 4E’s `grid81_4e.csv`: `full=28`, training `0.9995934959349594` (16 decimal places same).
2. **Ensuring pre-recorded determinism:** In 4E, shard-ed running and merged from the chain
   with **RandomState(2026)**, **3 seeds (15, 43, 71)** were run from scratch; each with **324
   chain lines, 0 different cells → 3/3 EXACTLY SAME** (`sanity_determinism.csv`).
   → 4E’s parallel shard results are reliable.

## 6. Limitations

- **Grid effectively 4 cells:** The entire numerical overflow axis of top-k=120 is empty; the “8 cells”
  expression is formal, σ trend was only tested with 4 points (top-k=80).
- **Numerical overflow is a DESIGN limit, not a capacity limit:** lr≥0.05 + 25000 epoch float32
  delta k rule is drifting in dense codes. This phase **learning rule/precision was NOT changed**
  (changing would be “DESIGN CHANGE”). Therefore, “top-k=120 bad” is not, “top-k=120 could not be measured with this rule”.
- **“In this grid” record:** σ ∈ {2.0…4.0} and top-k ∈ {80,120} were tried; σ<2.0 combinations (in 4E σ=1.0/1.5 padded %83.3), different padding widths, top-k ∈ (80,120) or other optimizations (epoch/lr) were not tried. Therefore, the result “N=81 unreachable” is not, **“≥%95 not in this grid”** is.
- **Single metric table:** Multiplication/division was never run in this phase (no freeze occurred).
- **30 seeds** → GA width ±10-15 points; the difference between %93.3 and %95 is statistically indistinguishable but **due to the pre-recorded threshold of %95, the decision remains the same**.
- Number→VPN / operator→ALPN assignments **arbitrary**; only VPN→KC / ALPN→KC cabling is real data.
  Thermometer code is **auxiliary outside**;
- **Simulation**, not a live bee (see `LIMITATIONS.md`, Phase 6).
- **Run conditions:** machine was heavily loaded; cells ran in 8 parallel processes and each line was written to disk immediately. This is the detail of parallelism execution; **the two safeguards in §5 show that the results of the results did not change**.

## 7. Reproducibility

```bash
cd flyputer
# 8 cells (parallel; each in its own process):
for i in 0 1 2 3 4 5 6 7; do .venv/Scripts/python.exe -X utf8 numcog/phase4f.py cell $i & done
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py merge     # summary + H4f.1 + freeze decision
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py sanity    # 4E determinism ensuring
.venv/Scripts/python.exe -X utf8 numcog/phase4f.py final 0 1 # (does not run because no freeze)
```

CSV: `results_p4f/` → `cell0_s0.csv … cell7_s0.csv`, `grid81_4f.csv`, `grid81_4f_summary.csv`,
`h4f1.csv`, `sanity_determinism.csv`, `frozen.json`, `run.log`.

## 8. DECISION (Summary)

1. **H4f.1 INVALIDATED (top-k=80):** σ array 0.933 → 0.800 → 0.733 → 0.833; not monotonic and
   σ=3.0/4.0 σ=2.0 below. Increasing σ **does not help, it hurts**.
2. **Code conflict σ increases** (4 → 8 → 14 → 12), training accuracy decreases → mechanism is consistent.
3. **top-k=120 axis float32 overflow** could not be measured (30/30 NaN) — not a capacity proof.
4. **No cell ≥%95 → no freezing, no 100 seed measurement done without calibration gate.**
   The best cell remains **σ=2.0 + padding + top-k=80 = %93.3**.
5. **Two scaling passed:** The 4E cell is exactly the same numbers; 3 seeds of the 4E chain are 3/3 exactly the same.
6. **Bird situation does not carry, controller carries.**

Open (next phase decision): N=81 without calibration gate full coverage
(i) either numerical stability is fixed (float64 / smaller lr / normalization) — this is a
**DESIGN CHANGE** and requires new pre-training; (ii) or a **double-digit backup** is implemented
(they/ones separate channel, carry/borrow controller) — labeled as 4D in design, still not implemented.
