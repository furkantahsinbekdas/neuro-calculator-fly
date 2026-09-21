<!-- Machine translation of `numcog/RAPOR_FAZ_5.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: REVIEW (13 of 548 numeric tokens missing, e.g. 0,00, 0,02242, 0,034, 0,048, 0,05, 0,173, 0,25397, 0,576) -->

# RAPOR FAZ 5 — Connectome yapısal analizi (iki parçalı) ve kapanış

Tarih: 2026-09-20. Durum: tamamlandı. Hipotez ön-kayıtlı (**commit `8ba1376`**, ölçümden ÖNCE).
Yeni kod: `numcog/structural_analysis.py`. Faz 0–4F dosyaları/sonuçları DEĞİŞTİRİLMEDİ.
Kenar tanımı ve eşikler Faz 0/1 ile AYNI: **min_syn=1**, KC = `cell_class="Kenyon_Cell"`,
VPN = `super_class="visual_projection"` → **427 KC × 265 VPN = 1.843 kenar**; ALPN = `cell_class="ALPN"`
→ 4.887 KC × 319 ALPN. Metrikler ikili matris üzerinde, yalnızca en az bir girdisi olan KC'lerde.

---

## 0. Etiket sayımları (ADIM 0 — ölçümden önce)

| küme | n |
|---|---|
| VPN (`super_class=visual_projection`) | **8.038** |
| KC (`cell_class=Kenyon_Cell`) | **5.177** |
| ALPN (`cell_class=ALPN`) | **685** |

Sütun bazında **etiketli / NaN / benzersiz** (`dropna=False`; Faz 0'daki groupby NaN tuzağına karşı):

| küme | sütun | etiketli | NaN | benzersiz |
|---|---|---|---|---|
| VPN | `cell_type` | **8.010** | 28 | **326** |
| VPN | `hemibrain_type` | 6.906 | 1.132 | 196 |
| VPN | `supertype` | 3.264 | 4.774 | 50 |
| VPN | `ito_lee_hemilineage` | 3.272 | 4.766 | 28 |
| VPN | `hartenstein_hemilineage` | 1.261 | 6.777 | 22 |
| VPN | `cell_sub_class` | 28 | 8.010 | 3 |
| KC | `cell_type` | 5.177 | 0 | 11 |
| KC | `hemibrain_type` | **5.177** | 0 | 12 |
| KC | `cell_sub_class` | 4.133 | 1.044 | 2 |
| KC | `supertype` | 5.172 | 5 | 4 |
| KC | `ito_lee / hartenstein_hemilineage` | 5.177 | 0 | 4 |
| ALPN | `cell_type` | 685 | 0 | 182 |
| ALPN | `hemibrain_type` | 667 | 18 | 173 |
| ALPN | `supertype` | 669 | 16 | 118 |

**Hangi sütundan:** VPN için birincil etiket sütunu `cell_type`'tır (8.010/8.038 = **%99.7**
etiketli, 326 tip); `hemibrain_type` VPN'lerde yalnızca %85,9'unda var (1.132 NaN) ve 196 tip verir.
Matristeki 265 VPN'de: `cell_type` **264**, `hemibrain_type` **192**. KC'lerde iki sütun da %100.

**KC alt tipleri (matristeki 427 canlı KC, `hemibrain_type`):**

| alt tip | n | alt-tip analizinde |
|---|---|---|
| **KCg-d** (γ-d) | **286** | ✓ dahil |
| **KCab-p** (αβ-p) | **102** | ✓ dahil |
| KCg-m | 29 | ✗ (<30) |
| KCg-s1 / s2 / s3 | 2 / 2 / 1 | ✗ (<30) |
| KCab-s / KCab-m | 2 / 1 | ✗ (<30) |
| KCa'b'-ap1 / -ap2 | 1 / 1 | ✗ (<30) |

**<30 hücreli alt tipler dışlandı: 8 alt tip, toplam 39 hücre.** Kalan evren: **388 KC**
(KCg-d 286 + KCab-p 102).

**M3 gerçek değeri (doğrulama):** VPN girdili KC = 427, ALPN girdili KC = 4.887, **ikisi = 151** ✓.

## 1. Mühendislik durumu (Faz 4A–4F kapanış özeti)

- **Hesap makinesi (N=81, 4E):** kabul edilen sineklerde 1..9 tüm add/subtract/**multiply/divide = 1.0000** (54/54 tohum, min 1.0000) ve **zincir p^k = 1.0, k=0..81** (17.496 adım, hepsi doğru).
  Bu **yalnızca kalibrasyondan geçen 54/100 tohumda** geçerlidir — 164 girdinin tamamı doğrulanmadan
  sinek reddedilir; **tasarım gereği** çalışan kısım kapının arkasındadır.
- **Ret oranı: %46,0 [36,6 – 55,7]** (kabul %54,0 [44,3 – 63,4]; 100 tohum).
- **N=81'de %95 ölçütü ızgarada SAĞLANMADI:** 4D en iyi %60,0; 4E en iyi **%93,3**; 4F'nin
  σ ∈ {2.0…4.0} × top-k ∈ {80,120} ızgarasında en iyi yine **%93,3** (σ=2.0, top-k=80, dolgulu,
  28/30). H4d.1 ve H4f.1 hipotezleri **çürüdü**.
- **Şu anki çözüm: kalibrasyon kapısı** — kontrolcü tarafı kalite kontrol; kural öğrenme DEĞİL.
- **top-k=120 float32 taşması:** 4 hücrede 30/30 tohum NaN (doğruluk şans düzeyi 2/164 = 0.0122).
  Bu, lr=0.05 + 25.000 epoch + float32 için **sayısal ıraksama**dır; **kapasite bilgisi taşımaz**.
  Bu fazlarda öğrenme kuralı/hassasiyet değiştirilmedi (TASARIM DEĞİŞİKLİĞİ olurdu).
- **İki haneli tasarım uygulanmadı**; 4D'de "tasarım" olarak etiketlendi (onlar/birler ayrı kanal,
  elde/borç kontrolcüde) ve hâlâ yalnızca tasarımdır.

---

## 2. Kod çakışması (ölçülen sayılar)

Özdeş-kod + farklı-etiket **çatışma sayısı** (30 tohum/hücre) ve tablo sonucu (N=81):

| hücre | çatışma (toplam) | rank<164 tohum | tam-doğru | kaynak |
|---|---|---|---|---|
| σ=1.5, top-k=80, dolgusuz | **27** | 19/30 | 18/30 (%60,0) | 4E |
| σ=2.0, top-k=80, dolgulu | **4** | 16/30 | 28/30 (%93,3) | 4F |
| σ=2.5, top-k=80, dolgulu | **8** | 14/30 | 24/30 (%80,0) | 4F |
| σ=3.0, top-k=80, dolgulu | **14** | 18/30 | 22/30 (%73,3) | 4F |
| σ=4.0, top-k=80, dolgulu | **12** | 19/30 | 25/30 (%83,3) | 4F |
| top-k=120 (tüm σ) | 2 – 10 | 11–15/30 | 0/30 (NaN) | 4F |

- **Kapalı form = delta kuralı:** 4E'de yakınsamış en iyi doğrusal sınıflandırıcı ile delta kuralı
  **aynı** doğrulukta (0,9967 = 0,9967) → tavan **öğrenme kuralında değil, kodda**.
- **Kenar hatası yoğunluğu (4E):** 12 başarısız tohumda 16 hatalı girdinin **8'i (%50,0) kenarda**
  (n ∈ {0,1,80,81}); taban oranı %4,88 → **~10×**. Hepsi **sınırın bir adım içi** girdiler:
  (1,+)=3, (80,−)=3, (81,−)=2. **Kırpılan** girdiler (0,−) ve (81,+) hiç hata vermedi.
- **Mekanizma:** hatalı girdilerin komşu kod kosinüsü **0,998** (doğrularda 0,902) → kod çakışması.
  Eksen dolgusu kırpılmayı azalttığı için tabloyu iyileştirir (%60 → %93,3) ama çakışmayı
  **sıfırlamaz** (σ=2.0'da hâlâ 4 çatışma ve 2/30 hatalı tohum).

## 3. Kural vs ezber (Faz 3 / 3c özeti)

| ölçüm | gerçek | shuffle | örtüşme-kontrol | ablas. | termometre |
|---|---|---|---|---|---|
| Faz 3 eğitim (n±1) | 1,000 | 1,000 | 1,000 | 0,667 | 1,000 |
| Faz 3 **combo (tam)** | **0,000** | 0,000 | 0,000 | 0,000 | 0,000 |
| Faz 3 combo (±1) | **1,000** | 1,000 | 1,000 | 1,000 | 0,900 |
| Faz 3c **G2 kural (tam)** | **0,000** | **0,000** | **0,000** | **0,000** | **0,000** |
| Faz 3c yeni-n (±1) | 0,650 | 0,738 | 0,650 | 0,812 | 0,750 |

**Sonuç:** ezber (bitişik hedefler) çalışır; **kural (G2) hiçbir kolda 0,000** ve **gerçek ile shuffle/örtüşme-kontrol ayrışmaz**. Kapsam uyarısı: **Grup 2 = 3 öğe** ve **tek mimari** (feedforward KC + doğrusal okuma, sabit σ/top-k/lr) → sonuç **bu mimariye özgüdür**, genel bir "connectome kural öğrenemez" yargısı **değildir**. Görev davranışının tamamı (sayaç, döngü, durma, geri besleme, hata kapısı) **kontrolcüde**dir; **sinek durum taşımaz**.

---

## 4. Yapısal analiz (M1–M4, Null A/B, 1000 örnek)

**Gözlenen:** kenar=1.843, KC=427, VPN=265 | **M1=0,25376** | **M2=1,42767** (M2 dışı KC=0) |
**M3=151** | **M4=0,57586 bit** (M4 evreni 388 KC, 1.657 kenar).

| test | gözlenen | null (ort ± sd) | fark (etki) | z | p_ham | p_holm | sonuç |
|---|---|---|---|---|---|---|---|
| M1 × Null A | 0,25376302 | 0,25376302 ± 0,00000000 | +5,6e−17 | tanımsız (sd=0) | 0,000999 | 0,005994 | **GEÇERSİZ (dejenere)** |
| **M2 × Null A** | 1,42767 | 1,60091 ± 0,00921 | **−0,17324** | **−18,82** | 0,000999 | 0,005994 | **AYRIŞIR** |
| M1 × Null B | 0,25376302 | 0,25376302 ± 0,00000000 | +5,6e−17 | tanımsız (sd=0) | 0,000999 | 0,005994 | **GEÇERSİZ (dejenere)** |
| **M2 × Null B** | 1,42767 | 1,46132 ± 0,00988 | **−0,03365** | **−3,41** | 0,000999 | 0,005994 | **AYRIŞIR** |
| **M3** | 151 | 165,16 ± 2,60 | **−14,16** | **−5,44** | 0,000999 | 0,005994 | **AYRIŞIR** |
| **M4** | 0,575855 | 0,047847 ± 0,006131 | **+0,528008** | **+86,12** | 0,000999 | 0,005994 | **AYRIŞIR** |

**p tabanı:** 1000 örnek → en küçük ölçülebilir **p = 1/1001 = 0,000999**; altı testin tümü bu tabana dayandığı için Holm düzeltmesi hepsini **6 × 0,000999 = 0,005994** yapar. Yani **p değerleri ölçüm çözünürlüğünde doygun**; ayrım gücü asıl olarak **z ve etki büyüklüğünden** okunmalıdır.

### M1'in dejenere olması — matematiksel ve ölçülmüş

M1 = (Σ_v d_v² − E) / (n(n−1)) olup **yalnızca sütun derecelerine** ve kenar sayısına bağlıdır. Derece-koruyan takas (Null A) ve alt-tip-koruyan takas (Null B) **ikisi de dereceyi birebir korur** → M1 null dağılımında **sabittir**. Ölçülen kanıt (`m1_degeneracy.csv`):

- closed form **0,253763015** vs observed **0,253763020** → absolute difference **4.8e−09**;
- 2,000 null samples with **unique value = 1**, min == max, **sd = 0.00e+00**.

Therefore, the “p_ham = 0,000999” value of M1 is a **float32 rounding artifact**
(|observed − null mean| = 5.6e−17), **this does not constitute evidence of separation**. The mechanical Holm reading
stated “separable”; **this reading was rejected.** This is a **pre-registration design error** (M1,
cannot be tested against a degree-preserving null); the metric/null/threshold was not modified after measurement.

### Hypothesis Results (unsuppressed hidden)

- **H5.1: INVALID — neither supported nor refuted.** The test shows no detectable structural difference (as above
  evidence). The pre-registration suppression criterion (p_adj ≥ 0.05) was technically not provided but this **separation is not quantifiable**; the effect size is **exactly zero**.
- **H5.2: SUPPORTED.** M4 (KCg-d vs KCab-p ↔ VPN `cell_type` mutual information) strongly separates from the null: **+0.528 bits** (0.576 vs 0.048), z = +86.1, p_holm = 0.005994.
- **H5.3: SEPARABLE (unexpected directional expectation).** M3: observed **151**, within-type independence null is **165.16 ± 2.60** → z = −5.44, p_holm = 0.005994. Direction: **over-representation of modal KC’s from expectation** (the number of KC’s with both modalities is below expectation).

**Descriptive Additional Finding:** M2 is **higher than observed in both nulls** (Null A: +0.173 bits;
Null B: +0.034 bits) → VPN-type diversity per KC in the actual connectome is **lower** (type composition is more homogeneous) according to degree-preserving chance.

### Discovery (post-registration; measurement/hypothesis not modified)

1. **M2’s `hemibrain_type` version (only in Null A):** observed **0.87222** (labeled VPN 192/265),
   null A **1.12619 ± 0.02242** → difference **−0.25397**, z ≈ **−11.3**. Same direction as `cell_type` version;
   result is not sensitive to label selection.
2. **M1 degeneration control** (§4) — added as evidence.

### Annotation Rule (applied)

Only **structural difference** was reported. In Phase 1–4E, task performance did not dissociate between the real and shuffle matrix; this structural finding cannot be “contributed to computation” or “evolutionary design” — and therefore it was not measured or interpreted.

---

## 5. CX Data Status (STEP 3 — only present/absent)

- **Searched for:** EPG, PEN, Delta7 cells; neuron/synapse coordinate (x,y,z); neuropil/ROI column
  (PB glomerulus, EB segment); synapse-level separate table.
- **Found (in this data version):**
  - **Cells:** EPG **51**, PEN **42**, Delta7 **42** → total **135** (text match `cell_class/super_class/hemibrain_type/cell_type/cell_sub_class/supertype`); all labeled.
  - **Neuron level coordinate PRESENT:** `annotations_783.tsv` → `pos_x,pos_y,pos_z` and
    `soma_x,soma_y,soma_z`; **135/135** CX cells filled.
  - **Neuropil column PRESENT:** `proofread_connections_783.feather.neuropil`. CX cells touching
    **34.154** edges: **EB 19.884**, **PB 8.376**, NO 2.330, GA_L/R, FB, CRE_R/L, MB_ML_R/L, ATL,
    LAL, IB, ICL… → **PB and EB coarse neuropil label PRESENT**.
  - **PB glomerulus / EB segment (ROI level) column NOT FOUND** — no annotation or connection file with `glomerulus`/`segment`/`roi` column.
  - **Synapse-level separate table NOT FOUND** — connection file is **summarized** with `(pre, post, neuropil)` per `syn_count`; no row/coordinate per synapse.
- Result: **“found/not found” in this data version was recorded; “permanently closed” was NOT indicated.** **No dynamic simulation was performed.**

## 6. Limitations

- **Group 2 = 3 items:** The universe for rule (G2) test is only 3 items → low power and effect size.
- **Single architecture:** feedforward KC code + linear readout, fixed σ/top-k/lr/epoch. Results are **specific to this architecture**; a general judgment like "connectome cannot learn rules" cannot be drawn.
- **Phase 2b post-hoc:** The exploratory diagnostic added after Phase 2 results are observed; it is not a confirming evidence.
- **Phase 4A-2 criterion trivial:** The criterion of ≥0.99 training AND op-sensitivity ≥%95 passed the **reference arm completely** → the criterion was not discriminative; this is why the "correction arms" were weak findings.
- **4E shuffle comparisons n=30 and limited power:** The result "NOT DISTINCT" is not evidence of "no difference"; the shuffle arm was nominally higher (%73.3 vs %60.0) and the GA's were wide (±10–15 points). Single shuffle seed and single overlap-control arm were used.
- **Structural test’s pre-registration error:** M1 is **not testable** against a degree-preserving null (degenerate; §4). This was not corrected after measurement; it was explicitly marked as invalid in the report.
- **p-value resolution:** 1000 samples → p ≥ 0,000999; all six tests were based on the bottom → the discrimination power should be read from z and effect size, not p-values.
- **Edge definition min_syn=1** (same as Phase 0/1, unchanged). A higher synapse threshold (e.g., sniff.circuit’s ≥3) reduces the edge set and changes the results; this was not tested in this phase.
- **Number→VPN and operator→ALPN assignments arbitrary:** only **VPN→KC** and **ALPN→KC** wiring is real data. The thermometer code is an **external helper**.
- **Simulation:** not a live fly; ion channel, neuromodulation, timing and dynamics were not measured.
- **Single connectome example:** hemibrain version 783; individual variation, gender (`side`) and hemisphere differences were not measured in this study.
- **Functional interpretation ban:** structural decompositions were not read as function/computation contribution (§4 rule comment); such a reading requires measurements which are **not available** in this study.

---

## 7. Method and reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py labels        # STEP 0
# STEP 2 (concurrent max 3 processes; shard = 0,1,2):
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py nullA <shard> 3
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py nullB <shard> 3
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py m3    <shard> 3
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py m4    <shard> 3
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py merge          # table + Holm
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py m1check        # EXPLORATORY
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py m2hemi <shard> 3  # EXPLORATORY
.venv/Scripts/python.exe -X utf8 numcog/structural_analysis.py cx             # STEP 3
```

**Shard'lar:** null A/B/m3/m4 ve keşifsel m2hemi 3 shard'da koştu; **her örnek deterministik
tohumla** üretildi (`RandomState(5000 + örnek_no)`) → shard sayısı sonucu değiştirmez; her shard'ın
çıktısı ayrı CSV'ye yazıldı (`nullA_shard0..2.csv`, `nullB_shard0..2.csv`, `m3_shard0..2.csv`,
`m4_shard0..2.csv`, `m2hemi_shard0..2.csv`) ve `merge` bunları birleştirdi.

Çıktılar (`numcog/results_p5/`): `label_columns.csv`, `kc_subtypes.csv`, `m3_observed.csv`,
`observed.csv`, `nullA_shard*.csv`, `nullB_shard*.csv`, `m3_shard*.csv`, `m4_shard*.csv`,
`mx_null_tests.csv`, `m1_degeneracy.csv`, `m2hemi_shard*.csv`, `cx_check.csv`, `cx_neuropil.csv`,
`run.log`.

---

## 8. KAPANIŞ (özet)

1. **Etiketler:** VPN'lerde birincil sütun `cell_type` (%99,7 etiketli, 326 tip); KC alt tipi
   `hemibrain_type` (%100). Matriste KCg-d 286, KCab-p 102; **8 küçük alt tip (39 hücre) dışlandı**.
2. **Mühendislik:** çarpma/bölme 1,0000 **yalnızca kalibrasyondan geçen 54/100 tohumda** (tasarım
   gereği); ret %46,0 [36,6–55,7]; N=81'de %95 ızgarada sağlanmadı (en iyi %93,3); top-k=120 taşması
   sayısal ıraksama (kapasite bilgisi yok); iki haneli tasarım uygulanmadı.
3. **Kod çakışması:** σ=1,5'te 27 çatışma, kenar hatası yoğunluğu %50 (taban %4,88); dolgu çakışmayı
   azaltır ama sıfırlamaz; **kapalı form = delta kuralı** (tavan kodda).
4. **Kural vs ezber:** ezber çalışır, **kural 0,000**; gerçek ile shuffle ayrışmaz; durum kontrolcüde.
5. **Yapısal:** **H5.2 DESTEK** (M4: +0,528 bit, z=+86,1); **H5.3 AYRIŞIR** (M3: 151 vs 165,16 ± 2,60);
   **M2 ayrışır** (gerçek, null'lardan daha az tip çeşitli); **H5.1 GEÇERSİZ** (M1 dejenere).
   Bu ayrışmalar **işlev iddiası değildir**.
6. **CX:** bu veri sürümünde nöron koordinatı ve kaba nöropil (PB/EB) **bulundu**; glomerül/segment
   ROI etiketi ve sinaps-başına tablo **bulunamadı**; dinamik simülasyon yapılmadı.
