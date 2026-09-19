# numcog — Hipotezler (ön-kayıt)

Bu dosya deney protokolünün bir parçasıdır: her fazın hipotezi, o fazın ölçümlerinden
**ÖNCE** buraya yazılır ve commit edilir. Ölçümden sonra bu metin **değiştirilmez**.
Çürüyen bir hipotez ilgili `RAPOR_FAZ_X.md` içinde "çürüdü" olarak raporlanır; düzeltilmiş
hipotez yeni bir bölüm olarak eklenir, eskisi silinmez.

---

## FAZ 0 — Veri keşfi: VPN (görsel projeksiyon nöronu) → KC bağlantısı

Kayıt tarihi: 2026-09-19. Aşağıdakiler veriye bakılmadan önce yazılmıştır.
Ön bilgi kaynakları: (i) biyolojik literatür önseli, (ii) mevcut kodun şeması —
kenar listesi `pre_pt_root_id → post_pt_root_id, syn_count, neuropil`; anotasyonlarda
`cell_class` içinde `ALPN` / `Kenyon_Cell` / `MBON` sınıflarının bulunduğunu `sniff.py`
zaten kullanıyor (`sniff.circuit()` gerçek ALPN→KC matrisini, 5177 KC × 685 ALPN,
≥3 sinaps olarak kuruyor).

- **H0.1 — VPN→KC varlığı ve oranı.** FlyWire v783 anotasyonlarında "görsel projeksiyon
  nöronu" (VPN) olarak sınıflanan nöronlar vardır ve bir kısmı Kenyon hücrelerine (KC)
  sinaptik bağlanır. Ancak VPN→KC kenar sayısı ALPN→KC'nin küçük bir azınlığıdır
  (beklenti: ALPN→KC'nin ~%1–10'u mertebesinde).
- **H0.2 — KC alt tipi seçiciliği.** VPN→KC girdisi KC alt tipleri arasında eşit dağılmaz;
  ağırlıklı olarak γ-d (KCg-d) hücrelerine iner. αβ (KCab) ve α'β' (KCa'b') alt tipleri
  doğrudan VPN girdisinden çok az / neredeyse hiç almaz.
- **H0.3 — Kenar ağırlıkları.** VPN→KC kenarı başına sinaps sayısı küçüktür
  (medyan ≤ ~10; ALPN→KC ile aynı mertebe).
- **H0.4 — Nöron sayısı.** KC'lere doğrudan bağlanan VPN nöron sayısı 685 ALPN'den
  belirgin biçimde küçüktür (onlarca–yüzler mertebesi).
- **H0.5 — Giriş katmanı stratejisi (ön-kayıt kuralı).** H0.1 tutarsa — gerçek ve
  kullanılabilir boyutta bir VPN→KC matrisi varsa — strateji **(a)** olur: `coarse_kc`'de
  gerçek VPN→KC matrisi kullanılır. Tutmazsa (VPN→KC yoksa ya da sayısal kodlama için çok
  küçük/seyrekse) strateji **(b)** olur: kaba kodlama ALPN/PN girdisi üzerine uygulanır ve
  raporda "görsel kanal gerçek bir görsel devre değil, soyut bir sayı kodudur" ifadesi
  açıkça yazılır.

---

## FAZ 1 — Sayı kodlama katmanı

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır.

### Kullanılabilirlik ölçütü (coarse_kc "kullanılabilir" sayılması için ÜÇÜ birden)

- **U1 (monotonluk):** Spearman ρ(kosinüs benzerlik, |n−m|) ≤ **−0.5**.
- **U2 (kapsama):** tarama içindeki en az bir (aktivasyon kuralı, parametre)
  yapılandırmasında, 9 sayının tamamında aktif KC ≥ 1 **VE** ortanca aktif KC ≥ **5**.
- **U3 (çökme yok):** max_{n≠m} kosinüs(kod_n, kod_m) < **0.95**.

Üç koşuldan herhangi biri sağlanmazsa `coarse_kc` "kullanılamaz" sayılır ve önceden
yazılmış yedek **(b)** devreye girer. Ölçüt, sonuç görüldükten sonra DEĞİŞTİRİLMEZ.

### Beklentiler

- **E1:** `coarse_direct`'te ρ < −0.9 (Gauss kaba kod neredeyse kusursuz monoton).
- **E2:** `hash`'te |ρ| < 0.2 (yapı yok).
- **E3:** `coarse_kc`'de ρ, `coarse_direct`'ten zayıf ama `hash`'ten belirgin güçlü
  (beklenti −0.9 < ρ ≤ −0.5); gerçek VPN→KC matrisi yalnızca γ-d KC'lerine dar bir kanal
  olduğu için monotonluğun bir kısmını kaybetmesi beklenir.
- **E4:** sabit eşik (coincidence ≥2/3/4) kuralları çok az KC aktif bırakır (çoğu sayı
  için 0 ya da birkaç); top-k (APL-benzeri global inhibisyon) yeterli KC üretir — U2'yi
  ancak top-k sağlar.
- **E5:** VPN→sayı-ekseni atama permütasyonları arasında ρ varyansı KÜÇÜK olacak
  (std ≤ ~0.1), çünkü 265 VPN üzerinde 9 Gauss merkezi homojen dağılır. Belirgin büyük
  çıkarsa bu, ayrı bir bulgu olarak raporlanır.

### Yorum disiplini (önceden yazılmıştır)

Sayı→VPN ataması **keyfîdir** (bizim kodlamamız); gerçek olan yalnızca VPN→KC aşağı akış
kablolamasıdır. Bu ayrım raporda açıkça yazılacaktır.

---

## FAZ 2 — Büyüklük karşılaştırması ("hangisi büyük")

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 1'de ölçülen hiperparametreler
kullanılır: `coarse_kc` için σ=1.5, top_k=40; iki sayı **ayrı popülasyonlarla** sunulur.

### Eğitim protokolü (sabitlenmiştir; sonuca göre DEĞİŞTİRİLMEZ)

- Öğrenme kuralı: delta kuralı (LMS); hedefler ±1 (sol büyük = +1); tahmin = sign(w·x + b).
- Öğrenme oranı **lr = 0.01**.
- Epoch = **500** (sabit; erken durma YOK).
- Batch = **tam batch** (10 eğitim çiftinin tamamı, ortalama gradyan).
- Başlatma: w = tohumlu küçük Gauss gürültüsü (std 0.01), b = 0.
- Tohum, (a) VPN→sayı atama permütasyonunu **ve** (b) ağırlık başlatmasını DEĞİŞTİRİR (≥20 tohum).

### Veri

- Eğitim: (1,2),(2,3),(4,5),(5,6),(1,3) + tersleri → 10 çift.
- Test1 (aralık içi): (3,5),(3,6),(2,5) + tersleri → 6 çift.
- Test2 (aralık dışı): (7,8),(8,9),(7,9) + tersleri → 6 çift.
- Sızıntı: hiçbir test çifti eğitimde yoktur; otomatik assert ile doğrulanır.

### Hipotezler

- **H2.1 (aralık içi):** `coarse_direct` ve `coarse_kc`, aralık içi test çiftlerinde %50'nin
  anlamlı üstünde; `hash` %50'de kalır.
- **H2.2 (aralık dışı — kademeli düşüş):** geniş σ=1.5 kaba kodlaması nedeniyle aralık dışında
  ANİDEN şansa düşüş beklenmez; doğruluk eğitim aralığına uzaklıkla orantılı kademeli azalır
  (7 vs 8, 8 vs 9'dan daha iyi sonuç verir).
- **H2.3 (mesafe etkisi):** doğruluk |n−m| ile pozitif korelasyon gösterir. Eğitimde fark=2
  çifti (1,3) olduğundan mesafe etkisi, test çiftleri içindeki varyansla da ayrıca yorumlanır.
- **H2.4 (gerçek vs karıştırılmış):** Faz 1 sonuçlarına dayanarak gerçek VPN→KC matrisi,
  derece-koruyan karıştırılmış (shuffled) matristen anlamlı bir öğrenme farkı yaratmaz.

### Asıl soru

"KC katmanı (gerçek veya rastgele) `coarse_direct`'e kıyasla ne kadar kayıp yaratıyor?"

---

## FAZ 2b — Ekstrapolasyon tanısı (KEŞİFSEL)

Kayıt tarihi: 2026-09-19. **FAZ 2 SONUÇLARI GÖRÜLDÜKTEN SONRA eklenmiştir** (Faz 2'de ölçülen
aralık-dışı ters çevirmeyi teşhis etmek için). Faz 2'nin hipotezleri ve raporu DEĞİŞTİRİLMEDİ;
bu bölüm yeni, keşifsel bir tanıdır.

### Hipotezler

- **H2b.1 (skor eğrisi):** eğitilmiş okuma katmanının tek-sayı skor eğrisi f(n) (n=1..9;
  sol=n, sağ=5 referans), **n≈6–7 civarında tepe yapar** (eğitim aralığının üst kenarı),
  8–9'da azalır. Bu, ters çevirmenin doğrudan imzasıdır.
- **H2b.2 (kenar dolgusu):** sayı ekseni [1,9] yerine dolgulu **[-3,13]** yapılınca ters
  çevirme **AZALIR ama şansın ÜZERİNE çıkmaz** (aralık dışı doğruluk ≈ %50).
- **H2b.3 (paylaşımlı okuma):** w_sol = −w_sağ (işaret-ters paylaşımlı, "karşılaştırma"
  yapısını mimariye gömme) aralık içini **KORUR**, aralık dışını şansa **YAKLAŞTIRIR** (~%50).
  NOT: bu bir **dış yardımdır** (mimariye gömülü kısıt); raporda açıkça yazılacaktır.
- **H2b.4 (eğitim aralığı):** eğitim aralığı daraldıkça (1-8 → 1-6 → 1-4) ekstrapolasyon
  uzaklığıyla doğruluk düşer ve ters çevirme derinleşir.
- **H2b.5 (shuffle):** tüm kollarda gerçek W ile derece-koruyan karıştırılmış W arasında
  anlamlı fark yoktur (Faz 1/2 ile tutarlı).



