# RAPOR — ARAYÜZ (AŞAMA 2): hesap makinesi sohbet arayüzüne bağlandı

Tarih: 2026-09-20. Dil: **"bu veride, bu modelde, bu ızgarada"**.
Yeni kod **`numcog/`** içinde; `flyputer/`'a yalnızca **ince köprü** eklendi.

## 1. Kullanım (kısa)

```bash
cd flyputer
.venv/Scripts/python.exe -X utf8 server.py          # sunucu: http://127.0.0.1:8000
# tarayıcıda aç:  http://127.0.0.1:8000
# sağ üstte "🧮 Hesap Makinesi / Calculator" düğmesi -> panel açılır
```

- **Panel:** ifade kutusu (`3+5`, `12-7`, `7x8`/`7*8`, `9/4`) + **Hesapla** (Enter de çalışır).
- **Cevap altında iki satır (dürüst iş bölümü):** `sinek çağrısı: N · seed: 0 · kalibre: evet` ve
  `KONTROLCÜ: … sayaç/döngü/durma …` + **açılır adım dökümü** (her sinek çağrısı: n, op, çıktı, güven).
- **SAHTE SİNEK / FAKE FLY** düğmesi: çekirdek yerine rastgele çıktı → cevaplar bozulur ve panelde
  **kırmızı uyarı** görünür ✓.
- **TR/EN** düğmesi (arayüz metinleri; **sonuç biçimi aynı**) ✓.
- **Toplu test (1..9)** düğmesi: 324 çifti (4 işlem) gerçek ve sahte çekirdekle tarar, sonucu yazar ✓.
- **Sınırlar panosu** panelin altında (rakam kaynakları: `RAPOR_FAZ_4E.md`, `results_p4e/final81_seeds.csv`).

## 2. Ne eklendi (ADDITIVE; mevcut davranış DEĞİŞMEDİ)

| dosya | değişiklik | not |
|---|---|---|
| `server.py` | **yeni** `POST /calc` rotası + `_calc()` metodu (~35 satır) | mevcut rotalar (`/`, `/initial`, `/poll`, `/state`, `/health`, `/chat`, `/interact`, `/tool`, `/vitals`, `/mode`) **hiç değiştirilmedi** |
| `chat3d.html` | `</body>` öncesi **yeni** blok: `<style>`, panel HTML'i, kendi `<script>`'i | mevcut 3D beyin/kelime sohbeti koduna **dokunulmadı** |
| `numcog/fly_calc.py` | servis (ayrıştırma, sınır doğrulaması, adım dökümü, `FakeCore`) | AŞAMA 1'de yazıldı |
| `_calc_smoke.py` | **ikame** otomatik test (aşağıda) | kayıp `_fly_smoke.py`/`_fly_frontend_test.js` yerine |

**Uç sözleşmesi** (`POST /calc`): gövde `{expr, fake, step_by_step}` →
`{ok, result, remainder, fly_calls, ticks[{i,n,op,out,confidence}], controller_ops[], seed,
calibrated, fake, two_digit, note}`; sınır dışı istekte **HTTP 422** +
`{ok:false, out_of_range:true, error, limit:"0..81"}`; ayrıştırılamayan girdide **HTTP 400**.

## 3. Doğrulama (canlı sunucu, `http://127.0.0.1:8000`)

| kontrol | sonuç |
|---|---|
| `GET /health` | ✓ `{"ok":true,"model":"gemma3:4b","seq":47}` |
| `GET /state` | ✓ (`bus, classifier, executor, loop, state`) |
| **`POST /chat`** (mevcut kelime sınıflandırma) | ✓ `elma` → "yiyorum · doydum [eating · full]", sınıflandırıcı güven **0.9674** → **bozulmadı** |
| `POST /calc` `3+5` | ✓ **8**, sinek çağrısı **5**, seed **0**, kalibre ✓ |
| `POST /calc` `7x8` | ✓ **56**, çağrı **56** |
| `POST /calc` `9/4` | ✓ **2 kalan 1**, çağrı **8** |
| `POST /calc` `fake=1`, `3+5` | ✓ bozuk (**81**) + `note` = "SAHTE SİNEK ETKİN…" |
| `POST /calc` `80+5` / `3-5` / `9x10` | ✓ **HTTP 422** + açık hata metni |
| `GET /` (chat3d.html) | ✓ 122.623 bayt; `calcpPanel/calcpBtn/calcpBatch` **var**; mevcut `chat/viz/log/three.min.js` **var** |

### `_calc_smoke.py` — otomatik toplu test (**ikame**; 10 s, `KIRMIZI: 0`)

```
[OK] mevcut uç /health yanıt veriyor
[OK] mevcut uç /state yanıt veriyor
[OK] mevcut uç /chat kelime sınıflandırması çalışıyor
[OK] /calc 1..9 tüm çiftler BEKLENEN davranış (324 istek)   -> 324/324
[OK] sahte sinek cevapları BOZULUYOR (<=0.60)               -> 0.2346 (76/324)
[OK] sahte modda 'not' alanı uyarı içeriyor
[OK] sınır dışı 80+5 / 3-5 / 9x10 AÇIK hata (HTTP 422)
KIRMIZI: 0   SONUC: TUM TESTLER GECTI
```

**İKAME UYARISI:** kapanış paketinin istediği `_fly_smoke.py` ve `_fly_frontend_test.js`
**repoda yoktu** (`RELEASE_PREFLIGHT.md` §6) → bu betik onların **yerine** geçer; **onların kendisi
değildir**. Kanıtladığı şey: (a) mevcut üç uç çalışıyor, (b) yeni uç beklenen davranışta,
(c) sahte çekirdek bozuyor, (d) sınır dışı açık hata. **Kelime sınıflandırmanın "değişmediği"**
çapraz kanıtı: `POST /chat` canlı yanıt verdi ve `server.py`'de o rotaya **hiç dokunulmadı** ✓.

## 4. İlk koşuda 1 KIRMIZI vardı (gizlenmedi)

`_calc_smoke.py` ilk koşusunda `/calc 1..9` = **288/324** ✗; kırmızıların tamamı **a<b çıkarmaları**
(36 çift). Neden: test, **tarihsel** `calc_measure` mantığını (çıkarma 0'a kırpılır → `want=0`)
bekliyordu; **arayüz ise negatifi açıkça reddediyor** (AŞAMA 1 §4.3 gereği). Yani **test hatası**ydı,
kod hatası değil ✗ → test, "negatif çıkarma → **ret** beklenir" olarak düzeltildi ve
**324/324** oldu ✓. Bu tasarım farkı sınır panosunda da yazılı ✓.

## 5. Bu aşamanın sınırlılıkları / notları

- **Arayüz, ölçülen hesap makinesinin ön yüzüdür**; yeni bir bilimsel iddia **içermez**.
  Rakamlar (`%54.0`, `GA95 [44.3, 63.4]`, 54 kabul) **`RAPOR_FAZ_4E.md`** ve
  **`results_p4e/final81_seeds.csv`**'den alındı; **uydurulmadı**.
- Kullanılan sinek **seed 0** (kalibrasyon: tablo 1.0000 ✓). Diğer 53 kabul edilen tohum da
  `build_fly.py <tohum>` ile üretilebilir.
- **Sunucu ayakta bırakıldı** (PID 2228, port 8000) — kapatmak için: `Stop-Process -Id 2228`.
- **WIP güvenceye alındı:** kullanıcının commit edilmemiş işi `1bf5dfb`'de **içerik değiştirilmeden**
  kaydedildi; köprü `server.py`/`chat3d.html` üzerine **ekleme** olarak yazıldı ✓.
- Ollama/LLM yolu **kaldırılmadı**; "ölü kod" iddiası `[VERIFY]` olarak duruyor (PREFLIGHT §5).

## 6. Kapanış SONRASI düzeltme (kullanıcı isteği): **sohbet kutusu → sinek çekirdeği**

**Sorun (bildirildi):** sohbet kutusuna `5+3=?` yazıldığında cevap **kelime sınıflandırıcıdan**
geliyordu ("kelime tanınmıyor · bilinen örnekler …"), yani **sineğin hesap çekirdeği kullanılmıyordu**.

**Düzeltme (ADDITIVE, `_chat` içinde):** `_chat`'te **`/öğret` kontrolünden SONRA**, mevcut
sınıflandırma akışından **ÖNCE** tek bir kapı eklendi:

```python
if self._try_chat_calc(message, payload, origin):
    return
```

- Kapı **dar**: mesaj, `=` ve `?` temizlendikten sonra **yalnızca** `<tam sayı> <op> <tam sayı>`
  biçimindeyse (`numcog/fly_calc.looks_arithmetic`) hesap çekirdeğine gider; **harf içeren hiçbir
  mesaj yakalanmaz** ✓ (ör. `3 tane elma` → eski akış ✓).
- Cevap, mevcut `say` olayıyla (`mode:"system"`) sohbete düşer ✓ ve **iş bölümünü yazar**:
  `🧮 5 + 3 = 8 · sinek: 3 adım (n→n±1) · sayaç/döngü kontrolcüde`.
- `numcog/fly_calc` yüklenemezse `_try_chat_calc` **`False`** döner → **eski davranış bozulmaz** ✓.

**Canlı doğrulama** (`/chat`, yeni kod; sunucu yeniden başlatıldı):

| mesaj | cevap | kaynak |
|---|---|---|
| `5+3=?` | **🧮 5 + 3 = 8 · sinek: 3 adım (n→n±1) · sayaç/döngü kontrolcüde** | `numcog_calculator` |
| `7x8` | 🧮 7 × 8 = **56** · sinek: 56 adım | `numcog_calculator` |
| `12-7` | 🧮 12 − 7 = **5** · sinek: 7 adım | `numcog_calculator` |
| `9/4` | 🧮 9 ÷ 4 = **2 (kalan 1)** · sinek: 8 adım · kalan kontrolcüde | `numcog_calculator` |
| `80+5=?` | 🧮 **açık hata**: "sonuç 85 > 81: sinek tablosu 0..81 ile sınırlı" | `numcog_calculator` |
| `elma` | "yaklaşıyor · şeker" (**değişmedi**) | `connectome` |
| `ne haber` | "kelime tanınmıyor · bilinen örnekler (besin)…" (**değişmedi**) | `oov` |
| `3 tane elma` | connectome (**hesap makinesine gitmiyor**) | `connectome` |

**Test:** `_calc_smoke.py`'ye **4 yeni sohbet kontrolü** eklendi → `KIRMIZI: 0` ✓.
**Not:** `= ` ve `?` temizlenir; **iki haneli operand** sonuç ≤ 81 ise çalışır; **negatif** ve **> 81**
sonuçlar **açık hata** verir (sessiz yanlış cevap yok) ✓.

