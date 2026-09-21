# PREREG LOG — ön-kayıt ↔ sonuç commit sırası (kronolojik)

Tarih: 2026-09-20. Ham girdi: **`results_release/git_history.txt`** (68 commit,
`git log --format="%h|%ad|%an|%ae|%s" --date=iso`). Bu belge **yeni ölçüm içermez**; yalnızca
**sıra kontrolü** yapar: ön-kayıt, sonuçtan **önce** mi?

## 1. Tablo

| faz | ön-kayıt commit'i | tarih | sonuç commit'i | tarih | ön-kayıt ÖNCE mi? |
|---|---|---|---|---|---|
| 0 | `364285d` | 2026-09-19 13:25 | `3e97777` | 2026-09-19 13:35 | **✓** |
| 1 | `26b1445` | 2026-09-19 13:53 | `18c7ad4` | 2026-09-19 14:04 | **✓** |
| 2 | `b721fe7` | 2026-09-19 14:26 | `10d9b19` | 2026-09-19 14:36 | **✓** |
| **2b** | `c43a06e` | 2026-09-19 14:52 | `5d496e6` | 2026-09-19 14:56 | **✓** (ama 2b **Faz 2 sonrası** yazıldı → **post-hoc, KEŞİFSEL** olarak etiketli ✓) |
| 3 | `81a90f1` | 2026-09-19 15:09 | `0318771` | 2026-09-19 15:20 | **✓** — arada **`7a15a4a`** (15:17) **veri tasarımı düzeltmesi**: ön-kayıt SONRASI tasarım düzeltmesi ✗ → raporda **açıkça** yazılı |
| 3c | `3b05762` | 2026-09-19 16:05 | `e8227a5` | 2026-09-19 16:10 | **✓** |
| 4A | `776e964` | 2026-09-19 19:58 | `3940c03` | 2026-09-19 20:30 | **✓** (sonuç: "hesap makinesi **çalışmıyor**" — dürüst negatif) |
| 4A-2 | `164d72c` | 2026-09-19 20:41 | `eceb466` | 2026-09-19 21:56 | **✓** |
| 4B-0 | `147b852` | 2026-09-19 22:09 | `379332c` | 2026-09-19 22:12 | **✓** |
| 4C | `ea941cd` | 2026-09-19 22:24 | `181ddfc` | 2026-09-19 22:42 | **✓** |
| 4D | `4505664` | 2026-09-19 22:50 | `ca10fe3` | 2026-09-19 23:38 | **✓** |
| 4E | `2435393` | 2026-09-19 23:53 | `c0b68d1`, `73f7f5a` | 2026-09-20 | **✓** |
| 4F | `46128e2` | 2026-09-20 | `2ea285b` | 2026-09-20 | **✓** |
| 5 | `8ba1376` | 2026-09-20 | `6af0820` | 2026-09-20 | **✓** |
| 6-0 | `13647d9` | 2026-09-20 | `97d181c` | 2026-09-20 | **✓** |
| 6-0b | `193f21c` | 2026-09-20 | `dd6d361` | 2026-09-20 | **✓** |
| 7-0 | `5e7956b` | 2026-09-20 13:00 | `adef2e2` (+`70bbb0f`) | 2026-09-20 | **✓** |
| 7-1 | `36e52df` (+`5f816d2`, `80fda08`) | 2026-09-20 13:25-13:45 | `ccdd1c1` (+`c553aba`) | 2026-09-20 17:00 | **✓** |
| 7-2 | `137b034` | 2026-09-20 17:58 | `96b6558` | 2026-09-20 20:01 | **✓** |
| 7-3 | `29bf396` (+`3e243a9` düzeltme, ölçüm öncesi) | 2026-09-20 20:28-20:32 | `379223f` | 2026-09-20 23:12 | **✓** |
| 8 | `3d7d638` (+`a69a8d9` kayıt) | 2026-09-20 23:34 | `2b9b21b` | 2026-09-20 23:56 | **✓** |
| Kapanış AŞAMA 3 | `d6bd546` | 2026-09-20 | `b6515ef` | 2026-09-20 | **✓** |

## 2. İstisnalar (açıkça)

1. **Faz 3 — `7a15a4a` (15:17):** ön-kayıt (`81a90f1`, 15:09) ile sonuç (`0318771`, 15:20)
   **arasında** bir **veri tasarımı düzeltmesi** commit'lendi ("op korelasyon kusuru").
   → **Ön-kayıt sonrası tasarım değişikliğidir**; raporda **belirtilmiştir**; **gizlenmemiştir** ✗✓.
2. **Faz 2b:** ön-kayıtı **Faz 2 sonucundan sonra** yazıldı → **post-hoc / KEŞİFSEL** etiketli ✓
   (başlıkta açıkça "Faz 2 sonrası ön-kayıt" yazıyor ✓).
3. **Faz 7-2 ve Faz 7-3:** bunlar **önceki fazın sonuçları görüldükten sonra** yazılan
   **KEŞİFSEL-YENİDEN-TEST**'lerdir → ön-kayıtları kendi ölçümlerinden **önce**dir ✓ ama
   **HARKing riski** taşırlar ve raporlarında **böyle etiketlenmiştir** ✓.
4. **Faz 8:** Aşama 0 **keşiftir (simülasyon yok)** ve kapı ölçütleri ön-kayıtta **ölçülmüş olarak**
   verilmiştir; Aşama 1/2 simülasyonları ön-kayıttan **sonra** çalıştırılmıştır ✓.
5. **Kapanış paketi (AŞAMA 2/3):** WIP anlık görüntüsü (`1bf5dfb`) **kullanıcı işidir ve içerik
   değiştirilmemiştir** ✓; köprü (`fc2c12c`) ve iki haneli ön-kayıt (`d6bd546`) sırası **doğrudur** ✓.

## 3. Sonuç

- **Bütün fazlarda ön-kayıt, kendi ölçümünden ÖNCE commit edilmiştir** ✓ — **tek istisna** Faz 3'ün
  arada yapılan **veri tasarımı düzeltmesidir** (`7a15a4a`) ve Faz 2b'nin **post-hoc** niteliğidir
  (ikisi de raporlarda yazılı) ✓.
- **GEÇMİŞ YENİDEN YAZILMADI** → bu tablodaki tüm hash'ler **orijinaldir** ✓
  (bkz. `RELEASE_PREFLIGHT.md` §3: 87,15 MB + 11,12 MB blob'lar geçmişte duruyor; silmek
  **hash'leri ve bu tarihleri bozardı** ✗ → karar kullanıcıya).
