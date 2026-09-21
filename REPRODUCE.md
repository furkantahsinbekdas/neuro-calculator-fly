# REPRODUCE — veri, betik → faz eşlemesi, süreler, tek komutlu küçük testler

Dil notu: bu belge operasyoneldir; bilimsel iddialar için `RESULTS_SUMMARY.md` / `PROJE_KAPANIS.md`.

## 0. Ortam

```bash
python --version        # 3.12.10 (ölçüldü)
pip install -r requirements.txt
```

## 1. Veri (zorunlu, depoda YOK)

```bash
bash get_data.sh        # proofread_connections_783.feather (~812 MB) indirir
# annotations_783.tsv (~30 MB) flysim.py ilk çalıştırmada indirir
```
Ayrıntı + lisans: **`DATA.md`** ([VERIFY: FlyWire license terms]).

## 2. TEK KOMUTLU KÜÇÜK TESTLER (hızlı; önerilen ilk adım)

```bash
# (a) hesap makinesi bütünlüğü — 34 kontrol, ~1 s, ağır eğitim YOK
#     (ağırlıklar numcog/fly_weights/ içinde hazır gelir)
python -X utf8 -m numcog.tests.test_calculator_integrity

# (b) arayüz smoke testi — 10 s; SUNUCU ÇALIŞIYOR OLMALI (aşağıdaki 3. adım)
python -X utf8 _calc_smoke.py
```

Beklenen: (a) `KIRMIZI sayisi: 0 / 34`, (b) `KIRMIZI: 0` (bkz. `numcog/RAPOR_HESAP_MAKINESI_BUTUNLUK.md`,
`numcog/RAPOR_ARAYUZ.md`).

## 3. Arayüzü çalıştırma

```bash
python -X utf8 server.py            # http://127.0.0.1:8000
# sağ üst: "🧮 Hesap Makinesi / Calculator"
```

## 4. Ağırlıkları (sineği) yeniden üretme

```bash
python -X utf8 numcog/build_fly.py            # kalibrasyondan geçen ilk tohumu eğitir (~16 s/tohum)
python -X utf8 numcog/build_fly.py 3          # belirli bir tohum (kabul listesinden)
```
`numcog/fly_weights/fly_N81_seed0.npz` (**0.14 MB**) depoda **tutulur** ✓ (<5 MB).

## 5. Bilimsel hattın betik → faz eşlemesi (numcog/)

| faz | betik(ler) | üretir | ölçülen süre (varsa) |
|---|---|---|---|
| 0–1 | `number_coding.py`, `explore_p0*.py` | `results_p0/`, `results_p1/` | — |
| 2 / 2b | `structural_analysis.py`… (`RAPOR_FAZ_2*.md`) | `results_p2/`, `results_p2b/` | — |
| 3 / 3c | `rule_learning.py`, `arithmetic.py` | `results_p3/`, `results_p3c/` | — |
| 4A–4C | `calculator.py`, `operator_diagnosis.py`, `phase4c.py` | `results_p4a*`, `p4b0`, `p4c` | — |
| 4D–4F | `phase4d.py`, `phase4e*.py`, `phase4f.py` | `results_p4d`, `p4e`, `p4f` | 4E hesap/zincir: **~18 s/tohum** (`results_p4e/run.log`) |
| 5 | `structural_analysis.py` (M1–M4) | `results_p5/` | — |
| 6-0 / 6-0b | `cx_geometry.py`, `cx_spectral.py` | `results_p6_0*` | — |
| 7-0 | `reservoir_discovery.py` | `results_p7_0/` (+ `scan_cache.npz`, **depoda yok**) | tarama ~41 s |
| 7-1 | `reservoir_run.py` | `results_p7_1/` | **174 dk** (165 tohum-kol) |
| 7-2 | `reservoir_fair.py` | `results_p7_2/` | **53 dk** (80 tohum-kol) |
| 7-3 | `reservoir_rule.py` | `results_p7_3/` | **80 dk** (80 tohum-kol) |
| 8 | `mb_learning.py` | `results_p8/` | **11 dk** (140 tohum-kol) |
| kapanış | `fly_calc.py`, `two_digit_probe.py`, `tests/` | `results_release/`, `fly_weights/` | bütünlük **1 s**; iki haneli **349 s** |

Komutların tam hali her fazın raporunun "Yeniden üretilebilirlik" bölümündedir
(ör. `RAPOR_FAZ_7_2.md` §6, `RAPOR_FAZ_8.md` §6).

## 6. Depoda TUTULMAYAN ara çıktılar (`.gitignore`)

`numcog/results_p7_0/scan_cache.npz` (87 MB), `results_p7_1/arms_cache.npz` (12 MB),
`results_p7_2/arms_raw_cache.npz` (4.5 MB), `results_p8/mb_cache.npz` (0.3 MB) — **hepsi betiklerle
yeniden üretilir**.

## 7. Bilinen tuzaklar (yeniden üretirken)

- **`-X utf8` gerekli** (Türkçe karakterler Windows konsolunda `charmap` hatası verir — AŞAMA 3'te
  yaşandı).
- Faz 4x matrisleri **`min_syn=1`**, Faz 1/7x/8 **`min_syn=3`** ile kurulur → **kenar sayıları
  karşılaştırılamaz** (`DATA.md` §4).
- Faz 4F `results_p4f/frozen.json` = **null** (hiçbir hücre %95'i geçmedi) → 4F sonrası "donmuş"
  hesap makinesi **yoktur**; çalışan hat **4E**'dir.
