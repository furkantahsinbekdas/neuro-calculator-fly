# Ask the Fly Brain 🪰🧠

Let a local **Gemma** model drive a simulation of the **FlyWire** fruit-fly brain
connectome. You ask a question in plain English; Gemma calls tools that pull the *real*
connectome (the ~140k-neuron wiring diagram of an adult *Drosophila*) and run a small
spiking simulation, then explains what lit up — gates, arithmetic, a heading memory, a
moving fly, shortest paths, even a game you play against the fly's real escape reflex.

```
you (English) ─▶ Gemma (local, via Ollama) ─▶ {"tool": ...}
                                                  │
        find_neurons ─ stimulate ─ show_logic_gate ─ do_math ─ show_compass
        ─ move_fly ─ navigate_fly ─ show_path ─ dodge_swatter ─ neuroglancer
                                                  │
                          real FlyWire data + a tiny LIF sim
                                                  │
                                results ─▶ Gemma ─▶ plain-English answer
```

## 🤖 Otonom katman — bu forkun ekledikleri (Türkçe)

Bu fork, yukarıdaki reaktif (tur tabanlı) uygulamayı **otonom bir sibernetik sineğe**
çevirir: sinek kendi iç durumuyla yaşar, kimse sormadan harekete geçer ve **gerçek yanıtı
konnektomun verdiği karardır** — sinirsel sınıflandırma sonucu arayüzde birincil blok olarak
görünür; dil modeli yalnızca o sonucu 2-4 kelimelik bir durum parçasına çevirir (Faz 13).
Serbest sohbet (sözlükte karşılığı olmayan mesajlar) ayrı bir balonda, "serbest sohbet (LLM)"
etiketli olarak akar; okuma tarayıcının kendi sesiyle yapılır (ses kapalıysa eski davranış:
**200 Hz kanat vızıltısı**).

**Faz 9 itibarıyla fiziksel gövde katmanı tamamen kaldırıldı** (`mujoco_bridge.py`,
`/motor` ucu, gövde telemetri paneli ve MJPEG akışı yok; `requirements.txt`'ten mujoco /
glfw / pillow çıktı). Sinek artık **saf metinle** yaşar: kullanıcının cümlesi sabit
sözlükle eşleştirilir, eşleşen her kelime **mantar cismi (Kenyon hücresi) sınıflandırıcısı**
`cognitive_matrix.py`'den geçer, çıkan kategori `FlyState`'i deterministik olarak değiştirir
ve sinek o durum için **elle yazılmış sabit bir dizgeyle** cevap verir (Faz 15: üretilmiş cümle
yok — eskiden LLM "olmuş bitmiş olayı" anlatıyordu, o yol kapatıldı).
Yukarıdaki İngilizce bölümler upstream `flyputer`'a aittir; aşağısı bu forkun mimarisidir.

```
[tarayıcı: 3D beyin + Vitals HUD + birincil sinyal bloğu + yorum + sesli okuma 🗣 + vızıltı + 🎙
           + 🍯/👋/🪰 düğmeleri + 7 sahne düğmesi + vitals − / + override]
     │  ▲ GET /poll?since=N            ┌── GameLoop (1 Hz tick) ──┐
     │  │  EventBus (seq'li JSON) ◀────┤ eşik aşılınca deterministik│
     │  │                              └── run_impulse ───────────┘
     │  └─ POST /chat ─▶ hepsi SENKRON ve LLM'siz (kuyruk yok, ~0.05 sn)
     │                   POST /interact (feed|poke|mate) · POST /vitals (manuel) · POST /tool (sahne)
     │
     └──────────────────────────────────────────────────────────────┐
        metin ─▶ sözlük eşleşmesi ─▶ cognitive_matrix (KC kodu) ─▶ kategori
                                              │  (isabet yoksa: anahtar kelime "eş" → sonra OOV)
                              CATEGORY_EFFECTS ─▶ FlyState deltası + bayrak
                                              │
                              classifier olayı + PHRASE_BANKS'ten sabit dizge (üretim yok)
```

**LLM artık sahnede değil:** `run_agent` ve istem blokları dosyada durur ama **hiçbir canlı yol
onları çağırmaz** (ölü kod; `_fly_smoke.py`'nin `llm/caption/tone/autollm/lazy/tools/bench`
fazları yalnızca o ölü modülü korur). Aşağıdaki LLM'li akış tarihsel bağlam içindir.

**Yeni dosyalar**
- **`brain_state.py`** — `FlyState` (enerji / açlık / can sıkıntısı + geçici bayraklar,
  kilitli) + `EventBus` (thread-safe, `seq` numaralı olay günlüğü) + `enable_utf8_console()`.
- **`game_loop.py`** — `LLMExecutor` (tek worker + `PriorityQueue`, token streaming; **Faz 15'ten
  beri hiçbir canlı yol kullanmıyor**), `GameLoop` (tick döngüsü, ihtiyaç eşikleri + cooldown
  kapıları; `impulse=` verilince otonom dürtüyü deterministik `run_impulse`'a devreder) ve iki
  eşleme tablosu: **`CATEGORY_EFFECTS`** (sınıflandırıcının 6 kararı, 1:1) + **`AUTONOMIC_EFFECTS`**
  (dinlenme refleksi, çevre olayları, "eş" uyarımı).
- **`cognitive_matrix.py`** — mantar cismi sınıflandırıcısı: `classify(word) -> (kategori,
  güven)`, `scan(text) -> isabetler`, `encode(text) -> KC kodu`. Ayrıntı ve dürüstlük
  notu aşağıda.

**Hızlı başlangıç**
```bash
.venv/Scripts/python.exe server.py                  # web arayüzü + 3D beyin (LLM canlı yolda değil)
.venv/Scripts/python.exe server.py --no-autonomy    # sadece konuşma modu
```

**Uçlar** — `GET /poll?since=N` (olay akışı; ayrıca `classifier_ready`), `GET /state` (vitals +
döngü + executor + **sınıflandırıcı durumu**), `GET /health`, `POST /chat {message, sensory?}`,
`POST /interact {action}` (feed|poke|mate), `POST /vitals {field, value}`, `POST /tool {name}`,
`POST /mode {autonomy}`. `server.py --require-tool autonomous|always|never` ile "araç
çalıştırmadan konuşma" engeli.

**Canlı öğretim (Faz 11)** — sohbete `/öğret elma besin` yaz: sinek kelimeyi o an öğrenir
(tüm sözlüğü yeniden eğitmeden), eski kelimelerin tamamını yeniden ölçer ve öncesi/sonrası
sayıları yazar. `/öğret` tek başına öğretilenleri listeler, `/öğret-geri` son öğretimi geri
alır. Bildiği bir kelimeyi başka kategoriye yazmak onay ister (`... onayla`).

**Yeni kategoriye beden etkisi (Faz 11.5)** — `/öğret korku tehlike-2` gibi bir komut yeni bir
*karar* açar ama tanım gereği hiçbir fizyolojisi yoktur; cevap bunu söyler ve sorar. İstersen
`/öğret-efekt tehlike-2 tehlike` ile o kategoriyi **mevcut altı etkiden birine** bağlarsın
(yeni satır, yeni kopya açılmaz; seçim `learned_words.json` içindeki `effect_aliases` alanında
saklanır ve açılışta geri gelir). `/öğret-efekt tehlike-2 yok` bağı çözer: kategori yine
bilinir ama bedeni kıpırdatmaz. Etki kelimeden ya da kategori adından **tahmin edilmez**.

**Bas-konuş + HUD bildirimleri (Faz 12A)** — 🎙 düğmesini **basılı tut** (fare, ya da odaktayken
boşluk/enter): Web Speech API `tr-TR` dinler, bırakınca duyduğu cümle sohbet kutusuna yazılıp
**elle yazılmışla aynı** yoldan gider — gövde tam olarak `{"message": "..."}`, ayrı uç ya da
ayrı gövde yok. Hiçbir şey duyulmazsa ya da tanıma/izin hatası olursa loga "anlaşılamadı, tekrar
dene" düşer; sessiz başarısızlık yok. Ayrıca Faz 11.5'in "GERİLEME ÖLÇÜLDÜ"/"GÜVENLİK SINIRI"
satırları ve `/öğret` onayları **ayrıca** sol üst köşede küçük, yarı saydam bir bildirim olarak
~5 sn görünür (tıklayınca hemen kapanır, en fazla 4 tanesi üst üste). Tetikleyici ve veri
değişmedi: tam metin **her zaman logda da durur**, bildirim yalnızca görsel bir kopyadır.

**Sesli okuma + gergin ton + iki dilli cevap (Faz 12B)** — sineğin Türkçe cevabı artık loga
düştüğü anda **okunur** (tarayıcının kendi `speechSynthesis` motoru; indirilen bir ses modeli yok).
HUD'daki **🗣 sesli oku** anahtarı açık gelir, tercihi sayfa yenilense de oturum boyunca hatırlanır
(`sessionStorage`; sunucuya hiçbir şey gönderilmez) ve kapatınca ses anında kesilir. Cevabın
sonundaki köşeli parantezli İngilizce **ekranda görünür ama okunmaz** — ses yalnızca Türkçeyi
duyar. Gerginken (açlık > 80 ya da "ürkmüş" bayrağı) üslup sertleşir; sinek kapalı bir listeden
(`lan`, `hassiktir`, `off`, `mahvolduk`, `ay`) en fazla bir ünlem kullanır, sakin haldeyken bu
liste isteme hiç girmez. Sesli okuma kapalıysa sinek eski usul **vızıldar** (vızıltı artık yedek
ses: ikisi asla üst üste konuşmaz).

**Sinyal önce, yorum sonra (Faz 13)** — kullanıcının eleştirisi haklıydı: LLM'in uzun cümleleri
"konuşan sinek" gibi görünüyordu ve çekirdeğin gerçek kararı küçük bir satırda kayboluyordu. Artık
sıra değişti:
- **Sınıflandırıcı kararı birincil**: 🧠 bloğu büyük puntoyla, en üstte, kendi stilinde çizilir
  (kategori · kelime · güven + vital etkisi). Bağlantı ağı (konnektom) ne dediyse o görünür —
  aracısız.
- **LLM'in çıktısı ikincil**: o turda model artık bir *çözücü* (decoder) olarak çalışır ve yalnızca
  **2-4 kelimelik bir durum parçası** üretir, örn. `aç · yaklaşıyor [hungry · approaching]`,
  `ürkmüş · kaçıyor [startled · fleeing]`. Bu satır "yorum" etiketiyle, küçük ve soluk, sinyal
  bloğunun altında durur. Birinci şahıs anlatım, metafor, cümle kurma yok.
- **Karakter balonu kalktı**: sınıflandırılmış turlarda "SİNEK" adına konuşan bir balon artık
  yok. Balon yalnızca **serbest sohbet** için kalır — sözlükte karşılığı olmayan mesajlarda
  çekirdeğin söyleyecek bir şeyi yoktur — ve o balon açıkça **"serbest sohbet (LLM)"** diye
  etiketlenir, yani ne olduğu asla belirsiz kalmaz. `/öğret` cevapları da çip olarak yazılır.
- Sesli okuma yalnızca parçayı okur (parantezdeki İngilizce yine ekranda kalır).

**Sinek artık kendi kendine dinleniyor, çevre de ona dokunabiliyor (Faz 14)** — canlı testte üç
gerçek boşluk çıktı ve üçü de kapatıldı:
- **Enerji refleksi (açlığın `eat` karşılığı):** enerji 30'un altına inince sinek **kendi kendine**
  dinlenmeye başlar — çip bir seferde 8 puan, sonra 10 tick boyunca tick başına 3 puan toplar
  (toplam ~38, 60 sn arayla). Enerji kritik eşiği (25) geçtiği anda tekrarlayan `show3d("clock")`
  dürtüsü **durur**; kullanıcının hiçbir şey yapması gerekmez.
- **Çevre olayları:** gerçekten yalnız kaldığında (≥45 sn insan yok, çalışan/sırada iş yok,
  dinlenme turu yok) ortam ona nadiren dokunur: **`darbe`** (enerji −15, can sıkıntısı −10,
  `startled` bayrağı) veya **`rastgele-besin`** (açlık −20). Olasılık tick başına ~0.004, yani
  dakikalar mertebesinde — sohbeti asla kesmez ve sözlük kelimeleriyle **aynı** efekt hattından
  (`apply_effect` + `reflex` olayı) geçer.
- **Gergin kaptanlarda ünlem geri geldi:** Faz 13 ünlemi kişilikle birlikte kaldırmıştı; artık
  gergin bir parça (açlık > 80 ya da `startled`) listeden **bir** kelimeyi ilk yuvaya koyabilir:
  `hassiktir · kaçıyor [oh no · fleeing]`. Sakin kaptanlar hâlâ ünlemsiz ve sakin istem listeden
  tek kelime bile içermez; `single_exclaim()` süzgeci bu yolda da tek ünlem sınırını korur.

**LLM tamamen devre dışı: kelime → konnektom → sabit dizgi (Faz 15)** — mimari karar net: canlı
yolda **hiçbir üretilmiş cümle yok**. Bir mesaj artık üç yoldan birine girer ve üçü de anında
(ölçülen: 0.02–0.05 sn) ve deterministik yanıt verir:
1. **sözlük kelimesi** → KC sınıflandırıcı kategorisi + vital etkisi + o kategorinin **elle yazılmış
   dizge bankasından** bir cümle (`PHRASE_BANKS`), örn. şeker → `yaklaşıyor · şeker [approaching · sugar]`,
   tehlike → `hassiktir · kaçıyor [oh no · fleeing]`.
2. **yeni "eş" uyarımı** → `dişi sinek / eş / çiftleş` gibi kelimeler sunucudaki anahtar-kelime
   yolundan geçer: sıkıntı −20 + 25 sn **`heyecanlı`** bayrağı, dizge bankası: `kanat · titriyor
   [wing · vibrating]` (kanat titretme gerçek Drosophila kur davranışıdır).
3. **bilinmeyen kelime** → LLM'e hiç gidilmez: `kelime tanınmıyor · bilinen örnekler (tehlike):
   kork, düşman, tehlike, kaç` — kullanıcı sözlüğü öğrenir.
Banka gerginken (`açlık > 80` ya da `startled`) ayrı yarıdan seçilir; ünlem sözcükleri orada durur.
Yeni uçlar: **`POST /interact {"feed"|"poke"|"mate"}`** (🍯 besle → besin etkisi, 👋 dokun/kovala →
tehlike etkisi + `startled`, 🪰 dişi sinek → eş etkisi + `heyecanlı`), **`POST /vitals
{"field","value"}`** (HUD'daki − / + düğmeleri: manuel override, simülasyonun parçası değil,
arayüzde "debug" diye etiketli) ve **`POST /tool {"name"}`** (LLM'in eskiden araç çağrısıyla
açtığı bağlantı ağı sahneleri — AND kapısı, yol, pusula, iki koku, göz, kaçış oyunu, yürüyüş —
artık düğmeden çalışıyor). Otonom dürtü de deterministik oldu (`run_impulse`: gerçek sahne +
refleks + sabit dizge), yani sunucuda LLM'i çağıran **hiçbir** yol kalmadı; `run_agent` ve istem
blokları dosyada duruyor ama ölü. `sensory` seçeneği artık yalnızca köken etiketi (`origin=sensory`),
çünkü ona anlam veren `[DUYU]` istem satırı yok. İlk mesaj konnektom matrisi hazır olana kadar
bekleyebildiği için `/poll` bir `classifier_ready` alanı yayınlar: arayüz "çekirdek yükleniyor…"
yazar ve gönder düğmesini o sırada kilitler.

**Dizge bankaları (elle yazıldı, 39 cümle, 7 kategori)** — her biri ≤4 kelime Türkçe + ≤4 kelime
İngilizce, tek köşeli parantez:

| kategori | normal | gergin |
|---|---|---|
| **besin** | `yaklaşıyor · şeker [approaching · sugar]`, `koku · güçlü [scent · strong]`, `tadıyorum · tatlı [tasting · sweet]`, `besin · bulundu [food · found]`, `yiyorum · doydum [eating · full]` | `hassiktir · açım [oh no · starving]`, `mahvolduk · açlık [we're doomed · hunger]`, `off · karnım boş [damn · belly empty]` |
| **tehlike** | `tehlike · uçuyor [danger · flying off]`, `gölge · büyük [shadow · big]`, `geri · çekiliyor [backing · away]` | `hassiktir · kaçıyor [oh no · fleeing]`, `off · sıçradı [damn · it jumped]`, `lan · düşman [damn · enemy]`, `mahvolduk · saklanıyor [we're doomed · hiding]`, `ay · tokat [ow · swat]` |
| **selam** | `selam · geldin [hello · you came]`, `anten · selam [antennae · greeting]`, `tanıdık · koku [familiar · scent]`, `merhaba · dostum [hello · friend]` | — |
| **açlık** | `açlık · düşük [hunger · low]`, `açlık · orta [hunger · medium]`, `açlık · yüksek [hunger · high]`, `tok · karnım [full · belly]`, `karnım · boş [belly · empty]` | `açlık · kritik [hunger · critical]` |
| **onay** | `anlaşıldı · tamam [understood · okay]`, `onay · verildi [approval · given]`, `doğru · katılıyorum [right · agreeing]`, `peki · olsun [okay · fine]` | — |
| **red** | `hayır · istemem [no · I refuse]`, `olmaz · uzak [no · stay away]`, `ret · kesin [refusal · firm]`, `yok · hayır [none · no]` | — |
| **eş** | `iz sürüyorum · heyecanlı [courting · excited]`, `kanat · titriyor [wing · vibrating]`, `dişi · yakın [female · near]`, `kur · başlıyor [courtship · starting]`, `feromon · güçlü [pheromone · strong]` | — |

Otonom dürtüler için ayrı üçlüler (`NEED_PHRASES`): **açlık** `açlık · kritik`, `yemek · aranıyor`,
`şeker · kokusu` · **enerji** `bitkin · dinlenme`, `güç · bitti`, `kanat · ağır` · **can sıkıntısı**
`sıkıntı · yüksek`, `uyarım · aranıyor`, `oyalanma · lazım`.

**Arayüz dili: figure.ai esinli endüstriyel sade (Faz 16, Task 1)** — koyu cam teması
(`rgba(14,18,30,…)` + `backdrop-filter` + 11-12 px yuvarlaklık + neon yeşil/turuncu vurgular)
bırakıldı; yerine **kağıt + mürekkep** sistemi geldi. Referanstan alınan **yalnızca palet ve tip
sistemi** (site kopyalanmadı): `#f6f6ef` kağıt, `#0c0c0c` / `#1d1d1d` / `#2e2e2e` mürekkep, `#fff`
yüzeyler, `#000` **düğme** dolgusu, `#dcdcdc` **liste** çizgisi, `-0.01em` sıkı harf aralığı, `1.5`
satır yüksekliği, geniş ekranda büyüyen gövde (ölçüldü: 1440 px'te gövde 16.29 px, sinyal başlığı
36 px/700). Yarıçap ölçümü: sayfada yalnızca üç değer kaldı — panellerin `2px`'i, legend/veri
noktalarının `50%`'si ve düğmelerin `999px`'i. Referanstan alınan dört kural **birebir** uygulandı
— yapılanlar:

- **Düğme**: referansın tek yuvarlak biçimi. Katı **siyah hap** + **saf beyaz** yazı + geniş yatay
  dolgu (`--btn-x` = 18 px; `Gönder` 24 px). Birincil eylem (`#send`), mikrofonun basılı hâli ve tüm
  çerçeveli hapların hover durumu aynı siyah haptır; ama paneller, sahne, sohbet sayfası, girdi ve
  kaydırma çubuğu **köşeli** kalır (2 px) — yuvarlaklık yalnızca düğmeye ait.
- **Liste/log = indeks listesi**: her kayıt bir kutu değil bir **satır**; `#log > *` altında
  `1px solid #dcdcdc` (`:last-child` hariç — kural ayırır, kapatmaz). Böylece insan turu dolguyla
  değil **ağırlık + mürekkep + `SEN` etiketi** ile işaretlenir; çiplerin tür rengi kutuyu bırakıp
  2 px `currentColor` sol çizgiye taşınır (`tool`/`viz`/`classifier`/`reflex` kodlaması korunur).
- **Gezinme/meta etiketleri BÜYÜK HARF** ve `0.08em` tracking: legend, HUD anahtarları, vitals
  anahtarları ve ruh hali, dokuz sahne panelinin başlığı, doğruluk tablosu başlığı. Gövde metni ve
  düğme yazıları kendi yazımını korur (ölçüldü: `#send`'in `text-transform`'u `none`).
- **Başlıklar büyük + kalın + sıkı**: tur başına tek `--fs-display` başlığı (`.signal .sbig`,
  ölçüldü 36 px/700, -0.72 px = -0.02em, satır 1.05), bölüm başlıkları `--fs-h` (23.9 px/700), yorum
  satırı `--fs-phrase` (18.5 px) — ölçek artık `--fs-head` yerine bu üç tokendan gelir.

- **Yazı tipi**: figure.ai'nin kullandığı `neue-haas-grot-text` Grilli Type lisanslı olduğu için
  **paketlenmedi ve hotlink edilmedi**; yerine açık lisanslı **Inter** (CDN, `font-display: swap`,
  yedekte sistem sans yığını) konuldu ve aynı tracking/leading/ölçek kuralları uygulandı —
  ölçüldü: tarayıcı gerçekten Inter 400/500/600'ü yükledi.
- **Yüzey katmanları**: kağıt taban → koyu **sahne** (3B beyin) → beyaz **sütun** (sohbet) →
  sahnede yüzen beyaz kartlar (vitals, HUD, sahne panelleri, bildirimler, ipucu).
- **Tek aile, hiyerarşi ağırlık/punto/tracking ile**: `.signal .sbig` 36 px/700 mürekkep
  (`--fs-display`); `.yorum` bir kademe küçük (18.5 px, `--ink-2`) — "sinyal birincil, yorum
  ikincil" kuralı görsel olarak da doğru.
- **Krom sadeleşti**: gradyan, gölge, glow ve `backdrop-filter` yok (kartlar artık opak); düğmeler
  hap biçimli (hairline çerçeveli, hover'da siyah hapa döner); tüm tıklanabilirlerde
  `hover`/`:focus-visible`/`:active` var; yalnızca `transform`/`opacity` animasyonu (ölçüldü:
  HUD/kontrol geçişleri `transform`, `transform, background` — `all` ya da `width` yok).
- **Vitals çubukları monokrom**: enerji/açlık/sıkıntı tonla ayrılır, kırmızı yalnızca **kritik**
  eşiğinde (refleks gerektiğinde) çıkar; dolgu artık `width` değil **`transform: scaleX()`**.
- **Bilinçli sapma**: 3B beyin **koyu sahnede kaldı**. Nöronlar additive (toplamalı) parıltıyla ve
  `FogExp2(0x05060a)` ile çiziliyor; additive karışım beyaz zeminde fiziksel olarak çalışmaz —
  açık temaya çevirmek materyal/blending ve shader'ı yeniden yazmayı gerektirir, bu fazın kapsamı
  ise "sunum katmanı, DOM/JS mantığına dokunma" idi. Açık zeminli varyant istenirse ayrı bir iş
  kalemi (shader + blending + sınıf renklerinin koyulaştırılması). İkinci sapma: tek yazı tipi
  kullanıldı (referansın kendi sistemi öyle) — hiyerarşi punto/ağırlık/tracking ile kuruldu.
- **Mobil (ilk kez gerçekten sorumlu)**: sayfada daha önce **hiç** `@media` yoktu ve 390 px'te
  paneller birbirinin üstüne biniyordu. Artık `≤980px`'te kabuk dikey yığılıyor (üstte sahne,
  altta sohbet sayfası), `≤620px`'te legend/alt başlık sadeleşiyor; vitals + HUD + sahne şeridi
  çakışmayacak şekilde tabandan konumlanıyor. Hap düğmeler satırları genişlettiği için üç düğme
  şeridi **tam satır** yüksekliğine sabitlendi (tarayıcıda ölçüldü: hap 34 px, çip 32 px, satır
  boşluğu 8 px; `box-sizing: border-box` olduğundan kabın kendi alt dolgusu da tavanın içinde):
  `≤980px`'te iki satır (82/86/86 px), `≤620px`'te tek satır (42/46/48 px) ve `--btn-x: 13px`.
  Böylece bir düğme asla ortadan kesilmiyor; fazlası şeridin içinde kaydırılıyor. **Dürüst sınır**:
  telefonda sahne kalabalık — gerçek çözüm panelleri sohbet sütununa taşımak (DOM değişikliği), o
  yapılmadı.

**Ses: TTS tavanının üstüne çıkan "helyum" katmanı (Faz 16, Task 2)** — önce dürüst sınır:
tarayıcı `speechSynthesis` çıktısını **hiçbir API vermiyor** (MediaStream yok, düğüm yok, kayıt
yok), yani gerçek konuşmayı pitch/formant kaydırmak sayfa içinde mümkün değil; `Say` zaten
motorun tavanı olan **pitch 2.0 / rate 1.5** ile konuşuyor (Faz 12B'de ölçüldü). Bu yüzden gerçek
bir sinyal işleme yolu kuruldu:

1. **Gerçek granular pitch-shifter**: overlap-add, yarım grain aralıklı iki Hann pencereli tap,
   `AudioWorklet` olarak **satır içi Blob**'dan derleniyor — dosya yok, sunucu ucu gerekmedi, yeni
   bağımlılık yok (`server.py` **hiç değişmedi**).
2. Shifter **sahibi olduğumuz sinyale** uygulanıyor: aynı cümlenin hece ritmini taşıyan ince bir
   **squeak taşıyıcısı** (1150 Hz testere + 575 Hz gövde + 3050 Hz band-geçiren formant + 6.5 Hz
   ±26 Hz vibrato). Helyum da böyle çalışır: temel **ve** formant yukarı gider.
3. Katman TTS'in **altına** biner (`LEVEL = 0.16`), yani algılanan perde 2.0 tavanının çok üstüne
   çıkar; okuma kapalıyken konuşan **vızıltı** ise aynı shifter'dan **geçirilir** (katman değil,
   gerçekten kaydırılmış sinyal).
4. **Opt-in**: HUD'daki **🎈 aşırı helyum** anahtarı (varsayılan kapalı, `sessionStorage`'da
   `fly.helium` olarak oturum boyunca hatırlanır). Kapalıyken ses yolu **hiç değişmez** — test bunu
   ölçüyor: kapalıyken tek bir osilatör bile kurulmuyor.

Ölçümler ve dürüst tavizler: shifter doğruluğu **ölçüldü** (worklet sınıfı Node'da gerçekten
çalıştırılıp çıkış frekansı sıfır-geçişleriyle sayılıyor): `shift=1.0` → 440 Hz giriş 440 Hz çıkış
ve kazanç **1.000** (birebir geçirgen; `wA + wB = 1` olduğu için dalgalanma yok), `shift=1.5` →
440 Hz → **655 Hz** (beklenen 660'ın −%0.8'i), `shift=2.0` → 300 Hz → **602 Hz** (+%0.3).
Tavizler: katman *kaydırılmış konuşma* değil bir **squeak**'tir — anlaşılırlık hâlâ TTS'ten gelir;
46 ms grain yüksek seviyede hafif chorus/robotik doku ekleyebilir (bu yüzden seviye kısık); worklet
ilk kullanımda ~10 ms derlendiği için **ilk cümle** shifter yetişmezse taşıyıcıyı kaydırmadan
çalar. Gerçek (formant kaydırmalı) konuşma isteniyorsa yol sunucudur: yerel bir TTS motoru
(piper/espeak) + rubberband/librosa ile yeni bir uç — bu **yeni bağımlılık** demek olduğu için
yapılmadı, yalnızca burada not edildi.

**Ön yüz testleri ve araçlar (Faz 16)** — `_fly_frontend_test.js` artık tasarım tokenlarını
(kağıt/mürekkep/hairline/tracking/`clamp` ölçeği), Inter lisans gerekçesini, koyu tema
artıklarının *yokluğunu*, `transition-all` yasağını, hover/focus-visible/active kapsamını, mobil
kırılım noktalarını, **dört kuralın birebir uygulandığını** (hap yarıçapı + saf siyah/beyaz düğme,
`#dcdcdc` satır kuralı + "son satır çizgisiz", kayıtların kutu olmaktan çıkması, BÜYÜK HARF
meta etiketleri, `--fs-display`/`--fs-h` başlıkları ve ölçüm çubuğu izleri) ve helyum davranışını
(kapalıyken sıfır osilatör, açıkken 3 osilatör + zarf, `sessionStorage`, varsayılan kapalı) ölçer;
**worklet DSP'si gerçekten çalıştırılıp frekansı ölçülür** (yukarıdaki sayılar bu testin çıktısı).
`_fly_smoke.py frontend` fazı 68 işaret (+46 yasak) kontrol eder; eski koyu tema dizileri,
`border-radius: 12px/8px/3px` gibi yumuşak köşeler ve `transition-all` yasak listesindedir.
Ek olarak `verify-phase16.mjs` **tarayıcının hesapladığı** stilleri okur (bu bölümdeki "ölçüldü"
sayıları oradan gelir): tokenlar, yüzeyler, düğme hap yarıçapları/dolgusu, `#log > *` satır kuralı
ve son satırın çizgisizliği, meta etiketlerin `uppercase`'i, başlık puntoları ve sayfada kalan
tüm yarıçap değerleri. `screenshot.mjs` iki yeni bayrak kazandı: `--click "<seçici>,…"` (bir düğmeye
basılmış hâli görüntülemek için) ve `--type "…"` (gerçek bir kullanıcı turu üretmek için);
numaralandırma artık atomik (`wx` ile rezervasyon), yani iki ekran görüntüsü aynı numarayı alamaz.

**Olay türleri** (`/poll`) — `state`, `say`, `thought`, `token`, `tool_call`, `tool_result`,
`viz`, `classifier`, `teach` (canlı öğretim: ölçülen öncesi/sonrası), `reflex`, `user`,
`queued`, `think_start`, `event`, `noop`, `warning`, `error`. Ön yüz `say`'i **sesli okumaya**
(Faz 12B: tarayıcının `speechSynthesis` motoru; okuma kapalıysa/eski davranışta vızıltıya),
`state`'i Vitals HUD'a, `viz`'i 3D sahneye, `classifier`'ı **birincil sinyal bloğuna** (Faz 13),
`teach`'i öğretim çipine bağlar. `say` olayı Faz 13'ten beri bir de `mode` taşır
(`caption` = çözülen parça → "yorum" satırı, `chat` = serbest LLM sohbeti → etiketli balon,
`system` = bizim cevabımız → çip). `warning` iki katmanlıdır: sıradan gerileme/boyut uyarısı
`level: "warn"`, Faz 11.5 güvenlik sınırı `level: "alert"` ve başında `⛔` işareti (EventBus
payload'ı düzleştirip `kind`'ı kendi alanı için ayırdığından katman `level` ile ve metinle
taşınır). `warning` ve `teach` satırları ayrıca geçici bir HUD bildirimi olarak da çizilir
(Faz 12A; log kaydı silinmez, bildirim aynı sözlerin görsel kopyasıdır).

**Dürüst notlar**
- "Yemek görmek, yemek yemek değildir": 4B model şeker devresini yakıp sonra yine "açım"
  diyordu ve hayati değerler hiç değişmediği için dürtü sonsuza kadar tekrar ediyordu. Bu
  yüzden **beslenme refleksi deterministik koda** bağlandı: `show3d("sugar")` başarılı olunca
  harness kendisi `eat` uygular ve `origin="reflex"` ile ayrı bir olay yayınlar. LLM sonucu
  sadece Türkçe anlatır, karar vermez.
- **Sınıflandırıcı gerçek konnektomu çalıştırır — ve neresi bizim, açıkça yazar.** `cognitive_matrix.py`
  `sniff.circuit()`'ı kullanır: FlyWire'ın gerçek ALPN→KC matrisi, 685 projeksiyon nöronu →
  5177 Kenyon hücresi (23.501 bağlı çift, ≥3 sinaps, KC fan-in ort 4,5). Kodu `sniff.kc_code()`
  üretir: bir Kenyon hücresi, aktif ALPN partnerlerinden **≥3'ü** uçarsa uçar — eşik-tesadüf,
  ağırlıklı toplam + k-WTA değil (mekanizma `sniff.py` ile *aynı fonksiyon*, kopya değil; test
  bit-bit eşitliği doğrular). **Bizim olan iki şey var:** (a) kelimeyi ALPN desenine çevirmek —
  kelimenin kokusu yok, bu yüzden karakter 3/4-gramları hash ile 685 PN'e dağılır ve k-WTA ile
  sabit ~%11 aktif kalır (`sniff.odor()`'un koku yoğunluğu), (b) ±1 hedefli delta kuralıyla
  eğitilen 6 çıkışlı okuma ve tanıdıklık kapısı (güven = softmax × koda en yakın *öğrenilmiş*
  kodun kosinüs karesi, yani "bu deseni daha önce gördüm mü"). `/state` bunu `"connectome": true`
  **ve** `"honest_note"` ile söyler. Ölçülen davranış: KC kodu hücrelerin %1,35'i (12-212 hücre),
  sözlükteki 55 kelimenin tamamı kendi kategorisini buluyor (güven 0,965-0,968; okuma 1422
  epoch'ta 55/55, ham okuma skorları ±1,00), "şeker" ↔ "şekerli" 55 ortak hücre paylaşırken
  "şeker" ↔ "tehlike" yalnızca 7 paylaşıyor, sözlük dışı kelimeler 0,00-0,03'te kalıyor
  (eşik 0,40). Güvenin neden bu kadar dar bir aralıkta olduğu da dürüst bir sonuç: kodlar
  neredeyse ayrık, yani hiçbir kelime diğerinden "zor" değil.
- **Faz 10 — kapasite: iki tavan ayrı ölçülür, karıştırılmaz.** `capacity_benchmark.py` gerçek
  Türkçe frekans listesiyle (`data/tr_50k.txt`, 48.376 benzersiz kelime; dosya yoksa kendisi
  indirir, inemezse sonucu "SYNTHETIC" diye etiketler) N = 55 → 500 kelimeye kadar zorlar ve
  **iki tavanı** ayrı ölçer: (A) KC kodlarının kendisi, (B) delta kuralı okuma. Kodlama ve
  eğitim **yeniden yazılmaz**: `cm.encode()` + `cm.readout()` çağrılır; analiz için
  `CATEGORIES`/`VOCAB` N çıkışa çevrilir ve çıkışta geri alınır. Önce üretim sözlüğü doğrulanır
  (1422 epoch, lr 0,01435, 55/55 — birebir aynı). Ölçülen (N=500): **hiçbir kod çifti
  çakışmıyor** (max Jaccard 0,472; eşiğin üstünde 0 çift; en yakın çift "kendini"/"kendine",
  kapsama 0,685 — fark kök paylaşımı, yani bizim giriş kodlamamız) ve **yanlış sınıflandırma
  yok**: argmax doğruluğu N=500'e kadar %100, en küçük doğru-doğru marj 0,386. Buna karşılık
  okuma **kendi ±1 toleransını N=150'de kaybediyor** (min doğru skor 0,980 → −0,402) ve **güven
  eşiği N=200'de kırılıyor**: bir-çıkış-ırk-kelime tasarımında en zayıf öğrenilmiş kelime
  0,72 → 0,35 (eşik 0,40); üretimin 6 çıkışlı hâli N=500'de 0,425 ile hâlâ üstünde ama marj
  yalnızca +0,025. Yani darboğaz ne konnektom ne karar: **güven kalibrasyonu** — 5177 hücreli
  kod uzayı fazlasını taşır. Tam rapor `capacity_report.txt` (yeniden: ~6 dk,
  `.venv/Scripts/python.exe capacity_benchmark.py --log capacity_report.txt`).
- **Faz 11 — canlı öğretim: tek delta adımı, ölçülmüş gerileme kontrolü, yeniden başlatmaya
  dayanıklı defter.** `/öğret elma besin` yazınca okuma **tüm sözlükle yeniden eğitilmez**:
  kelime gerçek KC koduna çevrilir, üretimin kendi delta kuralı **tek örnek** üzerinde uygulanır
  (`W += lr·hata⊗x`, `lr = 1/ortalama aktif`; ölçülen: 1-2 güncelleme, `TEACH_MAX_STEPS` sadece
  emniyet) ve yeni kategori gerekiyorsa okuma matrisine **bir satır eklenir** (ör. 6×5177 → 7×5177,
  yeniden başlatma yok). Ardından **eski sözlüğün tamamı** tek matris çarpımıyla yeniden ölçülür ve
  öncesi/sonrası sayılar hem cevaba hem `teach` olayına yazılır — delta kuralı *her* satırı
  güncellediği için "eski kelimeler dokunulmaz" bir varsayımdır ve bu projede varsayım ölçülür.
  Ölçülen: yeni kelime eklemek etiket doğruluğunu bozmadı (55/55 → 55/55) ve en düşük güveni
  0,965 → 0,960'a indirdi; **fabrika kelimesini yeniden etiketlemek** (`/öğret şeker tehlike
  onayla`) en düşük güveni 0,960 → 0,527'ye çekti — kayıp yok, ama sıfır da değil. Gerileme ya da
  eşiğin altında kalan kelime ölçülürse cevap UYARI ile döner, `/öğret-geri` okumayı ve defteri
  ağırlık-ağırlık eski hâline döndürür. Öğretilenler `VOCAB`'a karışmaz (`TAUGHT` ayrı; fabrika 55
  sabit ve koda gömülü kalır), bildiği bir kelimeyi başka kategoriye yazmak **onay ister**,
  `learned_words.json` elle düzenlenebilir ve açılışta taban eğitimin üstüne **yeniden oynatılır**
  (kaydedilen `.npy` ikilisi yalnızca karşılaştırma için okunur: elle eklenen kelimeyi bilemez,
  ölçülen fark `weights` alanında dürüstçe görünür — testte 0,036). Sözlük 100 kelimeyi geçerse
  (Faz 10: 150-200 civarında kalibrasyon bozuluyor) **engellemeden** uyarır.
- **Faz 11.5 — iki ölçülmüş boşluk kapatıldı: güvenlik sınırı ve canlı kategorinin beden etkisi.**
  Yeni yetenek eklenmedi; ikisi de Faz 11'in kendi dürüst raporundaki sayılardan çıktı.
  (a) **Güvenlik sınırı:** her `teach()` zaten tüm sözlüğü yeniden ölçtüğü için ek ölçüm yok —
  aynı tablo iki eşiğe bakıyor: bir kelime tabana `TEACH_SAFETY_MARGIN` (0,10 → 0,50) kadar
  yaklaşırsa **ya da** tek bir öğretim bir kelimeyi `TEACH_SAFETY_STEP` (0,30) kadar düşürürse
  cevap `⛔ GÜVENLİK SINIRI` katmanıyla döner (`level: "alert"`, `safety_warning`, ayrı bir
  `warning` olayı) ve çözümü adıyla söyler: `/öğret-geri`. Otomatik geri alma **yok**; kararı
  insan verir. Sabitler ölçümden seçildi: bir öğretim en zayıf kelimeyi 0,07-0,13 düşürüyor
  (marj ≈ bir öğretimlik pay), ama komşusu olan bir kelimeyi yeniden etiketlemek o komşuyu tek
  adımda 0,396-0,445 düşürüyor (adım eşiği bu iki rejimin arasında). Ölçülenler, aynen:
  **aynı kelimeyi arka arkaya çevirmek birikmiyor** — `şeker` besin↔tehlike beş kez: en düşük
  güven 0,493 ↔ 0,965 arasında salınıyor, hiçbir kelime 0,40 tabanını geçmiyor ve uyarı tam da
  böyle bir öğretimde (hiçbir geçiş yokken) çalışıyor; **farklı öğretimler birikiyor** — üstüne
  üç yeni kategori: 0,662'ye iniyor, sonraki komşu etiketi `şekerli`'yi 0,493 → 0,330'a
  düşürüyor (tabanın altı, `dropped` ile raporlanıyor); uyarılar `[1,3,5,6,7,8]`, geçişler
  `[6,7]`, yani **uyarı geçişten önce** geliyor. Dürüst sınır da yazılı: sade bir birikme
  sırasında (3 kategori → komşu etiketi) ilk uyarı geçişle *aynı* öğretimde gelir, çünkü o adım
  0,396 düşürüyor — sonradan ölçen bir sınır görmediği adımı önceden haber veremez; bu yüzden
  `dropped` ve `/öğret-geri` ayrıca söylenir. İsteğe bağlı "kategori sayısıyla lr'yi küçült"
  fikri **ölçüldü ve uygulanmadı**: yeni kategoride sürüklenme yapısal (lr×0,5 → en düşük güven
  0,832 → 0,833; lr×0,25 → 0,840 ama 8 güncelleme), yeniden etiketlemede diğer satırların toplam
  yer değiştirmesi zaten lr'den bağımsız (max|ΔW| 0,01681 → 0,01654, 7 kat güncellemeyle); küçük
  lr'de görünen kazanç yalnızca hedefin yakınsamaması (0,961 → 0,819) — eksik öğretimle eski
  kelime güveni satın almak, söylenmesi gereken bir uyarıdan daha kötü bir takas olurdu.
  (b) **Canlı kategorinin beden etkisi:** `/öğret` ile doğan kategori varsayılan olarak bilgi
  amaçlı kalır (etki tablosunda satırı yoktur; `CATEGORIES` 6'lı ve `CATEGORY_EFFECTS` ile 1:1
  kalır). Cevap **sorar** (engellemez): `/öğret-efekt <kategori> <etki>` ya da `yok`. Seçim
  `effect_aliases` alanıyla deftere yazılır, açılışta kelimelerden sonra geri uygulanır, o
  kategoriyi geri alan `/öğret-geri` bağını da götürür, tanımsız/eksik girdiler hata döner
  (fabrika kategorisine bağ takılamaz, fabrika dışı etki seçilemez). Ölçülen: `kitap→bilgi`
  öğretildiğinde yönlendirme var ama `delta={}` ve `noop=true` (kıpırdamıyor); `/öğret-efekt
  bilgi besin` sonrası aynı mesaj açlığı −35 oynatıyor (50 → 15); `yok` ile çözüldükten sonra
  vital yine hiç değişmiyor; bağ yeniden başlatmadan sonra da çalışıyor (`{'bilgi': 'besin'}`).
- **Faz 12A — sesli girdi tek yola indi, güvenlik satırları kaçırılamaz oldu.** Bas-konuş
  düğmesi (`#mic`, Web Speech API, `tr-TR`) **basılı tutunca** dinler (tek tutuşta bir cümle
  toplanabilsin diye `continuous = true`; fare ile `pointerdown/up`, klavyeyle boşluk/enter
  basılı tutma) ve bırakılınca duyduğu metni `#msg` kutusuna yazıp **formun submit'iyle aynı
  fonksiyondan** (`sendInput`) yollar: ayrı uç yok, ayrı gövde yok. Ölçülen kanıt: aynı cümle
  iki yoldan da bayt-bayt aynı `{"message": "..."}` gövdesiyle gitti ve ikisi de `origin=user`
  + `[KULLANICI]` etiketiyle çekirdeğe ulaştı (elle yazılanla karşılaştırmalı canlı koşu).
  Bunun **sonucu dürüstçe**: sayfa artık `sensory: true` yollamıyor, yani sesli tur `[DUYU]`
  etiketini ve `PRIORITY_SENSORY` önceliğini almıyor; `/chat {sensory:true}` API seçeneği
  sunucuda duruyor ve çalışıyor, yalnızca onu kullanan bir arayüz kalmadı (tek yolu korumak
  için bilinçli takas). Boş tanıma ya da tanıma/izin hatası loga "anlaşılamadı, tekrar dene"
  yazar. HUD bildirimi (`toast()`, sol üst `#toasts`, `TOAST_MS = 5000`, tıkla-kapat, en fazla
  `TOAST_MAX = 4`) `chip()`/`bubble()`'ın zaten yazdığını **kopyalar**: tetikleyici ve veri
  değişmedi, yalnızca `level` → uyarı/güvenlik sınırı/öğretim/hata stili. `level="error"` dönen
  bir `/öğret` cevabının arkasında olay olmadığı için o tek bildirimi `ask()` kendisi çizer
  (teach/warn/alert olayları iki kez söylenmesin diye). Ölü kalıntı olarak temizlenenler: eski
  film-şeridi oynatıcının `#play/#scrub/#time` CSS'i (markup'ı ve JS'i zaten silinmişti),
  mikrofon bloğuna düşmüş bayat "classifier chip" yorumu ve istemcideki `sensory` dalı.
- **Faz 12B — sinek artık gerçekten konuşuyor; tonu yalnızca gerginken sertleşiyor, cevabı iki dilli.**
  (a) **Sesli okuma (`Say`, yalnızca `chat3d.html`):** sineğin Türkçe cevabı loga düştüğü anda
  tarayıcının kendi `speechSynthesis` motoruyla okunur — RVC/ElevenLabs yok, indirilen model yok.
  İstenen ses: **pitch 2.0 / rate 1.5 / `lang="tr-TR"`**; Web Speech API pitch'i 0..2, rate'i
  0.1..10 aralığına kırpar, yani iki değer de geçerli ve **2.0 tam tavan** (`Say.settings()`
  okunur değerleri verir; motor farklı bir sayı kırparsa tek seferlik HUD bildirimi yazılır,
  sessizce yutulmaz). Mute anahtarı `#voice` (vızıltının yanında, varsayılan açık) tercihini
  `sessionStorage` `fly.voice` anahtarında **oturum boyunca** tutar — sunucuya hiçbir şey
  gönderilmez (test bunu fetch kaydıyla doğruluyor); kapatınca `synth.cancel()` sesi anında
  keser, açılınca kısa bir Türkçe onay okunur. Cevaptaki köşeli parantezli İngilizce **sese
  gitmeden** temizlenir (`Say.clean`: önce sondaki `[...]`, sonra güvenlik ağı olarak cümle içinde
  kalan parantezler) — log tam metni gösterir, ses İngilizceyi duymaz; yalnızca parantezden oluşan
  cevap sessiz kalır. Kullanıcının kendi cümlesi `say` olayı üretmediği için hiç okunmaz; ilk
  yüklemedeki olay tekrarı (`REPLAY_ONLY`) eski cevapları konuşturmaz, kayıtlı "kapalı" tercihiyle
  açılan sayfa da sessiz başlar. **Bilinçli takas:** vızıltı artık **yedek ses** — okuma
  başarılıysa `Buzz.speak` çağrılmaz, böylece 200 Hz vızıltı ile konuşma üst üste binmez; okuma
  kapalıysa ya da tarayıcı `speechSynthesis` sunmuyorsa davranış tam Faz 2'deki gibi kalır
  (vızıltı çalar, `#voice` devre dışı bırakılır, HUD bildirimi çıkar).
  (b) **Ton yalnızca gerginken ("server.py", yalnızca istem):** kapalı liste
  `EXCLAIM_ALLOWLIST = ("lan", "hassiktir", "off", "mahvolduk", "ay")`, eşik `STRESS_HUNGER = 80`
  (**katı**: 80 sakin, 80.1 gergin) ve `stress_reason()` iki koşuldan birini arar — açlık > 80 ya
  da `startled` bayrağı. Blok **yalnızca o turda** isteme girer; sakin turda liste istemde hiç
  geçmez, yerine `CALM_LINE` yasağı gelir, yani "sakin halde asla" temenni değil yapısal. Vague
  bir "hafif argo serbest" kuralı yok: model tam listeyi ve "yalnızca BİR kelime" sınırını görür.
  (c) **İki dilli cevap (yalnızca istem):** `BILINGUAL` bloku Türkçe cümlelerden sonra **tek**
  köşeli parantez içinde aynı cümlelerin İngilizcesini ister (birebir çeviri değil, aynı ses);
  `TAIL` satırı biçimi istemin **en sonunda** tekrar eder (4B model en sondaki kurala uyuyor).
  Kişilikteki iki "İyi" örneğine de parantez eklendi — ölçülen neden: sakin turlarda model tam o
  örneği kopyalayıp çeviriyi düşürüyordu ("Karnım kazınıyor. Şu tarafta tatlı bir koku var…").
  **Ölçüm (gerçek Gemma 3:4b, `_fly_smoke.py tone`, 4 koşu ≈ 24 tur; ikisi LLM'siz `voice` fazında
  ayrıca deterministik doğrulanır):** ilk koşuda parantez 3/6 turda vardı ve "tek ünlem" kuralı
  3/3 gergin turda aşılıyordu ("Lan, off!"); hatırlatma satırlarından sonra **6/6 parantez**, tavan
  hiç aşılmadı, sakin turlarda **0** liste kelimesi, örnekler: `Hassiktir, bu bir terlik! [Oh no,
  that's a slipper!]` (açlık 88), `Bir gölge üstüme kapandı, karnım da zil gibi çalıyor! [A shadow
  fell over me, my stomach is ringing like a bell!]`, sakin halde `Merhaba. Ben iyiyim, teşekkür
  ederim. [Hello. I'm fine, thank you.]`. Kalıntı risk dürüstçe yazılı: 4B model gergin turda ara
  sıra ikinci bir ünlem yazabiliyor (bir koşuda bir kez görüldü) ve bu faz istem-only olduğu için
  sunucuda süzgeç **yok**; kesin garanti istenirse `final` metnindeki ikinci ünlemi düşüren küçük
  bir deterministik kontrol eklenebilir (bilinçli olarak yapılmadı; `tone` fazı ihlali `[!!]` ile
  bağırır ve en fazla bir kaymayı tolere eder, sakin taraf ise sert doğrulanır).
  İstem bütçesi: sakin tur ~4,7 KB → **5,7 KB** (+~250 token), gergin tur **6,3 KB**; bu koşuda
  ortalama tur 13,7 sn (kayıtlı ~16 sn ile uyumlu). Kısaltma istenirse ilk aday `BILINGUAL`
  içindeki iyi/kötü örnek çifti.
- **Faz 12.5 — "tek ünlem" kuralı artık istem değil, garanti (yalnızca `server.py`; istem metni,
  liste ve eşik DEĞİŞMEDİ).** Ölçüm, 4B modelin gergin turda ara sıra iki ünlem yazdığını göstermişti
  ("Lan, off!", "Lan, hassiktir…"); Faz 12B bunu yalnızca *rica ediyordu*. Cevap artık istemciden
  çıkmadan önce tek bir noktada süzülüyor — `run_agent`'ın `final` dönüşü, yani istemciye giden LLM
  metninin **tek** çıkışı: `single_exclaim()` Türkçe kısımda `EXCLAIM_ALLOWLIST` kelimelerinden
  yalnızca **ilkini** bırakır, sonrakileri önlerindeki boşlukla birlikte siler ve noktalamayı yeniden
  kapatır: `"Lan, off!"` → `"Lan!"`, `"Lan, hassiktir, bu bir terlik!"` → `"Lan, bu bir terlik!"`,
  `"LAN, OFF, MAHVOLDUK!"` → `"LAN!"` — `,,` ya da sarkık virgül kalmaz. Eşleşme kelime sınırında
  (`(?<!\w)…(?!\w)`) ve `[iİıI]` sınıfıyla Türkçe büyük "İ"ye duyarlı, yani "planlama", "ayran",
  "ofis", "oflaz" tetiklemez. 0 ya da 1 eşleşmede metin **bayt-bayt aynı** geçer (sakin cevap =
  no-op; bu yeni bir davranış kapısı değil, sigorta); `[...]` içindeki İngilizce hiç taranmaz ve
  böl-yeniden-birleştir ile aynen korunur (tarayıcının sesli okuma temizliği ona bağlı). Her
  devreye girdiğinde sunucu loguna tek satır düşer (`tek ünlem süzgeci (2->1): … -> …`), böylece
  sessizce çalışan bir maske olmaz. Kanıt: LLM'siz `filter` fazı 17 girdilik tabloyu (2-3 ünlem,
  farklı konum/noktalama, `LAN/OFF/MAHVOLDUK`, `Hassİktİr`, iki parantezli bozuk cevap) ve sahte
  modelle `run_agent` entegrasyonunu doğrular; `tone` fazı gerçek Gemma turunda süzgeci bir kez
  yakaladı — HAM `Lan, hassiktir, bu bir terlik! [Oh no, that's a slipper!]` → istemciye giden
  `Lan, bu bir terlik! [Oh no, that's a slipper!]` (aynı koşuda 6 gergin turun 5'i zaten tek ünlem
  kullanmıştı, sakin turlarda 0 ve sakin cevapların hiçbiri değişmedi).
- **Faz 13 — sinyal birincil, LLM sadece çözücü.** Mimari düzeltme: LLM'in süslü cümleleri
  "konuşan sinek" gibi okunuyordu ve çekirdeğin gerçek kararı küçük bir satırda kalıyordu. Artık
  sunucu, o turu **zaten açıklayabiliyorsa** (sınıflandırıcı bir kategori verdi ya da otonom bir
  dürtü ateşledi) model kişilik istemini hiç görmez: `system_prompt(origin, signal=True)` bunun
  yerine `SYSTEM_SIGNAL`'ı (DECODER + `CONTRACT_SIGNAL` + araç kataloğu) kurar ve çıktı
  **2-4 kelimelik bir durum parçası** olmak zorundadır — `"durum · eylem [English]"`, örn.
  `aç · yaklaşıyor [hungry · approaching]`, `ürkmüş · kaçıyor [startled · fleeing]`,
  `tok · sakin [full · calm]`. Birinci şahıs anlatım, metafor, cümle ve ünlem yasak; ayrıntı
  promptta değil *örnekte* duruyor (`CONTRACT_SIGNAL`'ın `final` örneği parça+parantez), çünkü
  4B model sözü değil somut örneği taklit ediyor: sözle "parantez ekle" dediğimde 6 turun 2'sinde
  parantez düştü, örneği değiştirince iki koşuda **6/6** geldi. Serbest sohbet (sözlükte
  karşılığı olmayan mesaj) eski kişilikle devam eder — ama istemci onu **"serbest sohbet (LLM)"**
  diye etiketler, yani LLM cümlesi bir daha sineğin sözü sanılmaz. Arayüz: `classifier` olayı
  büyük `.signal` bloğu (kategori · kelime · güven + vital etkisi, birincil), modelin parçası
  altında `.yorum` satırı (küçük, soluk, "yorum" etiketli). Sınıflandırılmış turlarda "SİNEK"
  balonu tamamen kalktı; `/öğret` cevabı da artık çip. `mode` alanı (`caption`/`chat`/`system`)
  `say` olayında taşınır (`_chat` meta → executor → istemci), böylece istemci hiç tahmin etmez.
  Liste/eşik/12.5 süzgeci değişmedi (parçalarda ünlem olmadığı için süzgeç artık etkisiz bir
  güvenlik ağı). `test`: `caption` fazı gerçek modelle 6 kategoriyi tarar ve örnekleri basar;
  `llm` fazında "Merhaba! Kısaca kendini tanıt." turu `selam · konuşuyor [hello · talking]`
  döndü — eskiden bir tanıtım konuşması olurdu.
- **Faz 14 — gövde ve çevre söz sahibi oldu.** Üç boşluk kapatıldı, hepsi deterministik:
  (a) **Eksik enerji refleksi.** Açlık Faz 5'te `eat` refleksini almıştı, enerji almamıştı: yorgun
  sinek saat sorgusunu sonsuza kadar tekrarlayıp "yorgun · dinleniyor" diyordu ama enerji hiç
  toparlanmıyordu. `AUTONOMIC_EFFECTS["dinlenme"]` artık `{"action": "rest", "delta": {"energy":
  +8, "hunger": +2}, "recover": {"energy": 3.0, "ticks": 10}}` taşır: açılış taksiti
  `server.fire_reflex` ile (LLM turu bittiğinde), kalanı **GameLoop'un saatinde** tick başına.
  Tablo ayrı durur çünkü `CATEGORY_EFFECTS` ile `cognitive_matrix.CATEGORIES` 1:1 ve iki self-test
  bunu doğruluyor — `reflex_for()` her iki tabloya bakar, `effect_for()` yalnız fabrikaya (yani
  öğretilmiş bir kategori asla çevre satırını ödünç alamaz). Ölçüm: enerji 0 → 11 tick'te 27.3
  (> kritik 25), 15 tick daha → 52.8; `show3d(clock)` çağrıları tam o anda **durdu** (10 → 10) ve
  `top_need()` boşaldı. Eşik `REST_THRESHOLD = 30` (kritik 25'in üstünde, yani dürtü ateşlemeden
  önce toparlanıyor), turlar arası `REST_COOLDOWN = 60` sn.
  (b) **Çevre olayları.** `darbe` (enerji −15, can sıkıntısı −10, `startled`) ve `rastgele-besin`
  (açlık −20) `ENV_WEIGHTS` ağırlıklarıyla seçilir ve sözlük kelimeleriyle **aynı** hattan geçer
  (`apply_effect` → vital/bayrak + `reflex` olayı, `want`/`saturated` alanlarıyla, tıpkı
  sınıflandırıcı olayı gibi). Beş kapı: `env_chance` (0.004/tick ≈ ~4 dk), `env_cooldown` (90 sn),
  `state.idle_seconds() >= 45` (`_chat` her kullanıcı mesajında `touch()` çağırıyor), son dürtüden
  bu yana 45 sn, executor boş, dinlenme turu yok. `env_rng` enjekte edilebilir, bu yüzden kapılar
  tek tek ve olasılık da bağımsız sınanabiliyor: sohbet sırasında/executor meşgulken/dinlenirken
  **0 olay**, gerçekten yalnızken darbe (enerji 80 → 65) ve rastgele-besin (açlık 30 → 10.4),
  p=0.01 ile 2000 tick'te 23 olay (beklenen ~20). Karar: çevre olayı ek LLM turu **başlatmaz** —
  deterministik `reflex` çipi + vital hareketi anlatıdan önce gelir (Faz 13 hiyerarşisi).
  (c) **Gergin kaptanlarda ünlem izni.** `DECODER` hiç ünlem görmüyordu, o yüzden gergin bir kaptan
  küfredemiyordu. `system_prompt(signal=True)` artık gerginken `SYSTEM_SIGNAL_STRESS`'i kurar:
  `CONTRACT_SIGNAL_STRESS`'ın `final` örneği **`hassiktir · kaçıyor [oh no · fleeing]`**, artı
  `CAPTION_STRESS` bloğu (kapalı liste, "İLK YUVA ünlem OLACAK", en fazla bir) ve `signal_state()`
  gerginken `STRESS_FRAGMENT` örneğini gösterir; sakin istemde liste **hiç geçmez**
  (`CAPTION_CALM` + `CAPTION_TAIL`). Ölçüm: gergin 3 turun **2'si** listeden ünlem kullandı
  (`hassiktir · sıçradı`, `lan · sıçradı`), hiçbiri 1'i aşmadı, hepsi ≤4 kelime + parantezli; sakin
  5 kaptan turunda **0** ünlem. İnce bir ayrıntı ölçümde ortaya çıktı ve teste yazıldı: mesajın
  *kendi* etkisi durumu aynı turda değiştirebiliyor — `tehlike yaklaşıyor` sakin başlayıp
  `startled` bayrağıyla gergin bitiyor, `önünde şeker var` ise açlığı 35 düşürüp gerginliği
  **kaldırıyor**; bu yüzden test gerginliği `route_message`'dan *sonra* okuyor. `single_exclaim()`
  bu yolda da çalışıyor: `hassiktir · off · kaçıyor` → `hassiktir · kaçıyor` (parça ayırıcısı `·`
  için noktalama düzeltmesi de eklendi).
- **Sözlük küçük ve sabit — artık çalışırken de öğretilebilir.** Eşleşme yoksa mesaj
  sınıflandırıcıya hiç uğramaz, serbest sohbete düşer. Fabrika 55 kelime
  `cognitive_matrix.VOCAB` içinde tek satırdır; çalışma anındaki eklemeler `/öğret` ile yapılır ve
  ayrı tutulur, böylece "bu kelime eğitilmiş mi, öğretilmiş mi?" her zaman cevaplanabilir.
  Türkçe ekler çalışır ("şekerli", "merhabalar", "acıktım"), çünkü kelimeler ASCII'ye
  katlanır ve kök öneki eşleşir.
- **Bir mesaj = bir kategori.** Cümlede birden çok sözcük tanınırsa en yüksek güvenlisi
  kazanır; diğerleri `classifier` olayının `alternatives` alanında görünür. Kategori →
  vital eşlemesi tek tablodur (`game_loop.CATEGORY_EFFECTS`): "şeker" → açlık −35,
  "tehlike" → can sıkıntısı sıfırlanır + 25 sn `startled` bayrağı, "selam" → sadece sosyal,
  "acıktın mı?" → **hiçbir şey değişmez** (soru sorudur; sinek ölçümünü anlatır).
  Olay iki sayı taşır: `want` (tablonun niyeti) ve `delta` (0-100 kırpmasından sonra
  gerçekten olan); `saturated` hangi vitalin zaten sınırda olduğunu söyler, böylece tok bir
  sineğe şeker verildiğinde arayüz "açlık −35 (sınırda: açlık)" yazar, uydurmaz.
- Üslup: persona "kısa cümle + yasaklı mekanik kalıplar + iyi/kötü örnek" kuralları taşır;
  araç kataloğunda hareket/görselleştirme ayrımı açıkça yazılıdır ("yürü/dön/kaç" → move_fly,
  "göster/hangi bölge" → show3d; ikisi birlikteyse hareket kazanır).
- Sistem promptu ~3.0 KB: aynı iş yükünde tur süresi ~30 sn'den ~16 sn'ye inmişti. Ek
  açıklama yazacaksan `_fly_smoke.py bench` maliyetini ölçer.
- Fiziksel gövde **bilerek** yok. Gövde katmanı (MuJoCo köprüsü, `/motor` olayları, gövde
  telemetri paneli, MJPEG akışı) Faz 9'da tamamen silindi; `move_fly` / `navigate_fly`
  araçları hâlâ inen nöron komutlarını **3D sahnede** gösterir ama hiçbir aktüatöre bağlı
  değildir ve hiçbir araç `motor` olayı yayınlamaz (`_fly_smoke.py tools` bunu doğrular).
- flybody / NeuroMechFly indirmesi (`models/`, ~150 MB) diskte duruyor ama artık koda bağlı
  değil — klasörü elle silmek güvenlidir.

## Setup

1. **Ollama + a Gemma model.** Defaults to `gemma4:latest`. Check what you have:
   ```bash
   ollama list
   # don't have it? `ollama pull gemma3:4b` and set MODEL in agent.py
   ```
2. **Python deps** (uses a local venv with system site-packages):
   ```bash
   python3 -m venv .venv --system-site-packages
   .venv/bin/pip install -r requirements.txt
   ```
3. **Connectome data** (one-time, ~852 MB, no login):
   ```bash
   bash get_data.sh
   ```
   The neuron annotation file (~32 MB) auto-downloads on first run.

## Run — live chat + 3D (start here)

```bash
.venv/bin/python server.py        # then open http://localhost:8000
```
**Windows one-click:** double-click `start.bat` in the workspace root (`Genesis_Fly\`). It finds
`flyputer\server.py`, prefers `flyputer\.venv\Scripts\python.exe` (else `py -3`, else `python`),
warns if Ollama / a gemma model is missing, and — if the port is already listening — refuses to
start a second server: it just opens the browser. The server stays in the foreground, so `Ctrl+C`
stops it. Every `server.py` flag passes through: `start.bat --port 8081 --no-autonomy`.

Chat on the right, a live 3D fly brain on the left. (First start loads the connectome, ~5s,
then warms the gates / routing graph / escape circuit in the background.)

Things to ask — each lights up the real connectome and comes back with an energy ledger:

- **"What happens when the fly smells something?"** — stimulates olfactory neurons and you
  watch the signal cascade through the brain.
- **"Show me the fly brain computing an AND gate"** — three real neurons cycle through every
  input combination with a live truth table, a robustness chip, and an energy cost. The
  same convergent motif computes **AND or OR** depending on excitability; gates that work:
  AND, OR, AND-NOT. (`logic.py` finds the motifs; `energy.py` does the accounting.)
- **"Add 2 + 3 with the fly brain"** — composes those real gates into a half/full adder and
  ripple-carries across bits: `2 + 3 = 5` (`010 + 011 = 101`). It also **multiplies**
  ("multiply 6 × 7" → 42). `flymath.py` is the adder/multiplier.
- **"Show me the fly's compass"** — the central-complex ring of EPG/PEN/PEG/Δ7 neurons forms
  a **heading bump** that holds like a memory and **steers to track a turn**, with a live
  heading dial. First *stateful* computation in the project. (`compass.py`)
- **"Walk the fly forward, turn left, then make it escape"** — drives the real **descending
  command neurons** (DNp09 forward, MDN backward, DNa02 steering, DNp01 Giant Fiber escape)
  and a virtual fly body moves in a top-down arena. (`fly.py`)
- **"Release the fly at heading 120 and let it navigate"** — closed loop: the real
  **compass → PFL3 → DNa02** steering pathway homes the fly onto a stable heading. (`fly.py`)
- **"Trace the path from sugar to motor"** — "six degrees of the fly brain": one shortest
  *wiring* path lights up hop-by-hop. The graph recovers textbook circuits on its own
  (EPG→PFL3→DNa02 steering, olfactory ORN→PN→Kenyon). Pure topology, zero firing claims.
- **"Let me try to swat the fly"** — a **playable game**: a looming swatter drives the real
  LPLC2+LC4 detectors converging onto the Giant Fiber; swing faster than the circuit's
  reaction limit to land it, slower and the real escape reflex jumps first. (`swatter.py`)
- **"How does the fly remember two smells without forgetting?"** — two odors light up two
  near-disjoint sparse sets of Kenyon cells (~0.6% each, ~2% overlap), so a new memory barely
  touches an old one — the architecture behind not suffering catastrophic forgetting. (`sniff.py`)
- **"Show a heart on the fly's eye"** — paint a picture onto the ~789 L1 lamina columns and
  it travels along ~66k real L1→Mi1 synapses into the medulla: a recognizable image glowing
  on the real optic lobe (a ~750-column brain's-eye view, not a camera). (`optic.py`)

## Or use the pieces directly

```bash
.venv/bin/python agent.py                      # default: find sugar neurons → stimulate → explain
.venv/bin/python agent.py "Stimulate visual projection neurons and tell me what responds"
.venv/bin/python agent.py -i                   # interactive chat
.venv/bin/python visualize.py                  # plot the response → fly_response.png
.venv/bin/python visualize.py "mushroom body" 30 300   # any term, #seeds, duration(ms)
.venv/bin/python export3d.py olfactory 40 200          # 3D web view: opens fly3d.html

.venv/bin/python logic.py        # find AND / OR / AND-NOT gate motifs, with robustness
.venv/bin/python flymath.py      # add & multiply through real composed gates (demo set)
.venv/bin/python compass.py      # CUE → HOLD → TURN: heading-memory regime comparison
.venv/bin/python fly.py forward left forward escape   # ASCII trajectory from real DNs
.venv/bin/python swatter.py      # sweep swing speeds: who wins vs the escape circuit, and why
.venv/bin/python sniff.py        # two odors -> near-disjoint sparse Kenyon-cell codes
.venv/bin/python optic.py heart  # relay an image through the real optic lobe (ASCII in/out)

# find_neurons understands region names: sugar, gustatory, "mushroom body",
# "central complex", clock, olfactory, descending, motor, Kenyon, MBON.
```

Smoke-test the backend alone (no LLM needed):
```bash
.venv/bin/python flysim.py
```

Validate the claims (precision, control circuits, gate robustness, arithmetic):
```bash
.venv/bin/python eval.py         # neurons | controls | gates  to run one layer
```

## How it works

- **`flysim.py`** loads the connectome edge list + neuron annotations and exposes the core
  tools: `find_neurons` (search by cell type / class / region), `stimulate` (inject current,
  run a tiny leaky-integrate-and-fire sim over the 2-hop downstream subcircuit),
  `shortest_path` (BFS routing for "six degrees"), and `neuroglancer` (a 3D viewer URL).
- **`logic.py` / `flymath.py`** — real gate motifs and arithmetic composed from them.
- **`compass.py`** — the central-complex ring attractor (heading memory + steering).
- **`fly.py`** — descending-neuron → behavior mapping, body kinematics, and the closed-loop
  compass→DNa02 steering controller.
- **`swatter.py`** — the looming-escape circuit (LPLC2/LC4 → Giant Fiber) and the swat game.
- **`sniff.py`** — the mushroom-body olfactory-learning slice and sparse-coding analysis.
- **`optic.py`** — the retinotopic lamina→medulla (L1→Mi1) image relay.
- **`energy.py`** — the energy ledger (see below). **`export3d.py`** builds the 3D scenes;
  **`server.py`** is the web app; **`agent.py`** is the version-agnostic JSON tool-calling
  loop around Gemma. **`eval.py`** is the validation harness.
- **`brain_state.py`** / **`game_loop.py`** — this fork's autonomous core: the fly's vitals
  (enerji / açlık / can sıkıntısı) plus short-lived flags, the 1 Hz `GameLoop` that fires
  autonomous impulses, the thread-safe `EventBus`, the single-worker `LLMExecutor` behind a
  priority queue, and `CATEGORY_EFFECTS` (classifier category → vitals delta).
- **`cognitive_matrix.py`** — the mushroom-body classifier, now on the real wiring: a Turkish
  word is ASCII-folded, its char 3/4-grams light ~11% of the 685 FlyWire ALPNs, the real
  ALPN→KC matrix (`sniff.circuit()`: 23,501 connected pairs, edges ≥3 synapses) turns that into
  a boolean sparse Kenyon-cell code through `sniff.kc_code()`'s coincidence threshold, and a
  delta-rule readout trained on the 55-word vocabulary maps that code onto six categories.
  `/state` reports `"connectome": true`; what is *ours* is the word→ALPN input pattern and the
  readout, both named in `status()["honest_note"]`. The measured numbers (per-word confidence,
  KC density and overlap, out-of-vocabulary rejection) are in the Turkish section above.
  Since Phase 11 the vocabulary is also teachable while the server runs (`/öğret elma besin`):
  one single-example delta step plus one extra readout row for a new category, then a re-measure
  of the *whole* old vocabulary (before/after numbers in the reply, the `teach` event and
  `learned_words.json`), with `/öğret-geri` as the way back. Phase 11.5 added the measured
  safety net on top of that same re-measure (a word within `TEACH_SAFETY_MARGIN` of the 0.40
  floor, or a single teach that drops one word by `TEACH_SAFETY_STEP`, returns
  `level: "alert"` and a `⛔ GÜVENLİK SINIRI` block naming `/öğret-geri` — detection only, the
  human decides) and `/öğret-efekt <kategori> <etki>|yok`, which lets a live-taught category
  borrow one of the six factory effects (stored as `effect_aliases` in `learned_words.json`;
  with no mapping it stays informational and moves nothing, as in Phase 11).
  Phase 9 deleted the physical layer: no `mujoco_bridge.py`, no `/motor` endpoint, no body panel.

No CAVE token, no `fafbseg`, no GPU — just the Zenodo file + the GitHub annotation TSV.

### The energy ledger

The brain is **event-driven**: a synapse only costs energy when its neuron fires. A
conventional chip simulating the same circuit is **clocked** — it re-evaluates every synapse
every tick whether it fired or not. So the fly-vs-chip ratio isn't a fixed number; it tracks
**activity sparsity**, a real measured quantity. Sparse computations (a logic gate, ~3% of
synapses active) show the brain ~thousands of times cheaper; dense ones (a big olfactory
cascade, ~44% active) much less. Per-synapse cost ≈ 10 fJ (Attwell & Laughlin) vs ≈ 1 pJ per
clocked MAC (Horowitz); the chip clock is priced at a physical 1 kHz, not the sim's `dt`.

## Honest caveats

- The simulation is a **toy**: Shiu-style sign convention (ACh = excitatory, GABA/Glu =
  inhibitory, neuromodulators ≈ 0), ~13% neurotransmitter-prediction error, and absolute
  firing rates are **not** meaningful. It's for *qualitative* "what's downstream of what"
  exploration and motif-level computation, not biophysics.
- It runs a bounded **2-hop subcircuit**, not the whole brain at biophysical fidelity.
- **The VNC + muscles are not in this dataset (brain only).** The moving fly and the swatter
  game read the brain's *real* motor commands (descending neurons), but the body itself is a
  labelled stand-in for the missing ventral nerve cord.
- **"Six degrees" is topology, not timing** — it returns *a* shortest wiring path (one of
  possibly many, at ≥5 synapses/edge), not a causal/temporal signal path.
- **Dodge the swatter** reports the *order* of events (detectors charge → Giant Fiber spike →
  lunge) and which swing speeds escape — **not** calibrated millisecond latencies.
- The compass forms and steers a sharp bump faithfully; a *self-sustained* held heading needs
  finer excitation/inhibition tuning than this toy provides.
- **Two smells** demonstrates the *mechanism* (sparse, near-disjoint Kenyon-cell codes), not a
  rigged benchmark — a dense net on random odors can separate them too; the point is *how* the
  fly does it. The Kenyon code is a tuned coincidence threshold, not a calibrated firing rate.
- **The fly's eye** is a ~750-column retinotopic sensor / brain's-eye view, **not** a camera:
  no ommatidial optics, no T4/T5 motion detection, uncalibrated rates. The medulla is read out
  at each cell's lamina column (a full undistorted 2D reconstruction needs de-warping the
  curved hex lattice, which a plain PCA flatten can't do — verified retinotopic only in 1D).
- Root IDs are pinned to FlyWire materialization **v783** (the Oct 2024 *Nature* release).

## License / attribution

- **Code:** MIT — see [`LICENSE`](LICENSE).
- **Data:** the FlyWire connectome is **CC BY-NC 4.0 (non-commercial)**. See
  [`CITATION.md`](CITATION.md) for the papers to cite and the non-commercial terms.
- Independent hobby project — **not affiliated with the FlyWire consortium.**

## What's next

A sibling project turns the ~88-neuron central-complex "compass" circuit into an actual
**chip blueprint** (connectome → Verilog → GDSII layout, free on a laptop). The compass and
closed-loop steering demos here are the on-ramp to it.

---

> ### ⚠ İKİ AYRI PROJE — aynı depoda / two separate projects in one repository
> Yukarıdaki `flyputer` uygulaması (3D beyin + kelime sohbeti, Gemma/Ollama) **değiştirilmedi**.
> Aşağıdaki **`numcog/`** bölümü, ayrı bir **bilimsel** çalışmadır (Faz 0–8 + kapanış paketi):
> connectome üzerinde **sayı/kod, hesap makinesi, rezervuar ve MB öğrenme** deneyleri.
> Kod: **MIT**; **veri CC BY-NC 4.0** (`CITATION.md`, `DATA.md`, `NOTICE.md`).

# numcog — connectome simulations on the FlyWire brain (science track)

**What this is (one honest paragraph).** A simulation study, not a live fly. On the FlyWire
hemibrain connectome we built: (i) **number/operator codes** from real VPN→KC / ALPN→KC wiring;
(ii) a **gated, table-based calculator** at N=81 where the **fly core only computes `n → n±1`** and a
Python **controller** carries the counter, loop and remainder; (iii) **reservoir dynamics** in a
CX-core sub-network (A: N=4,236); and (iv) **DAN-gated KC→MBON plasticity** in the mushroom body with
odour/decision tasks. Results: the calculator works **exactly** (add/sub/mul/div = 1.0000, chain
k=0..81 correct) **only in the 54/100 seeds that pass a calibration gate**; the biological learning
rule **does learn** (sanity gate 0.982; T1 N≤4: 0.971) but its performance is **not** better than
degree-preserving/ER surrogates; the CX reservoir carries state for k≤8 in a fair (per-arm gain)
regime but **collapses at k=10** and is **not** superior to surrogates; rule/extrapolation (T3) is
**below chance**. In short: **connectome-derived circuits act as memorisation/pattern-separation
tables; there is no rule transfer, and no wiring-specific advantage on the tasks we designed.**
In this data, in this model, on this grid.

## Quick start / Hızlı başlangıç

```bash
pip install -r requirements.txt          # Python 3.12.10
bash get_data.sh                          # FlyWire v783 (~812 MB) — not committed (see DATA.md)

python -X utf8 server.py                  # http://127.0.0.1:8000  (chat + 3D + calculator tab)
# sağ üst: "🧮 Hesap Makinesi / Calculator" → 3+5 · 12-7 · 7x8 · 9/4 · adım dökümü · SAHTE SİNEK

python -X utf8 -m numcog.tests.test_calculator_integrity   # 34 checks, ~1 s, no heavy training
python -X utf8 _calc_smoke.py                              # interface smoke test (server running)
python -X utf8 numcog/build_fly.py                         # train the calculator fly (~16 s/seed)
```

## Results table (sourced) / Sonuç tablosu

- **`numcog/RESULTS_SUMMARY.md`** — TR/EN table: question · hypothesis → result · key numbers ·
  source file · pre-registration → result commit.
- **`numcog/PROJE_KAPANIS.md`** — full closing report (goals, what was measured, what could not be
  measured, what the fly vs the controller did, artifacts caught, limitations, **what we do NOT
  claim**, future work).
- **`numcog/PREREG_LOG.md`** — pre-registration vs result commit order (exceptions stated).
- **`numcog/RELEASE_PREFLIGHT.md`** — pre-release measurement (repo state, sizes, history blobs,
  privacy scan, dead-code status, **missing tests**).
- **`numcog/V1_OZET.md`**, `RAPOR_FAZ_0.md` … `RAPOR_FAZ_8.md`, `RAPOR_HESAP_MAKINESI_BUTUNLUK.md`,
  `RAPOR_ARAYUZ.md`, `RAPOR_IKI_HANELI.md` — phase reports.

## Limits (read before asking the fly anything)

`1..9` digits (measured); **result 0..81**; `x`/`*` = multiplication, `/` = **integer quotient +
remainder**; subtraction with a **negative** result is **rejected** (the legacy measurement clipped to
0); **no multi-digit arithmetic** (the two-digit tens/units design was **never implemented**); the
**state lives in the controller, not in the fly**; a random seed has ~46% chance of being rejected by
the calibration gate (the shipped fly is **seed 0**, accepted). Full list in the calculator panel and
in `numcog/RAPOR_ARAYUZ.md`.

## What we do NOT claim / İddia etmediklerimiz

Not "the fly does mathematics" (the core is an exact `n→n±1` table; the controller loops) · not
"multi-digit arithmetic" (not implemented) · not "language logic" (no language model exists in
`numcog/`; the word classifier is the separate `flyputer` app) · not "connectome gives a special
advantage" (it did not separate on any task) · not "it learns rules" (rule tests were at/below
chance) · not "state is carried by the network" (k≤8 only, and not better than surrogates).
**Simulation**, one connectome (hemibrain 783), NT signs assumed, MB compartments inferred,
input-neuron choice arbitrary.

## Translations / Çeviriler

`docs/en/` — English translations (Turkish originals remain authoritative, stay in place).
See `docs/en/INDEX.md` for the coverage list (and what is still pending).

