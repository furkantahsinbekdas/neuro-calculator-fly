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

---

## FAZ 3 — Toplama/çıkarma (n±1), operatör = koku, sayı = görsel

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-2b hipotezleri/raporları DEĞİŞTİRİLMEDİ.

### Tasarım (sabitlenmiştir)

- Sayı: Faz 1-2 en iyi kodlayıcı — σ=1.5 Gauss, top-k=40, gerçek VPN→KC (427 KC × 265 VPN,
  min_syn=1). Operatör: iki ayrık rastgele ALPN alt kümesi (op+, op−), her biri 319 ALPN'in
  ~%10'u (32 birim), ikili 1.0, tohum başına yeniden seçilir. KC: skor = W_vpn·g(n) +
  W_alpn·op (AYNI 427 hücrede toplanır), top-k=40 global inhibisyon. Çıktı: sonuç 0..10
  (11 sınıf, şans ≈ %9.1); çok-sınıflı delta kuralı (one-vs-all, doğru +1 / diğerleri −1,
  argmax), lr=0.01, epoch=1000, tam batch, erken durma yok. 20 tohum (VPN permütasyonu +
  operatör ALPN alt kümeleri + ağırlık başlatması).

- Veri: EĞİTİM n∈{1..6} dönüşümlü op (6 çift); TEST_KOMBINASYON aynı n'lerin diğer op'u
  (6 çift, her n ve her op eğitimde görüldü); TEST_YENI_N n∈{7,8,9} iki op (6 çift,
  ekstrapolasyon). Sızıntı otomatik assert.

### Kollar

1. hash · 2. coarse_direct (VPN⊕ALPN birleşik, KC yok) · 3. coarse_kc gerçek ·
4. coarse_kc derece-koruyan karıştırılmış · 5. coarse_kc ortak 151 KC çıkarılmış ·
6. coarse_kc ALPN girdisi aynı sayıda rastgele KC'ye verilmiş (örtüşme sayısı kontrolü) ·
7. termometre/rampa kodu (n → ilk ⌊n·265/9⌋ birim aktif) + aynı KC katmanı (**DIŞ YARDIM**).

### Hipotezler ve çürütme eşikleri

- **H3.1:** coarse_direct EĞİTİM doğruluğu 1.0'ın belirgin altında kalır (toplamsal okuma
  (n,op) konjunksiyonunu çözemez). Çürütme eşiği: eğitim doğruluğu ≥ 0.90 olursa çürür.
- **H3.2:** coarse_kc EĞİTİM ve TEST_KOMBINASYON doğruluğu coarse_direct'ten yüksektir.
  Çürütme eşiği: %95 GA'ların örtüşmesi.
- **H3.3:** Kol 5 (ortak KC çıkarılmış) doğruluğu Kol 3'ten anlamlı düşer. Çürütme eşiği: GA örtüşmesi.
- **H3.4:** Kol 4 ve Kol 6, Kol 3'ten ayırt edilemez (GA örtüşür). Ayrışırlarsa bu ÖNE ÇIKARILIR.
- **H3.5:** TEST_YENI_N doğruluğu tüm gerçek-kod kollarında şansa (~%9.1) yakın ya da altında;
  yalnızca Kol 7 belirgin daha iyi. Çürütme eşiği: Kol 7'nin GA'sı gerçek-kod kollarıyla örtüşürse.

### Yorum disiplini (önceden yazılmıştır)

Sayı→VPN ve operatör→ALPN atamaları **keyfîdir**; gerçek olan yalnızca VPN→KC ve ALPN→KC
aşağı akış kablolamasıdır. Kol 7 bir **dış yardımdır**. Bu ayrımlar raporda açıkça yazılacaktır.

### VERİ TASARIMI DÜZELTMESİ (ölçüm sırasında bulundu; hipotez DEĞİL)

Ön-kayıtlı "dönüşümlü op" bölümü (her n tek op'la, 6 çift) ölçüldüğünde **tüm kolların
TEST_KOMBINASYON'da 0.000** verdiği görüldü. Neden: bu bölüm n-paritesi ↔ op arasında mükemmel
bir korelasyon yaratıyor; model op'u yok sayıp "n → sonuç"u ezberliyor ("sadece-n" kontrolü de
0.000). Bu, H3.2'yi (kural mı ezber mi) test edilemez kılar. Bu bir VERİ KUSURU'dur (hipotez
değişikliği değil). Düzeltme: bazı n'ler (1,2,3) İKİ op'la eğitilir, böylece op kullanımı
zorlanır; TEST_KOMBINASYON = tek op'la eğitilmiş n'lerin (4,5,6) eksik op'u. Yeni EĞİTİM:
(1,+),(1,−),(2,+),(2,−),(3,+),(3,−),(4,+),(5,−),(6,+) [9 çift]; TEST_KOMBINASYON:
(4,−),(5,+),(6,−) [3 çift]. Hipotezler aynıdır; yalnızca veri bölümü düzeltildi.

---

## FAZ 3c — Kural öğrenimi: sürekli/topolojik çıktı (nominal sınıf yerine)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 3'ün nominal-çıktı kısıtını aşmak
için çıktı, girdi ile AYNI topolojik kaba kodla temsil edilir (kaydırma = kural/dönüşüm).

### Kilitli ön-kayıt (DEĞİŞTİRİLMEZ)

- Çıktı kodu: ana kol **Gauss σ=1.5**; ayrı kontrol kolu **Termometre** (t → ilk ⌊t·265/10⌋
  birim). Hedef aralığı 0..10. Eksen [0,10], 265 birim, girdi sayısı da aynı eksende Gauss.
- Kayıp: **MSE**. Eğitim: **lr=0.01, epoch=500, tam batch, erken durma YOK**.
- Çıkarım (decode): üretilen vektörün 0..10 ideal vektörlerine **kosinüs** benzerliğiyle argmax.
  Ana metrik = kesin eşleşme; yan metrik = ±1 tolerans.

### Veri bölmesi (sabit; asserts zorunlu)

- Eğitim n∈{1..7}: (n,+) tümü (7) + (n,−) n∈{1,2,3} (3) = **10 çift**. TEST_YENI_N = {8,9} (4 çift).
- TEST_KOMBINASYON (aynı n, görülmemiş op): (4,−),(5,−),(6,−),(7,−).
  - **Grup 1 (komşu bilinen):** (4,−) [komşu (3,−) eğitimde]. (1 öğe)
  - **Grup 2 (izole/kural):** (5,−),(6,−),(7,−) [ne (n−1,−) ne (n+1,−) eğitimde]. (3 öğe)
- Asserts: (1) eğitimde n-paritesi↔op korelasyonu YOK; (2) sızıntı YOK; (3) Grup 2 izolasyonu
  kesin; (4) eğitim hedefleri bitişik (ölü çıktı birimi yok). Grup 2 < 6 → "istatistiksel güç
  düşük" notu rapora eklenir.

### Kollar

coarse_direct (VPN⊕ALPN, KC yok, Gauss çıktı) · coarse_kc_gercek (151 ortak, Gauss) ·
coarse_kc_shuffled (derece-koruyan, Gauss) · coarse_kc_ablasyon (151 ortak çıkarılmış, Gauss) ·
coarse_kc_ortusme_kontrol (rastgele aynı-sayı ortak, Gauss) · coarse_kc_gercek_termometre
(151 ortak, **Termometre çıktı**).
Taban çizgileri: "hep n+1", "op yok say, n kopyala (kimlik)", "rastgele".

### Hipotezler ve çürütme eşikleri

- **H3c.1 (kural):** Grup 1'de interpolasyon başarısı beklenir; asıl test **Grup 2'de**
  coarse_kc_gercek şans/taban çizgilerinin anlamlı üstünde. Çürütme: Grup 2'de coarse_kc_gercek
  %95 GA'sının en iyi taban çizgisini içermesi ya da altında kalması.
- **H3c.2 (ekstrapolasyon sınırı):** TEST_YENI_N'de başarısızlık BEKLENİR (eğitimde aktif
  olmayan çıktı birimleri = ölü piksel). Şans yalnızca ulaşılabilir hedeflere göre. Çürütme:
  TEST_YENI_N %95 GA'sının şans düzeyini içermesi.
- **H3c.3 (biyolojik katkı):** coarse_kc_gercek, coarse_direct'i geçmeli; Kol 4 (ablasyon)
  Kol 2'ye göre anlamlı çökmeli. Çürütme: Kol 4/Kol 2 GA örtüşmesi VEYA coarse_direct'in
  gerçek KC'den ayırt edilememesi.

### Ek ölçümler

Eğitimde hiç hedef olmamış çıktı birimlerinin tespiti · op-duyarlılık (op çevrilince yön değişme
yüzdesi) · ≥20 tohum, ort±std+%95 GA · shuffle kontrolü. Sayı→VPN ve operatör→ALPN atamaları
keyfîdir; termometre bir DIŞ YARDIMdır.

---

## FAZ 4A — Ardışık hesap makinesi (mühendislik; iş bölümü açık)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-3c DEĞİŞTİRİLMEDİ.

### Tasarım (sabit)

- **Sinek çekirdeği:** yalnızca n→n±1 tablosu (Faz 3c mimarisi: coarse_kc + (n,op), sürekli
  Gauss çıktı, MSE, kosinüs decode), aralık 0..N. σ=1.5, top-k=40, lr=0.01, 500 epoch, 20 tohum.
- **Kontrolcü (Python):** sayaç, döngü, durma koşulu, durum geri beslemesi, sonuç okuma.
  **SİNEK DURUMU TAŞIMAZ; KONTROLCÜ TAŞIR.** "Uçuş simülatörü" gibi yeniden adlandırma YOK.
- Operatör kodu Faz 3'teki gibi (iki ayrık ALPN alt kümesi); değiştirilmedi.

### Adımlar

1. Kapasite (ÖNCE): N∈{10,20,40,81}, TÜM (n,op) çiftleri eğitimde; her N için eğitim doğruluğu,
   çıkarım güveni, süre. %100 çalışan en büyük N raporlanır.
2. (gerekirse) çok haneli: onlar/birler ayrı kanal, elde/borç kontrolcüde.
3. `numcog/calculator.py`: CyborgFly — add(a,b)= b kez +1; subtract(a,b)= b kez −1;
   multiply(a,b)= a'yı b kez topla; divide(a,b)= tekrarlı çıkarma + kalan. Kontrolcünün yaptıkları
   kodda ve raporda listelenir.
4. Ölçüm: 1..9 tüm a×b, a÷b; zincir uzunluğu k'ya göre doğruluk (p^k ile karşılaştır); gürültü;
   çağrı başına sinek çağrı sayısı.
5. Terminal demosu: her tick'te "Tick i: n → n±1, güven" logu.

### Hipotezler ve çürütme eşikleri

- **H4a.1 (kapasite):** sinek çekirdeği N≤20 için %100 eğitim doğruluğuna ulaşır; N=40 ve 81
  başarısız olur (KC kodu çarpışması). Çürütme: hiçbir N %100'e ulaşmazsa (kapasite <10) ya da
  N=81 bile %100 kalırsa.
- **H4a.2 (zincir bozulması):** k adımlı zincirin doğruluğu ≈ p^k (p = tek adım doğruluğu).
  Çürütme: ölçülen zincir doğruluğu p^k'dan belirgin saparsa (hata birikmiyor ya da fazla birikiyor).
- **H4a.3 (gürültü):** girdi gürültüsü arttıkça tek adım doğruluğu monoton azalır. Çürütme:
  monoton olmayan bir eğri.

---

## FAZ 4A-2 — Operatör yıkanmasının tanısı ve düzeltme denemesi

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-4A DEĞİŞTİRİLMEDİ.

### Ön-kayıt (sabit)

- **Çıktı: nominal sınıf okuması** (Faz 3 tarzı, one-vs-all ±1, argmax) — Faz 4A'nın MSE sürekli
  çıktısı DEĞİL. Sebep: Faz 3'te eğitim 1.0, MSE kimliğe çöktü. Bu bir **TASARIM SEÇİMİ**dir.
- Aralık: **N=10 ana, N=20 ikincil**. Öğrenme: lr=0.01, epoch=1000, tam batch, erken durma yok
  (Faz 3 ile aynı).
- **Başarı ölçütü (ölçümden önce):** N=10 eğitim doğruluğu **≥0.99** VE **op-duyarlılık ≥%95**
  (op çevrilince argmax tahmin değişir).
- g ∈ {1,2,4,8} **validasyonda** seçilir; hesap makinesi testi (multiply/divide) seçim için
  KULLANILMAZ.

### Adım 0 — Tanı (kod değişmeden)

top-k=40'ta aktif KC'lerin kaçı ALPN girdisi alıyor; ALPN sinyalinin hayatta kalma oranı;
(n,op+) vs (n,op−) kod kosinüs benzerliği (n başına); bunların g ile değişimi.

### Kollar (aynı öğrenme protokolü)

1. Referans (Faz 3 mimarisi, nominal, N=10).
2. Operatör kazancı ×g.
3. **Kanal başına inhibisyon (TASARIM DEĞİŞİKLİĞİ):** k_vpn ve k_alpn ayrı; ortak KC'ler için
   birleşik kural. Biyolojik yakınlığı raporda tartışılır (APL tek, global).
4. **Birleşim KC seti (VPN∪ALPN, ~5.000 hücre):** top-k tüm birleşimde; ALPN geniş, VPN dar kanal.
5. Kontroller: karıştırılmış matris, ortak-KC ablasyonu, örtüşme-kontrol, rastgele etiket.

### Karar

- Bir kol ölçütü sağlarsa: aynı CyborgFly kontrolcüsüyle add/sub/multiply/divide ölçülür (1..9,
  zincir k, gürültü). Sinek durum taşımaz, kontrolcü taşır.
- Hiçbir kol sağlamazsa: net raporlanır ve durulur. Kanal başına inhibisyon dahi başarısızsa
  **"feedforward KC + okuma, operatörlü ±1 tablosunda yetersiz"** denir.

### Hipotezler ve çürütme eşikleri

- **H4a2.1:** referans (g=1) ölçütü SAĞLAMAZ (operatör yıkanıyor). Çürütme: referans ≥0.99 & ≥%95.
- **H4a2.2:** g>1 operatörü kurtarır; bazı g ölçütü sağlar. Çürütme: hiçbir g sağlamaz.
- **H4a2.3:** kanal başına inhibisyon ölçütü sağlar. Çürütme: sağlamaz.
- **H4a2.4:** birleşim KC seti ölçütü sağlar. Çürütme: sağlamaz.

---

## FAZ 4B-0 — Central complex keşfi + çarpma düzeltmesi (kod YOK; keşif + küçük ölçüm)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-4A-2 DEĞİŞTİRİLMEDİ.

### A) Çarpma ölçümü (Faz 4A-2 nominal çekirdek, N=40)

- **H4b0.1:** a,b ∈ 1..6 (çarpım ≤36 < 40) çarpma doğruluğu **1.000** olur.
- **H4b0.2:** 1..9 çiftlerinde aralık içi (≤40) yüksek, aralık dışı (>40) düşük; ikisi AYRI raporlanır.
- **H4b0.3:** zincir hataları RASTGELE değil; belirli (n,op) girdilerinde toplanır (aralık sınırı
  civarı, ör. n≈0 ve n≈N). Çürütme: hatalar n boyunca homojen dağılırsa.

### B) Central complex keşfi

- **H4b0.4:** anotasyonlarda EPG / PEN / Delta7 hücre tipleri VAR (en az bir sütunda). Yoksa:
  bunu raporla ve dur (NaN tuzağı: boş kolonlar açıkça sayılır).
- **H4b0.5:** EPG wedge'leri dairesel komşuluk (halka) oluşturur; wedge sayısı ~16–18.
- **H4b0.6:** İşaret bilgisi mevcut ve literatürle uyumlu: EPG kolinerjik (uyarıcı), PEN kolinerjik,
  Delta7 glutamaterjik (inhibitör) — `top_nt` ile doğrulanır.
- **H4b0.7:** Karar: halka (hız) simülasyonu bu veriyle **mümkün** (ağırlıklar + işaretler + wedge
  halkası varsa), aksi halde gerekçeleriyle "mümkün değil" yazılır.

---

## FAZ 4C — Sistematik başlangıç hatası ve N=81 kapasitesi (mühendislik)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-4B0 DEĞİŞTİRİLMEDİ.
**Seçim ölçütü YALNIZCA tablo doğruluğudur** (tüm 2(N+1) (n,op) girdisinin doğru öğrenilmesi);
çarpma/bölme testi seçim için KULLANILMAZ.

### Adım 0 — Tanı (kod değişmeden; N=40, 100 tohum)

Kaç tohumda tablo tam doğru? Bozuk tohumlarda hangi girdiler yanlış, eğitim doğruluğu ve **marj**
(doğru sınıf skoru − en yüksek yanlış skor). (0,+),(1,+) ve kenar girdilerinin komşularıyla kod
benzerliği.

### Hipotezler ve çürütme eşikleri

- **H4c.1 (optimizasyon):** bozukluk epoch/lr yetersizliğinden; epoch ×4 ve ×10 tam-doğru tohum
  oranını belirgin artırır. **Çürütme:** ×4 ve ×10 sonrası tam-doğru oranı %95'e ulaşmazsa.
- **H4c.2 (kenar temsili):** n=0 ve n=N eksenin kenarında (kesilmiş Gauss) olduğu için bozuluyor;
  **dolgulu eksen** (n=0,N kenarda kalmaz) düzeltir. **Çürütme:** dolgu tam-doğru oranını artırmazsa.
- **Başarı ölçütü (ön-kayıtlı):** tohumların **≥%95'i** tabloyu **%100** öğrenir.
- **H4c.3 (N=81):** top-k ∈ {40,60,80,120} × σ ∈ {1.0,1.5} taramasında en az bir konfigürasyon
  ≥%95 başarı sağlar. **Çürütme:** hiçbiri sağlamazsa → iki haneli yedek (etiketli).

### Kollar (N=40; her düzeltme "TASARIM DEĞİŞİKLİĞİ")

1. Referans (Faz 4A-2: σ=1.5, top-k=40, lr=0.01, 1000 epoch).
2. Epoch ×4 ve ×10.
3. Sayı ekseninde dolgu (n=0 ve N kenarda kalmasın; eksen [−3, N+3]).
4. Sınıf dengeli kayıp (1/frekans ağırlık) ve farklı lr ızgarası {0.005, 0.02, 0.05}.

### Kontrolcü tarafı (KONTROLCÜ İŞİ, etiketli)

Açılışta kalibrasyon: sinek tüm tablo girdilerini sınar, geçemeyen sinek reddedilir. Bu bir **kalite
kontrolüdür; sinek kural öğrenmez**. Kaç tohum reddedildi raporlanır. Adım 1-4 başarılıysa gerekmez.

### Son ölçüm

Donmuş konfigürasyonla 1..9 tüm çarpma/bölme; tohum başına doğruluk dağılımı; zincir p^k
karşılaştırması. **Sinek durum taşımaz, kontrolcü taşır.**

---

## FAZ 4F — N=81: dolgu + σ genişletme (KISA, ön-kayıtlı)

Kayıt tarihi: 2026-09-20. Ölçümden ÖNCE yazılmıştır. Faz 0-4E dosyaları/sonuçları DEĞİŞTİRİLMEDİ.
**Seçim ölçütü YALNIZCA tablo doğruluğudur**; çarpma/bölme seçim için KULLANILMAZ.

### Izgara (sabit)

N=81; **dolgu sabit = 4E'nin en iyi dolgusu `lo=−3, hi=N+3`**; **σ ∈ {2.0, 2.5, 3.0, 4.0}** ×
**top-k ∈ {80, 120}** = 8 hücre × **30 tohum**; **epoch 25000, lr 0.05**. Başarı: tohumların
**≥%95'i** tabloyu **%100** öğrenir.

### Hipotez ve çürütme

- **H4f.1:** dolgu altında **σ arttıkça tam-doğru oranı monoton artar** (4E: σ=1.0 %83.3, σ=1.5 %83.3,
  σ=2.0 %93.3). **Çürütme:** σ=3.0 veya σ=4.0'un tam-doğru oranı σ=2.0'ın **altına düşerse**.
- Ek ölçüm (hipotez değil, mekanizma kontrolü): çok geniş σ kodları aşırı benzeştirebilir → **her
  hücrede özdeş-kod + farklı-etiket çatışma sayısı ve rank** raporlanır (4E: σ=1.5'te 27 çatışma).

### Karar

- **≥%95 hücre varsa:** tek konfigürasyon donar; **KALİBRASYON KAPISI OLMADAN 100 tohum** ile 1..9
  tüm çarpma ve bölme çiftleri ölçülür (tohum başına doğruluk dağılımı + zincir p^k). Kapı olmadığı
  için **başarısız tohumlar da** raporlanır.
- **Yoksa:** "bu ızgarada ulaşılamadı" diye net raporlanır; **kalibrasyon kapısı** çözüm olarak kalır.

### Sağlama (determinizm)

4E'de shard'lı koşup birleştirilen zincir sonucundan **3 tohum** (deterministik seçim:
`RandomState(2026)` ile 54 kabul edilen tohum arasından) **baştan** çalıştırılır ve zincir satırları
`chain81_rows.csv` ile **birebir** karşılaştırılır; aynı/aynı değil raporlanır.


---

## FAZ 4E — N=81 teşhisi, kalibrasyon ve shuffle (KISA)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-4D DEĞİŞTİRİLMEDİ.
**Seçim ölçütü YALNIZCA tablo doğruluğudur**; çarpma/bölme testi seçim için KULLANILMAZ.

### Sabit hücre

N=81, 4D en iyi hücre: **epoch 25000, lr 0.05, top-k 80, σ=1.5**; 30 tohum (Adım 4 son ölçüm 100).

### Adım 1 — Teşhis (hipotezler ölçümden önce)

Kenar kümesi **E = {(n,op) : n ∈ {0,1,80,81}}** → 8/164 = **%4.88 taban oranı**.

- **H4e.1 (kenar):** başarısız tohumlarda hatalar **kenar girdilerinde toplanır**.
  **Destek:** hatalı girdilerin E payı ≥ **2× taban oranı (≥%9.76)**. **Çürütme:** E payı < %9.76.
- **H4e.2 (ayrılabilirlik):** aynı kodlar üzerinde **kapalı formlu** (en küçük norm, `lstsq`)
  doğrusal sınıflandırıcı 164 girdiyi **tam ayırır** → sorun kod çakışması değil, **öğrenme
  kuralı / optimizasyon tavanı**. **Destek:** rank(X) = 164 VE farklı etiketli özdeş kod YOK VE
  kapalı form eğitim doğruluğu = 1.000. **Çürütme:** rank < 164 VEYA özdeş-kod çakışması VAR VEYA
  kapalı form < 1.000.
- Ek (tanımlayıcı, hipotez değil): hatalı girdilerin komşu kod kosinüs benzerliği (doğrularla
  karşılaştırmalı).

### Adım 2 — Shuffle kontrolü (aynı hücre, 30 tohum)

Kollar: **gerçek** (`W_vpn`); **derece-korunmuş shuffle**
(`nc.degree_preserving_shuffle(W_vpn, seed=999, swaps=200000)`, tek ve deterministik);
**örtüşme-kontrol** (`W_alpn_r` yerine `W_alpn_r_rand`). Ölçüt: tablo tam-doğru tohum oranı ± %95 GA.
**Yorum kuralı:** gerçek kolun oranı shuffle kolunun %95 GA'sı içindeyse **"ayırt edilemedi"**
(connectome'a özgü yapının bu tabloda ölçülebilir katkısı yok).

### Adım 3 — Küçük ızgara (YALNIZCA H4e.1 DESTEKLENİRSE)

Eksen dolgusu ∈ {yok, [−3, N+3]} × σ ∈ {1.0, 1.5, 2.0} = **6 hücre × 30 tohum**; hücre sabit
(epoch 25000, lr 0.05, top-k 80). **(σ=1.5, dolgu yok) hücresi Adım 1/2 ile aynıdır → yeniden
hesaplanmaz.** **Başarı: tohumların ≥%95'i tam-doğru.** Sağlanırsa **tek konfigürasyon donar**
(önce tam-doğru oranı, eşitlikte eğitim doğruluğu). Sağlanmazsa donma yok.

### Adım 4 — Kontrolcü kalibrasyonu (KONTROLCÜ İŞİ — etiketli)

Açılışta tüm 164 (n,op) girdisi sınanır; **herhangi biri yanlışsa sinek REDDEDİLİR**. Bu bir
**kalite kontrol kapısıdır**, kural öğrenme DEĞİL. 100 tohumda kaç tohum reddedildi rapor edilir.
Kabul edilen sineklerle 1..9 tüm çarpma ve bölme çiftleri; tohum başına doğruluk dağılımı + zincir
p^k. **Sinek durum taşımaz, kontrolcü taşır.** Adım 4 konfigürasyonu: Adım 3 donduysa **donmuş**,
durmadıysa **4D en iyi hücre**.


---

## FAZ 4D — N=81 tablo kapasitesi, uzun optimizasyonla (KISA)

Kayıt tarihi: 2026-09-19. Ölçümden önce yazılmıştır. Faz 0-4C DEĞİŞTİRİLMEDİ.
**Seçim ölçütü YALNIZCA tablo doğruluğudur**; çarpma/bölme testi seçim için KULLANILMAZ.

### Izgara (sabit)

N=81, σ=1.5; **epoch ∈ {10000, 25000}** × **lr ∈ {0.01, 0.05}** × **top-k ∈ {40, 80}** = 8 hücre;
**30 tohum**. Başarı: tohumların **≥%95'i** tabloyu **%100** öğrenir.

### Hipotez ve çürütme

- **H4d.1:** 4C'deki N=81 başarısızlığı **optimizasyon kaynaklıydı** (epoch/lr yetersiz); uzun
  optimizasyonla en az bir hücre ≥%95'e ulaşır. **Çürütme:** hiçbir hücre ≥%95'e ulaşmazsa.

### Karar

- **Başarılıysa:** tek konfigürasyon donar; **100 tohumla** 1..9 tüm çarpma ve bölme çiftleri
  (tohum başına doğruluk dağılımı, zincir p^k) ölçülür. **Sinek durum taşımaz, kontrolcü taşır.**
- **Başarısızsa:** "bu ızgarada ulaşılamadı" diye net raporlanır; **iki haneli yedek** (onlar/birler
  ayrı kanal, elde/borç kontrolcüde) TASARIM olarak etiketlenip uygulanır.











