# RAPOR FAZ 7-0 — Rezervuar keşfi + çerçeve ön-kaydı (DİNAMİK DENEY YOK)

Tarih: 2026-09-20. Durum: tamamlandı. Ön-kayıt **ölçümden ÖNCE** commit edildi (**`5e7956b`**).
Yeni kod: **`numcog/reservoir_discovery.py`**. Faz 0–6-0b dosyaları/sonuçları DEĞİŞTİRİLMEDİ.
**Eşzamanlı süreç: 1. Tüm hesaplar float64. Bağlantı dosyası parça parça (258 batch × 65.536 satır)
okundu. DİNAMİK SİMÜLASYON YAPILMADI.** Sonuç dili: **"bu veri sürümünde, bu seçim kuralıyla"**.

## 0. Etiket sayımları (EN BAŞTA; NaN'lar sayıldı, `dropna=False`)

| küme | n | `top_nt` dolu | `known_nt` dolu | **imza** (+/−) |
|---|---|---|---|---|
| **KC** (`cell_class=Kenyon_Cell`) | 5.177 | 5.177 | 5.177 | **+5.177 / −0** |
| **MBON** (`hemibrain_type` MBON*) | 96 | 96 | 68 | +51 / −45 |
| **DAN-benzeri** (PAM*/PPL1*/PPL2*) | 331 | 331 | 331 | +331 / −0 |
| **APL** | 2 | 2 | 2 | +0 / −2 |
| **DPM** | 2 | 2 | 2 | +2 / −0 |

- **NT kaynağı (tüm annotation, 139.248 hücre):** `known_nt` **71.337**, `top_nt` **67.335**,
  **hiçbiri 576**.
- **Ham `top_nt`:** acetylcholine 86.193 · glutamate 24.875 · gaba 19.171 · dopamine 5.909 ·
  serotonin 2.282 · NaN 602 · octopamine 216.
- **Ham `known_nt`:** NaN 51.411 · acetylcholine 33.222 · **histamine 9.795** · glutamate 9.261 ·
  `acetylcholine; acetylcholine` 7.335 · **`gaba-negative` 4.913** · gaba 4.188 ·
  `acetylcholine; sNPF; acetylcholine, sNPF` 4.133.
- **VERİ GÖZLEMİ (önemli):** KC'lerde `top_nt` çoğunlukla **"dopamine"** (5.172/5.177) görünüyor;
  bu **biyolojik beklentiyle çelişir** (KC kolinerjik). Ön-kayıtlı kural `known_nt`'yi öncelikli
  kıldığı için KC imzası **acetylcholine → +1** olur. Bu bir **veri gözlemidir**; kural değiştirilmedi.
- **İmza ayrıştırma (uygulama detayı, ön-kayıt varsayımına sadık):** çok-değerli etiketler `;`/`,`
  ile bölünür; `negative` içeren belirteçler **belirsiz** sayılır; listede olmayanlar (histamin, sNPF)
  **belirsiz**tir → o kenar imzasız kalır. Bu nedenle "histamin (9.795 hücre)" gibi etiketler
  **işaretsiz**dir ve raporda **varsayım/eksik** olarak sayılır.

## 1. Adım A — v1 kapanış özeti

`numcog/V1_OZET.md` (yeni ölçüm yok): kapılı hesap makinesi **54/100** (ret %46,0 [36,6–55,7]),
**durum kontrolcüde**, gerçek ile shuffle **görevde ayırt edilemedi**, yapısal ayrışmalar M2–M4
(M1 **dejenere**), **CX halkası bu veri sürümünde kurulamadı**, ve tüm sınırlılıklar.
Yasak ifadeler kullanılmadı; "bu veride / bu yöntemle / bu ızgarada" dili kullanıldı.

## 2. Adım B — Ön-kayıtlı Faz 7 çerçevesi (özet)

Tam metin `HIPOTEZLER.md` Faz 7 bölümünde (commit `5e7956b`, **hiçbir dinamik deney çalıştırılmadan**):

- **Model:** `x_{t+1} = (1−a)·x_t + a·tanh(g·W·x_t + B·u_t)`, **a = 0,5**; **W** = syn_count ağırlıklı,
  **NT tahminine göre işaretli (VARSAYIM)**, **spektral yarıçapı 1'e normalize**; **g** serbest.
- **Giriş:** iki kanal (+1/−1), tohumla seçilen **k nöronluk** ayrık küme; darbe 1 adım, aralık 5 adım.
  **Okuma:** ridge (λ yalnızca validasyonda). **g yalnızca validasyonda; test seçim için kullanılmaz.**
- **Kollar:** (1) gerçek, (2) derece-korunmuş shuffle, (3) ağırlık-shuffle, (4) Erdős–Rényi,
  (5) tekrarlama yok (W=0), (6) "ideal sayaç" (dış yardım, üst sınır).
- **Görevler:** T1 durum taşıma (k=1..K, s∈[−8,8], gap testi), T2 Jaeger MC,
  T3 ekstrapolasyon (eğitim |s|≤6, test s∈{7..10} + görülmemiş başlangıç; **≥30 öğe**),
  T4 yankı-durum/g taraması.
- **Başarı ölçütleri:** k=10'da **≥%90** VE kol (5)'ten **%95 GA ayrık** iyi; "connectome'a özgü" =
  (2)/(3)/(4)'ten GA ayrık üstünlük (yoksa "**taşıyor ama connectome'a özgü değil**" yazılır).
- **Beklentiler/çürütme:** H7.1, H7.2, H7.3, H7.4 — her biri için çürütme eşiği yazılı; **Holm**;
  **30 tohum**, ort ± std + **%95 GA**.

## 3. Adım C — Alt ağ adayları (bu veri sürümünde)

Tarama: **16.847.997 satır**, **138.639 benzersiz hücre**, **79 nöropil anahtarı**, önbellek 91 MB
(parça parça okuma; tepe bellek düşük tutuldu). Kenar tanımı: pre→post, ağırlık = `syn_count` toplamı.

| aday | alt-graf hücre | kenar | sinaps | karşılıklı oran | **en büyük SCC** | ρ(işaretli) | ρ(\|W\|) | kenar imzası +/−/belirsiz |
|---|---|---|---|---|---|---|---|---|
| **A: CX çekirdek (EB/PB/FB/NO)** | **4.236** (küme 4.259) | **298.532** | 1.339.370 | **0,399** | **3.711** | 66,56 | 142,61 | **0,514 / 0,486 / 0,0003** |
| A_geniş (duyarlılık: +GA/CRE/LAL/IB/ICL) | 19.033 | 1.039.675 | 3.871.768 | 0,237 | 18.916 | 83,59 | 150,84 | 0,611 / 0,389 / 0,0001 |
| **B: MB (KC/MBON/DAN/APL/DPM)** | 5.608 | 523.784 | 1.216.234 | 0,345 | 5.608 | 108,75 | 164,59 | **0,970 / 0,030 / 0** |

**C (kontrol; nöropil-kısıtlı rastgele SCC):** 79 uygun nöropil (≥1.000 satır); **30 rastgele
çekilişte SCC medyanı = 3.514** (min 248, **max 36.396**), hücre medyanı 4.929.
Deterministik referans: **ME_L** (hücre 36.841, kenar 2.426.813, **SCC 36.438**).

**Seçim kuralı (ön-kayıtlı; sonuca bakarak değiştirilmedi):** uygun = SCC ∈ [300, 5000];
**A uygunsa A, değilse B**; ikincil = kalan uygun aday.
→ **A (SCC 3.711) UYGUN → BİRİNCİL = A (CX çekirdek)**; A_geniş (18.916) ve B (5.608)
**uygun değil** → **ikincil aday YOK**.

**İki yapısal gözlem (test değil):** (i) CX çekirdeğinin SCC boyutu (3.711), **rastgele
nöropil-kısıtlı kontrollerin medyanına (3.514) çok yakın** — bu veride "bu büyüklükte tekrarlama"
tek başına ayırt edici değil; (ii) **B (MB) alt grafı %97 uyarıcı** (KC'ler ve DAN'lar +, APL
yalnızca 2 hücre) → işaretli W neredeyse **tek işaretli**; A ise **dengeli** (+0,514/−0,486).

## 4. Adım D — KARAR (kod yok; yalnızca ölçümden)

**Faz 7-1 için uygun alt ağ (bu veri sürümünde, bu seçim kuralıyla):** **A — CX çekirdek
(EB/PB/FB/NO)**.

- **Boyut:** alt-graf **N = 4.236** hücre, **E = 298.532** kenar (1.339.370 sinaps);
  **en büyük SCC = 3.711** (hücrelerin %87,6'sı). Durum uzayının **SCC mi yoksa tüm alt-graf mı**
  olacağı **Faz 7-1'in ön-kaydında** sabitlenmelidir (burada sabitlenmedi).
- **Maliyet tahmini (analitik; dinamik ÇALIŞTIRILMADI):**
  - Bellek: seyrek CSR ≈ **~4 MB** (E×(4 B indeks + 8 B değer) + satır işaretçisi) + durum vektörü
    34 KB → rahat. Yoğun matris (4.236² ≈ 18 M float64 ≈ 143 MB) **gerekmiyor**.
  - Adım başına: **298.532 çarpma-toplama** + 4.236 `tanh` ≈ 0,3 M işlem; numpy'de seyrek matvec
    (`np.bincount`) ile **mertebe ~0,3–2 ms/adım** (**tahmin**; 7-1'de ölçülecek).
  - Bir yörünge (T = 500 adım): **~0,15–1 s**.
  - 7-1 bütçesi (kaba): 30 tohum × 6 kol × ~2,4×10⁵ adım ≈ **4,3×10⁷ adım** → **~4–25 saat**
    tek çekirdek (tahmin) → 7-1 ön-kaydı **tohum/yörünge bütçesini** açıkça yazmalıdır.
- **Doğrusal kararlılık (yalnızca analiz):** normalize edilmiş W'de ρ = 1 → **kararlı bölge g < 1**;
  ham matriste eşdeğeri **g < 0,0150** (A). g taraması bu sınırın **civarında** yapılmalıdır.
- **Elle ayarlanacak parametreler:** **g** (yalnızca validasyon), **k** (giriş kümesi boyutu),
  **giriş nöronlarının seçimi**, **ridge λ** (yalnızca validasyon), T2 örnek sayısı, T1 zincir
  uzunluğu K. **Sabitlenmiş olanlar:** a = 0,5, darbe genişliği 1 adım, darbeler arası 5 adım,
  T3'te ≥30 öğe ve eğitim |s| ≤ 6.
- **Giriş nöron seçiminin keyfîliği (açıkça):** aday içinde **hangi k nöronun** giriş alacağı
  **veriden gelmiyor**; **tohumlu rastgele** seçilecek ve sonuçlar **tohumlar arası dağılım** olarak
  raporlanacak (7-1 ön-kaydında da böyle yazılmalı).
- **Kaç NT etiketi tahmin/varsayım:** **tüm işaret ataması bir VARSAYIMDIR** (7 sınıf → ±1).
  A'da kenarların **%99,97'si** işaret aldı (**91 kenar imzasız** = %0,03); hücre düzeyinde
  **4.258/4.259** etiketli. Tüm annotation'da **576 hücre** hiç etiketsiz; **histamin (9.795)** gibi
  etiketler listede olmadığı için **işaretsiz**dir. **KC'lerde `top_nt`="dopamine"** gözlemi
  (5.172/5.177) bu etiketlerin **tahmin** olduğunu ve **hatalı olabileceğini** gösterir.

## 5. Sınırlılıklar

- **Hiçbir dinamik deney çalıştırılmadı**; bu rapordaki her şey **yapısal**dır. T1–T4 sonuçları,
  başarı ölçütleri ve H7.1–H7.4 **beklentidir**, ölçüm değil.
- **Aday tanımları birer seçimdir:** CX için çekirdek nöropil kümesi {EB,PB,FB,NO} ve "hem pre hem
  post" koşulu; MB için hücre tipi listesi (KC/MBON/PAM/PPL1/PPL2/APL/DPM). Duyarlılık varyantı
  (A_geniş) raporlandı ama **kural değiştirilmedi**.
- **SCC sınırı [300, 5000] ön-kayıtlı bir seçimdir:** B (MB) **5.608** ile sınırın **hemen üstünde**
  kaldı; sınır farklı olsaydı B uygun olurdu. Kural ölçümden önce sabitlendi, **değiştirilmedi**.
- **İşaret ataması varsayımdır** (§4): histamin gibi sınıflar işaretsiz, `gaba-negative` belirsiz;
  KC `top_nt` anomalisi etiket güvenilirliğini sınırlıyor.
- **Spektral yarıçap bir tahmindir:** güç iterasyonu (float64); işaretli asimetrik matriste baskın
  özdeğer karmaşık olabilir → ρ(işaretli) **alt sınır** olabilir; ρ(|W|) Perron–Frobenius gereği
  **üst sınırdır**. İkisi de raporlandı.
- **C kontrolü** rastgele **tek nöropil** çekilişidir (30 örnek), boyut-eşleşmiş bir null değil;
  karşılaştırma **tanımlayıcıdır**, test değildir.
- **Tek connectome örneği** (hemibrain 783); bireysel/cinsiyet varyasyonu yok.
- **Maliyet tahminleri analitiktir**, ölçülmemiştir (dinamik deney yasağı).
- **İşlev/hesaplama katkısı ve evrimsel tasarım iddiası YASAK** (Faz 5 yorum kuralı).
- **Uygulama notları (şeffaflık):** (i) NT ayrıştırması ilk koşuda katı whitelist ile yapıldı ve
  KC'lerde **imza 0** çıktı; `known_nt` çok-değerli olduğu için ayrıştırma düzeltildi (ön-kayıt
  varsayımına sadık kalınarak) ve **tüm ölçüm yeniden çalıştırıldı** — ilk hatalı log
  `run_ilk.log` olarak saklandı, **hiçbir ölçüt/hipotez değiştirilmedi**;
  (ii) `np.where` dtype hatası giderildi; (iii) hücre sayısı raporlaması (alt-graf vs CX kümesi)
  netleştirildi.

## 6. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/reservoir_discovery.py scan     # parça parça tarama (~41 s)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_discovery.py metrics  # adaylar + C + seçim (~20 s)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_discovery.py all      # ikisi
```

Çıktılar (`numcog/results_p7_0/`): `label_counts.csv`, `neuropil_counts.csv`, `candidates.csv`,
`c_draws.csv`, `neuropil_scc.csv`, `run.log` (+ ilk koşunun NT-hatalı logu `run_ilk.log`).
Ara önbellek **`scan_cache.npz` (91 MB)**: depo hijyeni için **commit'ten çıkarıldı**
(`git rm --cached`, commit `70bbb0f`); dosya diskte kalır ve `scan` ile **~41 s'de yeniden
üretilebilir**. Çalışma ağacında **tek izlenmeyen (untracked) dosya** budur.

## 7. ÖZET

1. **Etiketler (§0):** KC 5.177 (+5.177/−0), MBON 96 (+51/−45), DAN-benzeri 331 (+331/−0),
   APL 2 (−2), DPM 2 (+2); NT kaynağı known_nt 71.337 / top_nt 67.335 / yok 576.
   **VERİ GÖZLEMİ:** KC'lerde `top_nt`="dopamine" (5.172/5.177) — biyolojik beklentiyle çelişir;
   ön-kayıtlı kural gereği KC imzası **+1** (acetylcholine).
2. **Faz 7 çerçevesi ön-kayıtlı** (`5e7956b`): sızıntılı hız modeli (a=0,5), işaretli + normalize W,
   ridge okuma (λ yalnızca validasyonda), g yalnızca validasyonda, 6 kol, T1–T4, başarı ölçütleri,
   H7.1–H7.4 + çürütme eşikleri, Holm, 30 tohum, %95 GA.
3. **Adaylar (bu veri sürümünde):** **A (CX çekirdek)** N=4.236, E=298.532, **SCC=3.711**, ρ=66,56,
   işaret dengesi **+0,514/−0,486**; **A_geniş** N=19.033, SCC=18.916; **B (MB)** N=5.608,
   E=523.784, SCC=5.608, **%97 uyarıcı**.
4. **C kontrolü:** 30 rastgele nöropil çekilişinde SCC medyanı **3.514** (min 248, max 36.396) →
   A'nın SCC'si bu dağılımın **ortasında**; tekrarlama büyüklüğü tek başına ayırt edici değil.
5. **Seçim kuralı uygulandı:** **BİRİNCİL = A (CX çekirdek)**; **ikincil aday YOK**.
6. **Karar:** 7-1 için uygun tek aday **A**; bellek ~4 MB, adım başına ~0,3 M işlem (tahmin);
   **g, k, giriş seçimi, λ** elle ayarlanacak; **giriş nöron seçimi keyfî ve tohumla rastgele**;
   NT işaretleri **varsayım**. **Dinamik deney yapılmadı.**


