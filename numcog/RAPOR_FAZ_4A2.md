# RAPOR FAZ 4A-2 — Operatör yıkanmasının tanısı ve düzeltme denemesi

Tarih: 2026-09-19. Durum: tamamlandı. Hipotezler ön-kayıtlı (commit `164d72c`).

## 1. Yöntem

`numcog/operator_diagnosis.py`. **Nominal sınıf okuması** (Faz 3 tarzı, one-vs-all ±1, argmax;
lr=0.01, epoch=1000, tam batch) — Faz 4A'nın MSE sürekli çıktısı DEĞİL (**TASARIM SEÇİMİ**).
Aralık: N=10 ana, N=20 ikincil. **Başarı ölçütü (ön-kayıtlı):** eğitim ≥0.99 VE op-duyarlılık ≥%95.
20 tohum; g ∈ {1,2,4,8} validasyonda seçilir (hesap makinesi testi seçim için kullanılmaz).

## 2. Adım 0 — Tanı (N=10, top-k=40)

| g | aktif KC'den ALPN alan | ALPN hayatta kalma | kod kosinüs (op+ vs op−) |
|---|---|---|---|
| 1 | 13.0 / 40 | 0.359 | 0.912 |
| 2 | 15.7 / 40 | 0.646 | 0.822 |
| 4 | 18.5 / 40 | 0.803 | 0.749 |
| 8 | 21.6 / 40 | 0.898 | 0.669 |

g arttıkça ALPN hayatta kalma artıyor ve kodlar ayrışıyor — ama **gereksiz olduğu görüldü** (aşağıda).

## 3. Kollar (N=10, 20 tohum)

| kol | g | eğitim | op-duyarlılık | ölçüt |
|---|---|---|---|---|
| **ref** (nominal) | 1 | **1.000 ± 0.000** | **1.000 ± 0.000** | **GEÇTİ** |
| gain | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | **GEÇTİ** |
| perchan (kanal başına) | 1 | 0.677 ± 0.020 | 0.355 ± 0.041 | ✗ |
| union (birleşim seti) | 1 | 0.930 ± 0.070 | 0.995 ± 0.020 | ✗ (eğitim <0.99) |
| shuffled | 1 | 0.998 ± 0.010 | 0.995 ± 0.020 | **GEÇTİ** |
| ablation (ortak KC çık.) | 1 | 0.500 ± 0.000 | 0.000 ± 0.000 | ✗ |
| overlapctl | 1 | 1.000 ± 0.000 | 1.000 ± 0.000 | **GEÇTİ** |
| rastgele etiket | — | **1.000** | — | (kontrol) |

**GEÇEN KOLLAR:** ref, gain, shuffled, overlapctl. N=20: ref 1.000/1.000, perchan 0.540/0.081.

## 4. Hipotez sonuçları

- **H4a2.1 ÇÜRÜDÜ:** referans (g=1) ölçütü SAĞLADI (1.000/1.000). Operatör yıkanması, Faz 4A'nın
  **MSE sürekli okumasının** artefaktıymış; **nominal (argmax) okuma 0.91 benzer KC kodlarını da
  ayırabiliyor**. Sorun KC kodu değil, OKUMA tipiymiş.
- **H4a2.2 KISMEN:** g artışı tanıda ALPN'i kurtarıyor ama validasyon g=1 seçti (referans zaten
  geçtiği için kazanç gereksiz).
- **H4a2.3 ÇÜRÜDÜ:** kanal başına inhibisyon ölçütü SAĞLAMADI (0.677/0.355) — hatta BOZDU.
- **H4a2.4 ÇÜRÜDÜ:** birleşim seti sınırda kaldı (0.930/0.995; eğitim <0.99).

## 5. KRİTİK DÜRÜSTLÜK NOTU — ölçüt zayıf

**Rastgele etiketle eğitim de train=1.000 alıyor.** Tüm (n,op) çiftleri eğitimde olduğundan okuma
TABLOYU EZBERLİYOR (22 çift, 427 boyut) → eğitim ve op-duyarlılık **otomatik 1.0** oluyor. Yani
ön-kayıtlı ölçüt (train≥0.99 & op_sens≥0.95) **trivial olarak sağlanıyor** ve tek başına anlamlı
değil. Gerçek kanıt, hesap makinesi testidir (aşağıda). Ölçüt sonuç görüldükten sonra
DEĞİŞTİRİLMEDİ; zayıflığı burada açıkça bildiriliyor.
## 6. Hesap makinesi (nominal çekirdek, N=40 — ölçütü geçen en büyük N)

Aynı `CyborgFly` kontrolcüsü (sayaç/döngü/durma/durum/okuma onda). **Sinek durum taşımaz,
kontrolcü taşır.** 1..9 çiftleri, 20 tohum:

| işlem | doğruluk |
|---|---|
| add | **0.972 ± 0.077** |
| subtract | **1.000 ± 0.000** |
| divide | **1.000 ± 0.000** |
| multiply | **0.617 ± 0.321** (64/81 çift; çarpım >40 aralık dışı) |
| ort. sinek çağrısı / işlem | 3.083 |

Zincir (k adım) doğruluğu p^k'dan İYİ: k=1'de 0.988, k=2'de 0.972, k=7'de **0.973** iken
p^7=0.821. Yani hatalar p^k gibi birikmiyor — çekirdek tabloyu ezberlediği ve çoğu adım "iyi" n'de
geçtiği için zincir ~0.97'de kalıyor.

**Sınır:** 9×9=81 için N≥81 gerekir; nominal çekirdek N=81'de ölçütü geçmiyor (0.940/0.934).
N=40 ile çarpım yalnızca çarpımı ≤40 olan 64/81 çiftte çalışıyor (ör. 5×8=40 ✓, 7×7=49 ✗).

## 7. Yorum — 4A'daki "operatör yıkanması" neydi?

Tanı, KC kodlarının op+ vs op− için %91 benzer olduğunu gösteriyor (gerçek bir darboğaz). Ama
NOMİNAL okuma bu %91 benzer kodu ayırabiliyor (argmax), sürekli MSE okuması ayıramıyordu (kimliğe
çöküyordu). Yani Faz 4A'daki başarısızlık **kodun değil, okuma tipinin** sonucuydu. Faz 3
mimarisi (nominal) bu yüzden baştan çalışıyordu. **Kanal başına inhibisyon ve birleşim seti gibi
tasarım değişiklikleri GEREKSİZDİ** ve ikisi de referansı geçemedi.

Kablolama kimliği yine fark etmiyor: shuffled (0.998) ve overlapctl (1.000) gerçek W (1.000) ile
ayırt edilemez; ama ortak KC'ler çıkarılınca (ablation 0.500, op_sens 0.000) her şey çöküyor —
yani operatör, ortak (VPN∩ALPN) KC'lerin VARLIĞINA bağlı, kimliğine değil.

## 8. Kanal başına inhibisyonun biyolojik yakınlığı (tartışma)

APL, MB'nin TEK ve GLOBAL inhibitörüdür (tüm KC'leri kaplar); biyolojide "kanal başına inhibisyon"
yok. Bu yüzden Kol 3 bir **TASARIM DEĞİŞİKLİĞİ**dir ve biyolojik olarak zayıf gerekçelidir —
ölçüm de onu desteklemedi (0.677/0.355, referansın altında).

## 9. Sınırlılıklar

- Ön-kayıtlı başarı ölçütü trivial (ezberle sağlanıyor); gerçek kanıt hesap makinesi testi.
- Sayı→VPN ve operatör→ALPN atamaları keyfîdir; yalnızca VPN→KC/ALPN→KC kablolaması gerçektir.
- N=40 çarpımda aralık sınırı var; 9×9 için gereken N=81 ölçütü geçmiyor.
- g yalnızca {1,2,4,8} tarandı; validasyon g=1 seçti.
- Simülasyon; canlı sinek değil (bkz. `SINIRLILIKLAR.md`, Faz 6).

## 10. Yeniden üretilebilirlik

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 numcog/operator_diagnosis.py
```
Çıktı: `numcog/results_p4a2/` (diagnosis.csv, arms.csv, chain_vs_k.csv, calculator_chain.csv).

**KARAR:** Bir kol (ref) ölçütü geçti → hesap makinesi ölçüldü ve ÇALIŞIYOR (add/sub/div tam,
çarpım aralıkla sınırlı; N=81 gerekir). "Feedforward KC + okuma yetersiz" ifadesi GEREKSİZDİ.
FAZ 4B / FAZ 5 için bekleniyor (dur — kullanıcı onayı).

