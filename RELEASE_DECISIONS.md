# RELEASE DECISIONS — owner rulings (2026-09-21)

These are the **owner decisions** that close the open items listed in `RELEASE_CHECKLIST.md`.
They are recorded here verbatim so that the repository does not have to be rewritten to answer them.

| # | Konu / Item | Karar / Decision | Sonuç / Consequence |
|---|---|---|---|
| 1 | `LICENSE` telif satırı uyuşmazlığı (Migen Karriqi ↔ git yazarı Furkan Tahsin Bekdaş) | **Migen Karriqi'nin satırı korunuyor**, altına `Copyright (c) 2026 Furkan Tahsin Bekdaş` eklendi | İki telif sahibi birlikte listelenir; MIT metni değişmedi |
| 2 | 87,15 MB + 11,12 MB geçmiş blob'ları (git geçmişi) | **`filter-repo` YAPILMIYOR**; geçmiş olduğu gibi kalıyor; e-posta açık kalabilir | Ön-kayıt zaman damgaları ve commit hash'leri (`PREREG_LOG.md`) aynen korunur — 87 MB'dan kıymetli |
| 3 | Kayıp testler (`_fly_smoke.py`, `_fly_frontend_test.js`) | **`_calc_smoke.py` ikamesi yeterli**; dokümantasyonda şeffafça yazılı kalır | Test kapsamı dokümante edilmiş bir ikame; gizlenmiyor |
| 4 | 21 faz raporunun çevirisi | **`docs/en/INDEX.md` içinde PENDING olarak kalıyor**; şu an dokunulmuyor | Faz raporlarının İngilizce erişimi `docs/en/PHASES.md` digest'i üzerinden |
| 5 | `np.bool_` artefaktı ve Ollama/LLM yolu | **Silinmiyor**, "kullanılmıyor" etiketiyle bırakılıyor | Kod ve yol korunur; durum etiketiyle belgelenir |

## Repo yayını / Repository publication

- **Push hedefi:** `origin` → `https://github.com/migkapa/flyputer.git`, branch **`main`** (doğrudan push, geçmiş yeniden yazılmadan).
- **Önerilen GitHub açıklaması (EN)** — `REPO_DESCRIPTION.txt` içinde birebir:
  > Genesis Fly — bio-calculator and fly-brain-based communication interface: a gated arithmetic core
  > driven by a real Drosophila connectome simulation, plus an interactive chat/3D front end.
- GitHub CLI (`gh`) bu makinede **kurulu değil** ✗ → açıklama alanı API'den otomatik yazılamadı; metin
  `REPO_DESCRIPTION.txt` dosyasında hazır (Settings → Description alanına kopyala-yapıştır).

## Bilinen ve açık kalan durum / Known remaining state

- `docs/en/PHASE_*_REPORT.md` dosyaları makine çevirisidir (yerel Ollama `gemma3:4b`); her dosyanın başında
  sayı-token bütünlüğü kontrolünün sonucu yazılıdır (`PASS` / `REVIEW`). Türkçe asıllar otoriterdir.
- `chat3d.html.bak-*` yedekleri commit **edilmez** (çalışma dosyalarıdır).
