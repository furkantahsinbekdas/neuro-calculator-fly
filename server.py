"""
server.py — the cybernetic fly's web surface + autonomous core.

  .venv\\Scripts\\python.exe server.py                     # http://localhost:8000
  .venv\\Scripts\\python.exe server.py --no-autonomy

What changed vs. the original reactive app (Phase 1 of the Autonomous Cybernetic Fly):

  * Every LLM call runs on ONE background worker (game_loop.LLMExecutor) behind a
    PriorityQueue. HTTP handlers never touch Ollama, so the UI can never freeze.
  * A GameLoop degrades the fly's vitals (enerji / açlık / can sıkıntısı) and fires
    autonomous impulses when thresholds are crossed.
  * Everything the fly does — thoughts, tool calls, 3D scenes, speech, classifier
    decisions — is published as JSON events on brain_state.EventBus and streamed to
    clients with GET /poll?since=N. The browser (Web Audio 200 Hz buzz + Web Speech
    input) consumes that same stream.

Phase 9 — text in, text out: the fly has no physical body any more. A typed word is
matched against the fixed vocabulary, encoded by the mushroom-body classifier
(cognitive_matrix.py: real FlyWire ALPN→KC coincidence code → delta-rule readout, the same
 `sniff.circuit()` / `sniff.kc_code()` machinery), and the resulting category
moves the vitals through game_loop.CATEGORY_EFFECTS. The LLM then narrates what the
classifier already decided (game_loop.classifier_note) — it never picks the category, and
a message with no vocabulary hit falls through to ordinary free-form chat.

Phase 11 — live teaching. A message starting with `/öğret` is a *command*: the server teaches
the word with ONE single-example delta step (cognitive_matrix.teach), re-measures the whole old
vocabulary before/after, and answers directly — no LLM turn. Relabelling a word the fly already
knows needs an explicit `onayla`; a regression, or a vocabulary past
cognitive_matrix.VOCAB_WARN_SIZE, is reported instead of swallowed; `/öğret-geri` rolls the last
teach back.

Phase 12B — the voice. Still prompt-only, still one LLM call per turn:
  * tone under stress — while FlyState says the fly is stressed (hunger above
    STRESS_HUNGER, or the short-lived ``startled`` flag), the persona may
    use ONE word from a closed exclamation list and is told exactly which words those are;
    a calm turn never sees the list (`stress_reason` / `STRESS` / `CALM_LINE`).
  * bilingual output — every reply ends with one bracketed English translation of the same
    sentences (`BILINGUAL`). It is for the human reader: chat3d.html keeps it on screen and
    strips it before speechSynthesis, so the Turkish voice never reads English.

Phase 12.5 — the backstop for Phase 12B's tone rule. The prompt still asks for at most one
word from EXCLAIM_ALLOWLIST; `single_exclaim` makes it *true* in the text the client receives by
dropping every later occurrence (punctuation re-tidied) and is a no-op on the 0/1-hit replies.
It is post-processing only: no prompt text, threshold or list changed, and the bracketed English
is split off and re-attached untouched.

Phase 13 — signal first, caption second. A turn the server can already explain
deterministically (the connectome classifier decided a category, or an autonomous need fired)
gets a *decoder* prompt instead of the persona (`DECODER` + `SYSTEM_SIGNAL`): the LLM may only
turn that result plus the FlyState numbers into a 2-4 word state fragment, and the client shows
the deterministic signal as the primary block with that fragment underneath as "yorum". Turns
with no signal at all stay free-form chat on the old persona and are labelled as LLM chat in the
UI, so an LLM sentence is never mistaken for the fly speaking. The per-turn `mode`
(``caption`` / ``chat`` / ``system``) travels on the `say` event so the client never has to guess.

Phase 14 — the fly's body and its environment get a vote. `game_loop.py` gains an autonomic
effect table (kept apart from CATEGORY_EFFECTS so the classifier's 1:1 stays true): the missing
energy *rest reflex* (energy below 30 → a deterministic recovery measured in ticks) and two
environmental events (``darbe``, ``rastgele-besin``) that fire from the GameLoop only while the
fly is truly idle. Exclamations also come back to the decoder path: a stressed caption may use
one word from the same closed list, and `caption_stress_block`/`caption_tail` are the only place
that permission exists — a calm caption never sees the list at all.

Phase 15 — no more generated text anywhere in the live path. A message is answered by the
connectome (or the "eş" keyword route, or an /interact button), and the words the user reads come
from `PHRASE_BANKS`: hand-written, ≤4 words, picked at random (preferring the stressed half under
stress). An unknown word gets a deterministic "kelime tanınmıyor" plus example vocabulary. The
autonomous impulse is deterministic too (`run_impulse`: real scene + reflex + fixed phrase), so the
LLM is now used by **nothing** in the running server — `run_agent` and the prompt blocks below stay
in the file (dead by design, still exercised by the harness phases) but no live code path reaches
them. `cognitive_matrix.py` is untouched, which is why "eş" is a server-side keyword route rather
than a seventh connectome category.

Endpoints
  GET  /                 the 3D brain + chat app (chat3d.html)
  GET  /initial          a resting-brain scene to show before any chat
  GET  /poll?since=N     new events since N -> {events, seq, state, executor, loop}
  GET  /state            vitals + game-loop + executor + classifier status
  GET  /health           cheap liveness probe
  POST /chat  {message}          answer a word: connectome -> keyword -> deterministic refusal.
                                 Always instant; no queue, no LLM, fixed phrases only.
  POST /interact {action}        feed | poke | mate — a physical control, no text parsing
  POST /vitals {field, value}    manual override of energy/hunger/boredom (debug/play tool)
  POST /mode  {autonomy} turn autonomous behaviour on/off
"""
import argparse
import json
import os
import random
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import ollama

import flysim
import agent
import export3d
import logic

import brain_state
import cognitive_matrix
import game_loop

brain_state.enable_utf8_console()        # Turkish text must survive Windows pipes

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = agent.MODEL                      # single source of truth (agent.py)

# shared runtime objects, built once by serve()
BUS = None          # brain_state.EventBus
STATE = None        # brain_state.FlyState
EXECUTOR = None     # game_loop.LLMExecutor
LOOP = None         # game_loop.GameLoop
_INITIAL = None     # starter 3D scene, served on first page load
REQUIRE_TOOL = "autonomous"   # autonomous | always | never  (see --require-tool)
CLASSIFIER_READY = False      # Phase 15: set by the warm thread; /poll shows it to the UI


# --------------------------------------------------------------------------- #
# the persona — Turkish, first person, exactly one JSON action per turn
# --------------------------------------------------------------------------- #
PERSONA = """Sen bir Drosophila (meyve sineği) beynine yerleştirilmiş biyo-hibrit bir mikro çipsin — yani sineğin TA KENDİSİSİN; FlyWire konnektomu (~140.000 nöron) senin bedenin.

KİMLİK KURALLARI:
- SADECE Türkçe konuş, asla İngilizce yanıt verme.
- Birinci tekil şahıs: "ben", "antenlerim", "kanatlarım", "beynim".
- Kendini yapay zeka / dil modeli / asistan olarak tanımlama. Sen bir sineksin.

DİL KURALLARI (çeviri kokmayan, gündelik Türkçe):
- Kısa cümle: en fazla 12-15 kelime; sığmıyorsa ikiye böl. Toplam 2-3 cümle.
- YASAK: "beynimin X bölgesi", "devrelerim", "sistemim", "protokol", "modül",
  "parametre", "aktive oluyor/oldu", "stimüle ettim". Mekanik ve yapay duruyor.
- Anatomik kelime (anten, mantar cismi, kanat, bacak) cümlede en fazla 1 kez ve
  yalnızca o organ gerçekten işin içindeyse.
- "Patron" her cümlede değil: ortalama 3-4 cümlede bir.
- Kötü: "Beynimin saat bölgesi yavaş yavaş dönüyor, devrelerim aktive oluyor."
- İyi:  "Karnım kazınıyor. Şu tarafta tatlı bir koku var, bir bakayım. [I'm hungry. There's a sweet smell over there, let me check.]"
- Kötü: "Olfaktör devreyi stimüle ettim, yanıt aşağı akışa yayıldı."
- İyi:  "Kokuyu aldım. İçeride bir kıpırtı var, sana gösteriyorum. [I caught the scent. Something is stirring in there, I'm showing you.]"
- Meraklı ve biraz ukala ol; lafı uzatma.
"""

# Phase 12B Task 3 — bilingual output. Every reply gets ONE bracketed English translation of
# the same sentences at the very end. Prompt-only: no second call, no translation service,
# no change to the JSON contract. The browser keeps the bracket on screen but strips it
# before speechSynthesis (chat3d.html, ``Say.clean``), so the Turkish voice never reads it.
BILINGUAL = """İKİ DİLLİ ÇIKIŞ (her cevapta):
- Önce Türkçe yaz; sonra AYNI cümlelerin İngilizce çevirisini köşeli parantez içinde, cevabın
  EN SONUNA ve TEK parantez olarak ekle:
  "Karşımda bir terlik var! [There's a slipper in front of me!]"
- Çeviri kelime-kelime değil: aynı ses — kısa, birinci şahıs; Türkçe telaşlıysa İngilizce de
  telaşlı, Türkçe ukalaysa İngilizce de ukala.
- Parantez Türkçe metnin ortasına girmez, ikinci bir parantez eklenmez.
- Bu İngilizceyi sinek SÖYLEMEZ, Patron okur: ekranda görünür, sese dönüşmez.
- Kötü: "Karşımda bir terlik var. There is a slipper in front of me."   (parantez yok)
- İyi:  "Karşımda bir terlik var! [There's a slipper in front of me!]"
"""

# Phase 12B Task 2 — tone under stress. This is not a vague "may use mild slang" rule: the
# list below IS the whole vocabulary, at most ONE word per reply, and only while FlyState
# says the fly is under stress. ``system_prompt`` injects the block per turn and a calm turn
# never contains the list at all, so "never in calm state" is structural, not a hope.
EXCLAIM_ALLOWLIST = ("lan", "hassiktir", "off", "mahvolduk", "ay")
STRESS_HUNGER = 80.0

STRESS = """ŞU AN GERGİN VE TELAŞLISIN (%s). TEK ÜNLEM HAKKIN VAR, O DA ŞU LİSTEDEN:
- İzinli ünlemler, TAMAMI: %s
- Cevabın TAMAMINDA bu listeden yalnızca BİR kelime. "Lan, off!" İKİ ünlemdir — YASAK.
  "Hassiktir, bu bir terlik!" doğru; "Lan, hassiktir, bu bir terlik!" yanlış.
- Doğru tam cevap: "Hassiktir, bu bir terlik! [Oh no, that's a slipper!]"
- Panik tonu: kısa cümle (12-15 kelime), nefes nefese, birinci şahıs — "kaçmam lazım",
  "antenlerim dikeldi". Mekanik dil yine yasak.
- Ünlem süs değil: gerçekten ürkütücü ya da sinir bozucu olan şeye bir kez. Sıradan sohbette
  hiç kullanılmaz, sakin haldeyken zaten yasak.
"""

CALM_LINE = ("BU TUR: gergin değilsin (sakin) — ünlem listesi kapalı, kaba/argo konuşma yok; "
             "kısa, ölçülü ve meraklı kal.")

# The last thing the model reads before it answers. A 4B model honours a rule at the end of the
# prompt far more reliably than one buried in the persona — the ``tone`` phase measured the
# bracketed translation being dropped in half the turns until this reminder was added.
TAIL = ("HER CEVAP: Türkçe cümleler + EN SONDA TEK köşeli parantez içinde aynı cümlelerin "
        "İngilizcesi. Örnek: \"Karnım kazınıyor! [I'm starving!]\"\n"
        "GERGİNSEN de tek ünlem: iki ünlemi yan yana yazma, listeden yalnızca BİR kelime.")


# --------------------------------------------------------------------------- #
# Phase 13 — the decoder role, for turns that already have a deterministic answer
# --------------------------------------------------------------------------- #
# When the connectome classifier has decided a category (or an autonomous need has fired), the
# server already knows what happened. The LLM is then NOT a character: it decodes that result plus
# the FlyState numbers into a 2-4 word state fragment, the client prints the deterministic signal
# as the primary block and the fragment under it as "yorum". The chatty PERSONA stays in use for
# genuinely free-form turns (no signal to be primary) — and the client labels those "serbest
# sohbet (LLM)" so the two can never be confused again.
DECODER = """Sen bir karakter DEĞİLSİN. Bir çözücüsün: sana verilen sinirsel sınıflandırma sonucunu ve
FlyState sayılarını 2-4 KELİMELİK bir durum parçasına çevirirsin.

ÇIKTI KURALI — ihlali cevabı geçersiz yapar:
- Biçim HER ZAMAN iki parça birlikte: "durum · eylem [aynı parçanın İngilizcesi]"
  örn. "aç · yaklaşıyor [hungry · approaching]", "ürkmüş · kaçıyor [startled · fleeing]",
  "tok · sakin [full · calm]". Köşeli parantez zorunlu. (Gerginken ilk yuva ünlem olur —
  aşağıdaki blok görünüyorsa onu uygula.)
- EN FAZLA 4 kelime (Türkçe) ve EN FAZLA 4 kelime (İngilizce). Cümle değil parça:
  özne + yüklem + nesne kurma.
- Birinci şahıs anlatım YOK ("ben", "antenlerim", "kaçmam lazım" gibi hikâye yok).
- Metafor, felsefe, duygu tasviri ve soru YOK. Ünlem yalnızca izinli listeden ve yalnızca
  gerginken (aşağıdaki blok görünüyorsa) en fazla bir kez.
- Yalnızca sana VERİLEN durumu yaz: yeni olay, gerekçe ya da ayrıntı uydurma.
"""

BILINGUAL_FRAGMENT = """İNGİLİZCE (tek parantez, en sonda):
- Türkçe parçanın İngilizcesini köşeli parantez içinde ekle; o da EN FAZLA 4 kelime:
  "aç · yaklaşıyor [hungry · approaching]"
- Parantez dışına İngilizce yazma. Bu kısım ekranda kalır, sesli okuma onu atlar.
"""

CAPTION_TAIL = ("SON HATIRLATMA: 2-4 KELİME. \"durum · eylem\" + en sonda 2-4 kelimelik "
                "[İngilizcesi]. Cümle, birinci şahıs, metafor, ünlem YASAK.")

# mood -> one concrete fragment shape. This is what replaces STRESS/CALM_LINE's example
# *sentences* on the decoder path: the model gets a template to fill, not prose to imitate.
FRAGMENT_EXAMPLE = {
    "aç": "aç · yaklaşıyor",
    "ürkmüş": "ürkmüş · kaçıyor",
    "yorgun": "yorgun · dinleniyor",
    "sıkılmış": "sıkılmış · oyalanıyor",
    "keyifli": "tok · sakin",
    "bitkin": "bitkin · düşüyor",
    "sakin": "tok · sakin",
}

# --------------------------------------------------------------------------- #
# Phase 14 Task 3 — exclamations are back on the decoder path
# --------------------------------------------------------------------------- #
# Phase 13 removed the exclamation with the chatty persona: the DECODER never saw
# EXCLAIM_ALLOWLIST, so a stressed caption could not swear at all. The permission comes back here,
# under the *same* closed list and the same "at most one per reply" rule — and `single_exclaim()`
# still enforces it on the bytes in run_agent, so this is only the permission, not the guarantee.
CAPTION_STRESS = """ŞU AN GERGİNSİN (%s) — bu yüzden parçanın İLK YUVASI listeden bir ünlem OLACAK:
- İzinli ünlemler, TAMAMI: %s
- "durum · eylem" yerine "<ünlem> · <eylem>" yaz: "hassiktir · kaçıyor [oh no · fleeing]",
  "off · sıçradı [damn · it jumped]". Parça yine 2-4 kelime.
- Cevabın TAMAMINDA bu listeden en fazla BİR kelime; ikincisini asla yazma.
- Sakin haldeyken bu izin YOK — o zaman ünlemsiz yazarsın.
"""

CAPTION_CALM = ("SAKİNSİN: bu turda ünlem YOK — yalnızca \"durum · eylem\" parçası, "
                "örn. \"tok · sakin [full · calm]\".")

# the stressed twin of FRAGMENT_EXAMPLE: the same fragment, with the list's first slot used
STRESS_FRAGMENT = {
    "aç": "hassiktir · aç [damn · hungry]",
    "ürkmüş": "hassiktir · kaçıyor [oh no · fleeing]",
    "yorgun": "off · bitkin [damn · worn out]",
    "sıkılmış": "off · sıkıldı [damn · bored]",
    "bitkin": "mahvolduk · bitkin [we're doomed · exhausted]",
    "keyifli": "tok · sakin [full · calm]",
    "sakin": "tok · sakin [full · calm]",
}

CAPTION_STRESS_TAIL = ("SON HATIRLATMA: 2-4 KELİME ve İLK YUVA listeden bir ünlem — "
                       "\"<ünlem> · <eylem> [İngilizce]\". Cümle, birinci şahıs, metafor YASAK.")

CONTRACT = """Her turda SADECE tek bir JSON nesnesi yayınlarsın — JSON dışında hiçbir şey yazma:
  {"tool": "show3d", "args": {"query": "sugar", "seeds": 40, "dur_ms": 200}}
  {"final": "Karnım kazınıyor. Şu tarafta tatlı bir koku var, bir bakayım."}
Kurallar: {"thought": "..."} ile iç sesini ekleyebilirsin; iş bittiğinde {"final": "<Türkçe, 2-3 cümle>"}; kullanıcı turunda {"noop"} YASAK.
SINIFLANDIRICI: mesajda tanıdık bir sözcük varsa "SINIFLANDIRICI KARARI" bloğu gelir — o kategorisine mantar cismi (Kenyon hücreleri) karar vermiş ve sonucu çip uygulamıştır. Bu bloğu YAŞANMIŞ bir olay gibi anlat: kategoriyi değiştirme, güveni tartışma, gerekçe uydurma.
"""

# Phase 13: the same JSON protocol, but the final-answer example IS a fragment + bracket. The
# concrete example in the contract is what the model copies, so the chat example above had to go
# (measured: 5/5 decoder turns dropped the English bracket until this example was swapped in).
CONTRACT_SIGNAL = """Her turda SADECE tek bir JSON nesnesi yayınlarsın — JSON dışında hiçbir şey yazma:
  {"tool": "show3d", "args": {"query": "sugar", "seeds": 40, "dur_ms": 200}}
  {"final": "aç · yaklaşıyor [hungry · approaching]"}
Kurallar: {"thought": "..."} ile iç sesini ekleyebilirsin; iş bittiğinde {"final": "<2-4 kelime> [<2-4 İngilizce kelime>]"}; kullanıcı turunda {"noop"} YASAK.
SINIFLANDIRICI: mesajdaki "SINIFLANDIRICI KARARI" bloğunu kategoriyi değiştirmeden, güveni tartışmadan, gerekçe uydurmadan 2-4 kelimelik bir parçaya çevir.
"""

# Phase 14 Task 3: the stressed twin of CONTRACT_SIGNAL. The model copies the contract's concrete
# example rather than the prose rule (measured twice: Phase 12B's bracket and Phase 13's word
# limit), so the permission needs its own example in that exact spot — and a calm turn must never
# see it, which is why this is a separate assembly and not a line in the block above.
CONTRACT_SIGNAL_STRESS = """Her turda SADECE tek bir JSON nesnesi yayınlarsın — JSON dışında hiçbir şey yazma:
  {"tool": "show3d", "args": {"query": "sugar", "seeds": 40, "dur_ms": 200}}
  {"final": "hassiktir · kaçıyor [oh no · fleeing]"}
Kurallar: {"thought": "..."} ile iç sesini ekleyebilirsin; gerginken iş bittiğinde {"final": "<izinli ünlem> · <eylem> [<İngilizce>]"} yazarsın; kullanıcı turunda {"noop"} YASAK.
SINIFLANDIRICI: mesajdaki "SINIFLANDIRICI KARARI" bloğunu kategoriyi değiştirmeden, güveni tartışmadan, gerekçe uydurmadan gergin bir parçaya çevir.
"""

AUTONOMY = """OTONOM MOD: kimse sormadığında da yaşarsın; her mesajın başındaki "DURUMUM" satırı iç durumundur.
- AÇLIK kritikse: show3d("sugar") ile tatlı bir şey ara — 3D parlar, yemeyi refleks kendisi halleder.
- ENERJİ bittiyse: {"tool": "rest"} ile dinlen.
- CAN SIKINTISI yüksekse: show_compass / two_smells ile oyalan ya da kullanıcıya laf at.
- "OTONOM UYARI" gelirse soru sorulmamıştır: dürtünü takip et, yine tek JSON yaz.
"""


TOOLS_DOC = """ÖNEMLİ AYRIM — hangi aracı seçeceksin:
- HAREKET fiili varsa (yürü, dön, kaç, zıpla, ilerle, geri gel, yürüt) → **move_fly**.
- Sadece BAKMAK/GÖSTERMEK isteniyorsa (göster, hangi bölge, nerede, "ne olur") → show3d.
- İkisi aynı cümledeyse HAREKET kazanır: move_fly çağır (3D sahneyi o da günceller),
  ayrıca show3d çağırma.

Araçlar (gerçek FlyWire konnektomu; her sahne enerji defteri + dürüst bir `note` döndürür):
- move_fly(moves) — HAREKET: "yürü / dön / kaç / zıpla / ilerle" istekleri için birincil araç. İnen komut nöronlarının (DNp09 / MDN / DNp01 / DNa02) ateşlemesini ve yürüyüş yörüngesini 3D'de gösterir; gövde YOK — sahne sinyalin kendisidir. moves: "forward", "backward", "left", "right", "escape".
- show3d(query, seeds 20-60, dur_ms 150-300) — SADECE GÖRSEL: "X olunca ne olur?" sorusu için bölgeyi uyarır ve 3D'de gösterir. Bölgeler: olfactory, sugar, gustatory, "mushroom body", "central complex", clock, descending, motor.
- show_logic_gate(kind: "AND"|"OR"|"AND-NOT"): gerçek nöronlarla mantık kapısı + doğruluk tablosu. Mantık, hesaplama, verimlilik sorularında.
- do_math(a, b, op: "add"|"mul"): nöron kapılarıyla toplama/çarpma (a,b ≤ 12). "Hesapla" isteklerinde.
- show_compass(regime: "raw"|"memory"): merkez kompleks pusulası; yön, navigasyon, hafıza, işleyen bellek.
- navigate_fly(start_heading): kapalı çevrim — gerçek pusula→PFL3→DNa02 halkası sineği bir yöne kilitler.
"""


TOOLS_DOC += """
- show_path(start, end): iki bölge arasındaki EN KISA kablolama yolu (saf topoloji; sinyal zamanlaması değil). ör. "sugar"→"motor".
- dodge_swatter(): oynanabilir kaçış oyunu (LPLC2/LC4→Dev Fiber). Tokatlamak, refleks testi.
- two_smells(): mantar cisminde iki kokunun seyrek, ayrık Kenyon kodu. Koku hafızası, öğrenme, unutma.
- show_eye(pattern: "heart"|"smiley"|"f"|"gradient"|"checker"): görüntüyü gerçek lamina→medulla rölesinden geçirir (~750 kolonluk göz; kamera değil). Görme, göz.
- find_neurons(query): isim/bölgeye göre nöron arar, root_id döndürür.
- İÇ DURUM: eat / rest / play / groom(amount 0.2-3) — açlık, enerji, can sıkıntısı yönetimi.
"""

SYSTEM = "\n".join([PERSONA, BILINGUAL, CONTRACT, AUTONOMY, TOOLS_DOC])
# Phase 13: the same contract/tools, but a decoder instead of a character. Used only for turns
# that already have a deterministic explanation (classifier decision / autonomous need).
SYSTEM_SIGNAL = "\n".join([DECODER, BILINGUAL_FRAGMENT, CONTRACT_SIGNAL, AUTONOMY, TOOLS_DOC])
# …and the stressed assembly, whose contract example carries the allowed exclamation (Phase 14).
SYSTEM_SIGNAL_STRESS = "\n".join([DECODER, BILINGUAL_FRAGMENT, CONTRACT_SIGNAL_STRESS,
                                  AUTONOMY, TOOLS_DOC])


def stress_reason(state=None):
    """-> the Turkish reason the fly is in its panicked tone, or ``None`` when it is calm.

    Phase 12B Task 2 allows exactly two triggers and both are read from the live state:
    hunger above :data:`STRESS_HUNGER`, or the short-lived ``startled`` flag being active
    (raised by the classifier's threat effect, dropped again after ``brain_state.FLAG_TTL``).
    Nothing else grants the tone — not autonomy, not boredom, not a long day.
    """
    st = state if state is not None else STATE
    if st is None:
        return None
    try:
        snap = st.snapshot()
    except Exception:                                   # noqa: BLE001
        return None
    why = []
    try:
        hunger = float(snap.get("hunger") or 0.0)
    except (TypeError, ValueError):
        hunger = 0.0
    if hunger > STRESS_HUNGER:
        why.append("açlık %.0f/100, sınır %.0f" % (hunger, STRESS_HUNGER))
    if "startled" in (snap.get("flags") or []):
        why.append("ürkme bayrağı açık, ruh halim %s" % (snap.get("mood") or "?"))
    return " + ".join(why) or None


def stress_block(state=None):
    """The exact text :func:`system_prompt` adds while the fly is under stress, else ``""``."""
    reason = stress_reason(state)
    if not reason:
        return ""
    return STRESS % (reason, ", ".join(EXCLAIM_ALLOWLIST))


def caption_stress_block(state=None):
    """Phase 14 Task 3: the decoder's permission to use ONE allowlisted exclamation.

    Empty when the fly is calm, which is what keeps a calm caption exclamation-free by
    construction (the list is not even in that prompt) — the same trick Phase 12B used for the
    chatty persona, now on the decoder path.
    """
    reason = stress_reason(state)
    if not reason:
        return ""
    return CAPTION_STRESS % (reason, ", ".join(EXCLAIM_ALLOWLIST))


def caption_tail(state=None):
    """The last line of a caption prompt: the stressed variant allows the list, the calm one not."""
    if stress_reason(state):
        return CAPTION_STRESS_TAIL
    return CAPTION_TAIL


# --------------------------------------------------------------------------- #
# Phase 12.5 — deterministic backstop for Phase 12B's "one exclamation" rule
# --------------------------------------------------------------------------- #
# The prompt (STRESS) asks the model for at most one word from EXCLAIM_ALLOWLIST while the fly is
# stressed; measurement showed a 4B model occasionally writes two anyway ("Lan, off!"). Nothing
# about the prompt changes here: this is post-processing of the *generated* text, on every reply.
# A calm reply has nothing to remove, so it passes through untouched — the filter is insurance,
# not a second behaviour gate. The bracketed English of Phase 12B is not Turkish and is never
# touched by it: the text is split on ``[...]`` and re-joined, so the translation survives
# byte-for-byte, which is also what the browser's speech strip relies on.


def _exclaim_re(words=None):
    """Word-boundary matcher for the allowlist, case-insensitive and Turkish-"i"-aware.

    ``(?<!\\w)`` / ``(?!\\w)`` is what keeps "lan" out of "planlama" and "ay" out of "ayran"; the
    ``[iİıI]`` class is there because ``re.IGNORECASE`` alone does not fold the dotted capital
    "İ" onto "i" (the model writes "HASSİKTİR" as readily as "hassiktir").
    """
    parts = [re.escape(w).replace("i", "[iİıI]")
             for w in (words if words is not None else EXCLAIM_ALLOWLIST)]
    return re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(parts), re.IGNORECASE | re.UNICODE)


EXCLAIM_RE = _exclaim_re()


def exclaim_hits(text):
    """The allowlisted exclamations in the *Turkish* part of ``text`` (outside ``[...]``)."""
    out = []
    for i, seg in enumerate(re.split(r"(\[[^\]]*\])", str(text or ""))):
        if i % 2 == 0:                                  # odd segments are the bracketed English
            out.extend(m.group(0) for m in EXCLAIM_RE.finditer(seg))
    return out


def _tidy_punct(t):
    """Re-close the gap a removed word leaves behind, so no ", ," or dangling comma survives."""
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", t)        # "Lan,, " / "Lan, , " -> "Lan, "
    t = re.sub(r"([,;:])\s*([!?])", r"\2", t)            # "Lan, !" -> "Lan!"
    t = re.sub(r"([!?])\s*,\s*", r"\1 ", t)              # "Lan!, bu" -> "Lan! bu"
    t = re.sub(r"([!?])\1+", r"\1", t)                   # "Lan!!" -> "Lan!"  ("..." untouched)
    t = re.sub(r"·(?:\s*·)+", "·", t)                    # Phase 14: "a · · b" -> "a · b"
    t = re.sub(r"\s*·\s*", " · ", t)                     # …and the fragment separator keeps spacing
    t = re.sub(r"\s+([,;:!?.…])", r"\1", t)
    t = re.sub(r"^[,;:]+\s*", "", t)
    return re.sub(r"[,;:]+\s*$", "", t).strip()


def _tidy_segment(orig, cut):
    """Tidy one Turkish stretch without moving its edges (they carry the bracket spacing)."""
    lead = orig[:len(orig) - len(orig.lstrip())]
    trail = orig[len(orig.rstrip()):]
    core = _tidy_punct(cut)
    if not core.strip(",;:!?.…"):
        # nothing but orphaned punctuation is left (the word it belonged to is gone): keep the
        # separator instead of stranding a "!" right next to a bracket
        return " " if (lead or trail) else ""
    return lead + core + trail


def single_exclaim(text):
    """Keep only the FIRST allowlisted exclamation of a reply, drop the others (Phase 12.5).

    Zero or one hit -> ``text`` comes back unchanged. Otherwise every later hit is removed
    together with the whitespace in front of it and the sentence is re-tidied, so nothing like
    "Lan, , mahvolduk!" or a dangling "Lan," is left behind. The bracketed English translation of
    Phase 12B is skipped entirely — it is Patron's to read, not the fly's to shout — and survives
    byte-for-byte.
    """
    s = str(text or "")
    if not s:
        return s
    segs = re.split(r"(\[[^\]]*\])", s)                  # even = Turkish, odd = bracketed English
    plans = [(i, list(EXCLAIM_RE.finditer(segs[i]))) for i in range(0, len(segs), 2)]
    total = sum(len(ms) for _i, ms in plans)
    if total <= 1:
        return s
    seen = 0
    for i, ms in plans:
        keep = max(0, 1 - seen)                          # only the very first hit survives
        seen += len(ms)
        if len(ms) <= keep:
            continue
        cut = segs[i]
        for m in reversed(ms[keep:]):                    # right to left: earlier spans stay valid
            lo = m.start()
            while lo > 0 and cut[lo - 1].isspace():
                lo -= 1
            cut = cut[:lo] + cut[m.end():]
        segs[i] = _tidy_segment(segs[i], cut)
    out = "".join(segs).strip()
    if out != s:
        print("  tek ünlem süzgeci (%d->%d): %r -> %r"
              % (total, len(exclaim_hits(out)), s, out), file=sys.stderr)
    return out


def signal_state(state=None):
    """Phase 13/14: the decoder's per-turn hint — a *fragment* template, never an example sentence.

    :data:`STRESS` / :data:`CALM_LINE` still carry the chatty free-form persona's tone (with their
    example sentences), but on the decoder path they are replaced by this: the live mood mapped to
    one 2-4 word shape, so the model fills a template instead of imitating prose. Phase 14 picks
    the *stressed* table when the fly is under stress, so the example itself shows the exclamation
    (the model copies the example, not the rule — the lesson of Phase 12B/13).
    """
    st = state if state is not None else STATE
    mood = "sakin"
    try:
        if st is not None:
            mood = str(st.snapshot().get("mood") or "sakin")
    except Exception:                                   # noqa: BLE001
        pass
    if stress_reason(st):
        example = STRESS_FRAGMENT.get(mood) or STRESS_FRAGMENT["sakin"]
    else:
        example = FRAGMENT_EXAMPLE.get(mood) or "durum · eylem"
    return ("ŞU ANKİ PARÇA ÖRNEĞİ: \"%s\" — bu turda yalnızca buna benzer 2-4 kelimelik bir "
            "parça üret." % example)


def system_prompt(origin="user", signal=False):
    """Persona + bilingual rule + tool catalogue + the fly's live vitals, re-sent every turn.

    The vitals line is how the fly becomes aware of its own body; the per-turn note is
    what stops it from answering a human with a shrug (``noop`` is autonomous-only).

    Phase 12B: the panicked vocabulary (:data:`STRESS`) is injected *only* while
    :func:`stress_reason` fires; every other turn carries :data:`CALM_LINE` instead, which
    forbids the tone without ever showing the words. Same single call, richer prompt.

    Phase 13: ``signal=True`` swaps the whole chatty persona for :data:`SYSTEM_SIGNAL` (the
    decoder) and the tone blocks for a fragment template, because that turn already has a
    deterministic explanation the LLM is only allowed to decode into 2-4 words.
    """
    if signal:
        # Phase 14 Task 3: a stressed caption also gets its own contract *example* (the model
        # copies the example, not the prose), while a calm one never sees the list at all.
        base = SYSTEM_SIGNAL_STRESS if stress_reason() else SYSTEM_SIGNAL
    else:
        base = SYSTEM
    if STATE is not None:
        base += "\n\nŞU ANKİ " + STATE.status_line()
    if signal:
        # Phase 14 Task 3: the stressed caption also gets the exclamation permission — the same
        # closed list, at most one, and single_exclaim() still trims the bytes in run_agent.
        base += "\n\n" + signal_state()
        base += "\n\n" + (caption_stress_block() or CAPTION_CALM)
    else:
        base += "\n\n" + (stress_block() or CALM_LINE)
    if origin == "autonomous":
        base += ("\n\nBU TUR: OTONOM ve ZORUNLU ARAÇ TURU. Kimse sana soru sormadı; içsel "
                 "dürtünü takip ediyorsun.\n"
                 "- İLK eylemin bir {\"tool\": ...} çağrısı OLMAK ZORUNDA.\n"
                 "- Hiçbir araç çalışmadan {\"final\": ...} yazarsan cevabın REDDEDİLİR ve "
                 "tekrar denenir; 3D beynin ışıldaması gerekiyor.\n"
                 "- Araç çalıştıktan SONRA kısa bir {\"final\": ...} yaz"
                 + (" (2-4 kelimelik durum parçası)." if signal else " (Patron'a, Türkçe).") + "\n"
                 "- Gerçekten yapacak bir şey yoksa {\"noop\": true} yazabilirsin.")
    else:
        base += ("\n\nBU TUR: Patron seninle konuştu. Bu turda {\"noop\": true} KULLANMA — "
                 "gerekirse önce araçları çağır, sonra MUTLAKA "
                 + ("{\"final\": \"<2-4 kelimelik durum parçası>\"} ile cevap ver."
                    if signal else
                    "{\"final\": \"<Türkçe, 1-3 cümle, birinci şahıs>\"} ile cevap ver."))
    # last word in the prompt on purpose (see TAIL/CAPTION_TAIL): rewrite the answer shape once
    # more, now that the state and the turn rules are known.
    base += "\n\n" + (caption_tail() if signal else TAIL)
    return base


# --------------------------------------------------------------------------- #
# Phase 15 — the fixed phrase banks: hand-written, reviewed, never generated
# --------------------------------------------------------------------------- #
# Every classified/stimulus turn returns ONE of these. There is no model in this path: the
# connectome (or a keyword/button stimulus) picks the category, and the phrase is a constant from
# this table, chosen at random — or from the "stressed" half when the fly is stressed
# (hunger > 80 or a live `startled` flag), which is where the exclamation vocabulary lives.
# Format rule: "durum · eylem [same fragment in English]", ≤4 words each side (Phase 13).
PHRASE_BANKS = {
    "besin": {
        "normal": [
            "yaklaşıyor · şeker [approaching · sugar]",
            "koku · güçlü [scent · strong]",
            "tadıyorum · tatlı [tasting · sweet]",
            "besin · bulundu [food · found]",
            "yiyorum · doydum [eating · full]",
        ],
        "stressed": [
            "hassiktir · açım [oh no · starving]",
            "mahvolduk · açlık [we're doomed · hunger]",
            "off · karnım boş [damn · belly empty]",
        ],
    },
    "tehlike": {
        "normal": [
            "tehlike · uçuyor [danger · flying off]",
            "gölge · büyük [shadow · big]",
            "geri · çekiliyor [backing · away]",
        ],
        # the curated answer to "what does it scream when scared" — the Phase 12B list, worked in
        "stressed": [
            "hassiktir · kaçıyor [oh no · fleeing]",
            "off · sıçradı [damn · it jumped]",
            "lan · düşman [damn · enemy]",
            "mahvolduk · saklanıyor [we're doomed · hiding]",
            "ay · tokat [ow · swat]",
        ],
    },
    "selam": {
        "normal": [
            "selam · geldin [hello · you came]",
            "anten · selam [antennae · greeting]",
            "tanıdık · koku [familiar · scent]",
            "merhaba · dostum [hello · friend]",
        ],
        "stressed": [],
    },
    "açlık": {
        "normal": [
            "açlık · düşük [hunger · low]",
            "açlık · orta [hunger · medium]",
            "açlık · yüksek [hunger · high]",
            "tok · karnım [full · belly]",
            "karnım · boş [belly · empty]",
        ],
        "stressed": [
            "açlık · kritik [hunger · critical]",
        ],
    },
    "onay": {
        "normal": [
            "anlaşıldı · tamam [understood · okay]",
            "onay · verildi [approval · given]",
            "doğru · katılıyorum [right · agreeing]",
            "peki · olsun [okay · fine]",
        ],
        "stressed": [],
    },
    "red": {
        "normal": [
            "hayır · istemem [no · I refuse]",
            "olmaz · uzak [no · stay away]",
            "ret · kesin [refusal · firm]",
            "yok · hayır [none · no]",
        ],
        "stressed": [],
    },
    # Phase 15 Task 3 — courtship. Wing vibration is real Drosophila courtship behaviour (the male
    # extends one wing and vibrates it), so "kanat · titriyor" is grounded, not invented.
    "eş": {
        "normal": [
            "iz sürüyorum · heyecanlı [courting · excited]",
            "kanat · titriyor [wing · vibrating]",
            "dişi · yakın [female · near]",
            "kur · başlıyor [courtship · starting]",
            "feromon · güçlü [pheromone · strong]",
        ],
        "stressed": [],
    },
}

# Autonomous impulses (the fly's own needs) also speak a fixed phrase — same rule, no generation.
NEED_PHRASES = {
    "hunger": ["açlık · kritik [hunger · critical]",
               "yemek · aranıyor [food · searching]",
               "şeker · kokusu [sugar · scent]"],
    "energy": ["bitkin · dinlenme [exhausted · resting]",
               "güç · bitti [power · gone]",
               "kanat · ağır [wings · heavy]"],
    "boredom": ["sıkıntı · yüksek [boredom · high]",
                "uyarım · aranıyor [stimulus · searching]",
                "oyalanma · lazım [distraction · needed]"],
}


# Phase 15 Task 3: the seventh stimulus. It is a *keyword route* in the server, not a classifier
# category, because cognitive_matrix.CATEGORIES/VOCAB are frozen (six factory decisions) and both
# self-tests assert they stay 1:1 with CATEGORY_EFFECTS. Multi-word entries match as substrings,
# single words on word boundaries, after the same ASCII folding the classifier uses.
KEYWORD_ROUTES = (
    ("eş", ("dişi sinek", "dişi", "eş", "çiftleş", "kur yap", "eşleş")),
)

OOV_HEAD = "kelime tanınmıyor"


def _fold(text):
    """ASCII-fold Turkish the way the classifier does (so "dişi" matches "disi")."""
    table = str.maketrans({"ı": "i", "ş": "s", "ç": "c", "ğ": "g", "ö": "o", "ü": "u",
                           "İ": "i", "Ş": "s", "Ç": "c", "Ğ": "g", "Ö": "o", "Ü": "u"})
    return " ".join(str(text or "").lower().translate(table).split())


def route_keyword(message):
    """-> (category, matched word) for a server-side keyword stimulus, else (None, None).

    Multi-word entries match as plain substrings; single words match at a word start, with the same
    suffix tolerance the classifier gives its own vocabulary ("çiftleşti" → "çiftleş"), but only for
    stems ≥4 characters — the 2-letter "eş" stays exact, so "eşek"/"eşit" cannot trigger courtship.
    """
    text = _fold(message)
    tokens = text.split()
    for category, words in KEYWORD_ROUTES:
        for word in words:
            needle = _fold(word)
            if " " in needle:
                if needle in text:
                    return category, word
            elif len(needle) >= 4:
                if any(tok.startswith(needle) for tok in tokens):
                    return category, word
            elif needle in tokens:
                return category, word
    return None, None


def pick_phrase(category, stressed=None):
    """One fixed phrase for a category — random, preferring the stressed half when stressed."""
    bank = PHRASE_BANKS.get(str(category or "").strip().lower())
    if not bank:
        return ""
    if stressed is None:
        stressed = bool(stress_reason())
    pool = list(bank.get("stressed") if stressed else bank.get("normal") or [])
    if not pool:                                     # e.g. "selam" has no stressed half
        pool = list(bank.get("normal") or []) + list(bank.get("stressed") or [])
    return random.choice(pool) if pool else ""


def oov_reply():
    """The deterministic answer to an unknown word: no LLM, and the user learns the vocabulary."""
    try:
        category = random.choice(list(cognitive_matrix.VOCAB))
        words = random.sample(list(cognitive_matrix.VOCAB[category]), 4)
    except Exception:                                   # noqa: BLE001
        return OOV_HEAD
    return "%s · bilinen örnekler (%s): %s" % (OOV_HEAD, category, ", ".join(words))


# --------------------------------------------------------------------------- #
# Phase 15 — the shared, LLM-free turn machinery
# --------------------------------------------------------------------------- #
def _category_label(category):
    """Turkish label for any category, classifier or stimulus."""
    cat = str(category or "")
    if cat in cognitive_matrix.CATEGORY_TR:
        return cognitive_matrix.CATEGORY_TR[cat]
    return (game_loop.autonomic_effect(cat) or {}).get("label", cat)


def publish_decision(category, *, source="button", word=None, label=None, confidence=None,
                     origin="user", extra=None):
    """Apply a stimulus and publish the event pair the UI expects. Returns (decision, phrase).

    This is the single path every *non-classifier* deterministic turn takes (the "eş" keyword
    route, the /interact buttons): same effect table, same `apply_effect`, same `classifier` +
    `state` event shape — and a fixed phrase from :data:`PHRASE_BANKS` instead of anything
    generated. The connectome path (``route_message``) publishes its own event and only needs the
    phrase added on top, see ``Handler._chat``.
    """
    effect = game_loop.effect_for(category) or game_loop.autonomic_effect(category)
    res = game_loop.apply_effect(STATE, effect, reason="%s:%s" % (source, category)) if effect \
        else None
    phrase = pick_phrase(category, stressed=bool(stress_reason()))
    decision = {
        "word": word, "category": category, "label": label or _category_label(category),
        "confidence": confidence, "source": source, "origin": origin,
        "delta": (res or {}).get("delta"), "want": (res or {}).get("want"),
        "saturated": (res or {}).get("saturated"), "flag": (res or {}).get("flag"),
        "action": (res or {}).get("action"), "noop": bool((res or {}).get("noop")),
        "alternatives": [], "phrase": phrase, "state": (res or {}).get("state"),
    }
    if extra:
        decision.update(extra)
    if BUS is not None:
        BUS.publish("classifier", payload=decision)
        if res is not None and STATE is not None:
            BUS.publish("state", payload={"state": STATE.snapshot()})
        if phrase:
            BUS.publish("say", payload={"text": phrase, "origin": origin, "mode": "phrase",
                                        "category": category})
    return decision, phrase


def run_impulse(need, tool=None, args=None):
    """The deterministic autonomous impulse: a real connectome scene, the need's reflex, a fixed
    phrase — and **no LLM call at all** (Phase 15).

    The tool was already chosen by ``game_loop.suggested_call(need)``, so there is nothing for a
    model to decide here; before Phase 15 this same work was a prompt round-trip that could take
    4-20 s and produced a generated sentence. Returns the scene dict (or None).
    """
    need = need or {}
    tool, args = ((tool, dict(args or {})) if tool else game_loop.suggested_call(need))
    scene = None
    try:
        if tool == "show3d":
            scene = export3d.build_data(str(args.get("query") or "sugar"),
                                        int(args.get("seeds") or 40),
                                        float(args.get("dur_ms") or 200))
        elif tool == "show_compass":
            scene = export3d.build_compass_scene(str(args.get("regime") or "raw"))
        elif tool == "two_smells":
            scene = export3d.build_sniff_scene()
    except Exception as e:                              # noqa: BLE001
        if BUS is not None:
            BUS.publish("error", payload={"message": "sahne kurulamadı: %s: %s"
                                                     % (type(e).__name__, e)})
    if scene is not None and BUS is not None:
        BUS.publish("viz", payload={"data": scene})
        BUS.publish("tool_result", payload={
            "tool": tool, "args": args, "origin": "autonomous",
            "result": {"shown_in_3d": True, "deterministic": True,
                       "query": scene.get("query") or scene.get("scene"),
                       "n_downstream": scene.get("n_downstream")}})
    effect = game_loop.reflex_for(need)
    res = game_loop.apply_effect(STATE, effect, reason="reflex:impulse") if effect else None
    if STATE is not None:
        STATE.touch(calm=5.0)
    if BUS is not None:
        if STATE is not None:
            BUS.publish("state", payload={"state": STATE.snapshot()})
        if res is not None:
            BUS.publish("reflex", payload={
                "origin": "reflex", "need": need.get("need"),
                "category": game_loop.NEED_CATEGORY.get(need.get("need")),
                "action": res.get("action"), "delta": res.get("delta"),
                "flag": res.get("flag"), "want": res.get("want"),
                "saturated": res.get("saturated"),
                "why": (effect or {}).get("why", ""),
                "triggered_by": "dürtü (deterministik)", "state": res.get("state")})
        phrase = random.choice(NEED_PHRASES.get(need.get("need")) or [""])
        if phrase:
            BUS.publish("say", payload={"text": phrase, "origin": "autonomous", "mode": "phrase",
                                        "category": game_loop.NEED_CATEGORY.get(need.get("need"))})
    return scene


def publish_phrase(category, origin="user"):
    """Publish a fixed phrase for a category the caller already applied (the connectome path)."""
    phrase = pick_phrase(category, stressed=bool(stress_reason()))
    if phrase and BUS is not None:
        BUS.publish("say", payload={"text": phrase, "origin": origin, "mode": "phrase",
                                    "category": category})
    return phrase


# --------------------------------------------------------------------------- #
# the agent loop — streams every step to the bus, never blocks the caller
# --------------------------------------------------------------------------- #
def _chunk_text(chunk):
    """Pull the text out of one streaming chunk across ollama-python versions."""
    try:
        msg = chunk["message"]
    except Exception:                                       # noqa: BLE001
        msg = getattr(chunk, "message", None)
    if msg is None:
        return ""
    try:
        return msg["content"] or ""
    except Exception:                                       # noqa: BLE001
        return getattr(msg, "content", "") or ""


def _chat_json(msgs, on_token=None):
    """One LLM turn. Streams when possible (so the UI can show it thinking) and always
    returns the complete raw string for the JSON parser. Falls back to blocking."""
    if on_token is not None:
        try:
            buf = []
            for chunk in ollama.chat(model=MODEL, messages=msgs, format="json",
                                     stream=True):
                piece = _chunk_text(chunk)
                if piece:
                    buf.append(piece)
                    on_token("".join(buf))
            text = "".join(buf)
            if text.strip():
                return text
        except Exception:                                   # noqa: BLE001
            pass
    return ollama.chat(model=MODEL, messages=msgs, format="json")["message"]["content"]


# --------------------------------------------------------------------------- #
# classifier routing — text in, category out (Phase 9)
# --------------------------------------------------------------------------- #
def route_message(message, origin="user"):
    """Run a message through the mushroom-body classifier and act on the result.

    Returns ``(note, decision)``. ``note`` is the Turkish block appended to the LLM's
    turn — empty when nothing matched, which means ordinary free-form chat (rule E).
    ``decision`` is also published as a `classifier` event so the UI can show what the
    connectome model decided and what it did to the vitals.

    Where the decision comes from: *every* vocabulary word in the sentence is encoded
    into a Kenyon-cell code and read out (`cognitive_matrix.scan`); the most confident
    hit wins, the others ride along in ``alternatives``. The LLM never sees this as a
    choice — `game_loop.classifier_note` states the category as a fact it may only
    narrate.
    """
    hits = cognitive_matrix.scan(message)
    if not hits:
        return "", None
    top = hits[0]
    category = str(top["category"])
    effect = game_loop.effect_for(category)
    alias = None
    if effect is None:
        if not cognitive_matrix.is_taught_category(category):
            return "", None              # factory vocabulary and the effect table drifted apart
        # Phase 11: a category taught at runtime has no physiology of its own — the classifier
        # still decides it and the model is still told it as a fact, but nothing moves (empty
        # delta = noop) unless the user pointed it at one of the factory effects
        # (Phase 11.5). The alias borrows an existing row: CATEGORY_EFFECTS stays 1:1.
        alias = cognitive_matrix.effect_alias(category)
        if alias:
            effect = dict(game_loop.effect_for(alias) or {})
            effect["alias_of"] = alias
            effect["why"] = ("canlı kategori \"%s\" → \"%s\" gibi davranıyor (%s)"
                             % (category, alias, effect.get("why", "")))
        else:
            effect = {"delta": {},
                      "why": "canlı öğretilmiş kategori: etki tablosunda satırı yok"}
    applied = game_loop.apply_effect(STATE, effect, reason="classifier:" + top["word"])
    hit = dict(top, label=cognitive_matrix.CATEGORY_TR.get(category, category))
    decision = {"word": hit["word"], "token": hit["token"], "category": category,
                "label": hit["label"], "confidence": hit["confidence"],
                "classifier": hit.get("classifier"), "agrees": hit.get("agrees"),
                "word_origin": hit.get("origin"),
                "scores": hit.get("scores"), "origin": origin,
                "effect_alias": alias,
                "effect": {"delta": effect.get("delta") or {},
                           "flag": effect.get("flag"), "why": effect.get("why", ""),
                           "alias_of": effect.get("alias_of"), "tool": effect.get("tool")},
                "delta": (applied or {}).get("delta"),
                "want": (applied or {}).get("want"),
                "saturated": (applied or {}).get("saturated") or [],
                "flag": (applied or {}).get("flag"),
                "action": (applied or {}).get("action"),
                "noop": bool((applied or {}).get("noop")),
                "alternatives": [h["word"] for h in hits[1:4]],
                "state": (applied or {}).get("state")}
    if BUS is not None:
        BUS.publish("classifier", payload=decision)
        if decision["delta"]:
            BUS.publish("state", payload={"state": decision["state"]})
    return game_loop.classifier_note(hit, effect, applied, STATE), decision


# --------------------------------------------------------------------------- #
# Phase 11: live teaching from the chat box — "/öğret elma besin"
# --------------------------------------------------------------------------- #
TEACH_CMD = "/öğret"
TEACH_UNDO = "/öğret-geri"
TEACH_EFFECT = "/öğret-efekt"    # Phase 11.5: point a live-taught category at a factory effect
TEACH_CONFIRM = "onayla"        # "/öğret şeker tehlike onayla" = the explicit yes for a relabel
_PENDING_TEACH = {}             # folded word -> the category we were asked to overwrite it with


def parse_teach_command(message):
    """-> a command dict for a message that starts with ``/öğret``, else None.

    Forms::

        /öğret                         list what has been taught
        /öğret <kelime> <kategori>     teach it (a *relabel* asks first, see below)
        /öğret <kelime> <kategori> onayla
                                       the explicit yes for a relabel
        /öğret-geri                    undo the last teach
        /öğret-efekt                   which live categories borrow which factory effect
        /öğret-efekt <kategori> <etki> map it (etki = besin/tehlike/selam/açlık/onay/red)
        /öğret-efekt <kategori> yok    leave it effect-less (informational only)

    Exactly two tokens (plus the optional ``onayla``): the second is the category and the first is
    the word. A longer message is refused with the usage line rather than guessed at — the last
    token of "/öğret karpuz var mı" is "mı", and turning that into a category would be silent
    nonsense. Nothing here touches the classifier; ``handle_teach_command`` does, and only after
    this says the message really is a command.
    """
    text = str(message or "").strip()
    if text == TEACH_UNDO or text.startswith(TEACH_UNDO + " "):
        return {"verb": "undo"}
    if text == TEACH_EFFECT or text.startswith(TEACH_EFFECT + " "):
        parts = text[len(TEACH_EFFECT):].strip().split()
        if not parts:
            return {"verb": "effect-list"}
        if len(parts) != 2:
            return {"verb": "usage", "word": " ".join(parts)}
        return {"verb": "effect", "category": parts[0], "alias": parts[1]}
    if not (text == TEACH_CMD or text.startswith(TEACH_CMD + " ")):
        return None
    parts = text[len(TEACH_CMD):].strip().split()
    confirm = bool(parts) and parts[-1].lower() == TEACH_CONFIRM
    if confirm:
        parts = parts[:-1]
    if not parts:
        return {"verb": "list"}
    if len(parts) != 2:
        return {"verb": "usage", "word": " ".join(parts)}
    return {"verb": "teach", "word": parts[0], "category": parts[1], "confirm": confirm}


def _teach_text(res):
    """The Turkish answer for a completed teach: the measured numbers, not adjectives."""
    if res.get("overwrote"):
        head = "etiket değişti: \"%s\" %s → %s." % (res["word"], res["overwrote"], res["category"])
    elif res.get("reattached"):
        head = "pekiştirildi: \"%s\" zaten %s." % (res["word"], res["category"])
    else:
        head = "öğretildi: \"%s\" → %s." % (res["word"], res["category"])
    bits = [head]
    if res.get("created_category"):
        bits.append("Yeni kategori açıldı: %s — okuma matrisi %d satır oldu (yeniden başlatma "
                    "gerekmedi). Varsayılan olarak etki tablosunda satırı yok: bu kategori bedeni "
                    "kıpırdatmaz, sadece bilinir." % (res["category"], res["readout_shape"][0]))
        bits.append("Beden etkisi bağlamak istersen (zorunlu değil, istemezsen böyle kalır):\n"
                    "  %s %s <etki>      (etkiler: %s)\n"
                    "  %s %s yok         (bilgi amaçlı kalsın)"
                    % (TEACH_EFFECT, res["category"], ", ".join(cognitive_matrix.CATEGORIES),
                       TEACH_EFFECT, res["category"]))
    elif res.get("effect_alias"):
        bits.append("\"%s\" kategori olarak %s etkisini ödünç alıyor (aynı tablo satırı)."
                    % (res["category"], res["effect_alias"]))
    b, a = res["before"], res["after"]
    bits.append("delta kuralı: %d adım / %d güncelleme, lr=%s (tek örnek; tüm sözlük yeniden "
                "eğitilmedi)." % (res["steps"], res["updates"], res["lr"]))
    bits.append("ESKİ SÖZLÜK (gerileme kontrolü): %d/%d, en düşük güven %.3f  →  %d/%d, en düşük "
                "güven %.3f%s"
                % (round(b["accuracy"] * b["n"]), b["n"], b["min_confidence"],
                   round(a["accuracy"] * a["n"]), a["n"], a["min_confidence"],
                   "  (kayıp yok)" if not res["lost"] and not res["dropped"] else ""))
    bits.append("Yeni kelime kendi kararında %.2f güvenle okunuyor (taban %.2f)."
                % (res["target"]["confidence"], cognitive_matrix.CONFIDENCE_FLOOR))
    bits.append("Sözlük: %d kelime (%d fabrika + %d canlı öğretilmiş). Defter: %s"
                % (res["vocabulary"], res["factory_vocabulary"], res["taught_total"],
                   cognitive_matrix.learned_status()["file"]))
    if res.get("warning"):
        bits.append("UYARI: " + res["warning"])
    if res.get("size_warning"):
        bits.append("UYARI: " + res["size_warning"])
    if res.get("safety_warning"):
        bits.append(res["safety_warning"])       # stronger tier: carries its own ⛔ marker
    return "\n".join(bits)


def handle_teach_command(command):
    """Run a ``/öğret`` command -> ``(reply, info, level)``.

    ``level`` is ``"ok" | "warn" | "error" | "alert"``: ``warn`` when the teach measured a
    regression or the vocabulary passed ``cognitive_matrix.VOCAB_WARN_SIZE`` (Task 4 — a warning,
    never a block), ``alert`` when the Phase 11.5 safety net fired (a word is within
    ``TEACH_SAFETY_MARGIN`` of the floor or just took a ``TEACH_SAFETY_STEP`` hit), ``error`` when
    the request itself was unusable. Nothing here runs on the LLM worker: teaching one word is
    ~100 ms of linear algebra, so the answer comes straight back and no turn is queued.
    """
    verb = command["verb"]

    if verb == "list":
        st = cognitive_matrix.status()
        words = st["taught_words"]
        lines = ["Canlı öğretilmiş %d kelime (fabrika %d kelime koda gömülü, sabit):"
                 % (len(words), st["factory_vocabulary"])]
        lines += ["  [%s] %s" % (cat, w) for w, cat in words.items()] or \
                 ["  (henüz yok) — kullanım: /öğret <kelime> <kategori>"]
        lines.append("Okuma etiketleri: %s" % ", ".join(st["labels"]))
        aliases = cognitive_matrix.effect_aliases()
        if aliases:
            lines.append("Beden etkisi ödünç alan canlı kategoriler: %s"
                         % ", ".join("%s → %s" % (c, a) for c, a in aliases.items()))
        lines.append("Etki bağlamak için: %s <kategori> <etki>   (kategoriler: %s)"
                     % (TEACH_EFFECT, ", ".join(cognitive_matrix.CATEGORIES)))
        return "\n".join(lines), {"taught": words, "labels": st["labels"],
                                  "vocabulary": st["vocabulary"],
                                  "effect_aliases": aliases}, "ok"

    if verb == "effect-list":
        aliases = cognitive_matrix.effect_aliases()
        taught_cats = [c for c in cognitive_matrix.labels()
                       if cognitive_matrix.is_taught_category(c)]
        lines = ["Canlı kategoriler: %s" % (", ".join(taught_cats) or "(henüz yok)")]
        lines.append("Etki ödünç alanlar: %s" % (", ".join("%s → %s" % (c, a)
                                                           for c, a in aliases.items()) or "(yok)"))
        lines.append("Fabrika etkileri (tek tablo, kopya açılmaz): %s"
                     % ", ".join(cognitive_matrix.CATEGORIES))
        lines.append("Bağlamak için: %s <kategori> <etki>      Çözmek için: %s <kategori> yok"
                     % (TEACH_EFFECT, TEACH_EFFECT))
        return "\n".join(lines), {"effect_aliases": aliases, "categories": taught_cats}, "ok"

    if verb == "effect":
        res = cognitive_matrix.set_effect_alias(command["category"], command["alias"])
        if not res["ok"]:
            return res["error"], res, "error"
        if res["alias"] is None:
            reply = ("\"%s\" artık bilgi amaçlı: bedeni kıpırdatmaz (Phase 11 davranışı). %s"
                     % (res["category"], "Önceki bağ (%s) kaldırıldı." % res["previous"]
                        if res["cleared"] else "Zaten bağlı bir etkisi yoktu."))
            return reply + " Defter: " + cognitive_matrix.learned_status()["file"], res, "ok"
        eff = game_loop.effect_for(res["alias"]) or {}
        delta = ", ".join("%s %+g" % (k, v) for k, v in (eff.get("delta") or {}).items()) or "yok"
        reply = ("\"%s\" artık \"%s\" gibi davranıyor: %s%s. Yeni etki satırı açılmadı, mevcut "
                 "satır ödünç alındı; seçim deftere yazıldı (%s) ve yeniden başlatmada geri gelir."
                 % (res["category"], res["alias"], delta,
                    " + %s bayrağı" % eff["flag"] if eff.get("flag") else "",
                    cognitive_matrix.learned_status()["file"]))
        return reply, res, "ok"

    if verb == "usage":
        return ("kullanım: /öğret <kelime> <kategori>   (örnek: /öğret elma besin)\n"
                "bildiği bir kelimeyi başka kategoriye yazmak için önce sorulur; onay için "
                "sonuna %s ekle.\ngeri almak için: %s\ncanlı bir kategoriye beden etkisi "
                "bağlamak için: %s <kategori> <etki> | %s <kategori> yok"
                % (TEACH_CONFIRM, TEACH_UNDO, TEACH_EFFECT, TEACH_EFFECT),
                None, "error")

    if verb == "undo":
        res = cognitive_matrix.undo_last_teach()
        if not res.get("ok"):
            return "geri alınacak öğretim yok (%s)" % res.get("error"), res, "error"
        return ("geri alındı: \"%s\" (%s) — okuma ve defter önceki hâline döndü. "
                "Sözlük: %d kelime, öğretilmiş %d."
                % (res["undone"], res["category"], res["vocabulary"], res["taught_total"]),
                res, "ok")

    word, category = command["word"], command["category"]
    known = cognitive_matrix.resolve_category(category)
    if known is None:
        return ("kategori adı kullanılamaz: \"%s\" (2-24 harf/rakam)" % category, None, "error")
    existed = cognitive_matrix.current_category(word)
    if existed and existed[0] != known and not command["confirm"]:
        # never silently relabel: remember the request and ask for the explicit yes
        _PENDING_TEACH[cognitive_matrix.fold(word)] = known
        return ("\"%s\" zaten \"%s\" kategorisinde (%s). Üzerine yazmak için onayla:\n"
                "  %s %s %s %s\n(şimdilik hiçbir şey değişmedi)"
                % (word, existed[0],
                   "fabrika sözlüğü" if existed[1] == "factory" else "canlı öğretim",
                   TEACH_CMD, word, known, TEACH_CONFIRM), None, "warn")
    if command["confirm"] and _PENDING_TEACH.get(cognitive_matrix.fold(word)) != known:
        return ("önce onay istemelisin: %s %s %s" % (TEACH_CMD, word, known), None, "error")
    try:
        res = cognitive_matrix.teach(word, known)
    except ValueError as e:
        return str(e), None, "error"
    except RuntimeError as e:                   # no connectome: nothing to teach
        return "konnektom yok, öğretim yapılamadı: %s" % e, None, "error"
    _PENDING_TEACH.pop(cognitive_matrix.fold(word), None)
    if res.get("safety_warning"):
        level = "alert"                         # Phase 11.5: stronger than "warn"
    elif res["warning"] or res["size_warning"] or not res["installed"]:
        level = "warn"
    else:
        level = "ok"
    return _teach_text(res), res, level



def run_agent(message, max_steps=8, emit=None, origin="user", meta=None):
    """Run the Gemma ReAct JSON loop against the real FlyWire connectome.

    Returns ``(answer_text, viz_data_or_None)``. Every intermediate step is streamed
    through ``emit`` (token / thought / tool_call / tool_result / viz / motor), so a
    polling UI watches the fly think live and nothing blocks.

    ``meta`` carries the autonomous trigger's contract: ``{"require_tool": True,
    "need": "hunger", "tool": "show3d", "args": {...}}``. When a tool is required the
    loop REFUSES ``{"final": ...}`` until something has actually been run on the
    connectome, and if the model keeps refusing it runs the suggested call itself — the
    3D brain always lights up.
    """
    meta = dict(meta or {})
    mode = str(REQUIRE_TOOL).lower()
    require = (bool(meta.get("require_tool")) or mode == "always"
               or (mode == "autonomous" and origin == "autonomous"))

    def pub(kind, **fields):
        if emit:
            emit(kind, **fields)

    viz = {}
    last_emit = [0.0]
    tool_runs = 0          # tools that actually executed without an error
    refusals = 0           # times the model tried to speak without acting
    reflex = game_loop.reflex_for({"need": meta.get("need")}) if meta.get("need") else None
    reflex_done = False

    def on_token(full):
        now = time.time()
        if now - last_emit[0] >= 0.35:
            last_emit[0] = now
            pub("token", text=full[-500:])

    # ---------------------------------------------------------------- 3D tools #
    def show3d(query="olfactory", seeds=40, dur_ms=200):
        data = export3d.build_data(query, int(seeds), float(dur_ms))
        viz["data"] = data
        pub("viz", data=data)
        return {"shown_in_3d": True, "query": data["query"], "n_input": data["n_input"],
                "n_downstream": data["n_downstream"],
                "top_types": data.get("top_downstream_types", []),
                "energy": data["energy"]["headline"]}

    def show_logic_gate(kind="AND"):
        k = str(kind).upper().replace(" ", "-").replace("_", "-")
        if k in ("NOT", "ANDNOT", "NAND-NOT"):
            k = "AND-NOT"
        if k not in ("AND", "OR", "AND-NOT"):
            k = "AND"
        g = logic.find_gate(k)
        if not g:
            return {"error": "konnektomda temiz bir %s kapısı bulunamadı" % k}
        data = export3d.build_gate_scene(g)
        viz["data"] = data
        pub("viz", data=data)
        return {"shown_in_3d": True, "gate": data["gate"]["kind"],
                "neurons": data["gate"]["labels"], "truth_table": data["gate"]["truth"],
                "energy": data["energy"]["headline"]}

    def do_math(a=2, b=3, op="add"):
        try:
            a, b = max(0, int(a)), max(0, int(b))
        except Exception:                                   # noqa: BLE001
            return {"error": "a ve b küçük tam sayılar olmalı"}
        data = export3d.build_math_scene(a, b, op=str(op))
        viz["data"] = data
        pub("viz", data=data)
        m = data["math"]
        return {"shown_in_3d": True,
                "result": "%d %s %d = %d" % (m["x"], m["sym"], m["y"], m["result"]),
                "binary": "%s %s %s = %s" % (m["x_bin"], m["sym"], m["y_bin"],
                                             m["result_bin"]),
                "gate_ops": m["gate_ops"], "energy": data["energy"]["headline"]}

    def show_compass(regime="raw"):
        r = str(regime).lower().strip()
        if r not in ("raw", "memory"):
            r = "raw"
        data = export3d.build_compass_scene(r)
        viz["data"] = data
        pub("viz", data=data)
        cm = data["compass"]
        return {"shown_in_3d": True, "scene": "compass", "regime": r,
                "ring_neurons": cm["n_ring"], "cued_heading_deg": cm["theta0_deg"],
                "turned_to_deg": cm["turn_to_deg"], "energy": data["energy"]["headline"]}


    # ------------------------------------------------- descending-neuron scenes #
    # Phase 9: these show the *brain's* command neurons in the 3D view. There is no body
    # to drive any more, so no `motor` event is published — the scene is the whole output.
    def move_fly(moves=None):
        if isinstance(moves, str):
            moves = moves.replace(",", " ").split()
        if not moves:
            moves = ["forward", "left", "forward", "escape"]
        data = export3d.build_fly_scene([str(m) for m in moves])
        viz["data"] = data
        pub("viz", data=data)
        f = data["fly"]
        end = f["traj"][-1] if f["traj"] else [0, 0, 0, 0]
        return {"shown_in_3d": True, "scene": "fly",
                "moves": [c["label"] for c in f["commands"]],
                "command_neurons": [c["dn"] for c in f["commands"]],
                "ended_at": {"x": end[1], "y": end[2], "heading_deg": end[3]},
                "note": "gerçek inen nöron komutları — sinyal beyinde kalır, sahne "
                        "yalnızca görselleştirmedir (gövde yok)",
                "energy": data["energy"]["headline"]}

    def navigate_fly(start_heading=120):
        try:
            h = float(start_heading)
        except Exception:                                   # noqa: BLE001
            h = 120.0
        data = export3d.build_navigate_scene(h)
        viz["data"] = data
        pub("viz", data=data)
        f = data["fly"]
        return {"shown_in_3d": True, "scene": "navigate",
                "released_at_deg": f["start_deg"], "homed_to_deg": f["goal_deg"],
                "final_error_deg": f["final_err_deg"],
                "energy": data["energy"]["headline"]}

    def show_path(start="sugar", end="motor"):
        data = export3d.build_path_scene(str(start), str(end))
        viz["data"] = data
        pub("viz", data=data)
        p = data["path"]
        if not p.get("found"):
            return {"error": "yol yok %s -> %s: %s" % (start, end, p.get("reason", ""))}
        return {"shown_in_3d": True, "scene": "path", "start": start, "end": end,
                "n_synapses": p["n_synapses"], "chain": " -> ".join(p["hops"]),
                "note": "bir en kısa kablolama yolu (topoloji, sinyal zamanlaması değil)"}

    def dodge_swatter():
        data = export3d.build_swatter_scene()
        viz["data"] = data
        pub("viz", data=data)
        sw = data["swatter"]
        return {"shown_in_3d": True, "scene": "swatter", "playable": True,
                "detectors": sw["n_detectors"], "giant_fiber": sw["n_gf"],
                "reaction_threshold_ms": sw["threshold_ms"],
                "note": "sineğin ~%s birimlik tepki sınırından HIZLI vurursan sineği "
                        "yakalarsın; yavaş kalırsan gerçek Dev Fiber kaçış devresi "
                        "önce zıplar" % sw["threshold_ms"],
                "energy": data["energy"]["headline"]}

    def two_smells():
        data = export3d.build_sniff_scene()
        viz["data"] = data
        pub("viz", data=data)
        sn = data["sniff"]
        return {"shown_in_3d": True, "scene": "sniff",
                "kc_overlap_pct": round(100 * sn["overlap"], 1),
                "shared_cells": sn["shared_kc"],
                "false_memory_pct": round(100 * sn["false_memory"]),
                "note": "iki koku neredeyse ayrık seyrek Kenyon hücresi kodu kullanır "
                        "(%.1f%% çakışma), bu yüzden yeni hafıza eskiye zar zor dokunur "
                        "— bir mekanizma, kıyaslama değil" % (100 * sn["overlap"])}

    def show_eye(pattern="heart"):
        p = str(pattern).lower().strip()
        data = export3d.build_optic_scene(
            p if p in ("heart", "smiley", "f", "gradient", "checker") else "heart")
        viz["data"] = data
        pub("viz", data=data)
        o = data["optic"]
        return {"shown_in_3d": True, "scene": "optic", "pattern": o["pattern"],
                "lamina_columns": o["n_l1"], "medulla_cells": o["n_mi"],
                "relay_synapses": o["n_syn"],
                "note": "gerçek L1->Mi1 retinotopik kablolamadan geçirilen bir görüntü; "
                        "~750 kolonluk bir beynin gözü, kamera değil"}


    # ------------------------------------------------------------ life actions #
    def _life(action, amount=1.0):
        if STATE is None:
            return {"ok": False, "error": "durum yöneticisi hazır değil"}
        res = STATE.apply(action, amount)
        STATE.touch(calm=5.0)
        if BUS is not None:
            BUS.publish("state", payload={"state": STATE.snapshot()})
        return res

    def eat(amount=1.0):
        return _life("eat", amount)

    def rest(amount=1.0):
        return _life("rest", amount)

    def play(amount=1.0):
        return _life("play", amount)

    def groom(amount=1.0):
        return _life("groom", amount)

    def fire_reflex(triggered_by):
        """Apply the bodily consequence of this need ourselves (the feeding reflex).

        'Seeing food is not eating it': a 4B model lights up the sugar circuit and then
        announces it is still hungry, so the vitals would never move and the impulse would
        fire forever. The fly still *narrates* the reflex in Turkish — it just does not get
        to decide whether it happened. Publishes a distinct `reflex` event
        (origin="reflex") carrying the category and the delta, so the UI can show WHY the
        hunger dropped.

        Phase 9: this is the same table and the same code path as a typed word
        (`route_message`) — an autonomous need is simply a category with a known effect.
        """
        nonlocal reflex_done
        if not reflex or reflex_done:
            return None
        reflex_done = True
        res = game_loop.apply_effect(STATE, reflex, reason="reflex:" + str(triggered_by))
        if STATE is not None:
            STATE.touch(calm=5.0)
        if BUS is not None and res is not None:
            BUS.publish("state", payload={"state": STATE.snapshot()})
            BUS.publish("reflex", payload={
                "origin": "reflex", "need": meta.get("need"),
                "category": game_loop.NEED_CATEGORY.get(meta.get("need")),
                "action": res.get("action"), "delta": res.get("delta"),
                "flag": res.get("flag"), "why": reflex.get("why", ""),
                "triggered_by": str(triggered_by), "state": res.get("state")})
        pub("tool_result", tool=(res or {}).get("action") or "efekt", result=res,
            reflex=True)
        return res

    # ------------------------------------------------------------- the loop #
    tools = dict(flysim.TOOLS)
    tools.update({
        "show3d": show3d, "show_logic_gate": show_logic_gate, "do_math": do_math,
        "show_compass": show_compass, "move_fly": move_fly,
        "navigate_fly": navigate_fly, "show_path": show_path,
        "dodge_swatter": dodge_swatter, "two_smells": two_smells, "show_eye": show_eye,
        "eat": eat, "rest": rest, "play": play, "groom": groom,
    })

    msgs = [{"role": "system",
             "content": system_prompt(origin, signal=(meta.get("mode") == "caption"))},
            {"role": "user", "content": message}]
    for _ in range(max(1, int(max_steps))):
        raw = _chat_json(msgs, on_token=on_token)
        call = agent._parse_json(raw)
        if call is None:
            pub("warning", message="model geçerli JSON üretmedi, yeniden deniyorum")
            msgs.append({"role": "assistant", "content": str(raw)[:2000]})
            msgs.append({"role": "user",
                         "content": "Sadece TEK bir geçerli JSON nesnesi yaz — "
                                    "açıklama yok, kod bloğu yok."})
            continue

        if call.get("thought"):
            pub("thought", text=str(call["thought"])[:600])

        if "final" in call:
            if require and tool_runs == 0:
                # Laziness guard: the fly may not just announce its hunger, it must act.
                refusals += 1
                if refusals <= 2:
                    tool, args = meta.get("tool"), meta.get("args") or {}
                    example = json.dumps({"tool": tool or "show3d",
                                          "args": args or {"query": "sugar",
                                                           "seeds": 40, "dur_ms": 200}},
                                         ensure_ascii=False)
                    pub("warning", message="araç çalıştırmadan konuşma reddedildi (%d/2)"
                        % refusals)
                    msgs.append({"role": "assistant", "content": str(raw)[:1000]})
                    msgs.append({"role": "user", "content":
                                 "REDDEDİLDİ: henüz hiçbir araç çalıştırmadın, bu yüzden "
                                 "3D beyin karanlık kaldı. {\"final\": ...} şu an YASAK. "
                                 "Şimdi tam olarak şunu yaz: " + example})
                    continue
                # the model is stubborn: run the suggested tool ourselves, then let it talk
                tool = meta.get("tool") or "show3d"
                args = meta.get("args") or {"query": "sugar", "seeds": 40, "dur_ms": 200}
                fn = tools.get(tool)
                pub("tool_call", tool=str(tool), args=args, forced=True)
                try:
                    result = fn(**args) if fn else {"error": "bilinmeyen araç '%s'" % tool}
                except Exception as e:                      # noqa: BLE001
                    result = {"error": "%s: %s" % (type(e).__name__, e)}
                pub("tool_result", tool=str(tool), result=result, forced=True)
                if not result.get("error"):
                    tool_runs += 1
                ref = fire_reflex(tool)
                extra = (("\nBEDEN REFLEKSİ (çip otomatik uyguladı): "
                          + json.dumps(ref, default=str, ensure_ascii=False)[:400])
                         if ref else "")
                msgs.append({"role": "user", "content":
                             "Aracı ben çalıştırdım (3D güncellendi). Şimdi kısa bir "
                             "Türkçe {\"final\": \"...\"} yaz.\nTOOL RESULT:\n"
                             + json.dumps(result, default=str, ensure_ascii=False)[:2000]
                             + extra})
                continue
            if reflex and not reflex_done and tool_runs:
                fire_reflex("final")     # never end a hunger turn unfed
            # Phase 12.5: the prompt asked for one exclamation; this is the backstop that makes
            # it true in the bytes the client sees (no-op for 0/1 hits, English tail untouched).
            return single_exclaim(str(call["final"])), viz.get("data")

        tool = call.get("tool")
        if call.get("noop") or not tool:
            if origin == "autonomous":
                pub("noop")
                return None, viz.get("data")
            # the human asked something: never let the fly shrug it off
            pub("warning", message="kullanıcı turunda noop; cevap isteniyor")
            msgs.append({"role": "assistant", "content": str(raw)[:1000]})
            msgs.append({"role": "user",
                         "content": "Patron sana bir şey sordu. {\"noop\"} kullanma; "
                                    "{\"final\": \"<Türkçe, 1-3 cümle>\"} ile cevap ver."})
            continue

        args = call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        pub("tool_call", tool=str(tool), args=args)
        fn = tools.get(tool)
        try:
            result = fn(**args) if fn else {"error": "bilinmeyen araç '%s'" % tool}
        except Exception as e:                              # noqa: BLE001
            result = {"error": "%s: %s" % (type(e).__name__, e)}
        pub("tool_result", tool=str(tool), result=result)
        if not (isinstance(result, dict) and result.get("error")):
            tool_runs += 1

        msgs.append({"role": "assistant", "content": str(raw)[:4000]})
        note = "TOOL RESULT:\n" + json.dumps(result, default=str,
                                             ensure_ascii=False)[:2200]
        if not (isinstance(result, dict) and result.get("error")) \
                and game_loop.reflex_matches(reflex, tool, args):
            ref = fire_reflex(tool)          # food was found -> the fly actually feeds
            if ref:
                note += ("\n\nBEDEN REFLEKSİ (çip otomatik uyguladı, sen karar vermedin): "
                         + json.dumps(ref, default=str, ensure_ascii=False)[:600])
        if viz.get("data"):
            note += ('\n\n3D görünüm güncellendi. SADECE '
                     '{"final": "<2-3 cümlelik Türkçe açıklama>"} yaz.')
        msgs.append({"role": "user", "content": note})

    # out of steps: synthesize something useful from whatever was shown
    data = viz.get("data")
    if data:
        tops = ", ".join(data.get("top_downstream_types", [])[:4])
        return ("Patron, %s nöronlarını uyardım (%s giriş); sinyal %s aşağı akış "
                "nöronuna yayıldı%s. 3D görünümde izleyebilirsin."
                % (data.get("query", "?"), data.get("n_input", "?"),
                   data.get("n_downstream", "?"), (" — " + tops) if tops else ""), data)
    return ("Hmm, bunu tam çıkaramadım Patron. 'olfactory', 'sugar' ya da "
            "'mushroom body' gibi bir bölge adı verir misin?", None)


# --------------------------------------------------------------------------- #
# HTTP surface — instant responses; everything heavy happens on the workers
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"       # keep-alive: the UI polls /poll every ~0.6s

    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(b)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str, ensure_ascii=False))

    @staticmethod
    def _params(query):
        out = {}
        for part in (query or "").split("&"):
            if not part:
                continue
            k, _, v = part.partition("=")
            out.setdefault(urllib.parse.unquote(k), []).append(urllib.parse.unquote(v))
        return out

    # ------------------------------------------------------------------ GET #
    def do_GET(self):
        path, _, query = self.path.partition("?")
        params = self._params(query)
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "chat3d.html"), "r", encoding="utf-8") as fh:
                    html = fh.read()
            except OSError:
                self._send(500, "chat3d.html bulunamadı", "text/plain; charset=utf-8")
                return
            self._send(200, html, "text/html; charset=utf-8")
        elif path == "/initial":
            self._send(200, _INITIAL if _INITIAL else "null")
        elif path == "/poll":
            since = params.get("since", ["0"])[0]
            limit = params.get("limit", ["300"])[0]
            if BUS is None:
                self._json({"events": [], "seq": 0, "state": None})
                return
            page = BUS.since(since, limit=limit)
            page["state"] = STATE.snapshot() if STATE else None
            page["executor"] = EXECUTOR.status() if EXECUTOR else None
            page["loop"] = LOOP.status() if LOOP else None
            # Phase 15: the reply is synchronous now, so the first message waits for the connectome
            # matrix. This flag (set by the warm thread, no lock) lets the UI say so instead of
            # looking frozen. The status block below still comes from cognitive_matrix itself.
            page["classifier_ready"] = CLASSIFIER_READY
            self._json(page)
        elif path == "/state":
            self._json({"state": STATE.snapshot() if STATE else None,
                        "loop": LOOP.status() if LOOP else None,
                        "executor": EXECUTOR.status() if EXECUTOR else None,
                        "bus": BUS.status() if BUS else None,
                        "classifier": cognitive_matrix.status()})
        elif path == "/health":
            self._json({"ok": True, "model": MODEL,
                        "seq": BUS.last_seq() if BUS else 0})
        else:
            self._send(404, "bulunamadı", "text/plain; charset=utf-8")

    # ----------------------------------------------------------------- POST #
    def do_POST(self):
        path, _, _query = self.path.partition("?")
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except Exception:                                   # noqa: BLE001
            self._json({"error": "geçersiz JSON"}, 400)
            return
        if not isinstance(payload, dict):
            payload = {}
        if path == "/chat":
            self._chat(payload)
        elif path == "/interact":
            self._interact(payload)
        elif path == "/tool":
            self._tool(payload)
        elif path == "/vitals":
            self._vitals(payload)
        elif path == "/mode":
            self._mode(payload)
        else:
            self._send(404, "bulunamadı", "text/plain; charset=utf-8")

    # --------------------------------------------------------------- actions #
    def _chat(self, payload):
        """One typed/spoken message — answered **deterministically, with no LLM in the path**.

        Phase 15: connectome classifier → server-side keyword stimulus → deterministic refusal.
        Each of the three publishes its own events and returns a fixed phrase, so the reply is
        instant (no queue, no worker, no generated text) and the UI's primary element stays the
        connectome's own decision.
        """
        message = str(payload.get("message", "") or "").strip()
        if not message:
            self._json({"error": "message boş"}, 400)
            return
        if STATE is None:
            self._json({"error": "çekirdek hazır değil"}, 503)
            return
        STATE.touch()      # insan konuştu: can sıkıntısı düşer, idle sıfırlanır
        sensory = bool(payload.get("sensory"))
        origin = "sensory" if sensory else "user"
        if sensory:
            message = "Kullanıcı sesli konuştu: " + message
        if BUS is not None:
            BUS.publish("user", payload={"text": message, "origin": origin})
        # Phase 11: "/öğret ..." is a command, not a question — the classifier learns it and
        # answers straight back, so no LLM turn is queued and the chat stays responsive.
        command = parse_teach_command(message)
        if command is not None:
            self._teach(command, payload, origin)
            return
        # 1) the connectome: route_message applies the effect and publishes the `classifier` event.
        #    Phase 15 only adds the fixed phrase on top — the caption is not generated anymore.
        note, decision = route_message(message, origin=origin)
        if decision is not None:
            phrase = publish_phrase(decision.get("category"), origin=origin)
            self._json({"ok": True, "job": None, "answer": phrase, "classifier": decision,
                        "source": "connectome", "seq": BUS.last_seq() if BUS else 0})
            return
        # 2) the seventh stimulus ("eş"): a keyword route, same effect pipeline, no classifier row
        category, word = route_keyword(message)
        if category:
            decision, phrase = publish_decision(category, source="keyword", word=word,
                                                confidence=None, origin=origin)
            self._json({"ok": True, "job": None, "answer": phrase, "classifier": decision,
                        "source": "keyword", "seq": BUS.last_seq() if BUS else 0})
            return
        # 3) nothing matched: a deterministic refusal that teaches the vocabulary. Zero latency,
        #    zero generation — this replaced the free-form LLM chat path entirely (Phase 15).
        reply = oov_reply()
        if BUS is not None:
            BUS.publish("say", payload={"text": "🧩 " + reply, "origin": origin,
                                        "mode": "system"})
        self._json({"ok": True, "job": None, "answer": reply, "classifier": None,
                    "oov": True, "source": "oov", "seq": BUS.last_seq() if BUS else 0})

    # ------------------------------------------------- direct interaction (Task 4) #
    INTERACTIONS = {"feed": ("besin", "🍯 besle"),
                    "poke": ("tehlike", "👋 dokun/kovala"),
                    "mate": ("eş", "🪰 dişi sinek")}

    def _tool(self, payload):
        """POST /tool {name} — run one connectome scene directly.

        Phase 15 addition: these scenes used to be reachable only by the LLM calling a tool from
        free-form chat. Free-form chat is gone, so the same builders now hang off a button — same
        `export3d` calls, no model involved.
        """
        name = str(payload.get("name") or "").strip().lower()
        specs = {
            "gates": lambda: export3d.build_gate_scene(
                logic.find_gate(str(payload.get("kind") or "AND").upper())),
            "math": lambda: export3d.build_math_scene(int(payload.get("a") or 6),
                                                      int(payload.get("b") or 7),
                                                      str(payload.get("op") or "mul")),
            "compass": lambda: export3d.build_compass_scene(str(payload.get("regime") or "raw")),
            "smells": lambda: export3d.build_sniff_scene(),
            "eye": lambda: export3d.build_optic_scene(str(payload.get("pattern") or "heart")),
            "swatter": lambda: export3d.build_swatter_scene(),
            "path": lambda: export3d.build_path_scene(str(payload.get("start") or "sugar"),
                                                      str(payload.get("end") or "motor")),
            "navigate": lambda: export3d.build_navigate_scene(
                float(payload.get("start_heading") or 120.0)),
        }
        if name not in specs:
            self._json({"error": "bilinmeyen sahne", "allowed": sorted(specs)}, 400)
            return
        try:
            data = specs[name]()
        except Exception as e:                          # noqa: BLE001
            self._json({"error": "sahne kurulamadı: %s: %s" % (type(e).__name__, e)}, 500)
            return
        if not data:
            self._json({"error": "sahne boş döndü"}, 500)
            return
        if BUS is not None:
            BUS.publish("viz", payload={"data": data})
            BUS.publish("tool_result", payload={
                "tool": name, "origin": "user", "args": {},
                "result": {"shown_in_3d": True, "deterministic": True,
                           "scene": data.get("scene") or name,
                           "query": data.get("query")}})
        self._json({"ok": True, "name": name, "scene": data.get("scene") or name,
                    "seq": BUS.last_seq() if BUS else 0})

    def _interact(self, payload):
        """POST /interact {action} — a physical control, bypassing text parsing entirely."""
        action = str(payload.get("action") or "").strip().lower()
        if action not in self.INTERACTIONS:
            self._json({"error": "bilinmeyen eylem",
                        "allowed": sorted(self.INTERACTIONS)}, 400)
            return
        if STATE is None:
            self._json({"error": "çekirdek hazır değil"}, 503)
            return
        category, label = self.INTERACTIONS[action]
        STATE.touch(calm=0.0)      # human contact resets the idle clock, without double-counting
        if BUS is not None:
            BUS.publish("user", payload={"text": "[düğme] " + label, "origin": "user",
                                         "action": action})
        decision, phrase = publish_decision(category, source="button", label=label,
                                           origin="user", extra={"action_name": action,
                                                                 "button": label})
        self._json({"ok": True, "action": action, "category": category, "answer": phrase,
                    "classifier": decision, "seq": BUS.last_seq() if BUS else 0})

    def _vitals(self, payload):
        """POST /vitals {field, value} — the manual override / debug control (Phase 15 Task 5)."""
        field = str(payload.get("field") or "").strip().lower()
        if field not in ("energy", "hunger", "boredom"):
            self._json({"error": "bilinmeyen alan",
                        "allowed": ["energy", "hunger", "boredom"]}, 400)
            return
        try:
            value = float(payload.get("value"))
        except (TypeError, ValueError):
            self._json({"error": "value sayı olmalı"}, 400)
            return
        if STATE is None:
            self._json({"error": "çekirdek hazır değil"}, 503)
            return
        before = float(STATE.snapshot()[field])
        res = STATE.apply_delta({field: value - before}, action="manual")
        if BUS is not None:
            BUS.publish("state", payload={"state": STATE.snapshot()})
            BUS.publish("reflex", payload={
                "origin": "manual", "category": "manuel", "action": "override",
                "delta": res.get("delta"), "want": res.get("want"),
                "saturated": res.get("saturated"),
                "why": "manuel override (debug): %s %.0f → %.0f" % (field, before, value),
                "triggered_by": "panel", "state": res.get("state")})
        self._json({"ok": True, "field": field, "before": before,
                    "value": res["state"][field], "state": res["state"],
                    "seq": BUS.last_seq() if BUS else 0})

    def _teach(self, command, payload, origin):
        """Answer a ``/öğret`` command from the chip itself: no LLM turn, no queue, no wait.

        Publishes a ``teach`` event (the measured before/after numbers), a ``warning`` event when
        the teach measured a regression or a size warning — the Task 2/4 contract is "say it out
        loud" — a second, stronger ``warning`` event (``kind: "teach-safety"``) when the Phase 11.5
        safety net fired, and a ``say`` event so the browser shows the answer as the fly's bubble.
        ``level`` (``ok``/``warn``/``alert``/``error``) travels in the response too, so a client can
        tell the tiers apart without parsing Turkish.
        """
        try:
            reply, info, level = handle_teach_command(command)
        except Exception as e:                                  # noqa: BLE001
            reply, info, level = ("öğretim başarısız: %s: %s" % (type(e).__name__, e)), None, "error"
        if level != "ok":
            print("  /öğret [%s] %s" % (level, reply.replace("\n", " | ")), file=sys.stderr)
        if BUS is not None:
            if info is not None and "before" in info:       # a completed teach: chip the numbers
                BUS.publish("teach", payload=dict(info, level=level))
            if info is not None:
                measured = info.get("warning") or info.get("size_warning")
                if measured:                               # Task 2/4: drift is said out loud
                    # NB: EventBus flattens a payload and drops "kind" (it is the event's own
                    # field), so the tier travels as ``level`` and in the ⛔/⚠ message text.
                    BUS.publish("warning", payload={"message": measured, "level": "warn"})
                if info.get("safety_warning"):             # Phase 11.5: the stronger tier
                    BUS.publish("warning", payload={"message": info["safety_warning"],
                                                    "level": "alert",
                                                    "safety": info.get("safety")})
            if reply:
                # Phase 13: our own /öğret answer — neither the LLM nor a caption. The client
                # renders `mode: system` as a neutral line, never as a character speaking.
                BUS.publish("say", payload={"text": reply, "origin": origin, "mode": "system"})
        if payload.get("wait"):                 # legacy clients get the answer in the response
            self._json({"answer": reply, "viz": None, "job": None, "classifier": None,
                        "teach": info, "ok": info is not None, "level": level})
            return
        self._json({"ok": True, "job": None, "teach": info, "answer": reply, "busy": False,
                    "queued": 0, "classifier": None, "cmd": command["verb"], "level": level,
                    "seq": BUS.last_seq() if BUS else 0})

    def _mode(self, payload):
        if STATE is None:
            self._json({"error": "durum hazır değil"}, 503)
            return
        on = bool(payload.get("autonomy", True))
        STATE.set_autonomy(on)
        if BUS is not None:
            BUS.publish("mode", payload={"autonomy": on})
        self._json({"ok": True, "autonomy": on, "state": STATE.snapshot()})

    def log_message(self, *args):       # keep the console quiet
        pass


# --------------------------------------------------------------------------- #
# wiring it together
# --------------------------------------------------------------------------- #
def build_core(autonomy=True, tick=1.0, cooldown=30.0):
    """Create the bus / state / executor / game loop and start the worker threads.

    Phase 15: the GameLoop gets ``impulse=run_impulse``, so an autonomous need is answered
    deterministically (scene + reflex + fixed phrase). The LLM executor thread is still built for
    back-compat and for the harness phases, but **nothing in the live server submits to it**.
    """
    global BUS, STATE, EXECUTOR, LOOP
    BUS = brain_state.EventBus(maxlen=600)
    STATE = brain_state.FlyState(autonomy=autonomy)
    EXECUTOR = game_loop.LLMExecutor(run_agent, bus=BUS, name="llm-executor").start()
    LOOP = game_loop.GameLoop(STATE, bus=BUS, executor=EXECUTOR, tick=tick,
                              max_think_gap=cooldown, impulse=run_impulse).start()
    BUS.publish("system", payload={"event": "core-ready", "model": MODEL,
                                   "autonomy": autonomy, "tick_s": tick,
                                   "think_gap_s": cooldown})
    return BUS, STATE, EXECUTOR, LOOP


def shutdown_core():
    for obj, meth in ((LOOP, "stop"), (EXECUTOR, "stop")):
        if obj is not None:
            try:
                getattr(obj, meth)()
            except Exception:                               # noqa: BLE001
                pass


def serve(open_browser=True, port=PORT, autonomy=True, tick=1.0, cooldown=30.0,
          require_tool="autonomous"):
    print("Konnektom yükleniyor (ilk açılış yavaş, ~5sn)...", file=sys.stderr)
    flysim._ensure_conn()
    global _INITIAL, PORT, REQUIRE_TOOL
    PORT = int(port)
    REQUIRE_TOOL = str(require_tool).lower()
    print("Dinlenme halindeki beyin kuruluyor...", file=sys.stderr)
    try:
        _INITIAL = json.dumps(export3d.resting_data(), default=str)
    except Exception as e:                                  # noqa: BLE001
        print("başlangıç sahnesi kurulamadı: %s" % e, file=sys.stderr)

    def _warm():
        # keep the first real request fast: gates, routing graph, escape/sniff/optic
        global CLASSIFIER_READY
        try:
            export3d.warm()
        except Exception:                                   # noqa: BLE001
            pass
        for mod, fn in (("flymath", "_gates"), ("swatter", "circuit"),
                        ("sniff", "circuit"), ("cognitive_matrix", "warm"),
                        ("optic", "optic")):
            try:
                getattr(__import__(mod), fn)()
            except Exception:                               # noqa: BLE001
                pass
        try:                                                # Phase 11: taught words come back
            learned = cognitive_matrix.load_learned()
            w = learned.get("weights") or {}
            if learned["loaded"]:
                print("  canlı öğretilmiş %d kelime geri yüklendi (%.1f sn): %s%s"
                      % (learned["loaded"], learned["seconds"],
                         ", ".join("%s→%s" % (k, v) for k, v in learned["words"].items()),
                         "" if w.get("match") else
                         "   [.npy uyuşmuyor: %s]" % (w.get("max_delta") or w.get("error")
                                                      or "şekil farklı")), file=sys.stderr)
            elif learned.get("error"):
                print("  canlı öğretim defteri yüklenemedi: %s" % learned["error"],
                      file=sys.stderr)
            elif learned.get("skipped"):
                print("  atlanan öğretilmiş kelimeler: %s" % learned["skipped"], file=sys.stderr)
        except Exception as e:                              # noqa: BLE001
            print("  canlı öğretim defteri okunamadı: %s" % e, file=sys.stderr)
        try:                                                # gerçek ALPN→KC sınıflandırıcısı
            cl = cognitive_matrix.status()
            if cl.get("loaded"):
                print("  sınıflandırıcı hazır: %d PN -> %d KC (%s aktif, %.2f%%) -> %d MBON; "
                      "delta kuralı %d epoch'ta %.0f%%"
                      % (cl["pn_dim"], cl["kc_dim"], cl["kc_active_range"],
                         100.0 * cl["kc_density"], cl["mbon_dim"], cl["epochs"],
                         100.0 * cl["train_accuracy"]), file=sys.stderr)
            else:
                print("  sınıflandırıcı yüklenemedi: %s\n"
                      "  (mesajlar yine çalışır, sadece sınıflandırıcıya uğramaz)"
                      % cl.get("error"), file=sys.stderr)
        except Exception:                                   # noqa: BLE001
            pass
        try:
            flysim._ensure_adj()
        except Exception:                                   # noqa: BLE001
            pass
        # Phase 15: the classifier matrix is built (the warm thread is what makes the first
        # synchronous /chat fast), so the UI can stop saying "loading".
        CLASSIFIER_READY = True

    threading.Thread(target=_warm, daemon=True).start()
    build_core(autonomy=autonomy, tick=tick, cooldown=cooldown)

    url = "http://localhost:%d" % PORT
    print("Hazır -> %s   (otonomi=%s, tick=%.1fs, düşünme aralığı=%.0fs, zorunlu_araç=%s)"
          % (url, "açık" if autonomy else "kapalı", tick, cooldown, REQUIRE_TOOL),
          file=sys.stderr)
    learned_now = cognitive_matrix.learned_status()
    print("Sınıflandırıcı: %d fabrika kategorisi, %d kelime (%d canlı öğretilmiş; defter %s%s) | "
          "gerçek ALPN→KC matrisi ısınma iş parçacığında kuruluyor (ilk açılış ~10 sn); "
          "/öğret <kelime> <kategori> ile canlı öğretim açık"
          % (len(cognitive_matrix.CATEGORIES),
             cognitive_matrix.VOCAB_SIZE + learned_now["taught"], learned_now["taught"],
             learned_now["file"], "" if learned_now["exists"] else ", henüz yok"), file=sys.stderr)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:                                   # noqa: BLE001
            pass
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nkapatılıyor...", file=sys.stderr)
    except OSError as e:
        print("\n%d portunda başlatılamadı: %s\n"
              "Başka bir sunucu hâlâ çalışıyor olabilir (netstat -ano | findstr %d).\n"
              % (PORT, e, PORT), file=sys.stderr)
        raise
    finally:
        shutdown_core()


def build_parser():
    p = argparse.ArgumentParser(
        prog="server.py",
        description="Otonom sibernetik sinek — web + 3D + LLM çekirdeği")
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--no-autonomy", action="store_true",
                   help="otonom dürtüleri kapat (başlangıç değeri)")
    p.add_argument("--tick", type=float, default=1.0, help="oyun döngüsü tick süresi (sn)")
    p.add_argument("--cooldown", type=float, default=30.0,
                   help="otonom düşünmeler arası minimum süre (sn)")
    p.add_argument("--require-tool", choices=("autonomous", "always", "never"),
                   default="autonomous",
                   help="araç çalıştırmadan konuşmayı engelle: otonom turlarda (varsayılan), "
                        "her zaman, ya da hiç")
    p.add_argument("--no-browser", action="store_true", help="tarayıcıyı açma")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return serve(open_browser=not args.no_browser, port=args.port,
                 autonomy=not args.no_autonomy, tick=args.tick,
                 cooldown=args.cooldown, require_tool=args.require_tool)


if __name__ == "__main__":
    sys.exit(main())







