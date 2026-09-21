# RAPOR — HESAP MAKİNESİ BÜTÜNLÜĞÜ (AŞAMA 1)

Tarih: 2026-09-20. Soru: **hesabı sinek çekirdeği mi yapıyor, Python mu?**
Dil: **"bu veride, bu modelde, bu ızgarada"**. Kaynak: statik okuma (`calculator.py`, `phase4c.py`,
`operator_diagnosis.py`) + `numcog/tests/test_calculator_integrity.py` çıktısı.
**Hiçbir tarihsel dosya değiştirilmedi** (test ve servis **yeni** dosyalar: `numcog/fly_calc.py`,
`numcog/tests/test_calculator_integrity.py`, `numcog/build_fly.py`).

## 1. STATİK KONTROL — operandlar üzerinde doğrudan aritmetik var mı?

`calculator.py` ve çağırdığı yollarda, **sonucu üreten** her satır incelendi. Sayaç/döngü indeksi
dışındaki tüm aritmetik satırlar ve gerekçeleri:

| dosya / fonksiyon | satır (aritmetik) | ne üretiyor? | meşru mu? |
|---|---|---|---|
| `calculator.FlyCore._result` | `min(max(n + (±1), 0), N)` | **beklenen değer** (eğitim hedefi + `train_accuracy`) | ✓ **yanıt yolu değil** |
| `operator_diagnosis.clip_result` | `min(max(n ± 1, 0), N)` | beklenen değer (ölçüm karşılaştırması) | ✓ yanıt yolu değil |
| `calculator.CyborgFly.add` | `range(b)` | **sayaç üst sınırı** | ✓ döngü kuralı |
| `calculator.CyborgFly.add` | `n = self._step(n, '+')` | **sonuç** | ✓ çekirdekten geliyor |
| `calculator.CyborgFly.subtract` | `range(b)`, `self._step(n, '-')` | sayaç + sonuç | ✓ |
| `calculator.CyborgFly.multiply` | `n = 0`, `range(b)`, `self.add(n, a)` | akümülatör başlangıcı + döngü | ✓ (değer `add`'den geliyor) |
| `calculator.CyborgFly.divide` | `n = a`, `q = 0` | başlangıç/sayaç | ✓ |
| `calculator.CyborgFly.divide` | `while n >= b and q < 50` | **durma koşulu** (+ güvenlik sınırı) | ✓ karşılaştırma, aritmetik değil |
| `calculator.CyborgFly.divide` | `q += 1` | **sayaç artışı** | ✓ |
| `calculator.CyborgFly.divide` | `n = self.subtract(n, b)` | sonuç/kalan | ✓ çekirdekten |
| `calculator.measure_calculator` | `a * b`, `a // b`, `b * (a // b)` | **beklenen değer + zincir meta verisi** | ✓ ölçüm/karşılaştırma, yanıt yolu değil |
| `phase4c.Core.step` | `code(n,op) @ W.T + b`, `argmax`, `exp(s-s.max())` | **sonucu üreten okuma** | ✓ bu **modelin kendisi** (Python aritmetiği operanda değil, matris çarpımı) |
| `phase4c.core / gauss_axis` | `A[n]` (Gauss kodu) | **kod tablosu araması** (n üzerinde hesap yok) | ✓ |
| `phase4c.fit_fast` / `cal._fit32` | delta kuralı eğitimi | ağırlıklar | ✓ **öğrenme**, yanıt üretimi değil |
| **`fly_calc.expected`** (YENİ) | `a+b`, `a-b`, `a*b`, `a//b`, `a%b` | beklenen değer: **yalnızca sınır doğrulaması** ve test karşılaştırması | ✓ kod içinde böyle etiketlendi |

**STATİK SONUÇ:** Döndürülen sonuç, **operandlar üzerinde doğrudan aritmetikle üretilmiyor**;
tek üretim yolu `core.step` (eğitilmiş okuma) ve kontrolcünün **döngü/sayaç** mantığı.
Operand değerleri üzerinde hesap yapan tek yerler: **döngü sınırı/sayaç**, **beklenen değer**
(eğitim+ölçüm), **sınır doğrulaması** ✓ — hepsi listelendi ve gerekçelendi.

## 2. DİNAMİK KONTROL — test sonuçları (ham)

Komut: `python -X utf8 -m numcog.tests.test_calculator_integrity` · **süre: 1 s** · çekirdek:
`numcog/fly_weights/fly_N81_seed0.npz` (Faz 4E kalibrasyonundan geçen **tohum 0**, tablo **1.0000**).
**KIRMIZI: 0 / 34 → TÜM TESTLER GEÇTİ.**

### A. Gerçek çekirdek (1..9 tüm çiftler, `od.calc_measure` — tarihsel ölçüm fonksiyonu)

| işlem | ölçülen |
|---|---|
| add | **1.0000** |
| subtract | **1.0000** |
| multiply | **1.0000** |
| divide | **1.0000** |
| tablo (164 girdi) | **1.0000** |

### B. SAHTE çekirdek (rastgele çıktı) — tasarım tabanlarıyla karşılaştırma

| işlem | gerçek | **sahte** | tasarım tabanı ("en sık cevap") | sahte ≤ taban+0.05 |
|---|---|---|---|---|
| add | 1.0000 | **0.0000** | 0.1111 | ✓ |
| subtract | 1.0000 | **0.0123** | **0.5556** (45/81 çiftte `max(a-b,0)=0`) | ✓ |
| multiply | 1.0000 | **0.0000** | 0.0494 | ✓ |
| divide | 1.0000 | **0.4815** | **0.4444** (a<b olan 36/81'de döngü hiç çalışmaz) | ✓ |
| **ortalama** | 1.000 | **0.1235** | — | ✓ (≤0.25) |

### B2. Karar kanıtı: çağrı sayısı çekirdeğe bağlı DEĞİL

| ifade | gerçek çekirdek çağrısı | sahte çekirdek çağrısı | sonuç |
|---|---|---|---|
| `3+5` | 5 | 5 | gerçek **8**, sahte **68** |
| `9-4` | 4 | 4 | — |
| `6x7` | 42 | 42 | — |
| `8-3` | 3 | 3 | — |

→ Döngüyü **kontrolcü** kurar (çağrı sayısı çekirdekten bağımsız, aynı); **cevap çekirdekten gelir**
(aynı ifade, farklı çekirdek → farklı sonuç) ✓.

### C. Adım sayısı (tam assert)

| ifade | beklenen çağrı | ölçülen | sonuç |
|---|---|---|---|
| `add(3,5)` | b = 5 | **5** | 8 ✓ |
| `subtract(9,4)` | b = 4 | **4** | 5 ✓ |
| `multiply(3,4)` | a·b = 12 | **12** | 12 ✓ |
| `divide(9,4)` | q·b = 2·4 = 8 | **8** | (2, kalan 1) ✓ |

### D. Sınır davranışı (sessiz yanlış cevap YOK)

| girdi | beklenen | sonuç |
|---|---|---|
| `9x9`, `81+0`, `0+0`, `9/1`, `8-8` | **çalışır** | ✓ (sonuç ≤ 81) |
| `80+5` (=85) | **açık hata** | ✓ "sonuç 85 > 81: sinek tablosu 0..81 ile sınırlı" |
| `82+0` (=82) | açık hata | ✓ |
| `9x10` (=90) | açık hata | ✓ |
| `3-5` (=−2) | açık hata | ✓ "sonuç -2 < 0 … (negatif yok)" |
| `0-1` (=−1) | açık hata | ✓ |
| `45+45` (=90) | açık hata | ✓ |

## 3. İLK KOŞU KIRMIZIYDI — gizlenmiyor (ve neden kırmızı değildi)

İlk koşuda B testi **KIRMIZI** verdi: keyfî eşik "tüm işlemler < 0.30" ile `divide` = **0.4815** ✗.
İnceleme: `divide(a,b)` içinde **a < b olan 36/81 çiftte döngü gövdesi hiç çalışmaz** (n = a < b) →
q = 0 = doğru cevap, **çekirdek hiç çağrılmadan** → taban **36/81 = 0.4444**. Aynı şekilde
`subtract`'ta **45/81** çiftte beklenen değer 0'dır (taban 0.5556). Yani bu bir "Python hesaplıyor"
kanıtı değil, **tarihsel fonksiyonların dejenere tabanıdır**.
→ Eşik, **tasarımdan hesaplanan tabana** çevrildi (`design_baselines()`, test içinde analitik);
kırmızı sonuç ve gerekçesi bu raporda **aynen** duruyor ✓. Ek olarak (B2) **çağrı-sayısı
değişmezliği** ve **farklı sonuç** kanıtı eklendi.

**Ölçümden çıkan dürüst not:** `divide = 1.0000` değerinin **36/81'i çekirdeksiz** (trivial)
doğrudur; yani "divide %100" ifadesi **çekirdek başarısı olarak olduğundan büyük** okunmamalıdır.
`add`/`multiply` için trivial çift yoktur (her çiftte döngü çalışır) ✓.

## 4. SONUÇ

1. **Hesabı sinek yapar, Python değil** ✓ — statik olarak sonucu üreten tek yol `core.step`;
   dinamik olarak **sahte çekirdek cevabı bozar** (ortalama 1.000 → **0.1235**; `3+5`: 8 → 68) ve
   **çağrı sayısı değişmez** (döngü kontrolcüde) ✓.
2. **Durum ve mantık kontrolcüdedir** (sayaç, döngü, durma, kalan) ✓ — sinek yalnızca `n → n±1`.
3. **Sınır dışı işlem sessizce yanlış cevaplanmaz**: >81 veya <0 sonuç **açık hata** verir ✓.
4. **Kapsam/limitler:** rakamlar 1..9 (ölçülmüş alan); sonuç 0..81; `divide` **tam bölme + kalan**;
   **iki haneli girdi** arayüzde yalnızca "sonuç ≤ 81" ise kabul edilir ve **KEŞİFSEL** etiketlidir
   (AŞAMA 3'te ölçülür); **"çok haneli aritmetik" YOK** (uygulanmadı); kesirli/negatif sonuç **yok**.
5. **Simülasyon**: canlı sinek değil; tek connectome (hemibrain 783); sayı→VPN ataması **keyfî**;
   kalibrasyon kapısı tohumların **%46'sını reddeder** (Faz 4E) → kullanılan sinek **seed 0** (geçti ✓).

## 5. Bu aşamanın çıktıları

- `numcog/build_fly.py` → `numcog/fly_weights/fly_N81_seed0.npz` (**0.14 MB**, tablo 1.0000)
- `numcog/fly_calc.py` (servis: ayrıştırma + sınır doğrulaması + adım dökümü)
- `numcog/tests/test_calculator_integrity.py` (tek komut, **1 s**, 34 kontrol, 0 kırmızı)
- `numcog/__init__.py`, `numcog/tests/__init__.py` (paket yapısı)
- bu rapor

