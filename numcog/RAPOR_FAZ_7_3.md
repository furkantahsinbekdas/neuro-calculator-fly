# RAPOR FAZ 7-3 — Kural/ekstrapolasyon testi (T3), 6 adımlık rejimde
Tarih: 2026-09-20. Ön-kayıt **ölçümden ÖNCE** commit edildi: **`29bf396`** ("Faz 7-3 ek ön-kayıt +
kod + tasarım tabanları"); teknik düzeltme (np.polyfit tekil sistem) **`3e243a9`** — **ölçüm
başlamadan önce**. Yeni kod: **`numcog/reservoir_rule.py`**; çıktılar **`results_p7_3/`**.
Faz 0–7-2 dosyaları/sonuçları **değiştirilmedi** (o dizinlere yazılmadı).
**Eş zamanlı süreç: 1. float64. Seyrek W × yoğun durum matrisi. Tohum başına ayrı CSV.**
Dil kalıbı: **"bu veride, bu modelde, bu ızgarada"**.

> ### ⚠ KEŞİFSEL-YENİDEN-TEST BEYANI (ölçütler GEVŞETİLMEDİ)
> Bu faz, **7-2 sonuçları görüldükten sonra** yazılmıştır (7-2: adil g ile **k≤8'de durum taşıma
> 0,99/0,71** ama **k=10'da çöküş**). HARKing riski **kabul edilir ve azaltılamaz**.
> **Ölçütler 7-1/7-2 ile aynı katılıkta tutuldu; hiçbir eşik gevşetilmedi.** Sonuç, 7-2'nin
> "connectome'a özgü üstünlük yok" bulgusunu değiştirmez; yalnızca **kural boyutunu** ekler.

## 0. Parametreler ve etiketler (EN BAŞTA)

| öğe | değer | kaynak |
|---|---|---|
| model | `x_{t+1}=(1−a)x_t+a·tanh(g·W·x_t+B·u_t)`, a=0,5; işaretli W (NT **VARSAYIM**), ρ(W)=1; I1 giriş; gürültü 1e-3×std | 7-1/7-2 (kilitli) |
| kollar | A_gercek, A_derece, A_er, A_w0 + **ideal sayaç (DIŞ YARDIM referansı, simüle edilmedi)** | 7-3 |
| **donmuş (g, amp)** | A_gercek **40,0/1,0** · A_derece **20,0/1,0** · A_er **20,0/1,0** · A_w0 **40,0/0,5** | **7-2 Adım 1** (`results_p7_2/frozen_config.csv`); **YENİ IZGARA YOK** |
| ızgara sınırı | A_gercek'in g'si 7-2'de ızgaranın **üst ucunda (40)** seçilmişti; g>40 **denenmedi** | 7-2 |
| dizi | **k=6 darbe**, ±1, koşan toplam [−8,8]; net toplam **s ∈ {−6,−4,−2,0,2,4,6}** | 7-3 |
| **JİTTER (SAPMA)** | darbeler arası aralık her darbede **{4,5,6}'dan RASTGELE** (7-1/7-2'de **sabit 5**) | 7-3 (etiketli) |
| bekleme | **H=10 birincil**; H=0 ve H=20 ikincil; **T3-H**: okuma H=10'da eğitilir, H=0/20'de test (KEŞİFSEL) | 7-3 |
| bölmeler | eğitim **300**, validasyon **150** (aynı s aralığı), test **60 öğe/s** | 7-3 |
| okuma | **skaler ridge + en yakın ÇİFT tam sayıya yuvarlama (BİRİNCİL)**; nominal sınıf (ikincil, **eğitimde görülmemiş sınıfı üretemez**); λ yalnızca validasyonda | 7-3 |
| tohum | **20** | 7-3 |

### Tasarım tabanları (ÖLÇÜMDEN ÖNCE; `design_baselines.csv`)

| bölme | öğe | sınıf | şans | "en sık sınıf" |
|---|---|---|---|---|
| S1 (ALL) | 4.800 | 4 | 0,2500 | 0,2500 |
| **S1 uzak (\|s\|=6)** | 2.400 | **2** | **0,5000** | **0,5000** |
| **S2 (s=±6)** | 2.400 | **2** | **0,5000** | **0,5000** |
| P (ALL) | 6.000 | 7 | 0,1429 | 0,1497 |

**Kritik uyarı:** uzak/±6 testlerinde **yalnızca iki olası toplam** vardır → **"hep +6 de" bile %50
alır**; ölçüt bu yüzden **şansın (0,50) GA-ayrık ÜSTÜ VE ≥%50** olarak katı tutuldu.


## 1. Jitter sapması (T3'e özel) ve veri

- **SAPMA:** 7-1/7-2'de darbeler **sabit 5 adım** arayla geliyordu (t = 0,5,10,15,20,25). 7-3'te
  **darbeler arası aralık her darbede {4,5,6}'dan rastgele** çekilir (jitter). Bu **etiketli bir
  tasarım sapmasıdır** ve **yalnızca** T3'ün ölçülebilmesi içindir: s=±6 durumunda **tek bir işaret
  örüntüsü** vardır (6/6 darbe aynı yönde) → sabit aralıkla **tek test öğesi** olurdu; jitter ile
  **3⁵=243** farklı zamanlama → **≥50 farklı öğe** üretilebilir. **Tüm** kümeler (eğitim/validasyon/
  test) aynı jitter kuralıyla üretilir; örüntüler **global benzersizdir** (assert'li).
- Bundan sonraki tüm cümleler **"bu veride, bu modelde, bu ızgarada"** kaydıyla okunmalıdır:
  **sabit aralıklı** 7-1/7-2 sonuçlarıyla doğrudan karşılaştırma **yapılmaz** (farklı girdi dağılımı).
- Bölmeler ve öğe sayıları: eğitim **300**, validasyon **150** (eğitimle aynı s aralığı),
  test **60 öğe/s** → S1 690 + S2 570 + P 1000 = **2.260 dizi/tohum**; yörünge **≤51 adım**.

## 2. Sonuçlar — T3-S1 / T3-S2 (BİRİNCİL: H=10, 20 tohum)

Kesin doğruluk = **skaler ridge + en yakın ÇİFT tam sayıya yuvarlama**. Test seçimde **kullanılmadı**.

| bölme | kol | **kesin ± %95 GA** | ±2 | nominal | "takılı" | PCA artık | doygun | aktif |
|---|---|---|---|---|---|---|---|---|
| **S1 ALL** (şans 0,25) | **A_gercek** | **0,024 ± 0,022** | 0,264 | 0,000 | **0,80** | 0,167 | 0,266 | 0,680 |
| | A_derece | 0,001 ± 0,002 | 0,198 | 0,000 | **0,97** | **0,580** | 0,633 | 0,976 |
| | A_er | **0,108 ± 0,067** | 0,592 | 0,000 | 0,43 | **0,100** | 0,953 | 1,000 |
| | A_w0 | 0,000 ± 0,000 | 0,000 | 0,000 | 1,00 | 0,000 | 0,000 | 0,000 |
| **S1 uzak (\|s\|=6)** (şans **0,50**) | **A_gercek** | **0,002 ± 0,002** | 0,117 | 0,000 | 0,76 | 0,171 | | |
| | A_er | 0,065 ± 0,056 | 0,385 | 0,000 | 0,30 | 0,106 | | |
| **S2 (s=±6)** (şans **0,50**) | **A_gercek** | **0,128 ± 0,064** | 0,601 | 0,000 | 0,65 | 0,158 | | |
| | A_er | **0,230 ± 0,082** | 0,898 | 0,000 | 0,37 | 0,089 | | |
| | A_derece | 0,005 ± 0,005 | 0,431 | 0,000 | 0,92 | 0,548 | | |

**Hedef-bazlı ayrıntı (H=10, kesin):** S1 s=−6/−4/+4/+6: A_gercek 0,003/0,047/0,042/0,002;
A_er 0,072/0,152/0,150/0,057. S2 s=±6: A_gercek 0,121/0,136; A_er 0,224/0,237.

**Bulgu:** **BÜTÜN KOLLAR ŞANSIN ALTINDA** (S1: 0,001-0,108 < 0,25; S1-uzak ve S2: ≤0,230 < 0,50).
A_gercek'in tahminleri **eğitim aralığının ucuna yapışıyor** (takılı oranı 0,65-0,80 ≥ 0,5) ve
nominal okuma **yapısal olarak 0,000** (eğitimde görülmemiş sınıfı üretemez ✓ beklenen).

### İkincil bekleme değerleri (aynı okuma kuralı, H=0 ve H=20)

| bölme | kol | H=0 | H=10 (birincil) | H=20 |
|---|---|---|---|---|
| S1 ALL (şans 0,25) | A_gercek | **0,361 ± 0,105** | 0,024 ± 0,022 | 0,000 ± 0,000 |
| | A_er | 0,431 ± 0,109 | 0,108 ± 0,067 | 0,015 ± 0,010 |
| | A_derece | 0,106 ± 0,043 | 0,001 ± 0,002 | 0,000 ± 0,000 |
| S2 (şans 0,50) | A_gercek | **0,660 ± 0,072** | 0,128 ± 0,064 | 0,007 ± 0,008 |
| | A_er | **0,720 ± 0,087** | 0,230 ± 0,082 | 0,059 ± 0,029 |

→ **Dikkat (ikincil, KEŞİFSEL değil; ön-kayıtlı):** H=0'da **kısmi ekstrapolasyon şansın ÜSTÜNDE**
(S1 0,361 > 0,25; S2 0,660 > 0,50; hiçbiri GA-ayrık değil), ama **bekleme ile çöküyor** (H=10 ve H=20).
Yani *bu veride, bu modelde, bu ızgarada* ekstrapolasyon **bekleme olmadan** kısmen mümkün,
**bekleme sonrası** imkânsız.

## 3. T3-P (örüntü tutma) ve T3-H (okuma aktarımı)

**T3-P — İNTERPOLASYON kontrolü (KURAL KANITI DEĞİL; şans 0,143; H=10):**

| kol | kesin ± %95 GA | ±2 | nominal |
|---|---|---|---|
| A_er | **0,626 ± 0,055** | 0,969 | 0,484 |
| **A_gercek** | **0,508 ± 0,051** | 0,912 | 0,376 |
| A_derece | 0,389 ± 0,020 | 0,890 | 0,429 |
| A_w0 | 0,192 ± 0,013 | 0,588 | 0,284 |

→ Hepsi şansın (0,143) **üstünde** (beklenen: tüm s'ler eğitimde ✓) ama **A_gercek 0,508 < 0,90** →
**H7.12 ÇÜRÜDÜ**. Yani **örüntü (işaret+jitter) genellemesi zayıftır**; bu, jitter'lı zamanlamanın
okuma için **zor bir genelleme ekseni** olduğunu gösterir (7-2'de sabit aralıkta aynı H=10'da 0,990'dı).

**T3-H (KEŞİFSEL; okuma H=10'da eğitildi, başka H'de test, S2):**

| kol | H=0 | H=20 |
|---|---|---|
| A_gercek | 0,069 ± 0,028 | 0,084 ± 0,030 |
| A_er | 0,052 ± 0,019 | 0,060 ± 0,020 |
| A_derece | 0,000 ± 0,000 | 0,002 ± 0,002 |

→ Aktarılan okuma da **şansın çok altında** (0,50) → çöküş **okuma seviyesinde de** sürüyor.

## 4. Ön-kayıtlı ölçütler ve hipotezler

| ölçüt (7-1/7-2 ile aynı katılık) | sonuç | karar |
|---|---|---|
| **"Kural/ekstrapolasyon"** — S1 uzak (\|s\|=6): GA-ayrık > 0,50 **ve** > A_w0 **ve** ≥ 0,50 | A_gercek **0,002 ± 0,002** | **GEÇMEDİ** |
| aynı ölçüt — S2 (s=±6) | A_gercek **0,128 ± 0,064** | **GEÇMEDİ** |
| **"Connectome'a özgü kural"** — S1-uzak/S2'de A_derece **VE** A_er'den GA ayrık üstünlük | vs A_derece: üstün (ikisi de ~0); **vs A_er: A_er ÜSTÜN** (0,230 vs 0,128) | **GEÇMEDİ** |

| hipotez | sonuç | karar |
|---|---|---|
| **H7.11** (ekstrapolasyon çöker; tahmin eğitim ucuna yapışır) | takılı oranı **0,76** (S1-uzak) ve **0,65** (S2) ≥ 0,5; kesin 0,002 / 0,128 (şans 0,50) | **DESTEK** |
| **H7.12** (T3-P'de A_gercek ≥ 0,90) | **0,508** | **ÇÜRÜDÜ** |
| **H7.13** (A_gercek ≈ A_derece ≈ A_er) | S2: vs A_w0 **+0,128 (p_holm=0,005)**, vs A_derece **+0,123 (p_holm=0,006)** → ayrışır; **vs A_er −0,102 (p_holm=0,29) → ayrışamaz**; S1-uzak: hiçbiri ayrışamaz | **KISMEN** |
| **H7.14** (TANI, yön yok: PCA artık ↔ hata) | Spearman **rho=−0,05, p=0,91 (n=8)** | **ilişki gösterilemedi** |

- **Holm (m=6)** sonuçları: A_gercek, S2'de **A_w0 ve A_derece'den anlamlı üstün** (p_holm ≈ 0,005-0,006),
  ama **A_er'den üstün değil** (0,230 vs 0,128) ve **hepsi şansın altında** → bu fark **"yokluk
  bölgesinde"**dir (hiçbir kol kuralı öğrenmiyor; yalnızca **kim daha az kötü**).
- **Betimsel (tanı):** en düşük PCA artığı **A_er'de** (0,089-0,106) ve **en yüksek kesin doğruluk da
  A_er'de**; en yüksek artık **A_derece'de** (0,548-0,595) ve **en kötü doğruluk da** onda → kol
  düzeyinde **nitel bir örüntü** var, ama **8 noktalı sıra testi anlamlı değil** (H7.14).

## 5. Hangi işi ağın, hangisini okumanın yaptığı

- **Kontrolcü yalnızca ±1 darbesi gönderir; sayaç TUTMAZ** — toplamı taşımak/hesaplamak ağın işidir.
- **İdeal sayaç (DIŞ YARDIM, simüle edilmedi):** durum doğrudan net toplam olduğunda kesin doğruluk
  **tanım gereği 1,000**dir → **kural kontrolcüde tam olarak uygulanabilir**; ağın işi onu **temsil
  etmekti** ve bu **başarılamadı**.
- **No-recurrence kontrolü (A_w0):** **tam olarak 0,000** (S1, S1-uzak, S2) → okuma, tekrarlama
  olmadan **hiçbir** ekstrapolasyon yapamıyor (tahminler sabit/eğitim aralığında).
- **Gerçek ağ (A_gercek):** 0,002-0,128 (H=10) → **tekrarlamanın katkısı var ama yetmiyor**:
  A_w0'a göre S2'de anlamlı üstün (+0,128), ama **şansın (0,50) çok altında**.
- **Nominal okuma katmanı T3'te kullanılamaz:** eğitimde görülmemiş sınıfı **yapısal olarak**
  üretemez (nominal = 0,000 ✓); bu yüzden T3'ün ölçütü **skaler + yuvarlama**ya dayanır.


## 6. Sınırlılıklar

- **KEŞİFSEL-YENİDEN-TEST:** faz 7-2 görüldükten sonra tasarlandı → **HARKing riski**; sonuçlar
  doğrulayıcı değildir. Ölçütler gevşetilmedi, ama bu riski ortadan kaldırmaz.
- **6 adım kapasitesi 9×9 için YETMEZ:** k=6 ile **yalnızca 9 toplam** (s=−6..6, çift) üretilebilir;
  bu, "kural öğrenme" için **dar** bir çıkış uzayıdır ve ±6 testlerinde **iki sınıf** kalır
  (şans 0,50) → ölçüt katı tutulsa da **ayırt edicilik sınırlıdır**.
- **Jitter sapması** (yukarıda): 7-1/7-2 ile karşılaştırma **doğrudan değildir**.
- **T3-P kural kanıtı DEĞİLDİR:** eğitimde **tüm s'ler** görülür; yalnızca **örüntüler** (işaret +
  jitter) dışarıda kalır → **interpolasyon** kontrolüdür.
- **Nominal okuma yapısal olarak ekstrapole edemez** (eğitimde görülmemiş sınıf üretemez) →
  T3'ün birincil ölçütü **skaler regresyon + yuvarlama**dır; bu okuma da yapısal olarak
  **eğitim aralığının dışına çıkmayabilir** (bu raporda "takılı" oranı ile ölçülür).
- **Izgara sınırı:** A_gercek'in g'si 7-2'de **40 = ızgaranın üst ucu** seçilmişti; g>40 denenmedi.
- **T2/T4 bu fazda yok**; H=40 yok; **tek connectome**; **giriş seçimi keyfî**; **NT işaretleri
  varsayım**; **simülasyon**.
- **Ölçüm sırasında hiçbir şey değiştirilmedi**; sonradan eklenen analizler **KEŞİFSEL** etiketli.
  (Teknik düzeltme `3e243a9` **ölçüm başlamadan önce** yapıldı: `np.polyfit` sabit hedefte tekil
  sistem → yalnızca tanı sütunu; hiçbir ölçüt/okuma/veri değişmedi.)

## 7. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/reservoir_rule.py baselines   # tasarım tabanları (ölçümden önce)
.venv/Scripts/python.exe -X utf8 numcog/reservoir_rule.py runall 20     # 20 tohum × 4 kol
.venv/Scripts/python.exe -X utf8 numcog/reservoir_rule.py merge        # özet + ölçüt/hipotez
```

Çıktılar (`numcog/results_p7_3/`): `design_baselines.csv`, `<kol>_seed<NN>.csv` (tohum başına),
`summary_T3.csv`, `hypotheses.csv`, `merge_out.txt`, `run.log`. **Koşu süresi: 80 tohum-kol, 80 dk**
(ön-kayıt tahmini ~47 dk idi; makine yükü nedeniyle ilk kollar ~170-240 s/tohum, sonra ~45 s).
Donmuş (g, amp) 7-2'nin `frozen_config.csv`'sinden **dinamik olarak okunur** (elle yazılmadı).
Ara önbellek yok (7-3 kolları 7-2'ninkileri yeniden üretir).

## 8. ÖZET (bu veride, bu modelde, bu ızgarada)

1. **"Kural/ekstrapolasyon" ölçütü GEÇMEDİ.** A_gercek, T3-S1 uzak (|s|=6) **0,002±0,002** ve
   T3-S2 (s=±6) **0,128±0,064** — **ikisi de şansın (0,50) ALTINDA**; A_w0'dan S2'de anlamlı üstün
   (p_holm=0,005) ama bu **yokluk bölgesinde** bir farktır (hiçbir kol kuralı öğrenmiyor).
2. **H7.11 DESTEK:** tahminler **eğitim aralığının ucuna yapışıyor** (takılı oranı 0,76 / 0,65) —
   ekstrapolasyon **çöküyor**.
3. **H7.12 ÇÜRÜDÜ:** T3-P'de (yakın örüntü tutma, İNTERPOLASYON) A_gercek **0,508 < 0,90** →
   **jitter'lı örüntü genellemesi zayıf** (7-2'de sabit aralıkta aynı H=10'da 0,990 idi).
4. **"Connectome'a özgü kural" GEÇMEDİ:** A_er, hem S1-uzak (0,065) hem S2'de (0,230) **A_gercek'ten
   üstün**; A_derece ise en kötü (0,001 / 0,005).
5. **H7.13 KISMEN:** A_gercek, A_w0 ve A_derece'den anlamlı üstün (S2), ama **A_er'den değil** →
   *bu veride* kural boyutunda da **connectome'a özgü bir avantaj yok**.
6. **H7.14 ilişki gösterilemedi** (Spearman −0,05, p=0,91, n=8) — ama **betimsel** olarak en düşük
   PCA artığı A_er'de, en yüksek A_derece'de (doğruluk sıralamasıyla aynı yönde).
7. **Bekleme etkisi (ikincil):** H=0'da kısmi ekstrapolasyon **şansın üstünde** (S1 0,361; S2 0,660),
   H=10'da ve H=20'de **çöküyor** → *bu modelde* toplam bilgisi **son darbeden sonra kısa süre**
   mevcut, **bekleme** onu siliyor. Aktarılan okuma (T3-H) da **yardımcı olmuyor** (0,069/0,084).
8. **Nominal okuma T3'te yapısal olarak kullanılamaz** (0,000) → T3 ölçütü skaler+yuvarlamaya dayanır;
   **6 adım kapasitesi 9×9 için yetmez** (yalnızca 9 toplam, ±6 testlerinde **2 sınıf**).
9. **Genel sonuç:** *bu veride, bu modelde, bu ızgarada* **kural/ekstrapolasyon yoktur**; 7-2'nin
   "connectome'a özgü bellek avantajı yok" bulgusu **kural boyutunda da** doğrulanır; gerçek ağ
   A_w0'dan ve A_derece'den **daha az kötüdür**, ama **ER surrogatından daha kötüdür** ve hiçbir kol
   şansı geçemez.
