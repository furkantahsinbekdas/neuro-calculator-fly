# RAPOR FAZ 4A — Ardışık hesap makinesi (mühendislik; iş bölümü açık)

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `776e964`).

## 1. İş bölümü (AÇIK)

`numcog/calculator.py`. **Sinek çekirdeği** (`FlyCore`) yalnızca tek adım `(n,op) → clip(n±1,0..N)`
yapar (Faz 3c mimarisi: coarse_kc + sürekli Gauss çıktı, MSE, kosinüs decode). **Kontrolcü**
(`CyborgFly`) sayaç, döngü, durma koşulu (güvenlik sınırı), durum geri beslemesi ve sonuç okumayı
taşır. **SİNEK DURUM TAŞIMAZ; KONTROLCÜ TAŞIR.** "Uçuş simülatörü" gibi yeniden adlandırma YOK.
add/subtract = b kez ±1 tick; multiply = b kez toplama; divide = tekrarlı çıkarma + kalan.
Operatör kodu Faz 3'teki gibi (iki ayrık ALPN alt kümesi), değiştirilmedi.

## 2. Kapasite ölçümü (H4a.1)

| N | eğitim doğruluğu (ort ± std) | çıkarım güveni | süre/tohum |
|---|---|---|---|
| 10 | **0.502 ± 0.189** | 0.984 | 0.18 s |
| 20 | 0.196 ± 0.125 | 0.981 | 0.19 s |
| 40 | 0.109 ± 0.091 | 0.977 | 0.28 s |
| 81 | 0.166 ± 0.064 | 0.957 | 0.37 s |

**H4a.1 ÇÜRÜDÜ:** hiçbir N %100'e ulaşmıyor; en iyi N=10'da bile %50. **Kapasite < 10.**
Not: güven %95+ iken doğruluk %50 — model **kendinden emin ama yanlış** (kosinüs decode yanlış
referansı %98 güvenle seçiyor).

## 3. Mekanizma — operatör yıkanıyor

`(n,op+)` ile `(n,op−)` KC kodlarının kosinüs benzerliği **0.88–0.98**; top-k=40'ın **38–39'u ortak**.
Yani operatör (ALPN, yalnızca 151 ortak KC'ye iner) sayı (VPN, 427 KC) karşısında çok zayıf;
top-k=40 global inhibisyon sayıyı seçer, operatörü dışlar. Sonuç: okuma katmanı (n,op+) ve (n,op−)
ayıramaz, ~"kimlik" (n→n) üretir. Bu, sürekli (MSE) çıktının nominal (argmax) çıktıdan daha kırılgan
olduğunu gösterir: Faz 3'ün nominal okuması küçük KC farklarını ayırabilmişti (eğitim 1.0), sürekli
regresyon aynı farkla "kimliğe" çöker.

## 4. Hesap makinesi (N=10) — ÇALIŞMIYOR

| metrik | değer |
|---|---|
| p (tek adım doğruluğu) | 0.502 ± 0.189 |
| multiply doğruluğu (81 çift) | **0.075 ± 0.079** |
| divide doğruluğu | 0.548 ± 0.099 (çoğu a<b→q=0 triviyal; 36/81=0.44 zaten 0) |
| ort. sinek çağrısı / işlem | 7.992 (divide'ın 50-iterasyon güvenlik sınırına takılması) |

**Terminal demosu (hata gözle görülür):**
```
add(3,2):      Tick 1: 3→3 (güven 0.98) · Tick 2: 3→3  → sonuç 3 (beklenen 5)
multiply(2,3): Tick 1: 0→1 · Tick 2..6: 1→1 ...        → sonuç 1 (beklenen 6)
```
+1 adımı 0→1'de çalışıyor ama n=1,2,3'te "kimliğe" takılıp kalıyor (adım adım ilerlemiyor).

## 5. Zincir bozulması (H4a.2) ve gürültü (H4a.3)

- **H4a.2 KISMEN ÇÜRÜDÜ:** zincir doğruluğu küçük k'da p^k'nin ÜSTÜNDE (hata bağımsız değil;
  "kimliğe takılma" modu rastgele yürüyüş değil), k≥12'de 0'a çöküyor. Ör: k=2'de acc=0.360 vs
  p²=0.252; k=4'te 0.185 vs 0.064; k≥12'de 0.
- **H4a.3 ÇÜRÜDÜ:** gürültü eğrisi monoton değil — 0.0→0.500, 0.05→0.545 (**artıyor**),
  0.10→0.545, 0.20→0.409, 0.50→0.364, 1.0→0.273. Düşük gürültü "kimlik" çökmesini kırıp doğruluğu
  ARTTIRIYOR; yüksek gürültü bozuyor.

## 6. Hipotez değerlendirmesi

| Hipotez | Sonuç |
|---|---|
| H4a.1 kapasite: N≤20 %100, N=40/81 başarısız | **ÇÜRÜDÜ**: N=10 bile %50; kapasite <10 |
| H4a.2 zincir ≈ p^k | **KISMEN**: "takılma" modu yüzünden p^k'dan sapıyor |
| H4a.3 gürültü monoton azalır | **ÇÜRÜDÜ**: düşük gürültü doğruluğu artırıyor (monoton değil) |

## 7. Sınırlılıklar

- Operatör (ALPN) kanalının zayıflığı bu sonucun asıl sebebi; operatör kodu ön-kayıtta sabit
  olduğundan değiştirilmedi (görev: "operatör kodu aynen kalır").
- Sayı→VPN ve operatör→ALPN atamaları keyfîdir; yalnızca VPN→KC/ALPN→KC kablolaması gerçektir.
- Çıktı aralığı 0..N; 9×9=81 için N≥81 gerekirdi ama kapasite zaten <10.
- Bu bir simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 8. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/calculator.py
```
Çıktı: `numcog/results_p4a/` (capacity.csv, calculator.csv, chain_vs_k.csv).

**KARAR:** Hesap makinesi bu çekirdek üzerinde ÇALIŞMIYOR (kapasite <10; operatör yıkanıyor).
FAZ 4B (çarpma/bölme, doğrudan yol) ya da FAZ 5 için bekleniyor (dur — kullanıcı onayı).
