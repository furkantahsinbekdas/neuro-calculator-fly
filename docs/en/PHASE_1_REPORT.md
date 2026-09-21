<!-- Machine translation of `numcog/RAPOR_FAZ_1.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 274 numeric tokens present) -->

# RAPOR FAZ 1 — Sayı kodlama katmanı

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `26b1445`,
`numcog/HIPOTEZLER.md`, Faz 1 bölümü), ölçümler onlardan sonra yapıldı.

## 1. Yöntem

`numcog/number_coding.py`. Sayı 1-9 → 265 VPN üzerinde Gauss ayarlı aktivasyon:
`a_i(n) = exp(-(n - p_i)² / (2σ²))`. `p_i` = VPN i'nin tercih ettiği sayı; pozisyonlar
`linspace(1,9,265)`, VPN→pozisyon eşlemesi tohumlu permütasyon. **Sayı→VPN ataması keyfîdir;
gerçek olan yalnızca aşağı akış VPN→KC kablolamasıdır.**

Üç kodlama:
- `hash`: sayının deterministik sha256-tabanlı seyrek ikili kodu (yapısız taban çizgisi),
  427 KC uzayında, aktif = 5/10/20.
- `coarse_direct`: 265-boyutlu gerçel Gauss vektörü (KC katmanı YOK).
- `coarse_kc`: gerçek VPN→KC matrisi (427 KC × 265 VPN) + aktivasyon kuralı.

KC aktivasyon kuralları (iki kol):
- **sabit eşik**: (a) eş-zamanlı aktif VPN sayısı ≥ k (k∈{2,3,4}, "count"); (b) aktif
  partnerlerin sinaps toplamı ≥ θ (θ∈{2,3,4}, "syn"). "Aktif VPN" = aktivasyon > 0.5.
- **top-k** (APL-benzeri): en yüksek ağırlıklı-aktivasyonlu k KC (k∈{5,10,20,40}).

Matrisler: `min_syn=1` (tüm kanıtlanmış kenarlar) → **427 KC × 265 VPN** (2.035 kenar);
`min_syn=3` alt matrisi (sniff.circuit eşiği) → 373 KC × 129 VPN (1.055 kenar).
ALPN→KC (referans) = 4.887 KC × 319 ALPN. Ölçüt: kosinüs benzerliği 9×9, Spearman
ρ(benzerlik, |n−m|), aktif KC sayısı, max off-diagonal kosinüs.

## 2. Sonuç — tarama (tohum 0)

| kodlama | σ | kural | param | ρ | aktif KC ortanca | aktif KC min | max off-cos |
|---|---|---|---|---|---|---|---|
| coarse_direct | 0.5/1.0/1.5 | — | — | **−0.987** | (yoğun 265) | — | 0.475–0.948 |
| coarse_kc | 0.5 | count 2 | 2 | −0.315 | 52 | 10 | 0.457 |
| coarse_kc | 1.0 | count 2 | 2 | −0.803 | 111 | 47 | 0.789 |
| coarse_kc | 1.0 | syn 2 | 2 | −0.790 | 243 | 135 | 0.901 |
| coarse_kc | 1.0 | topk 20 | 20 | −0.888 | 20 | 20 | 0.650 |
| coarse_kc | 1.5 | syn 4 | 4 | −0.921 | 244 | 159 | 0.930 |
| coarse_kc | 1.5 | topk 20 | 20 | −0.955 | 20 | 20 | 0.750 |
| coarse_kc | **1.5** | **topk 40** | **40** | **−0.977** | 40 | 40 | 0.850 |
| hash | — | 5/10/20 aktif | — | 0.00 / 0.22 / 0.07 | — | — | 0.00–0.15 |

Tam tablo: `results_p1/sweep.csv`; grafik: `results_p1/rho_by_config.png` +
`active_kc_by_config.png` + ısı haritaları `sim_coarse_direct.png` / `sim_coarse_kc_best.png`.

**Aktif VPN / sayı** (aktivasyon > 0.5): σ=0.5 → 39 (min 20), σ=1.0 → 77 (min 39),
σ=1.5 → 117 (min 59).

## 3. Permütasyon varyansı (E5) — ρ, ortalama ± std, n=20

| kodlama | σ | ρ mean ± std |
|---|---|---|
| coarse_direct | hepsi | −0.987 ± **0.0002** |
| hash (aktif 10) | — | 0.018 ± 0.206 |
| coarse_kc | 0.5 | −0.04…−0.48 ± **0.12–0.21** |
| coarse_kc | 1.0 | −0.33…−0.77 ± 0.07–0.17 |
| coarse_kc | 1.5 | −0.72…−0.92 ± **0.03–0.08** |

Tam tablo: `results_p1/perm_stats.csv`. **E5 kısmen doğrulandı, kısmen çürüdü**: geniş σ'da
(≥1.0) varyans küçük; dar σ'da (0.5) varyans belirgin (std 0.21'e kadar) — çünkü az VPN aktif
olunca sonuç, hangi VPN'in hangi sayıya atandığına (keyfî atama) duyarlı hale geliyor. Bu,
görevdeki "belirgin büyükse ayrıca raporla" durumudur.

## 4. Kontrol: gerçek VPN→KC vs degree-preserving karıştırılmış matris

| σ | kural | ρ gerçek | ρ karıştırılmış |
|---|---|---|---|
| 0.5 | count 2 | −0.315 | −0.437 |
| 0.5 | topk 20 | −0.291 | −0.333 |
| 1.0 | count 2 | −0.803 | −0.833 |
| 1.0 | topk 20 | −0.888 | −0.762 |
| 1.5 | count 2 | −0.905 | −0.928 |
| 1.5 | topk 20 | −0.955 | −0.910 |

Tam tablo: `results_p1/control_shuffle.csv`.

**KRİTİK BULGU:** Gerçek VPN→KC matrisi ile derece-koruyan rastgele matris **istatistiksel
olarak ayırt edilemez** (bazı konfigürasyonlarda karıştırılmış olan daha monotondur).
Yani coarse_kc'nin ρ'su bağlamanın özel yapısından DEĞİL, yukarı akış Gauss kaba kodundan
gelir; VPN→KC katmanı yalnızca genel (generic) bir seyrek genişleme gibi davranır.
"Gerçek görsel devre büyüklük kodluyor" iddiası desteklenmedi.
## 5. İki sayının birlikte sunumu (σ=1.0, VPN düzeyi)

| mod | n1 kurtarma | n2 kurtarma | 81-çift max off-cos |
|---|---|---|---|
| (i) ayrı popülasyonlar | **1.00** | **1.00** | 0.937 |
| (ii) konjunktif çarpım | 0.21 | 0.21 | **1.000** (çökme) |

`results_p1/two_number.csv`. Ayrı popülasyonlar her iki sayıyı da kusursuz korur (her yarı
kendi sayısını bağımsız kurtarır). Konjunktif çarpım `g(n1)·g(n2)`, merkezi (n1+n2)/2 olan tek
bir Gauss'a çöker: **sırayı ve tek tek sayıları kaybeder**, yalnızca toplam/orta noktayı kodlar
((2,3) ile (3,2) birebir aynı koddur → max off-cos = 1.0). Faz 2+ için (i) ayrı popülasyonlar
seçilmelidir.

## 6. Kanal örtüşmesi (VPN + ALPN → aynı KC)

- VPN-hedef KC: 427; ALPN-hedef KC: 4.887; **kesişim: 151 KC** (%35'i γ-d değil, tüm alt tipler).
- Kesişim alt tipleri: **γ = 94, αβ = 55, α'β' = 2**.
- Bu 151 KC'ye düşen ağırlık: VPN **4.365** sinaps, ALPN **2.288** sinaps.

`results_p1/channel_overlap.csv`. **Yorum:** 151 KC hem görsel (VPN) hem koku (ALPN) girdisi
alır — yani "operatör=koku, sayı=görsel" (Faz 3) tasarımının konjunktif multimodal KC üzerinde
buluşabileceği gerçek bir zemin var. Ama kesişim dar (VPN hedeflerinin %35'i, ALPN hedeflerinin
%3'ü) ve VPN ağırlığı bu ortak KC'lerde ALPN'in ~2 katı. Faz 3'te iki kanalın aynı KC üzerinde
çarpışması (interferans) mümkündür; bu ölçülmeli, varsayılmamalı.

## 7. Availability Decision (Pre-written U1 & U2 & U3)

U1: ρ ≤ −0.5
U2: min active ≥ 1 AND median active ≥ 5 · U3: max off-cos < 0.95.

**Result: Out of 30 coarse_kc configurations, 19 meet all three criteria → `coarse_kc`
"AVAILABLE".** Best: σ=1.5, topk=40 (ρ=-0.977, active=40, max off-cos=0.850).

This validates the pre-recorded strategy **(a)** (VPN→KC matrix) in Phase 0;
the backup (b) was not triggered. However, the control in Section 4 showed that this "availability" did not stem from the specific structure of the context: the same degree-preserving random matrix also yields the same result. The decision was given by the criteria (U1/U2/U3) and the criteria were not changed; this does not add an extra interpretation decision, but it affects the interpretation.

## 8. Hypothesis Evaluation

| Hypothesis | Result |
|---|---|
| E1 coarse_direct ρ<−0.9 | SUPPORTED (−0.987) |
| E2 hash \|ρ\|<0.2 | SUPPORTED (20-seed mean 0.018 ± 0.206) |
| E3 coarse_kc, weaker than direct but stronger than hash (−0.9<ρ≤−0.5) | PARTIALLY REFUTED: at a wide σ, ρ ≈ −0.9…−0.98 (close to direct, “weak” not true); at a narrow σ, −0.24…−0.7. |
| E4 fixed threshold leaves little KC, top-k sufficient | SUPPORTED (count k=4 → 4 active at σ0.5; top-k guarantees k values) |
| E5 permutation variance is small | PARTIALLY: σ≥1.0’s small (std≤0.08), σ=0.5’s significant (std≤0.21) |

## 9. Limitations

- **Number→VPN assignment is arbitrary** (in our coding); the only thing that is real is VPN→KC downstream cabling. The control in Section 4 tests exactly this and shows that the context did not add anything to it.
- `min_syn=1` uses all proven edges (including 1-2 synapse weak contacts); ≥3 threshold reduces the matrix to 373×129. The decision was given over 427×265.
- Cosine + Spearman is not a reasonable similarity for sparse binary codes; but the hash base line comparison checks this choice.
- This is a **simulation/measurement**; not a live bee (see `LIMITATIONS.md`, Phase 6).
- The definition of "active KC = k" in top-k is fixed by definition; U2’s scope is the primary constraint for count/syn rules.

## 10. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/number_coding.py
```
All results are under `numcog/results_p1/`: 5 CSV + 4 PNG (heat map + ρ/active-KC graphs).

**DECISION:** `coarse_kc` is available (strategy (a) is preserved), but the control showed that the specific context contribution was not present. Expected for Phase 2 (state — user approval).
