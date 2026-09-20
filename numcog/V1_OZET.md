# V1 ÖZET — Faz 0–6-0b kapanış özeti (yeni ölçüm YOK)

Tarih: 2026-09-20. Bu belge **yalnızca mevcut raporlara** dayanır; **yeni ölçüm içermez**.
Dil kuralı: **"bu veride / bu yöntemle / bu ızgarada"**. "Kanıtladık", "kusursuz", "kesin kapandı"
gibi ifadeler **kullanılmaz**.

## 1. Ne ölçüldü, ne bulundu (özet)

| Faz | Soru | Sonuç (bu veride, bu yöntemle) |
|---|---|---|
| 0 | VPN→KC nöropil/etiket yapısı | CX (EB/PB) nöropillerine sınırlı, γ-özel küçük bir VPN→KC yolu var; wedge/glomerül etiketi **yok** |
| 1 | Sayı kodlama (VPN→KC) | Gerçek VPN→KC + top-k ile 9×9 kosinüs yapısı kurulabiliyor; sayı→VPN ataması **keyfî** |
| 2 | "Hangisi büyük" | Aralık içi test **0,992 ± 0,037**; **aralık dışı 0,208 ± 0,131**; gerçek ile shuffle **ayırt edilemedi** |
| 2b | Ekstrapolasyon tanısı (KEŞİFSEL) | Kenar dolgusu/paylaşımlı okuma tanıları; Faz 2 sonuçları görüldükten sonra eklendi |
| 3 / 3c | Kural vs ezber | Ezber (bitişik hedefler) çalışıyor; **kural (G2) tüm kollarda 0,000**; gerçek/shuffle/örtüşme-kontrol ayrışmadı |
| 4A / 4A-2 | Hesap makinesi çekirdeği | Nominal okuma ile n±1 tablosu kurulabiliyor; **durum, sayaç, döngü kontrolcüde** |
| 4B-0 | Çarpma + CX keşfi | Çarpma 0,790 (N=40 **aralık** sınırı); CX tipleri (EPG 51, PEN 42, Delta7 42) ve kenar sayıları ölçüldü |
| 4C | N=40 tablo hatası tanısı | **ep10x** dondu; hatalar kenarda (n=0,1,38,39,40) toplanıyor |
| 4D / 4E / 4F | N=81 kapasitesi | Hiçbir ızgara hücresi **%95** ölçütünü geçmedi (en iyi **%93,3**); **H4d.1/H4f.1 çürüdü** |
| 4E | N=81 tanısı + kalibrasyon | Hatalar kenarda + **kod çakışması**; **kapalı form = delta kuralı**; shuffle: **ayırt edilemedi** |
| 5 | Yapısal analiz (M1–M4) | M2/M3/M4 **ayrışıyor**; **M1 dejenere** (derece dizisi fonksiyonu); shuffle'da görev farkı yok |
| 6-0 / 6-0b | CX halka geometrisi | **Halka bu veri sürümünde kurulamadı** (H6.1–H6.3 ve H6b.2 çürüdü) |

## 2. Mühendislik durumu (Faz 4 ziniciri)

- **Kapılı hesap makinesi:** N=81'de 1..9 tüm add/subtract/**multiply/divide = 1,0000** ve zincir
  p^k = 1,0 (k = 0..81) — **ancak yalnızca kalibrasyon kapısından geçen 54/100 tohumda**
  (ret oranı **%46,0 [36,6–55,7]**). Kapı, **kontrolcü tarafı bir kalite kontrolüdür**; kural
  öğrenme değildir.
- **Durum kontrolcüde:** sayaç, döngü, durma koşulu, geri besleme ve okuma kontrolcüde;
  **sinek durum taşımıyor** (bu, v1'in en net mimari özelliğidir).
- **N=81'de %95 ölçütü bu ızgarada sağlanmadı** (en iyi %93,3: σ=2,0, top-k=80, dolgulu);
  top-k=120 hücrelerindeki float32 taşması **sayısal ıraksama**dır, **kapasite bilgisi taşımaz**.
- **İki haneli yedek** tasarım olarak etiketlendi; **uygulanmadı**.

## 3. En net iki sınır

1. **Gerçek connectome ile shuffle/kontrol kolları görev performansında ayrışmadı**
   (Faz 2, 3, 3c, 4E, 5). Yapısal ölçütler (M2–M4) ayrışsa da, **görevde** bir üstünlük
   **bu veride, bu mimarilerde ve bu ızgaralarda gösterilemedi**.
2. **CX halka geometrisi bu veri sürümünde kurulamadı:** soma tabanlı testler (H6.1–H6.3) ve
   koordinattan bağımsız spektral test (H6b.2) çürüdü; wedge/glomerül ROI etiketi ve sinaps-başına
   tablo **yok**; somalar ile PEN giriş merkezleri arasında ~80° uyumsuzluk ölçüldü.

## 4. Sınırlılıklar (v1'in tamamı için)

- **Grup 2 = 3 öğe**, **tek mimari** (feedforward KC + doğrusal okuma) → kural sonuçları bu mimariye
  özgüdür; genel bir yargı değildir.
- **Görev davranışının tamamı kontrolcüde** olduğu için "sineğin hesabı" iddiası ölçülmedi;
  ölçülen şey **kod + okuma katmanının n±1 tablosunu kurabilmesi**dir.
- **Sayı→VPN ve operatör→ALPN atamaları keyfî**; gerçek olan yalnızca **VPN→KC / ALPN→KC kablolaması**.
  Termometre kodu **dış yardımcı**dır.
- **Faz 2b post-hoc**; bazı ölçütler trivial (Faz 4A-2'de referans kol tam puan aldı);
  **M1 testi dejenere** (derece-koruyan null'a karşı test edilemez).
- Shuffle karşılaştırmaları **n=30 ve güç sınırlı**; "ayırt edilemedi" ≠ "fark yok".
- **Simülasyon**; canlı sinek değil. **Tek connectome örneği** (hemibrain 783).
- Öğrenme kuralı/hassasiyet (lr, float32) ızgara boyunca **değiştirilmedi**; değiştirmek
  TASARIM DEĞİŞİKLİĞİ olurdu ve bu fazlarda yapılmadı.

## 5. Faz 7'ye devredilen açık soru

**Sayıyı kontrolcü değil, ağın iç durumu taşıyabilir mi?** v1'de durum **tamamen** kontrolcüdeydi;
bu, v1'in bilinçli tasarımıydı ve **v2'nin asıl sorusudur**. Faz 7-0 bu soru için **çerçeveyi
ön-kaydeder** ve **alt ağ adaylarını ölçer**; **hiçbir dinamik deney çalıştırmaz**.
