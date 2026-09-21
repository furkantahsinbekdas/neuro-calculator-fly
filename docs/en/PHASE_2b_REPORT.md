<!-- Machine translation of `numcog/RAPOR_FAZ_2b.md` (local Ollama / gemma3:4b). The Turkish original is the authoritative record; this file is a reading copy.
     Numeric-token check: PASS (all 175 numeric tokens present) -->

# RAPOR FAZ 2b — Ekstrapolasyon tanısı (KEŞİFSEL)

Tarih: 2026-09-19. Durum: tamamlandı. **Faz 2 sonuçları görüldükten sonra eklenen keşifsel
tanıdır**; Faz 2 hipotezleri/raporu DEĞİŞTİRİLMEDİ. Hipotezler ön-kayıtlı (commit `c43a06e`).

## 1. Yöntem

`numcog/extrapolation_diagnosis.py`. Faz 2'nin `magnitude_compare.py` (delta kuralı, ±1 hedef,
lr=0.01, 500 epoch) ve `number_coding.py` (VPN→KC, topk=40) modülleri yeniden kullanılır.
Dört kol, her kolda gerçek W + derece-koruyan karıştırılmış W, 20 tohum:

1. **Skor eğrisi:** f(n) = okuma skoru(sol=n, sağ=5 referans), n=1..9; tepe noktası.
2. **Kenar dolgusu:** sayı ekseni [1,9] → **[-3,13]** (sayılar ortada); aynı eğitim/test.
3. **Paylaşımlı okuma:** w_sol = −w_sağ (fark kodlaması g(n1)−g(n2); mimariye gömülü
   karşılaştırma — **dış yardım**).
4. **Eğitim aralığı:** 1-4 / 1-6 / 1-8 ile eğit; komşu test çiftlerinde ekstrapolasyon
   uzaklığına göre doğruluk.

## 2. Kol 1 — Skor eğrisi f(n) (H2b.1)

| model | f(1) | f(2) | f(3) | f(4) | f(5) | f(6) | f(7) | f(8) | f(9) | tepe |
|---|---|---|---|---|---|---|---|---|---|---|
| coarse_direct | -3.18 | -2.70 | -1.90 | -0.99 | 0.00 | 0.89 | 1.11 | 0.39 | -0.84 | 7 |
| coarse_kc | -0.97 | -0.89 | -0.78 | -0.99 | 0.05 | 0.99 | 0.60 | 0.18 | -0.19 | 6 |
| coarse_kc_shuffled | -1.09 | -0.97 | -0.59 | -0.98 | 0.00 | 0.98 | 0.59 | 0.22 | -0.18 | 6 |

**H2b.1 DESTEKLENDİ:** f(n) 6–7'de tepe yapar, 8–9'da azalır (f(9) < f(5)=0). Yani okuma
katmanı 9'u 5'ten "küçük" sanıyor — ters çevirmenin doğrudan imzası.

## 3. Kol 2 — Kenar dolgusu [-3,13] (H2b.2)

| model | test2 (dolgusuz, Faz 2) | test2 (dolgulu [-3,13]) |
|---|---|---|
| coarse_direct | 0.000 | 0.000 |
| coarse_kc | 0.208 ± 0.131 | 0.233 ± 0.205 |
| coarse_kc_shuffled | 0.175 ± 0.239 | 0.192 ± 0.173 |

**H2b.2 ÇÜRÜDÜ:** dolgu ters çevirmeyi AZALTMADI (coarse_direct hâlâ %0; kc pratikte değişmedi).
→ Kenar kesilmesi (edge truncation), ters çevirmenin sebebi DEĞİL.

## 4. Kol 3 — Paylaşımlı işaret-ters okuma (H2b.3)

| metrik | sonuç |
|---|---|
| eğitim | 1.000 ± 0.000 |
| test1 (aralık içi) | 1.000 ± 0.000 |
| test2 (aralık dışı) | 0.000 ± 0.000 |

**H2b.3 ÇÜRÜDÜ:** mimariye "karşılaştırma" yapısı gömülmesine rağmen (w_sol=−w_sağ, dış yardım)
aralık dışı **şansa yaklaşmadı** — hâlâ tam ters çevirme (%0). Yani sorun, okumanın simetrik
olmaması da DEĞİL.
## 5. Kol 4 — Eğitim aralığı ablasyonu (H2b.4)

coarse_direct: **her** aralıkta ve **her** uzaklıkta test çiftleri = 0.000 (dist=1'de bile tam ters).
coarse_kc / shuffled: 0.125–0.375 arasında gürültülü, uzaklıkla **net bir düşüş yok**.

**H2b.4 ÇÜRÜDÜ/KARIŞIK:** kademeli derinleşme yok — ters çevirme coarse_direct'te anında ve
tamdır (%0), coarse_kc'de uzaklıkla monoton derinleşme gözlenmez (gürültülü, şansın altında).

## 6. Shuffle kontrolü (H2b.5, tüm kollar)

Her kolda gerçek W ile karıştırılmış W istatistiksel olarak ayırt edilemez (ör. dolgulu test2:
kc 0.233 vs shuffled 0.192; f(n) tepeleri her ikisinde de 6). **H2b.5 DESTEKLENDİ.**

## 7. Asıl bulgu — mekanizma düzeltildi (kenar kesilmesi DEĞİL)

Üç ablasyon da (dolgu, paylaşımlı okuma, eğitim aralığı) ters çevirmeyi kaldıramadı. Birleşik
yorum (etiketli, doğrudan ölçülmemiş ama veriyle tutarlı):

**Doğrusal okuma katmanı (delta kuralı → min-norm LMS), yerel Gauss kodu üzerinde, eğitim
aralığının dışındaki büyüklüğü "eğitim çiftlerine benzerlik" üzerinden tahmin eder.** Öğrenilen
büyüklük fonksiyonu u·g(n), eğitim sayıları (1-6) merkezli Gauss benzerlik tepelerinin toplamı
olduğundan, eğitim aralığının ÜST SINIRINDA tepe yapar ve ötesinde sıfıra (merkeze göre negatife)
düşer. Bu yüzden 7-9 aralığında karşılaştırma TERS döner. Bu, (a) eksen dolgusuna, (b) işaret-ters
ağırlık paylaşımına ve (c) gerçek/rastgele KC matrisine karşı **duyarsızdır** — kodlama+okuma
çiftinin temel bir özelliğidir.

Yani Faz 2'deki ters çevirmenin sorumlusu ne "gerçek görsel devre" ne de "kenar kesilmesi";
**doğrusal okumanın yerel koddaki sınırlı ekstrapolasyonudur.**

## 8. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H2b.1 f(n) 6-7'de tepe yapar | **DESTEKLENDİ** (tepe 6–7, sonra düşüş) |
| H2b.2 dolgu ters çevirmeyi azaltır | **ÇÜRÜDÜ** (hiç azalmadı) |
| H2b.3 paylaşımlı okuma şansa yaklaştırır | **ÇÜRÜDÜ** (hâlâ %0) |
| H2b.4 aralık daraldıkça uzaklıkla düşüş | **ÇÜRÜDÜ** (anında/ tam ters çevirme, kademeli düşüş yok) |
| H2b.5 shuffle farkı yok | **DESTEKLENDİ** |

## 9. Sınırlılıklar

- Bu keşifsel tanı, Faz 2 sonrası eklenmiştir (post-hoc); sonuçları Faz 2
  "düzeltmez", Faz 2 raporu olduğu gibi durur.
- Mekanizma (benzerlik-tabanlı ekstrapolasyon) bir yorumdur; doğrudan ölçülmedi.
- "Paylaşımlı okuma" yalnızca coarse_direct'e uygulandı (KC kodu sol/sağ ayrımı taşımadığından
  işaret-ters paylaşım oraya doğrudan uygulanamaz).
- Tek karıştırılmış matris gerçeklemesi (tohum 12345).
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 10. Reproducibility

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/extrapolation_diagnosis.py
```
Output: `numcog/results_p2b/` (diagnosis_fn.csv, padding.csv, shared_readout.csv, range_ablation.csv).

**DECISION:** Pending for Phase 3 (status — user approval).
