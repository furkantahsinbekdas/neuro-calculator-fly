<!-- Machine translation of `numcog/RAPOR_FAZ_4B0.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 227 numeric tokens present) -->

# RAPOR FAZ 4B-0 — Central complex keşfi + çarpma düzeltmesi (keşif; model kodu YOK)

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `147b852`).

## 1. Yöntem

`numcog/explore_4b0.py`. Yeni model kodu yok; Faz 4A-2'nin `NominalFlyCore`'u (N=40) ve
`CyborgFly` kontrolcüsü import edilip kullanıldı, hiçbir eski dosya değiştirilmedi.

## 2. A) Çarpma ölçümü (N=40 nominal çekirdek, 20 tohum)

| ölçüm | sonuç |
|---|---|
| (i) a,b ∈ 1..6 (çarpım ≤36) | 0.790 ± 0.400 |
| (ii) aralık İÇİ (çarpım ≤40): 1280 çift | 0.780 ± 0.406 |
| (ii) aralık DIŞI (çarpım >40): 340 çift | 0.000 ± 0.000 |
| (iii) hatalı +1 adım girdileri (n) | n=0 (2025), n=1 (3000), n=17 (494) — **%100'ü bu 3 n'de** |

**(i) H4b0.1 ÇÜRÜDÜ:** a,b ≤6 çarpma 1.000 değil 0.790. Sebep aşağıda (tek adım hataları).
**(ii) H4b0.2 DESTEKLENDİ:** aralık içi yüksek (0.780), aralık dışı sıfır (çarpım >40 → N=40 dışı).
**(iii) H4b0.3 DESTEKLENDİ:** hatalar homojen değil; tek adım hataları **7 girdide toplanıyor**.

**Tek adım hatalarının tam listesi** (20 tohumda toplam 13 hata / 1640 adım = %0.8):
`(0,+)` 1/20 · `(1,+)` 3/20 · `(3,+)` 1/20 · `(17,+)` 1/20 · `(36,+)` 1/20 · `(39,−)` 3/20 ·
`(40,−)` 3/20. Yani hatalar **alt/üst sınır** (0,1,39,40) ve birkaç iç n'de (3,17,36).

**Neden çarpma %79?** Çarpma her zaman n=0'dan başlar. `(0,+)` veya `(1,+)` adımı bir tohumda
bozuksa o tohumun **TÜM** çarpmaları baştan yanlış gider. ~5/20 tohum bu sınıfta olduğundan
çarpma ≈0.79'a düşüyor — hata tek adımda %0.8 ama **sistematik olarak zincirin başına denk geliyor**.

## 3. B) Central complex keşfi

**NaN tuzağı (boş kolonlar açıkça sayıldı, 139.248 satır):** cell_type 1.528 · hemibrain_type
105.977 · supertype 105.403 · cell_sub_class 113.420 · cell_class 31.730 · top_nt 602. Yani
CX hücreleri **cell_type / hemibrain_type** sütunlarında işaretli (supertype boş).

| tip | sayı | cell_type değerleri | top_nt |
|---|---|---|---|
| **EPG** | 51 | EPG 47, EPGt 4 | acetylcholine 51 |
| **PEN** | 42 | PEN_b(PEN2) 22, PEN_a(PEN1) 20 | acetylcholine 41, serotonin 1 |
| **Delta7** | 42 | Delta7 42 | glutamate 41, acetylcholine 1 |

**(H4b0.4 DESTEKLENDİ:** üç tip de mevcut.) **(H4b0.6 DESTEKLENDİ:** işaretler literatürle
uyumlu — EPG/PEN kolinerjik **uyarıcı**, Delta7 glutamaterjik **inhibitör**.)

**Bağlantı matrisleri (kenar / sinaps / medyan / pre-nöron):**

| pre → post | kenar | sinaps | medyan | pre |
|---|---|---|---|---|
| EPG → PEN | 663 | 6.852 | 6 | 50 |
| EPG → Delta7 | 1.009 | 3.798 | 2 | 51 |
| PEN → EPG | 698 | 9.753 | 9 | 42 |
| **PEN → Delta7** | **5** | **5** | 1 | 5 |
| Delta7 → EPG | 369 | 1.966 | 3 | 42 |
| Delta7 → PEN | 296 | 2.715 | 4 | 42 |
| EPG→EPG / PEN→PEN / Delta7→Delta7 | 630 / 1.122 / 1.086 | 3.107 / 6.795 / 3.354 | | |

**Kritik:** classic speed modelindeki **PEN→Delta7 bağlantısı yok denecek kadar az (5 kenar)**.
**(H4b0.5 ÇÜRÜDÜ / DOĞRULANAMADI):** anotasyonlarda **wedge/glomerül numarası YOK** — yalnızca
"EPG" ve "EPGt" var (hemibrain_type'te de aynı; synonyms boş). Bu yüzden wedge sayısı (beklenti
16–18) ve dairesel komşuluk doğrudan çıkarılamıyor.

**Halka yapısı bağlantıdan çıkarılmaya çalışıldı (iki-hop EPG→PEN→EPG):**
- EPG→PEN: 582/2142 dolu (%27); her EPG ortalama **11.4** PEN'e gidiyor.
- PEN→EPG: 608/2142 dolu; her PEN ortalama **14.5** EPG'ye gidiyor.
- İki-hop EPG→EPG: **1616/2601 dolu (%62)** ve 51 EPG'nin **49'unda öz-iki-hop** var.

Yani hücre düzeyinde EPG↔PEN bağlantısı **yoğun ve yapısız** — halka imzası (seyrek, kaydırılmış
komşuluk) **görünmüyor**. Halka, wedge düzeyinde bir yapıdır ve wedge etiketi olmadan
kurulamıyor.

## 4. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H4b0.1 a,b ≤6 çarpma = 1.000 | **ÇÜRÜDÜ** (0.790; tek adım hataları zincir başına denk geliyor) |
| H4b0.2 aralık içi/dışı ayrı | **DESTEKLENDİ** (0.780 / 0.000) |
| H4b0.3 hatalar belirli (n,op)'de toplanır | **DESTEKLENDİ** (7 girdi; %0.8; sınırdaki n'ler) |
| H4b0.4 EPG/PEN/Delta7 anotasyonlarda var | **DESTEKLENDİ** (51/42/42) |
| H4b0.5 wedge halkası ~16–18 | **DOĞRULANAMADI** (wedge etiketi yok; bağlantı yoğun) |
| H4b0.6 işaretler literatürle uyumlu | **DESTEKLENDİ** (EPG/PEN ACh+, Delta7 Glu−) |
| H4b0.7 halka simülasyonu mümkün | **HAYIR** (aşağıda) |

## 5. KARAR (H4b0.7) — halka simülasyonu MÜMKÜN DEĞİL

Gerekçeler:
1. **Wedge/glomerül etiketi yok** → EPG hücreleri halkanın hangi pozisyonunda bilinmiyor; halka
   topolojisi kurulamıyor (bağlantıdan da çıkmıyor: iki-hop %62 yoğun).
2. **PEN→Delta7 klasik bağlantısı yok** (5 kenar) → hız integratorünün kanonik üçlü devresi
   (EPG→PEN→Delta7→EPG) eksik; Delta7 daha çok EPG'ye doğrudan (369 kenar) ve PEN'e (296 kenar)
   bağlanıyor.
3. Hücre düzeyi EPG↔PEN bağlantısı yoğun/yapısız (halka imzası yok).

**Elde OLAN:** ağırlıklar (bağlantı matrisleri) ve işaretler (EPG/PEN ACh+, Delta7 Glu−) tam.
Yani **halkasız, hücre düzeyinde** bir CX modeli (ör. EPG↔PEN↔Delta7 dengeli bir devre) kurulabilir;
ama bu "halka/hız integratorü" DEĞİL, topografyasız bir devre olur. **Halka iddiası bu veriyle
kurulamaz.** Bu adımda dinamik simülasyon yok.

## 6. Sınırlılıklar

- Wedge etiketi, EB arbor pozisyonu veya glomerül haritası veride yok; bu yüzden H4b0.5 ve ring
  kararı bu eksikliğe dayanıyor.
- N=40 çekirdeğinin tek adım hataları (%0.8) çarpma doğruluğunu zincir başından vuruyor; bu bir
  çekirdek-kapasite sorunu, çarpma algoritmasının değil.
- Sayı→VPN / operatör→ALPN atamaları keyfî; yalnızca kablolama gerçek.
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 7. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/explore_4b0.py
```
Output: `numcog/results_p4b0/` (multiply.csv, multiply_error_steps.csv, cx_edges.csv).

**DECISION:** Wedge simulation not possible (wedge label missing; PEN→Δ7 missing; connection unstructured).
Waiting for next step (pause — user confirmation).
