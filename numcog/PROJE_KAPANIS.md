# PROJE KAPANIŞI (v1 + v2) — ölçülenlerin tam dökümü

Tarih: 2026-09-20. Bu belge **yeni ölçüm içermez**; mevcut raporlara/CSV'lere dayanır ve her rakam için
**kaynak dosya** verilir. Dil kuralı: **"bu veride, bu modelde, bu ızgarada"**.
Yasak ifadeler kullanılmadı: "kanıtladık", "kusursuz", "sinek matematik yapıyor", "çok haneli aritmetik",
"dil mantığı", "connectome özel bir üstünlük sağlıyor".

## 1. Hedefler ve durumları

| # | hedef | durum (bu veride, bu modelde, bu ızgarada) | kanıt |
|---|---|---|---|
| 1 | FlyWire connectome'unu **sayı/kod** için kullanmak | **Kısmen:** VPN→KC kablolaması ile 9×9 kosinüs yapısı kurulabiliyor; **sayı→VPN ataması keyfî** | `RAPOR_FAZ_1.md` |
| 2 | **Karşılaştırma** ("hangisi büyük") | Aralık içi **0,992 ± 0,037**; **aralık dışı 0,208 ± 0,131**; gerçek↔shuffle **ayırt edilemedi** | `RAPOR_FAZ_2.md` |
| 3 | **Kural** öğrenimi (n±1) | **Ezber çalışıyor; kural (G2) tüm kollarda 0,000** | `RAPOR_FAZ_3.md`, `RAPOR_FAZ_3c.md` |
| 4 | **Hesap makinesi** (kapılı, N=81) | **Çalışıyor:** add/sub/mul/div **1,0000**; zincir p^k=1,0 (k=0..81) — **ama yalnızca kalibrasyondan geçen 54/100 tohumda** | `RAPOR_FAZ_4E.md`, `results_p4e/final81_seeds.csv` |
| 4b | N=81'de **%95 tablo** ölçütü | **Sağlanmadı** (en iyi **%93,3**); ızgara genişletmesi de geçmedi | `RAPOR_FAZ_4F.md`, `results_p4f/frozen.json` = **null** |
| 5 | Yapısal analiz (M1–M4) | M2/M3/M4 **ayrışıyor**; **M1 dejenere** | `RAPOR_FAZ_5.md` |
| 6 | CX **halka geometrisi** | **Kurulamadı** (H6.1–H6.3, H6b.2 çürüdü) | `RAPOR_FAZ_6_0.md`, `RAPOR_FAZ_6_0b.md` |
| 7 | **Durumu ağ taşısın** (rezervuar) | **Hayır.** Adil g'de k≤8'de taşıyor (k=6: **0,990**) ama **k=10'da çöküyor** ve **surrogatlardan üstün değil** | `RAPOR_FAZ_7_1.md`, `RAPOR_FAZ_7_2.md` |
| 8 | **Kural/ekstrapolasyon** (T3) | **Yok.** A_gercek S1-uzak **0,002**, S2 **0,128** — **şansın altında** (şans 0,50) | `RAPOR_FAZ_7_3.md` |
| 9 | MB'de **biyolojik öğrenme kuralı** | **Çalışıyor** (G1: 0,982; T1 N≤4: ort 0,971); **ama connectome'a özgü üstünlük YOK** (ER eşit/daha iyi) | `RAPOR_FAZ_8.md` |

**Özet hüküm:** *bu veride, bu modelde, bu ızgarada* **çalışan** iki şey var — (i) **kapılı tablo
hesap makinesi**, (ii) **DAN-kapılı KC→MBON plastisitesi**; **gösterilemeyen** şey ise
**connectome'a özgü bir görev üstünlüğü**dür.

## 2. Faz faz ÖLÇÜLENLER (anahtar rakamlar + kaynak)

| faz | ne ölçüldü | anahtar rakam | kaynak dosya |
|---|---|---|---|
| 0 | nöropil/etiket yapısı | VPN→KC **265** VPN'de, γ-özel küçük yol; wedge/glomerül etiketi **yok** | `RAPOR_FAZ_0.md` |
| 1 | sayı kodlama | 9×9 kosinüs yapısı; `min_syn=3`, top-k=40 | `RAPOR_FAZ_1.md`, `results_p1/` |
| 2 | "hangisi büyük" | **0,992 ± 0,037** (aralık içi) / **0,208 ± 0,131** (dışı) | `RAPOR_FAZ_2.md` |
| 3 / 3c | ezber vs kural | ezber ✓; **kural 0,000** | `RAPOR_FAZ_3.md`, `RAPOR_FAZ_3c.md` |
| 4A–4C | hesap çekirdeği | n±1 tablosu; N=40 **aralık** sınırı; **ep10x** dondu | `RAPOR_FAZ_4A.md`, `4C.md` |
| 4D–4F | N=81 kapasitesi | en iyi **%93,3**; **H4d.1/H4f.1 çürüdü**; 4F `frozen=null` | `RAPOR_FAZ_4D.md`, `4E.md`, `4F.md` |
| 4E | kalibrasyon + hesap | kabul **54/100 (%54,0, GA95 [44,3, 63,4])**; add/sub/**mul**/**div = 1,0000**; zincir **17.496 adım** | `RAPOR_FAZ_4E.md`, `results_p4e/` |
| 5 | M1–M4 + null | M2 **1,42767**, M3/M4 ayrışıyor; **M1 = 0,25376302 (dejenere)** | `RAPOR_FAZ_5.md` |
| 6-0/6-0b | CX halka | **kurulamadı**; soma↔PEN ~**80°** uyumsuzluk | `RAPOR_FAZ_6_0.md`, `6_0b.md` |
| 7-0 | alt ağ seçimi | **A = CX çekirdek** (N=4.236, E=**298.441**); C kontrol medyan SCC 3.514 | `RAPOR_FAZ_7_0.md` |
| 7-1 | rezervuar (tek g) | k=10/H=10: A_gercek **0,252** vs **A_w0 0,227**; surrogatlar **daha iyi** (−0,10…−0,21) | `RAPOR_FAZ_7_1.md` |
| 7-2 | adil rejim (kol başına g) | A_gercek g=**40** (ızgara sınırı); k=6 **0,990**, k=8 **0,710**, **k=10 0,227**; fark kapandı (p_holm=0,34) | `RAPOR_FAZ_7_2.md` |
| 7-2 | spektrum | gerçek W: **1 yavaş mod / 239 GB bileşen**; A_derece **50/50** | `results_p7_2/spec_summary.csv` |
| 7-3 | kural testi (jitter) | S1-uzak **0,002**, S2 **0,128** (şans 0,50); T3-P **0,508** | `RAPOR_FAZ_7_3.md` |
| 8 | MB öğrenme | G0 ✓ (MBON **96**, k=**12**, KC→MBON **35.204**); G1 **0,982**; T1 N≤4 **0,971**; **ER 1,000** | `RAPOR_FAZ_8.md`, `results_p8/` |
| kapı | hesap bütünlüğü | **34/34 geçti**; sahte çekirdek ort. **0,1235**; sınır dışı **açık hata** | `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` |
| kapı | arayüz | `/calc` **324/324** beklenen davranış; `/chat` **bozulmadı** | `RAPOR_ARAYUZ.md`, `_calc_smoke.py` |
| kapı | iki haneli girdi | genel **0,9984** ≥ %99 (add/sub/mul **1,0000**; divide **0,9935**) | `RAPOR_IKI_HANELI.md` |

## 3. ÖLÇÜLEMEYENLER / YAPILAMAYANLAR (açık liste)

| ne | neden |
|---|---|
| **Çok haneli aritmetik** | **Uygulanmadı** — iki haneli (onlar/birler) tasarımı yazıldı ama **hiç kodlanmadı**; sonuç uzayı **0..81** |
| **N=81'de %95 tablo ölçütü** | Bu ızgarada **sağlanmadı** (en iyi %93,3); `results_p4f/frozen.json` = **null** |
| **CX halka geometrisi** | Bu **veri sürümünde kurulamadı** (H6.1–H6.3, H6b.2 çürüdü) |
| **Kural öğrenimi (n±1)** | Tüm kollarda **0,000** (Grup 2 = 3 öğe) |
| **Durumun ağda taşınması** | k≤8'de var (adil g'de), **k=10'da yok**; surrogatlardan **üstün değil** |
| **Connectome'a özgü üstünlük** | **Hiçbir fazda gösterilemedi** (Faz 2, 3, 3c, 4E, 5, 7-1, 7-2, 7-3, 8) |
| **T3 kural/ekstrapolasyon** | **Çöktü** (şansın altında) |
| **T7 (MB kural testi)**, **T6c** | **KEŞİFSEL etiketliydi ve UYGULANMADI** |
| **İki haneli ızgara taraması** | Yalnızca **tek ayar** (ön-kayıtlı tasarım) ölçüldü |
| **Canlı sinek** | **Simülasyon**; tek connectome (hemibrain 783) |
| **Ollama/LLM yolu ölü mü?** | **Doğrulanamadı** — `server.py`/`game_loop.py` referans ediyor → `[VERIFY]` |
| **E-posta sızıntısı** | Takipli dosyalarda **yok**; **git yazar e-postası geçmişte** (`furkantahsinb@gmail.com`) → düzeltme = geçmişi yeniden yazmak → **kullanıcı kararı** |
| **Geçmişteki büyük blob'lar** | **87,15 MB** + **11,12 MB** (kaldırıldı ama **geçmişte duruyor**) → `[karar: bırak / rewrite]` |

## 4. Sinek KENDİ BAŞINA ne yaptı, KONTROLCÜ yardımıyla ne yaptı?

| iş | sinek | kontrolcü (Python) |
|---|---|---|
| `n → n±1` tek adımı (0..81) | **tamamen sinek** (eğitilmiş KC→okuma) ✓ | — |
| sayaç, döngü sayısı, durma koşulu | — | **kontrolcü** ✓ |
| add/sub/mul/div akışı | yalnızca tek adımlar | **kontrolcü** ✓ |
| **kalan** (bölme) | — | **kontrolcü** ✓ |
| çıktının okunması/raporlanması | — | **kontrolcü** ✓ |
| durum (hangi sayıda olduğumuz) | **TAŞIMAZ** | **kontrolcü** ✓ |

**Dinamik kanıt:** aynı ifade için **çağrı sayısı** gerçek ve **sahte** çekirdekte **aynı**
(`3+5`→5, `6x7`→42), ama **sonuç farklı** (`3+5`: 8 vs 68) → döngüyü kontrolcü kurar, **cevabı
çekirdek verir** ✓ (`RAPOR_HESAP_MAKINESI_BUTUNLUK.md` §2.B2).

**Bilimsel karşılığı:** hesap makinesi bir **tablo makinesidir** (`n±1` tam doğru), **aritmetik
öğrenmez**; MB tarafında öğrenme **vardır** ama **kablolamadan bağımsız** çalışır.

## 5. YAKALANAN ARTEFAKTLAR / HATALAR (kaynaklı)

| # | artefakt | faz | nasıl yakalandı | commit / kaynak |
|---|---|---|---|---|
| 1 | **NaN groupby tuzağı** | Faz 0 | NaN'ların sayımdan düşmesi → sonraki fazlarda `dropna=False` standardı | `RAPOR_FAZ_5.md:19`, `RAPOR_FAZ_7_0.md` §0 |
| 2 | **MSE (sürekli) okuma kırılganlığı** | 4A | sürekli çıktı "kimlik" (n→n) üretti → nominal okumaya geçildi | `RAPOR_FAZ_4A.md:32` |
| 3 | **Yetersiz epoch/lr** | 4C | epoch ×4/×10 ile sınandı (H4c.1) | `HIPOTEZLER.md:359`, `RAPOR_FAZ_4C.md` |
| 4 | **Dejenere M1 testi** | 5 | null A/B'de M1 **sd=0** → **GEÇERSİZ** | `RAPOR_FAZ_5.md:128-139` |
| 5 | **float32 taşması (NaN)** | 4F | top-k=120 hücrelerinde **30/30 tohum** NaN → "monotonluk" yanılgısı | `RAPOR_FAZ_4F.md:42-45` |
| 6 | **Ölü birim** | 3c | maks aktivasyon < 0,01 olan birimler | `RAPOR_FAZ_3c.md:55` |
| 7 | **ρ=1 normalizasyon artefaktı** | 7-1 → 7-2 | "gerçek ağ surrogatlardan kötü" sonucu **rejim artefaktı** çıktı | `RAPOR_FAZ_7_2.md` §4 |
| 8 | **Bileşen/yapı farkı uyarısı** | 7-2 | gerçek W: **239 GB bileşen**, ER: **2** | `results_p7_2/spec_summary.csv` |
| 9 | **Izgara sınırı** | 7-2 | seçilen g = **40 (uç)** → "dışarıda daha iyi olabilir" kapatılamadı | `RAPOR_FAZ_7_2.md` §5 |
| 10 | **np.polyfit tekil sistem** | 7-3 | sabit hedefli satırda SVD çökmesi | commit **`3e243a9`** (ölçüm öncesi) |
| 11 | **jitter duyarlılığı** | 7-3 | T3-P **0,508** vs 7-2 sabit aralıkta **0,990** | `RAPOR_FAZ_7_3.md` §3 |
| 12 | **`np.clip(..., out=mask)` kopya hatası** | 8 | pilot tüm ayarlarda **0,525** → W negatife iniyordu | `RAPOR_FAZ_8.md` §5, commit **`a69a8d9`** |
| 13 | **Dejenere `divide` tabanı** | Kapanış/1 | sahte çekirdekte `divide` **0,4815** → **36/81 çift çekirdeği hiç çağırmıyor** | `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` §3 |
| 14 | **Kontrolcü `q < 50` sınırı** | Kapanış/3 | `81/1 → 50`, `60/1 → 50` → iki haneli bölmede %0,65 sapma | `RAPOR_IKI_HANELI.md` §4 |
| 15 | **İkame test yanılgısı** | Kapanış/2 | ilk smoke'ta 36 kırmızı: test "0'a kırp" bekliyordu, arayüz **reddediyor** | `RAPOR_ARAYUZ.md` §4 |
| 16 | **Yanlış commit'lenen önbellekler** | 7-0/7-1 | fark edilip `git rm --cached`; **geçmişte kaldı** | `70bbb0f`, `838aae1`, `RELEASE_PREFLIGHT.md` §3 |
| 17 | **`np.bool_` toplama hatası** | — | **bu repoda kaynağı bulunamadı** | **[VERIFY: hangi faz/commit]** |

## 6. SINIRLILIKLAR (v1+v2 tamamı için)

**Tek connectome** (hemibrain 783) · **simülasyon** · **sayı→VPN ve operatör→ALPN ataması keyfî**
(gerçek olan yalnızca **kablolama**) · **NT işaretleri VARSAYIM** (KC = +1/ACh sabit) ·
**kalibrasyon kapısı %46 tohumu reddeder** (kabul %54,0; GA95 [44,3, 63,4]) · **N=81'de %95 tablo
ölçütü yok** (en iyi %93,3) · **iki haneli tasarım uygulanmadı** · **Grup 2 = 3 öğe**, tek mimari
(feedforward KC + doğrusal okuma) · **Faz 2b post-hoc**; **4A-2'de referans kol tam puan aldı**
(ölçüt trivial); **M1 testi dejenere** · **shuffle karşılaştırmaları n=30/20, güç sınırlı**
("ayırt edilemedi" ≠ "fark yok") · **MB bölmeleri ÇIKARIM** (k=12, dengesiz; gerçek anatomi değil) ·
**valans varsayımı test edilmedi**, **US tip-içi seçici değil** · **tek plastisite kuralı biçimi**
(yalnız LTD) · **Faz 7-2/7-3/8 KEŞİFSEL-yeniden-test** (HARKing riski kabul) · ızgaralar sabit.

## 7. İDDİA ETMEDİĞİMİZ ŞEYLER

1. **"Sinek matematik yapıyor"** — hayır: çekirdek yalnızca `n→n±1`; **sayaç/döngü/kalan kontrolcüde**.
2. **"Çok haneli aritmetik"** — **yok**; iki haneli tasarım **uygulanmadı**.
3. **"Dil mantığı"** — `numcog/` içinde **dil modeli yok** (kelime sınıflandırma **ayrı** `flyputer/` uygulaması).
4. **"Connectome özel bir üstünlük sağlıyor"** — **görevlerde ayrışmadı**; hiçbir fazda gösterilemedi.
5. **"Kural öğreniyor"** — kural testleri (G2/T3) **şansın altında**.
6. **"Durumu ağ taşıyor"** — k≤8'de kısmen (adil g'de), k=10'da **hayır**; surrogatlardan **üstün değil**.
7. **Biyolojik doğruluk** — NT işaretleri **varsayım**, bölmeler **çıkarım**, giriş seçimi **keyfî**.

## 8. GELECEK ÇALIŞMA (hepsi **YAPILMADI**)

- **Etiketli CX verisi** (wedge/glomerül ROI, sinaps-başına tablo) → halka geometrisi yeniden denenebilir.
- **Nöromodülasyon**: DAN dışı modülatörler (OA/5-HT), dopamin dinamiği, **LTP + LTD birlikte**.
- **Sinaptik güvenilmezlik** (stokastik yayılım) ve **zaman sabiti ızgarası**.
- **İki haneli (onlar/birler) tasarımının uygulanması** → çok haneli aritmetiğin **tek yolu**.
- **MBON→DAN ve DAN→KC geri beslemesinin** öğrenmeye katılması (şu an yalnız ileri yol).
- **Hemibrain dışı** bir connectome ile çapraz doğrulama.

