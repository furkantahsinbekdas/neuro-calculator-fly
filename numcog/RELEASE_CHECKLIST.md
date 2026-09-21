# RELEASE CHECKLIST — kapanış paketi (kanıtlı)

Tarih: 2026-09-20. Her madde **✓/✗ + kanıt**. `git push` **YAPILMADI**, remote **eklenmedi** ✓.

| # | madde | durum | kanıt |
|---|---|---|---|
| 1 | Faz 0–8 sonuç dosyaları değişmedi | **✓** | yalnızca **yeni** dosyalar eklendi; `results_p*/` ve `RAPOR_FAZ_*.md` içeriğine dokunulmadı |
| 2 | Ön-kayıtlar ölçümden önce | **✓** (1 istisna) | `numcog/PREREG_LOG.md` (Faz 3'ün arada yapılan veri-tasarımı düzeltmesi `7a15a4a` ve Faz 2b'nin post-hoc niteliği **açıkça** yazılı) |
| 3 | Hesap makinesi bütünlük testi | **✓** | `python -X utf8 -m numcog.tests.test_calculator_integrity` → **34/34, 0 kırmızı, 1 s**; `RAPOR_HESAP_MAKINESI_BUTUNLUK.md` |
| 4 | Sahte-sinek testi **çöküyor** mu | **✓** | sahte ortalama **0.1235** (gerçek 1.000); `3+5`: **8 → 68**; çağrı sayısı **değişmiyor** (5==5) |
| 5 | Arayüz toplu testi | **✓** | `_calc_smoke.py` → **324/324** beklenen davranış; sahte **0.2346**; sınır dışı **HTTP 422**; `/health`, `/state`, **`/chat`** çalışıyor |
| 6 | Mevcut kelime sınıflandırma bozulmadı | **✓** (ikame kanıt) | canlı `POST /chat` → "yiyorum · doydum" (güven 0.9674); o rotaya **hiç dokunulmadı**; `chat3d.html`'de mevcut `chat/viz/log/three.min.js` yerinde |
| 6b | İstenen `_fly_smoke.py` / `_fly_frontend_test.js` | **✗ YOK** | repoda **bulunamadı** → `_calc_smoke.py` **ikame** olarak yazıldı ve **ikame olduğu** her yerde yazılı (`RELEASE_PREFLIGHT.md` §6, `RAPOR_ARAYUZ.md` §3) |
| 7 | Mutlak yol / e-posta / anahtar taraması | **✓ (kodda)** / **✗ (geçmişte)** | gizli anahtar/token/`.env`: **yok** ✓; mutlak yol: yalnızca **numcog faz log'ları** (`run.log`, `run_ilk.log`, `merge_out.txt`) → **kural gereği dokunulmadı** ✓; **git yazar e-postası** (`furkantahsinb@gmail.com`) **geçmişte** ✗ → düzeltme = geçmişi yeniden yazmak → **karar sahibine** |
| 8 | >20 MB dosya | **✓ (takipli değil)** | 4 dosya (812 MB feather, 87 MB scan_cache, 30 MB annotations, 30 MB flybody) → **hepsi untracked + `.gitignore`'da**; takipli büyük veri **YOK** |
| 9 | Geçmişte büyük blob | **✗ VAR** | **87,15 MB** (`adef2e2`→`70bbb0f`) + **11,12 MB** (`ccdd1c1`→`838aae1`); `.git` **104,44 MiB**; **GEÇMİŞ YENİDEN YAZILMADI** → seçenekler + sonuçları `RELEASE_PREFLIGHT.md` §3 |
| 10 | `.gitignore` genişletildi | **✓** | 4 numcog önbelleği eklendi; `fly_weights/*.npz` **tutulur** (0.14 MB) |
| 11 | `requirements.txt` | **✓** | sürümler `pip freeze`'den sabitlendi; **eksik olan `scipy==1.18.1` eklendi** ✗→✓; Python **3.12.10** |
| 12 | Lisans kararı | **✗ BEKLİYOR** | `LICENSE` = MIT, "Copyright (c) 2026 **Migen Karriqi**" ↔ git yazarı **Furkan Tahsin Bekdaş** **uyuşmuyor** → sahibine soruldu (`NOTICE.md`) |
| 13 | Upstream atıfları | **✓ (kısmi)** | `CITATION.md` mevcut ✓; `NOTICE.md` yazıldı ✓; **flybody lisansı okunmadı** → `[VERIFY: flybody license terms]`; three.js CDN sürümü → `[VERIFY]` |
| 14 | `CITATION.cff` | **✓ (taslak)** | yazar alanı **boş**; atıflar `CITATION.md`'den; sayfa/DOI'ler `[VERIFY]` |
| 15 | Çeviri kapsaması | **KISMİ** | `docs/en/INDEX.md`: **tamam** → V1_OZET, RAPOR_HESAP_MAKINESI_BUTUNLUK, RAPOR_IKI_HANELI, RAPOR_ARAYUZ, RESULTS_SUMMARY (zaten iki dilli), `PROJE_KAPANIS` (**kısmi**, translator note'lu); **BEKLEYEN** → 21 `RAPOR_FAZ_*.md` + `HIPOTEZLER.md` ✗ (**açıkça** "pending", sessizce atlanmadı) |
| 16 | Her rakamın kaynağı | **✓ (1 istisna)** | `RESULTS_SUMMARY.md` ve `PROJE_KAPANIS.md` tablolarında her satırda kaynak dosya; **istisna**: `np.bool_` toplama hatası → **kaynağı bulunamadı** → `[VERIFY]` ✗ |
| 17 | Ölü LLM kodu | **✗ işaretlenmedi** | `server.py` (53) / `game_loop.py` (23) **referans ediyor** → "dead code" **iddiası doğrulanamadı** → `[VERIFY]`; **silinmedi** ✓ |
| 18 | WIP güvenliği | **✓** | kullanıcının commit edilmemiş işi **`1bf5dfb`** ile **içerik değiştirilmeden** kaydedildi |
| 19 | Sunucu durumu | **not** | kapanış sırasında **çalışır bırakıldı** (PID 2228, port 8000) → `Stop-Process -Id 2228` |
| 20 | `git push` / remote | **✓ push yapılmadı** | talimat gereği **push yapılmadı**; **remote EKLENMEDİ** — ancak `origin` **önceden vardı** (`https://github.com/migkapa/flyputer.git`, kullanıcının önceki işinden) → **bu pakette hiçbir push işlemi çalıştırılmadı** ✓ |

## Karar bekleyen maddeler (sahibine)

1. **Lisans telif adı** uyuşmazlığı (#12).
2. **Geçmişteki 87 MB + 11 MB blob** (#9): bırak ya da `filter-repo` (→ **tüm hash'ler ve
   `PREREG_LOG.md` tarihleri geçersiz olur**).
3. **Git yazar e-postası** (#7): geçmişte açık.
4. **`_fly_smoke.py` / `_fly_frontend_test.js`**: gerçek testler sağlanacak mı, yoksa ikame mi kalacak (#6b)?
5. **Kalan çeviriler** (#15): 21 faz raporu + `HIPOTEZLER.md` çevrilecek mi?
6. **`np.bool_` artefaktının kaynağı** (#16) ve **Ollama/LLM yolu** (#17) — `[VERIFY]`.

## Durum notu (AŞAMA 5 sonu)

- **AŞAMA 0–5 tamamlandı**; aşamaların hiçbirinde **test kırmızısı kalmadı** ✓ (iki geçici kırmızı
  yaşandı ve **gizlenmeden** çözüldü: AŞAMA 1 §3 dejenere `divide` tabanı, AŞAMA 2 §4 test yanılgısı).
- **`git push` yok, remote yok** ✓.
