# RELEASE PREFLIGHT — kapanış paketi ön kontrolü (AŞAMA 0)

Tarih: 2026-09-20. **Bu aşamada hiçbir dosya DEĞİŞTİRİLMEDİ/SİLİNMEDİ** (yalnızca bu rapor, ham git
geçmişi dökümü ve `results_release/` dizini **eklendi**). Kaynak: aşağıdaki her rakam, belirtilen
komutun çıktısıdır. Dil: **"bu veride, bu modelde, bu ızgarada"**.

## 1. Git durumu ve ÇALIŞMA AĞACI (uyarı: commit edilmemiş WIP var)

- **HEAD:** `a69a8d9` · **commit sayısı: 68** (`git rev-list --count HEAD`).
- Tam geçmiş dökümü: **`numcog/results_release/git_history.txt`** (68 satır,
  `%h|%ad|%an|%ae|%s`, `--date=iso`) → `PREREG_LOG.md` için ham girdi ✓.
- **ÇALIŞMA AĞACI TEMİZ DEĞİL** (`git status --short`) — **bu değişiklikler kapanış paketi kapsamında
  DEĞİLDİR ve bu pakette üretilmemiştir**:

| dosya | durum | diff (`git diff --stat`) |
|---|---|---|
| `server.py` | **M** | ~+2007 satır |
| `chat3d.html` | **M** | ~+1779 |
| `README.md` | **M** | ~+565 |
| `CLAUDE.md` | **M** | ~+472 |
| `agent.py` | **M** | ~+90 |
| `.gitignore` | **M** | ~+11 |
| `fly.py`, `optic.py`, `sniff.py` | **M** | 4 / 3 / 8 |
| `brain_state.py`, `capacity_benchmark.py`, `capacity_report.txt`, `cognitive_matrix.py`, `game_loop.py` | **?? untracked** | — |
| `numcog/results_p7_0/scan_cache.npz`, `results_p7_1/arms_cache.npz`, `results_p7_2/arms_raw_cache.npz`, `results_p8/mb_cache.npz` | **?? untracked** (önbellek) | — |

**Sonuç / öneri:** AŞAMA 2 `server.py` ve `chat3d.html`'e **ekleme** yapacaktır; bu dosyalar zaten
**commit edilmemiş kullanıcı işi** içerdiği için önce **WIP anlık görüntüsü ayrı commit** olarak
kaydedilecek (içerik **değiştirilmeden**), sonra köprü eklenip **ayrı** commit edilecek. Aksi hâlde
kullanıcı işi ile kapanış paketi aynı commit'te karışır ve geri alınamaz.

## 2. Boyutlar (`Get-ChildItem -Recurse -File`; `.venv`/`.git` hariç)

**>20 MB olan dosyalar (4):**

| MB | dosya | takipli mi? |
|---|---|---|
| 812,6 | `proofread_connections_783.feather` | **HAYIR** ✓ (`.gitignore`) |
| 87,2 | `numcog/results_p7_0/scan_cache.npz` | **HAYIR** ✓ (önbellek) |
| 30,2 | `annotations_783.tsv` | **HAYIR** ✓ (`.gitignore`) |
| 29,7 | `models/flybody/.../fruitfly.xml` | **HAYIR** ✓ (`models/` ignore) |

→ **Takip edilen büyük veri dosyası YOKTUR** ✓ (`git ls-files --error-unmatch
proofread_connections_783.feather` → "did not match any file(s) known to git"; `annotations_783.tsv`
için de aynı ✓). Takipli dosya: **697**, bunun **674'ü `numcog/`** altında (ağırlıklı faz CSV'leri).

## 3. GEÇMİŞTEKİ büyük blob'lar (`git rev-list --objects --all` + `git cat-file --batch-check`)

| MB | blob | eklendiği | çıkarıldığı |
|---|---|---|---|
| **87,15** | `numcog/results_p7_0/scan_cache.npz` | `adef2e2` (Faz 7-0) | `70bbb0f` |
| **11,12** | `numcog/results_p7_1/arms_cache.npz` | `ccdd1c1` (Faz 7-1) | `838aae1` |

`.git` boyutu: **104,44 MiB**, 894 gevşek nesne, pack 139,45 KiB (`git count-objects -vH`).
→ Depo ağırlığının tamamı bu **iki tarihsel blob**tan geliyor. **GEÇMİŞ YENİDEN YAZILMADI** ✓.
Karar **kullanıcıya**: (a) olduğu gibi (push ağır ama 100 MB tek-dosya sınırının altında),
(b) `filter-repo`/BFG → **tüm hash'ler ve `PREREG_LOG.md`'deki commit no'ları geçersiz olur** ✗.

## 4. Gizlilik taraması (takipli dosyalar; `Select-String -Path (git ls-files)`)

- **E-posta / API anahtarı / token: YOK** ✓ (`gmail|sk-[A-Za-z0-9]{20,}|ANTHROPIC|OPENAI|api_key` → 0 eşleşme).
- **`.env` dosyası YOK** ✓ (`-Force -Filter '.env*'`, `.venv` hariç).
- **Mutlak yol / kullanıcı adı bulunan takipli dosyalar:**

| dosya | eşleşme | **işlem** |
|---|---|---|
| `numcog/results_p7_1/run_ilk.log` | 2 | **DOKUNULMADI** (Faz 7-1 sonuç dosyası; kural: değişmez) |
| `numcog/results_p7_1/run.log` | 2 | **DOKUNULMADI** |
| `numcog/results_p7_1/merge_out.txt` | 1 | **DOKUNULMADI** |
| `CLAUDE.md` | 9 | flyputer WIP → dokunulmadı, karar kullanıcıya |
| `server.py` | 3 | AŞAMA 2'de **o dosya düzenlenirken normalize edilecek** |
| `README.md` | 1 | dokunulmadı (AŞAMA 5'te üzerine **yazılmayacak**, **eklenecek**) |

- **Git yazar e-postası geçmişte açık:** `furkantahsinb@gmail.com` (68 commit) ✗ → tek düzeltme yolu
  geçmişi yeniden yazmaktır (§3(b) sakıncalarıyla) → **karar kullanıcıya**; bu pakette bir şey yapılmadı.

## 5. "Ölü kod" iddiası — DOĞRULANMADI (dikkat)

Tarama (kök `*.py`: `ollama|run_agent|prompt|llm|openai|anthropic`):

| dosya | eşleşme | ilk satır |
|---|---|---|
| `server.py` | **53** | "Every LLM call runs on ONE background worker (game_loop.LLMExecutor)…" |
| `game_loop.py` | 23 | "LLMExecutor — ONE worker thread in front of Ollama…" |
| `agent.py` | 7 | "1. Install Ollama: https://ollama.com/download" (`import ollama`, `ollama.chat`) |
| `flysim.py` | 3 | "…that a local LLM…" |
| `brain_state.py` | 10 | "of any LLM / connectome / web dependency…" |

→ Bu kod **canlı `server.py` ve `game_loop.py` tarafından referans ediliyor**; "ölü/kullanılmayan"
olduğu **bu taramayla gösterilemez** ✗ → **"dead code, unused" diye işaretlenmedi**; `README`'ye
**"[VERIFY: is the Ollama/LLM path still used?]"** notu düşülecek. **Silme yapılmadı** ✓.

## 6. ENGEL: AŞAMA 2'nin "mevcut testler"i REPODA YOK

`_fly_smoke.py` ve `_fly_frontend_test.js` **repo genelinde yoktur** (tüm ağaçta `*smoke*`,
`*frontend*`, `*test*` → **0 sonuç**; `.venv`/`.git` hariç). `numcog/tests/` dizini de yok.

**Sonuç:** "mevcut testler geçmeli; geçmiyorsa DUR" maddesi **olduğu gibi uygulanamaz** (çalıştırılacak
test yok). Önerilen **ikame** (raporda "**ikame**" diye etiketlenecek):
1. `POST /calc` eklenirken mevcut uçlara (`GET /`, `/health`, `/state`, `POST /chat`) **dokunulmaz**;
2. yeni **`_calc_smoke.py`**: (a) `/health` + `/state` yanıt veriyor, (b) `/chat` çalışıyor,
   (c) `/calc` 1..9'da doğru ve `fake=1`'de **bozuk**.
Bu **kanıt** olur; kayıp testin yerine geçtiği **açıkça yazılır** (uydurma test değil, ikame).

## 7. Upstream ve atıf durumu

- **`models/flybody/`** → harici **flybody** (MuJoCo sinek gövdesi); kendi `LICENSE`'ı ağaç içinde ✓
  (içeriği bu pakette **okunmadı**) → `NOTICE.md`'de **"[VERIFY: flybody license terms]"**.
- **FlyWire verisi:** `proofread_connections_783.feather` (v783), `annotations_783.tsv`; indirme
  betiği **`get_data.sh`** ✓ (Zenodo: `https://zenodo.org/records/10676866`, `curl`).
- **Mevcut `CITATION.md`** (kök): veri lisansı **CC BY-NC 4.0 (ticari olmayan)** + Dorkenwald 2024 /
  Schlegel 2024 / Zheng 2018 atıfları → `DATA.md` **bu dosyayı kaynak gösterecek**; upstream lisans
  sayfalarını **kendim doğrulamadım** → ilgili satır **[VERIFY: license terms of the FlyWire/Codex
  release used]** notuyla verilecek ✓.
- **Mevcut `LICENSE`** = **MIT**, "Copyright (c) 2026 **Migen Karriqi**" — **git yazarı
  (`Furkan Tahsin Bekdaş`) ile uyuşmuyor** ✗ → **karar kullanıcıya** (bu pakette **dokunulmadı**).

## 8. `requirements.txt` durumu

Mevcut: `pandas>=2.0`, `pyarrow>=14`, `numpy>=1.24`, `ollama>=0.3`, `matplotlib>=3.7`,
`cloud-volume>=8.0`. **EKSİK: `scipy`** ✗ — `numcog/` (Faz 7-1'den beri) `scipy.sparse`,
`scipy.stats`, `scipy.cluster`, `scipy.sparse.linalg` kullanıyor; kurulu **1.18.1** ✓ (AŞAMA 5'te
sürüm sabitlenerek eklenecek).

Kurulu (kaynak: `pip freeze`; Python **3.12.10**): `numpy==2.5.3`, `pandas==3.0.5`, `scipy==1.18.1`,
`matplotlib==3.11.2`, `pyarrow==25.0.1`, `ollama==0.6.2`, `networkx==3.6.1`, `mujoco==3.13.0`.

## 9. Kullanıcı kararı bekleyen maddeler (bu aşamada hiçbiri uygulanmadı)

1. **WIP anlık görüntüsü commit'i** (AŞAMA 2 öncesi) — onay/ret.
2. Geçmişteki **87,15 MB + 11,12 MB** blob'lar: bırak / geçmişi yeniden yaz (§3).
3. **`LICENSE` telif sahibi** uyuşmazlığı.
4. **Ollama/LLM yolu** gerçekten kullanılıyor mu? (`[VERIFY]`).
5. Eksik testler yerine **ikame** smoke testin kabulü (§6).
6. **`models/flybody`** lisans metni (okunmadı → `[VERIFY]`).

## 10. Bu aşamanın çıktıları

- `numcog/RELEASE_PREFLIGHT.md` (bu dosya)
- `numcog/results_release/git_history.txt` (68 satır ham geçmiş)

