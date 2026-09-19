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

## 7. Kullanılabilirlik kararı (önceden yazılmış U1 & U2 & U3)

U1: ρ ≤ −0.5 · U2: min aktif ≥ 1 VE ortanca aktif ≥ 5 · U3: max off-cos < 0.95.

**Sonuç: 30 coarse_kc konfigürasyonundan 19'u üçünü birden sağlıyor → `coarse_kc`
"KULLANILABİLİR".** En iyi: σ=1.5, topk=40 (ρ=−0.977, aktif=40, max off-cos=0.850).

Bu, Faz 0'da ön-kayıt edilen strateji **(a)** (gerçek VPN→KC matrisi) geçerli kılar;
yedek (b) tetiklenmedi. AMA Bölüm 4'teki kontrol, bu "kullanılabilirlik"in bağlamanın özel
yapısından gelmediğini gösterdi: aynı sonucu derece-koruyan rastgele matris de verir. Karar
ölçütlerle (U1/U2/U3) verildi ve ölçüt değiştirilmedi; bu ek yorum kararı değil, yorumu
etkiler.

## 8. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| E1 coarse_direct ρ<−0.9 | **DESTEKLENDİ** (−0.987) |
| E2 hash \|ρ\|<0.2 | **DESTEKLENDİ** (20-tohum ort. 0.018 ± 0.206) |
| E3 coarse_kc, direct'ten zayıf ama hash'ten güçlü (−0.9<ρ≤−0.5) | **KISMEN ÇÜRÜDÜ**: geniş σ'da ρ ≈ −0.9…−0.98 (direct'e yakın, "zayıf" değil); dar σ'da −0.24…−0.7. |
| E4 sabit eşik az KC bırakır, top-k yeterli | **DESTEKLENDİ** (count k=4 → σ0.5'te 4 aktif; top-k k kadarını garanti eder) |
| E5 permütasyon varyansı küçük | **KISMEN**: σ≥1.0'da küçük (std≤0.08), σ=0.5'te belirgin (std≤0.21) |

## 9. Sınırlılıklar

- **Sayı→VPN ataması keyfîdir** (bizim kodlamamız); gerçek olan yalnızca VPN→KC aşağı akış
  kablolamasıdır. Bölüm 4'teki kontrol tam da bunu test eder ve bağlamanın yapı eklemediğini
  gösterir.
- `min_syn=1` tüm kanıtlanmış kenarları kullanır (1-2 sinapslı zayıf temaslar dahil); ≥3
  eşiği matrisi 373×129'a daraltır. Karar 427×265 üzerinden verildi (görevin açık sayıları).
- Kosinüs + Spearman, seyrek ikili kodlar için tek makul benzerlik değil; ama hash taban
  çizgisiyle karşılaştırma bu seçimi denetler.
- Bu bir **simülasyon/ölçüm**; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).
- top-k'de "aktif KC = k" tanım gereği sabittir; U2'nin kapsama anlamı count/syn kuralları
  için asıl sınayıcıdır.

## 10. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/number_coding.py
```
Tüm sonuçlar `numcog/results_p1/` altında: 5 CSV + 4 PNG (ısı haritası + ρ/aktif-KC grafikleri).

**KARAR:** `coarse_kc` kullanılabilir (strateji (a) korunuyor), ama kontrol bağlamanın özel
katkısının olmadığını gösterdi. FAZ 2 için bekleniyor (dur — kullanıcı onayı).

