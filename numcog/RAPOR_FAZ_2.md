# RAPOR FAZ 2 — Büyüklük karşılaştırması ("hangisi büyük")

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `b721fe7`,
`numcog/HIPOTEZLER.md`, Faz 2 bölümü — lr=0.01, epoch=500, tam batch, erken durma yok).

## 1. Yöntem

`numcog/magnitude_compare.py`. İki sayı ayrı popülasyonlarla (sol→H1, sağ→H2) Gauss σ=1.5
olarak kodlanır. Dört model: `coarse_direct` (265-VPN vektörüne doğrudan doğrusal okuma),
`coarse_kc` (gerçek VPN→KC, topk=40 → 427-boyutlu ikili kod), `coarse_kc_shuffled`
(derece-koruyan karıştırılmış W), `hash` (çiftin deterministik hash'i, 427-boyut, aktif 40).
Okuma = delta kuralı (LMS), hedef ±1 (sol büyük=+1), tahmin = sign(w·x+b). lr=0.01, 500 epoch,
tam batch. 20 tohum; her tohum VPN→sayı permütasyonunu VE ağırlık başlatmasını değiştirir.
Sızıntı kontrolü: test çiftleri eğitimde yoktur (otomatik assert).

## 2. Özet (ortalama ± std, %95 GA, n=20)

| model | eğitim | test1 (aralık içi) | test2 (aralık dışı) |
|---|---|---|---|
| coarse_direct | 1.000 ± 0.000 | **1.000 ± 0.000** | **0.000 ± 0.000** |
| coarse_kc | 1.000 ± 0.000 | **0.992 ± 0.037** [0.975, 1.008] | **0.208 ± 0.131** [0.151, 0.266] |
| coarse_kc_shuffled | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.175 ± 0.239 [0.070, 0.280] |
| hash | 1.000 ± 0.000 | 0.525 ± 0.156 | 0.475 ± 0.197 |

Tüm modeller eğitimi ezberler (1.000). Kontrol 2 "hep-sol" = 0.500 (test setleri dengeli).

## 3. Çift bazında doğruluk (ortalama, 20 tohum)

| model | (3,5) | (3,6) | (2,5) | (7,8) | (8,9) | (7,9) |
|---|---|---|---|---|---|---|
| coarse_direct | 1.00 | 1.00 | 1.00 | **0.00** | **0.00** | **0.00** |
| coarse_kc | 1.00 | 1.00 | 0.98 | 0.35 | 0.20 | 0.08 |
| coarse_kc_shuffled | 1.00 | 1.00 | 1.00 | 0.28 | 0.13 | 0.13 |
| hash | 0.48 | 0.58 | 0.53 | 0.48 | 0.45 | 0.50 |

## 4. Kontroller

- **Kontrol 1 (rastgele etiket):** tüm modeller test1/test2 ≈ 0.42–0.55 (şans). → Gerçek
  görevdeki aralık-içi başarının gerçek öğrenme olduğu kanıtlandı (gürültü ezberi değil).
- **Kontrol 2 (hep-sol):** 0.500.

## 5. KRİTİK BULGU — aralık dışında TERS ÇEVİRME (inversion)

`coarse_direct` aralık dışı çiftleri **tamamen ters** tahmin ediyor (test2 = 0.000, std=0):
(7,8),(8,9),(7,9) için hep "sağ büyük" demesi gerekirken hep "sol büyük" diyor (ya da tam
tersi). `coarse_kc` ve `coarse_kc_shuffled` da şansın **altında** (0.21 / 0.18) — yani ters
çevirme kısmen sürüyor, KC katmanı onu "gürültülü" hale getiriyor ama düzeltmiyor.

**Muhtemel mekanizma (yorum, açıkça etiketli):** [1,9] eksenindeki Gauss kodu σ=1.5 genişliğinde
olduğu için 7,8,9'da tepenin üst kenarda **kesilmesi** (truncation) toplam enerjiyi n=7→9
arttıkça AZALTIR. 1-6 üzerinde öğrenen doğrusal okuma, "büyüklük" vekili olarak bu enerjiyi
kullanıyorsa, 9'u "küçük" sanar → karşılaştırmayı ters çevirir. Bu bir yorumdur; ölçülen olgu
ters çevirmenin kendisidir.

## 6. Gerçek vs karıştırılmış matris (H2.4, asıl sorunun parçası)

| model | test1 | test2 |
|---|---|---|
| coarse_kc (gerçek W) | 0.992 ± 0.037 | 0.208 ± 0.131 |
| coarse_kc_shuffled | 1.000 ± 0.000 | 0.175 ± 0.239 |

Örtüşen GA'lar; anlamlı bir gerçek-matris avantajı YOK (test1'de karıştırılmış hafif daha iyi).
Faz 1'in kontrolüyle tutarlı: gerçek VPN→KC kablolaması öğrenmeye özel bir yapı eklemiyor.
## 7. Mesafe etkisi (H2.3)

`coarse_direct` r=0.816, `coarse_kc` r=0.728 (doğruluk vs |n−m|, 6 test çifti). AMA bu korelasyon
**aralık karıştırıcısıyla (range confound)** kirlidir: aralık içi çiftler hem büyük |n−m| (2,3)
hem de yüksek doğruluğa sahip; aralık dışı çiftler küçük |n−m| (1,2) ve düşük doğruluğa sahip.
Aralık dışı İÇİNDE etki ters bile görünür: (7,9) [d=2] = 0.08, (7,8) [d=1] = 0.35 — yani uzak
çift DAHA kötü. Bu, H2.3'teki ön-kayıt uyarısıyla uyumlu: mesafe etkisi yalnızca test çiftleri
içindeki varyansla yorumlanmalı ve bu varyans aralık etkisiyle örtüşüyor. **Temiz bir "mesafe
etkisi" gözlemlenmedi; baskın etki aralık-dışı ters çevirmedir.**

## 8. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H2.1 aralık içi: coarse_direct/coarse_kc > %50, hash ≈ %50 | **DESTEKLENDİ** (1.00 / 0.99 / 0.53) |
| H2.2 aralık dışı kademeli düşüş, ani şansa düşüş yok | **ÇÜRÜDÜ**: ani düşüş DEĞİL, ani **ters çevirme** (şansın altına: 0.00 / 0.21). Aralık-dışı içinde sıra kısmen tutar ((7,8)>(8,9)>(7,9)) ama seviye şansın altında. |
| H2.3 mesafe etkisi (pozitif korelasyon) | **KARIŞIK**: r≈0.8 aralık karıştırıcısının artefaktı; temiz mesafe etkisi yok. |
| H2.4 gerçek vs karıştırılmış fark yok | **DESTEKLENDİ** (GA'lar örtüşüyor) |

## 9. Asıl soru — "KC katmanı coarse_direct'e kıyasla ne kadar kayıp yaratıyor?"

- **Aralık içi:** coarse_direct %100 → coarse_kc %99.2. KC katmanı (gerçek W, topk=40)
  **≈ %1 kayıp** yaratıyor — ihmal edilebilir.
- **Aralık dışı:** coarse_direct %0 (temiz ters çevirme) → coarse_kc %21 (gürültülü ters
  çevirme). KC katmanı burada "kayıp" YARATMIYOR; tersine, doğrusal-olmayan seyrek projeksiyon
  temiz doğrusal ters çevirmeyi BOZUYOR (0→%21). Ama ikisi de şansın altında kalıyor.
- **Gerçek vs rastgele KC katmanı:** fark yok (H2.4).

Özet: KC katmanı aralık içinde neredeyse kayıpsız; aralık dışındaki başarısızlık KC katmanının
değil, Gauss kaba kodunun kenar kesilmesinden gelen **ters çevirme**dir.

## 10. Sınırlılıklar

- Sayı→VPN ataması keyfîdir; gerçek olan yalnızca VPN→KC kablolamasıdır. (H2.4 bunu test eder.)
- Tek karıştırılmış-matris gerçeklemesi kullanıldı (tohum 12345); Faz 5 çoklu karıştırma yapacak.
- Mesafe etkisi (H2.3) aralık etkisiyle örtüşüyor; temiz ayrıştırma için aralık-içi mesafe
  manipülasyonu gerekiyordu (mevcut test setinde aralık içi çiftlerin hepsi d=2,3).
- delta kuralı tek okuma algoritmasıdır; daha güçlü okumalar sonucu değiştirebilir (Faz 5).
- Ters çevirmenin mekanizması (kenar kesilmesi) bir yorumdur; doğrudan ölçülmedi.
- Bu bir simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 11. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/magnitude_compare.py
```
Çıktı: `numcog/results_p2/` (summary.csv, per_pair.csv, seeds_raw.csv).

**KARAR:** FAZ 3 için bekleniyor (dur — kullanıcı onayı).

