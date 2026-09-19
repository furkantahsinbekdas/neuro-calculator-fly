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
