# RAPOR — İKİ HANELİ GİRDİ ölçümü (AŞAMA 3, KEŞİFSEL)

Tarih: 2026-09-20. Ön-kayıt **ölçümden ÖNCE** commit edildi: **`d6bd546`**
("Asama 3 on-kayit (KAPANIS PAKETI - KESIFSEL iki haneli girdi olcumu)").
Kod: **`numcog/two_digit_probe.py`** · Sonuç CSV: **`numcog/results_release/two_digit.csv`**.
Dil: **"bu veride, bu modelde, bu ızgarada"**. **KEŞİFSEL** — Faz 4E'nin ön-kayıtlı ölçütlerini
değiştirmez.

## 1. Soru, beklenti, ölçüt (ön-kayıtlı)

- **Soru:** hesap makinesi **iki haneli girdilerle** (en az bir operand ≥ 10) çalışır mı?
- **Beklenti:** **sonuç ≤ 81 ise ÇALIŞIR** — çünkü çekirdek yalnızca `n → n±1` **tablosudur**
  (durum 0..81); operandın büyüklüğü **döngü sayısını** değiştirir, tabloyu değiştirmez.
- **Çürütme eşiği:** doğruluk **< %99** (her işlemde). **81 üstü işlemler ÖLÇÜLMEZ** (arayüz reddeder).

## 2. Tasarım (ölçümden önce sabit)

| öğe | değer |
|---|---|
| tohumlar | **20 kabul edilen tohum**: `[0, 3, 5, 7, 8, 9, 10, 11, 12, 14, 15, 20, 21, 22, 23, 24, 25, 28, 31, 32]` (`results_p4e/final81_seeds.csv`, `table == 1.0`) |
| örnekleme | tohum başına rastgele tam sayı `a,b ∈ [1,81]`, **en az bir operand ≥ 10** |
| süzgeç | beklenen sonuç **[0,81]** (çıkarmada `a ≥ b`; toplamada `a+b ≤ 81`; çarpmada `a·b ≤ 81`; bölmede `b ≥ 1`) |
| öğe | **her işlem için 200 çift × 20 tohum = 4.000** (toplam **16.000**) |
| eşik | beklenen sonuç == (çekirdek + kontrolcü) sonucu; bölmede **bölüm ve kalan** |

## 3. Sonuçlar (ham)

```
=== OZET (iki haneli girdi; 20 tohum x 200 cift/islem) ===
  add       dogruluk=1.0000 +- 0.0000 (n=20 tohum, 4000 cift) -> CALISIYOR (>= %99)
  subtract  dogruluk=1.0000 +- 0.0000 (n=20 tohum, 4000 cift) -> CALISIYOR (>= %99)
  multiply  dogruluk=1.0000 +- 0.0000 (n=20 tohum, 4000 cift) -> CALISIYOR (>= %99)
  divide    dogruluk=0.9935 +- 0.0023 (n=20 tohum, 4000 cift) -> CALISIYOR (>= %99)
  GENEL dogruluk=0.9984 | toplam cift=16000 | sure=349 s
  esik %99 -> GECTI
```

**Beklenti DESTEK:** iki haneli girdilerde (sonuç ≤ 81) **genel doğruluk 0,9984 ≥ 0,99** ✓;
`add`/`subtract`/`multiply` **tam 1,0000** ✓.

## 4. `divide` neden 0,9935? (mekanizma — ÖLÇÜLDÜ)

Sapmanın kaynağı **sinek değil, KONTROLCÜDÜR**: tarihsel `CyborgFly.divide` döngüsü
`while n >= b and q < 50`dur; **bölüm 50'ye ulaşınca döngü erken durur** ve sonuç kırpılır.
Doğrulama (tarihsel kontrolcü, kayıtlı ağırlıklarla):

| ifade | sonuç | beklenen | eşleşme |
|---|---|---|---|
| `81/1` | **50** | 81 | ✗ (döngü `q<50`'de durdu) |
| `60/1` | **50** | 60 | ✗ (aynı) |
| `50/1` | 50 | 50 | ✓ |
| `81/2` | 40 | 40 | ✓ (80 sinek çağrısı) |

Sapma oranı bu mekanizmayla **uyumludur**: örneklemede `b=1` ve `a ≥ 51` olasılığı ≈ %0,5 →
ölçülen %0,65 ✓ *bu veride, bu modelde, bu ızgarada*.

**Bu yüzden arayüz sertleştirildi (ölçümden sonra eklenen GUARD; ölçüm tasarımı/ölçütü DEĞİŞMEDİ):**
`fly_calc.run` artık **beklenen bölüm ≥ 50** ise **açık hata** verir
("bölüm 81 >= 50: kontrolcünün durma sınırı (q < 50) sonucu kırpar") → **sessiz yanlış cevap yok** ✓.
Ölçüm betiği kontrolcüyü **doğrudan** çağırdığı için (arayüzü kullanmaz) bu guard **ölçümü
değiştirmez** ✓ — ölçüm, tarihsel kontrolcünün **gerçek** davranışını raporlar ✓.

## 5. Yorum ve sınırlar

- **Beklenti doğrulandı:** iki haneli girdi, çekirdek için **yeni bir yetenek değildir**;
  çekirdek yalnızca `n → n±1` yapar, büyük operand yalnızca **daha çok adım** demektir
  (ör. `81/2` = **80 sinek çağrısı**).
- **"ÇOK HANELİ ARİTMETİK" YOKTUR**; **iki haneli (onlar/birler) tasarımı UYGULANMADI** —
  bu ölçüm yalnızca girdi büyüklüğünü sınar ✓.
- **81 üstü sonuçlar ölçülmedi**; arayüz bunları **açık hata** ile reddeder ✓ (sessiz yanlış yok).
- **Kontrolcü sınırı:** bölüm ≥ 50 → tarihsel döngü kırpar (yukarıda) ✓; arayüz bunu reddeder ✓.
- Diğer sınırlar Faz 4E/7-0 ile aynı: **tek connectome** (hemibrain 783), **simülasyon**,
  **sayı→VPN ataması keyfî**, **kalibrasyon kapısı tohumların %46'sını reddeder**,
  **durum sinekte değil kontrolcüde**.
