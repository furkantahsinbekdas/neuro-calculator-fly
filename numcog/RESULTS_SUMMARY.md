# RESULTS SUMMARY / SONUÇ ÖZETİ (TR/EN)

Her satır bir faz: **soru · hipotez → sonuç · 2-3 anahtar rakam · kaynak · ön-kayıt → sonuç commit'i**.
Rakamlar **mevcut raporlardan/CSV'lerden** alındı; **uydurulmadı**. Dil: **"bu veride, bu modelde,
bu ızgarada"** / **"in this data, in this model, on this grid"**.

| faz | soru | hipotez → sonuç | anahtar rakamlar | kaynak | commit (prereg → result) |
|---|---|---|---|---|---|
| 0 | VPN→KC yapısı | H0.4 **destek** | VPN→KC **265** VPN; wedge etiketi **yok** | `RAPOR_FAZ_0.md` | `364285d` → `3e97777` |
| 1 | sayı kodlama | **destek** | 9×9 kosinüs yapısı; min_syn=3, top-k=40 | `RAPOR_FAZ_1.md` | `26b1445` → `18c7ad4` |
| 2 | "hangisi büyük" | aralık içi **destek**, dışı **çürüdü**, shuffle **ayırt edilemedi** | **0,992 ± 0,037** / **0,208 ± 0,131** | `RAPOR_FAZ_2.md` | `b721fe7` → `10d9b19` |
| 2b | ekstrapolasyon tanısı | **KEŞİFSEL (post-hoc)** | kenar dolgusu/paylaşımlı okuma | `RAPOR_FAZ_2b.md` | `c43a06e` → `5d496e6` |
| 3 | toplama/çıkarma | **destek** | operatör bilgisi kullanılabiliyor | `RAPOR_FAZ_3.md` | `81a90f1` → `0318771` |
| 3c | **kural** öğrenimi | **ÇÜRÜDÜ** | **G2 = 0,000** (tüm kollar) | `RAPOR_FAZ_3c.md` | `3b05762` → `e8227a5` |
| 4A | ardışık hesap makinesi | **çürüdü (çalışmıyor)** | sürekli çıktı "kimlik" üretti | `RAPOR_FAZ_4A.md` | `776e964` → `3940c03` |
| 4A-2 | operatör yıkanması | **destek** (nominal düzeltme) | op-duyarlılık; referans kol **trivial** | `RAPOR_FAZ_4A2.md` | `164d72c` → `eceb466` |
| 4B-0 | çarpma + CX keşfi | **kısmi** | çarpma **0,790** (N=40 **aralık** sınırı) | `RAPOR_FAZ_4B0.md` | `147b852` → `379332c` |
| 4C | N=40 tablo hatası | **ep10x dondu** | hatalar kenarda (n=0,1,38,39,40) | `RAPOR_FAZ_4C.md` | `ea941cd` → `181ddfc` |
| 4D | N=81 kapasitesi | **H4d.1 çürüdü** | %95 yok | `RAPOR_FAZ_4D.md` | `4505664` → `ca10fe3` |
| 4E | kalibrasyon + hesap makinesi | **destek (kapılı)** | kabul **54/100 (%54,0; GA95 [44,3, 63,4])**; add/sub/**mul**/**div = 1,0000**; zincir **17.496 adım** | `RAPOR_FAZ_4E.md` | `2435393` → `73f7f5a` |
| 4F | dolgu + σ ızgarası | **H4f.1 çürüdü**; top-k=120 **taşma** | en iyi **%93,3**; `frozen.json` = **null** | `RAPOR_FAZ_4F.md` | `46128e2` → `2ea285b` |
| 5 | M1–M4 + null | M2/M3/M4 **ayrıştı**; **M1 dejenere (geçersiz)** | **M1 = 0,25376302**, sd=0 | `RAPOR_FAZ_5.md` | `8ba1376` → `6af0820` |
| 6-0 | CX halka geometrisi | **ÇÜRÜDÜ** | H6.1–H6.3 çürüdü | `RAPOR_FAZ_6_0.md` | `13647d9` → `97d181c` |
| 6-0b | spektral halka testi | **ÇÜRÜDÜ** (H6b.2) | H6b.1 literal geçti | `RAPOR_FAZ_6_0b.md` | `193f21c` → `dd6d361` |
| 7-0 | alt ağ seçimi | seçim kuralı uygulandı | **A = CX çekirdek** (N=4.236, E=298.441) | `RAPOR_FAZ_7_0.md` | `5e7956b` → `adef2e2` |
| 7-1 | durum taşıma (tek g) | **"taşıyor" ÇÜRÜDÜ**; gerçek ağ **surrogatlardan kötü** | k=10: **0,252** vs A_w0 **0,227**; farklar −0,10…−0,21 | `RAPOR_FAZ_7_1.md` | `36e52df` → `ccdd1c1` |
| 7-2 | adil rejim (kol başına g) | **H7.7 destek**, **H7.8 kısmen**, **H7.9 destek**; connectome'a özgü **YOK** | g=**40**; k=6 **0,990**, k=8 **0,710**, k=10 **0,227** | `RAPOR_FAZ_7_2.md` | `137b034` → `96b6558` |
| 7-3 | kural/ekstrapolasyon (T3) | **H7.11 destek** (çöktü); **H7.12 çürüdü**; kural ölçütü **geçmedi** | S1-uzak **0,002**, S2 **0,128** (şans 0,50) | `RAPOR_FAZ_7_3.md` | `29bf396` → `379223f` |
| 8 | MB öğrenme + görevler | G0/G1 **geçti**; **H8.1/H8.2/H8.4 destek**; **H8.3 çürüdü**; **"sarsıcı bulgu" YOK** | G1 **0,982**; T1 N≤4 **0,971**; **ER 1,000**; T6a **0,678** | `RAPOR_FAZ_8.md` | `3d7d638` → `2b9b21b` |
| kapanış/1 | hesap bütünlüğü | **34/34 geçti** | sahte çekirdek **0,1235**; sınır dışı **açık hata** | `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` | — (yeni faz) |
| kapanış/2 | arayüz | **geçti** | `/calc` **324/324**; `/chat` **bozulmadı** | `RAPOR_ARAYUZ.md` | — (yeni faz) |
| kapanış/3 | iki haneli girdi | **beklenti desteklendi** | genel **0,9984**; divide **0,9935** | `RAPOR_IKI_HANELI.md` | `d6bd546` → `b6515ef` |

## EN — same table (condensed)

| phase | question | hypothesis → result | key numbers | source |
|---|---|---|---|---|
| 0 | VPN→KC structure | H0.4 **supported** | 265 VPNs; no wedge label | `RAPOR_FAZ_0.md` |
| 1 | number coding | **supported** | 9×9 cosine structure | `RAPOR_FAZ_1.md` |
| 2 | "which is bigger" | in-range **supported**, out-of-range **refuted**, shuffle **indistinguishable** | **0.992 ± 0.037** / **0.208 ± 0.131** | `RAPOR_FAZ_2.md` |
| 2b | extrapolation diagnosis | **EXPLORATORY (post-hoc)** | edge padding / shared readout | `RAPOR_FAZ_2b.md` |
| 3 | add/subtract | **supported** | operator information usable | `RAPOR_FAZ_3.md` |
| 3c | **rule** learning | **REFUTED** | **G2 = 0.000** (all arms) | `RAPOR_FAZ_3c.md` |
| 4A | sequential calculator | **refuted (does not work)** | continuous readout gave "identity" | `RAPOR_FAZ_4A.md` |
| 4A-2 | operator wash-out | **supported** (nominal fix) | reference arm trivially perfect | `RAPOR_FAZ_4A2.md` |
| 4B-0 | multiplication + CX survey | **partial** | 0.790 (N=40 **range** limit) | `RAPOR_FAZ_4B0.md` |
| 4C | N=40 table error | **ep10x frozen** | errors at the edges | `RAPOR_FAZ_4C.md` |
| 4D | N=81 capacity | **H4d.1 refuted** | no cell ≥95% | `RAPOR_FAZ_4D.md` |
| 4E | calibration + calculator | **supported (gated)** | accepted **54/100 (54.0%, 95%CI [44.3, 63.4])**; add/sub/**mul**/**div = 1.0000**; chain **17,496 steps** | `RAPOR_FAZ_4E.md` |
| 4F | padding + σ grid | **H4f.1 refuted**; top-k=120 **overflow** | best **93.3%**; `frozen.json` = **null** | `RAPOR_FAZ_4F.md` |
| 5 | M1–M4 + nulls | M2/M3/M4 **separate**; **M1 degenerate (void)** | **M1 = 0.25376302**, sd=0 | `RAPOR_FAZ_5.md` |
| 6-0 / 6-0b | CX ring geometry | **REFUTED** | H6.1–H6.3, H6b.2 refuted | `RAPOR_FAZ_6_0.md`, `RAPOR_FAZ_6_0b.md` |
| 7-0 | sub-network selection | selection rule applied | **A = CX core** (N=4,236, E=298,441) | `RAPOR_FAZ_7_0.md` |
| 7-1 | state carrying (single g) | **"carries state" REFUTED**; real net **worse than surrogates** | k=10: **0.252** vs A_w0 **0.227** | `RAPOR_FAZ_7_1.md` |
| 7-2 | fair regime (per-arm g) | **H7.7/H7.9 supported**, **H7.8 partial**; no connectome-specific edge | g=**40**; k=6 **0.990**, k=8 **0.710**, k=10 **0.227** | `RAPOR_FAZ_7_2.md` |
| 7-3 | rule/extrapolation (T3) | **H7.11 supported (collapse)**, **H7.12 refuted**; rule criterion **not met** | S1-far **0.002**, S2 **0.128** (chance 0.50) | `RAPOR_FAZ_7_3.md` |
| 8 | MB learning rule + tasks | G0/G1 **passed**; **H8.1/H8.2/H8.4 supported**; **H8.3 refuted**; **no "striking finding"** | G1 **0.982**; T1 N≤4 **0.971**; **ER 1.000**; T6a **0.678** | `RAPOR_FAZ_8.md` |
| closing/1 | calculator integrity | **34/34 passed** | fake core **0.1235**; out-of-range **explicit error** | `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` |
| closing/2 | interface | **passed** | `/calc` **324/324**; `/chat` **unchanged** | `RAPOR_ARAYUZ.md` |
| closing/3 | two-digit input | **expectation supported** | overall **0.9984**; divide **0.9935** | `RAPOR_IKI_HANELI.md` |

**Overall (both versions, in this data, in this model, on this grid):** two things work — a **gated
table-based calculator** (fly = exact `n→n±1`, controller carries the state) and **DAN-gated
KC→MBON plasticity**; a **connectome-specific task advantage was not demonstrated** in any phase.

