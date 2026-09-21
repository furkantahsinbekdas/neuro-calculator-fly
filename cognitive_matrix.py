"""
cognitive_matrix.py — the fly's mushroom-body classifier (Phase 9).

The fly has no physical body any more: everything the user does is text. This module is the
piece of *neural* machinery left in the loop — and since the Phase 9 correction it runs on the
REAL wiring, not on a model of it:

    kelime --(karakter 3/4-gram → 685 ALPN indeksi, %11 aktif)-->  PN katmanı   (bizim kodlama)
           --(gerçek FlyWire ALPN→KC matrisi + eşik-tesadüf)---->  5177 KC 0/1  (ÖLÇÜM)
           --(delta kuralı + tanıdıklık kapısı)------------------>  6 kategori + güven

`sniff.circuit()` builds `Wpk` (5177 KC × 685 ALPN) from `flysim.ANN` / `flysim.CONN` — the
FlyWire 783 connectome, edges with ≥3 synapses — and `sniff.kc_code()` is reused *verbatim*: a
Kenyon cell fires when ≥ `coincidence` of its active ALPN partners are active. That is
coincidence detection producing a BOOLEAN sparse code, not a weighted sum + k-WTA; the code
below is deliberately thin because the mechanism must not drift from `sniff.py`.

What is measured and what is ours — kept explicit so nothing over-claims:
  * ÖLÇÜM: the KC code (real `Wpk`, real threshold), the layer sizes, the KC fan-in.
  * BİZİM: (a) turning a word into an ALPN activation pattern — a word has no odour, so the
    input layer is our encoding, (b) the delta-rule readout and its familiarity gate.
`/state` reports this as `"connectome": true` **plus** `"honest_note"`, and the README quotes
the measured confidence numbers rather than adjectives.

Turkish is folded to ASCII first (ş→s, ı→i, ğ→g …), so "şekerli" and "seker" land on
neighbouring codes, and a keyword matches its suffixed forms (Turkish agglutination would
otherwise defeat exact matching).

Public API:
    classify(word)  -> (kategori, güven)      tek etiket + güven (okuma × tanıdıklık)
    scan(text)      -> [hit, ...]             cümledeki sözlük isabetleri (en iyi önce)
    encode(text)    -> np.ndarray             gerçek KC kodu (bool, kc_dim) — seyrek 0/1
    pn_code(text)   -> np.ndarray             ALPN girişi (float32 0/1, pn_dim)
    scores(word)    -> {kategori: skor}       ham MBON okuması (hedef ±1)
    status()        -> /state + README + testler için neyden yapıldığı
    teach(word, kategori) -> dict             TEK örnekli delta adımı + gerileme kontrolü
    undo_last_teach()     -> dict             son öğretimi geri al (yeniden başlatmadan)
    set_effect_alias(kategori, etki) -> dict  canlı kategoriyi bir fabrika etkisine bağla (ya da
                                              "yok" ile bağını çöz) — kalıcı, deftere yazılır
    load_learned()        -> dict             açılışta learned_words.json'u taban 55'in üstüne
                                              yeniden öğretir; .npy'yi sadece karşılaştırır
    save_learned()        -> dict             sözlüğü (JSON) + okumayı (.npy çifti) diske yazar

Faz 11 — canlı öğretim. Fabrika sözlüğü (55 kelime, `VOCAB`) sabittir ve öyle kalır; canlı
öğretilen kelimeler `TAUGHT` içinde ayrı durur, böylece hangi kelimenin eğitildiği hangisinin
sonradan öğretildiği her zaman söylenebilir. Öğretim TÜM okumayı yeniden eğitmez: tek örnekli
delta adımı uygular, sonra **eski sözlüğün tamamını yeniden ölçer** ve gerileme varsa yüksek sesle
söyler (Faz 10'un kuralı: varsayma, ölç). Ayrıntı ve ölçülen sayılar `teach()` docstring'inde.

Faz 11.5 — iki ölçülmüş boşluk kapatıldı, yeni yetenek eklenmedi:
  * **Güvenlik sınırı.** Her `teach()` sonrası ölçülen en düşük güven tabana yaklaşırsa
    (`TEACH_SAFETY_MARGIN`) ya da tek bir adım bir kelimeyi çok sert düşürürse
    (`TEACH_SAFETY_STEP`) `safety_warning` dolar — "GERİLEME ÖLÇÜLDÜ"den güçlü bir uyarı katmanı,
    çözümü (`/öğret-geri`) adıyla söyler. Otomatik geri alma YOKTUR: kararı insan verir.
    Ölçülen: aynı kelimeyi tekrar tekrar çevirmek **birikmez** (0.527 ↔ 0.960 salınır), ama
    *farklı* öğretimler birikir (3 yeni kategori: 0.960 → 0.832 → 0.756 → 0.662; ardından komşu
    bir kelimenin etiketi: `şekerli` 0.748 → 0.352, yani tabanın altı). Delta kuralı tüm satırları
    yazdığı için bu beklenen sonuçtur; sınır bunu *görünür* yapar.
  * **Canlı kategorinin beden etkisi.** `/öğret` ile doğan kategori varsayılan olarak bilgi amaçlı
    kalır (`CATEGORY_EFFECTS`'te satırı yoktur, `CATEGORIES` 6'lı kalır). Kullanıcı isterse
    `set_effect_alias()` ile o kategoriyi mevcut altı etkiden birine bağlar — yeni satır, yeni
    kopya yok; seçim `learned_words.json` içindeki `effect_aliases` alanında saklanır ve açılışta
    geri gelir. Kelimeden/kategori adından etki **tahmin edilmez**.

NumPy + pandas (via flysim) + the 813 MB connectome feather. Aynı kelime her zaman aynı kodu
verir; okuma katmanı sabit sözlükle bir kez eğitilir, rastgelelik yoktur.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import unicodedata

import numpy as np

import sniff                     # circuit() / kc_code(): the real ALPN→KC wiring, reused here

# --------------------------------------------------------------------------- #
# tunables
# --------------------------------------------------------------------------- #
SEED = 20240917          # hash salt base — the only remaining "randomness" is the hashing
NGRAM_SIZES = (3, 4)     # character n-grams = the "odour molecules" of a word
PN_ACTIVE = 75           # ~11% of the 685 ALPNs active per word (sniff.odor: active_frac=0.11)
PN_SPREAD = 8            # PN indices each n-gram fans out to; salt rounds grow until PN_ACTIVE
PN_MAX_ROUNDS = 64       # safety stop for very short words
COINCIDENCE = 3          # sniff.kc_code default: a KC needs ≥3 active ALPN partners
LR_MAX_EPOCHS = 4000     # delta-rule cap (measured: converges long before this)
LR_TOL = 0.02            # stop when every output is within this of its ±1 target
TEMP = 0.40              # softmax temperature over the readout (targets are ±1, so this reads
                         # "the fly is sure" ≈ 1.0 and "no evidence" ≈ 1/6)
CONFIDENCE_FLOOR = 0.40  # below this, classify() is guessing and the caller should not route
MIN_PREFIX = 4           # shortest keyword allowed to match as a prefix (Turkish suffixes)

# --- Phase 11: live teaching -------------------------------------------------- #
TEACH_MAX_STEPS = 8      # cap on single-example delta steps. Measured: 2 updates (3 loop passes)
                         # converge — lr = 1/mean-active makes the *weight* part of one step exact
                         # (lr·‖x‖² = 1), while the bias term adds lr·err, so the first update
                         # overshoots by ≈lr·err and the second lands inside LR_TOL
VOCAB_WARN_SIZE = 100    # warn (never block) past this many words: Phase 10 measured the delta
                         # rule missing its ±1 tolerance at N≈150 and the 0.40 floor at N≈200
DRIFT_WARN = True        # measure the WHOLE old vocabulary after every teach, and say it out loud
_ORIGIN_FACTORY = "factory"
_ORIGIN_TAUGHT = "taught"

# --- Phase 11.5: the drift safety net (detection only — the human decides) ----------------- #
# Phase 11 measured that a teach() writes EVERY label row, so old words can lose confidence.
# These two constants turn that into a warning tier. They are not a fix and not a tuner: the fix
# is /öğret-geri, and nothing here rolls anything back by itself.
TEACH_SAFETY_MARGIN = 0.10   # a word closer than this to CONFIDENCE_FLOOR raises the alert tier.
                             # Justified by measurement: a new category costs the weakest old word
                             # 0.07-0.13, so 0.10 ≈ one teach of headroom before the floor.
TEACH_SAFETY_STEP = 0.30     # a single teach that drops ONE word by this much alerts even while
                             # that word is still far above the floor. Measured: routine teaches
                             # move the weakest word ≤0.13, but relabelling a word whose code has
                             # a near neighbour costs that neighbour 0.396-0.445 in one step — the
                             # shape that later lets a word cross 0.40.

# The fixed vocabulary. Folded at import, so natural Turkish is fine here.
# Categories are the fly's *decisions*, not sentences: game_loop.CATEGORY_EFFECTS maps
# each one onto a vitals delta (or, for a question, onto nothing at all).
CATEGORIES = ("besin", "tehlike", "selam", "açlık", "onay", "red")

CATEGORY_TR = {
    "besin": "yiyecek var",
    "tehlike": "tehdit",
    "selam": "selam",
    "açlık": "açlık sorusu",
    "onay": "onay",
    "red": "ret",
}

VOCAB = {
    # yiyecek VAR: beslenme refleksini tetikler (açlık düşer)
    "besin": ("şeker", "şekerli", "tatlı", "bal", "pekmez", "yemek", "meyve", "üzüm",
              "maya", "kurabiye", "lokum", "nektar", "muz", "elma"),
    # tehdit: looming/kaçış devresi — beden irkilir, can sıkıntısı sıfırlanır
    "tehlike": ("tehlike", "tehlikeli", "tokat", "korku", "korkunç", "kork", "yırtıcı",
                "düşman", "saldırı", "saldır", "öldür", "yaklaşıyor", "gazete", "el",
                "kaç"),
    # sosyal selamlama: vital DEĞİŞMEZ, sadece karşılık verilir
    "selam": ("selam", "selamlar", "merhaba", "merhabalar", "günaydın", "iyi akşamlar",
              "hoş geldin", "hey"),
    # kendi açlığı hakkında SORU: ölçüm anlatılır, vital değişmez
    "açlık": ("acıktın", "acıktım", "açlık", "karnın", "aç", "tok", "doydun"),
    # onay / ret: sosyal, vital değişmez
    "onay": ("evet", "tamam", "olur", "peki", "aynen", "doğru"),
    "red": ("hayır", "olmaz", "istemem", "yok", "asla"),
}

# Where live learning is kept. The JSON is the source of truth (human-readable and editable:
# {"kelime": "kategori"}); the .npy pair is the readout itself, and on startup it is only used to
# *compare* against what replaying the JSON produces — see load_learned().
_HERE = os.path.dirname(os.path.abspath(__file__))
LEARNED_JSON = os.path.join(_HERE, "learned_words.json")
LEARNED_NPY = os.path.join(_HERE, "learned_weights.npy")
LEARNED_BIAS = os.path.join(_HERE, "learned_bias.npy")

# --------------------------------------------------------------------------- #
# Turkish folding + the input layer (projection neurons)
# --------------------------------------------------------------------------- #
def fold(text):
    """Lowercase, drop Turkish diacritics, keep ASCII letters.

    ‟Şekerli” -> ‟sekerli”, ‟AÇLIK” -> ‟aclik”. This is what lets a keyword match its
    suffixed forms and what makes ‟şeker” and ‟seker” the same input.
    """
    t = str(text or "").lower()
    t = (t.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u")
          .replace("ö", "o").replace("ç", "c").replace("â", "a").replace("î", "i")
          .replace("û", "u"))
    t = "".join(ch for ch in unicodedata.normalize("NFKD", t)
                if not unicodedata.combining(ch))
    return t


def tokens(text):
    """Folded word list — punctuation and digits are separators, not content."""
    return re.findall(r"[a-z]+", fold(text))


def _h(s, salt=0):
    """Stable 64-bit hash. NOT Python's ``hash()``: that one is salted per process."""
    return int.from_bytes(hashlib.blake2b(("%d|%s" % (salt, s)).encode("utf-8"),
                                          digest_size=8).digest(), "big")


def _grams(text):
    """Padded char n-grams of every token: ^se, sek, …, er$, ^sek$ (^/$ = word edges).

    Padded so the string edges become real features, so any input length lands in the same
    layer, and so a suffix lengthens a word instead of replacing it.
    """
    out = []
    for word in tokens(text):
        padded = "^" + word + "$"
        for n in NGRAM_SIZES:
            out.extend(padded[i:i + n] for i in range(len(padded) - n + 1))
    return out


# --------------------------------------------------------------------------- #
# the real circuit: sniff.circuit() = FlyWire ALPN -> KC -> MBON
# --------------------------------------------------------------------------- #
_WIRE_LOCK = threading.Lock()
_CIRC = None


def wire():
    """The real olfactory slice, built once and cached: 685 ALPN → 5177 KC → 96 MBON + `Wpk`.

    ``sniff.circuit()`` reads ``flysim.ANN`` (cell classes) and ``flysim.CONN`` (every edge with
    ≥3 synapses) — the same matrices ``sniff.py`` runs its two-odour experiment on, so the
    classifier and that demo can never drift apart. It needs the 813 MB connectome feather
    (`get_data.sh`); when that file is missing ``flysim`` calls ``sys.exit()``, which we turn
    into a `RuntimeError` so a missing download cannot take the whole server down.
    """
    global _CIRC
    if _CIRC is not None:
        return _CIRC
    with _WIRE_LOCK:
        if _CIRC is None:
            try:
                _CIRC = sniff.circuit()
            except SystemExit as e:                     # flysim exits when the data is absent
                raise RuntimeError(
                    "FlyWire konnektomu okunamadı (%s) — sınıflandırıcı gerçek ALPN→KC "
                    "matrisini kuramıyor. Çözüm: flyputer/README.md'deki get_data.sh adımı "
                    "(proofread_connections_783.feather, ~852 MB)." % (e or "veri dosyası yok")
                ) from None
    return _CIRC


def pn_code(text):
    """The ALPN activation pattern of a piece of text: 0/1 over the 685 real projection neurons.

    Our design choice, because a word has no odour: every char n-gram lights a fixed set of PN
    indices (blake2b salts), salt rounds continue until the pattern covers `PN_ACTIVE` distinct
    PNs, and the strongest `PN_ACTIVE` survive. So the input density is the ~11% `sniff.odor()`
    uses for a real odour, and two words that share letters share PNs ("şeker" ⊂ "şekerli"),
    which is what carries Turkish suffixes into the mushroom body.
    """
    n_pn = len(wire()["pn"])
    v = np.zeros(n_pn, dtype=np.float32)
    grams = _grams(text)
    if not grams:
        return v                                       # boş/sayısal girdi: hiçbir PN uçmaz
    round_no = 0
    while round_no < PN_MAX_ROUNDS and int((v > 0).sum()) < PN_ACTIVE:
        for g in grams:
            for s in range(PN_SPREAD):
                v[_h(g, SEED + round_no * PN_SPREAD + s) % n_pn] += 1.0
        round_no += 1
    out = np.zeros(n_pn, dtype=np.float32)
    k = min(PN_ACTIVE, int((v > 0).sum()))
    if k > 0:                                          # k=0 olursa [-0:] tüm diziyi seçerdi
        out[np.argpartition(v, -k)[-k:]] = 1.0
    return out


# --------------------------------------------------------------------------- #
# the Kenyon-cell layer: sniff.kc_code() on the real Wpk — a boolean sparse code
# --------------------------------------------------------------------------- #
def encode(text):
    """The KC code for any text: ``status()["kc_dim"]`` boolean cells, ~1% of them True.

    ``sniff.kc_code`` is called as-is (``(Wpk > 0) @ pn >= coincidence``): the mushroom body
    reads the *count* of co-active ALPN partners per Kenyon cell and keeps the cells that reach
    the coincidence threshold, which is why the code is boolean and genuinely sparse instead of
    a weighted sum that a k-WTA then trims. ~1 ms per call.
    """
    return sniff.kc_code(pn_code(text), coincidence=COINCIDENCE)


# --------------------------------------------------------------------------- #
# readout (MBON): a delta-rule linear map, trained once on the fixed vocabulary
# --------------------------------------------------------------------------- #
_TRAIN_LOCK = threading.RLock()   # reentrant: readout() trains → vocabulary_codes() → lock
_W = None            # (n_categories, kc_dim) float32 — the learned MBON weights
_B = None            # (n_categories,)    float32 — the learned thresholds
_CODES = None        # (n_vocab, kc_dim)  bool    — the vocabulary's KC codes, computed once
_UNIT = None         # the same codes, L2-normalised (familiarity compares against these)
_TRAIN_INFO = {}     # measured training numbers, for status()/README/tests
_MEASURED = None     # cached measured() dict


def vocabulary_codes():
    """KC codes of every word the fly knows (factory + live-taught), in ``_rows()`` order.

    Computed once per vocabulary; a live teach appends its row instead of recomputing this, and
    an undo drops the cache (the row set shrinks only when a *new* word is taken back).
    """
    global _CODES, _UNIT
    if _CODES is None:
        with _TRAIN_LOCK:
            if _CODES is None:
                codes = np.stack([encode(w) for w, _lab, _org in _rows()])
                _CODES = codes
                norm = np.maximum(1e-9, np.linalg.norm(codes, axis=1, keepdims=True))
                _UNIT = codes / norm
    return _CODES


def readout():
    """Train (once) the linear MBON readout with the delta rule on the boolean KC codes.

    Targets are +1 for the word's category and −1 for the others, so a *learned* pattern drives
    its own output to +1 while an unseen pattern — near-orthogonal to every learned code — lands
    near 0. The code stays 0/1; only the step size has to respect LMS stability: a code has ~72
    ones, so ‖x‖² ≈ 72 and lr must stay under ~2/72. We use ``1/mean active`` and a 4000-epoch
    cap (measured: 55/55 in ~2300 epochs, ≈1.5 s, once per process, deterministic).

    Rows follow ``labels()`` (factory decisions, then live-taught categories), so output row *i*
    always belongs to label *i* — that is what lets a live teach append one row without
    retraining. The lock is taken on the fast path too: a live teach swaps in a new matrix under
    the same lock, so a reader can never see W from one generation with B from another.
    """
    global _W, _B
    with _TRAIN_LOCK:
        if _W is not None:
            return _W, _B
        X = vocabulary_codes().astype(np.float32)         # 0/1, exactly as encode() gives it
        lab = labels()
        index = np.array([lab.index(cat) for _w, cat, _o in _rows()])
        want = np.full((len(X), len(lab)), -1.0, dtype=np.float32)
        want[np.arange(len(X)), index] = 1.0
        lr = 1.0 / max(1.0, float(X.sum(axis=1).mean()))
        W = np.zeros((len(lab), X.shape[1]), dtype=np.float32)
        B = np.zeros(len(lab), dtype=np.float32)
        epoch = 0
        for epoch in range(LR_MAX_EPOCHS):
            err = want - (X @ W.T + B)
            if float(np.abs(err).max()) < LR_TOL:
                break
            W += lr * (err.T @ X) / len(X)
            B += lr * err.mean(axis=0)
        got = X @ W.T + B
        _W, _B = W, B
        _TRAIN_INFO.update({
            "epochs": epoch + 1, "lr": round(lr, 5),
            "train_accuracy": round(float((got.argmax(axis=1) == index).mean()), 4),
            "min_correct_score": round(float(got[np.arange(len(X)), index].min()), 3)})
    return _W, _B


def _grow_readout(n):
    """Append zero rows so the readout has one output per label — teaching a new category.

    Called with the readout already trained (``teach()`` trains first): the new row starts at 0,
    i.e. "no evidence", until the incremental step writes its target into it. Returns True when
    the matrix actually grew (so the caller can report the shape change honestly).
    """
    global _W, _B
    readout()
    if n <= len(_W):
        return False
    pad = n - len(_W)
    _W = np.vstack([_W, np.zeros((pad, _W.shape[1]), dtype=np.float32)])
    _B = np.concatenate([_B, np.zeros(pad, dtype=np.float32)])
    return True


def _familiarity(code):
    """How familiar is this KC code? ``cos²`` to the nearest *learned* vocabulary code.

    A vocabulary word matches its own code exactly (1.0); an unrelated word only collides by
    chance (~0.1–0.2 cosine, so ~0.01–0.04 squared, for 72-cell subsets of 5177). Squared, so a
    word must share most of its code with something the fly has actually learned before its
    confidence can clear the floor; a *suffixed* form sits in between (measured "tehlikesiz"
    0.51 → 0.25, "merhabacık" 0.31 → 0.09), which is the honest middle ground. Routing only ever
    classifies fixed-vocabulary words, so in production this gate is exactly 1.0 — it exists so
    that a direct ``classify()`` call on an unknown word cannot invent a decision.
    """
    norm = float(np.linalg.norm(code))
    if norm == 0.0:
        return 0.0
    vocabulary_codes()
    return float(np.max(_UNIT @ (code / norm))) ** 2


def _z(word):
    """Raw MBON readout per label, in ``labels()`` order (targets are ±1).

    Both matrices are read under the training lock: a live teach swaps in a new (or grown) W/B
    pair there, so this never mixes generations.
    """
    code = encode(word).astype(np.float32)
    with _TRAIN_LOCK:
        W, B = readout()
        return W @ code + B


def _softmax(z):
    e = np.exp((np.asarray(z, dtype=np.float64) - np.max(z)) / TEMP)
    return e / e.sum()


def _softmax_rows(z):
    """Row-wise ``_softmax`` for a batch of readouts — the regression check's fast path."""
    z = np.asarray(z, dtype=np.float64)
    e = np.exp((z - z.max(axis=1, keepdims=True)) / TEMP)
    return e / e.sum(axis=1, keepdims=True)


def scores(word):
    """Raw readout scores, ±1 meaning ‟learned / explicitly not this category” (diagnostics)."""
    return {lab: round(float(v), 5) for lab, v in zip(labels(), _z(word))}


def probability(word):
    """The readout's decision distribution (label -> probability, sums to 1).

    ``classify()`` multiplies the winner of this by the familiarity gate; this stays the raw
    readout so a diagnostic can still see *how close* the runner-up was.
    """
    return {lab: round(float(p), 4) for lab, p in zip(labels(), _softmax(_z(word)))}


def classify(word):
    """-> ``(kategori, güven)``. Confidence below ``CONFIDENCE_FLOOR`` = no reliable label.

    Only the real KC code and the trained readout decide this (factory vocabulary, live-taught
    words and live-taught categories alike). The language model receives the result as a *fact*
    about what happened to the fly — never as a suggestion it may overrule (Phase 9 rule D,
    enforced in ``game_loop.classifier_note``).
    """
    code = encode(word)
    probs = _softmax(_z(word))
    i = int(np.argmax(probs))
    return labels()[i], round(float(probs[i]) * _familiarity(code), 4)


# --------------------------------------------------------------------------- #
# routing: which vocabulary words appear in a sentence?
# --------------------------------------------------------------------------- #
def _index():
    """Folded (keyword, category) pairs, longest first: ‟şekerli” beats ‟şeker”."""
    pairs = [(fold(word), cat) for cat in CATEGORIES for word in VOCAB[cat]]
    pairs.sort(key=lambda p: (-len(p[0]), p[0]))
    return tuple(pairs)


INDEX = _index()
VOCAB_SIZE = sum(len(v) for v in VOCAB.values())
# folded keyword -> the way it is actually written in Turkish (for display and prompts)
_ORIG = {fold(word): word for cat in CATEGORIES for word in VOCAB[cat]}

# --------------------------------------------------------------------------- #
# Phase 11: what was *taught* (additive, kept apart from the factory table)
# --------------------------------------------------------------------------- #
# Folded keyword -> {"word": the way the user wrote it, "category": label, "taught": unix time,
# "source": "factory" when it overrides a factory word, "taught" when it is a new word}.
# VOCAB is never mutated, so "was this word part of the factory 55?" always has an answer.
TAUGHT = {}
_FACTORY_FOLDED = {}      # folded factory keyword -> (display word, category)
_LAST_TEACH = None        # one-step undo snapshot (W, B, TAUGHT, aliases) taken before teach()
_LOAD_INFO = None         # what the last load_learned() did, for /state

# --------------------------------------------------------------------------- #
# Phase 11.5: what a *taught category* does to the body
# --------------------------------------------------------------------------- #
# A category invented by /öğret is an extra output row, not new physiology: game_loop.
# CATEGORY_EFFECTS has no row for it, so by default it informs the classifier note and moves
# nothing (Phase 11 behaviour — and it stays the default). The user may instead point it at ONE
# of the six factory effects — teach "korku" under a new category and say "treat it like
# tehlike". That choice is a mapping, not a new effect row: CATEGORY_EFFECTS stays 1:1 with
# CATEGORIES (both self-tests assert it), and nothing is ever guessed from the word or the
# category name. Persisted as ``"effect_aliases"`` in learned_words.json.
_EFFECT_ALIAS = {}        # taught category -> the factory category whose effect it borrows
_ALIAS_NONE = ("yok", "hicbiri", "hiçbiri", "none", "-", "")   # "leave it effect-less"


def effect_alias(category):
    """The factory category this live-taught category borrows its body effect from (or None)."""
    return _EFFECT_ALIAS.get(str(category if category is not None else "").strip())


def effect_aliases():
    """``{taught category: factory category}`` — only for categories that still exist."""
    return {c: a for c, a in _EFFECT_ALIAS.items() if is_taught_category(c)}


def set_effect_alias(category, alias, *, save=True):
    """Point a live-taught category at one of the six factory effects, or clear that mapping.

    ``alias`` may be ``None``/``"yok"``/``"-"`` — that means "informational only", i.e. exactly
    Phase 11's behaviour, and it is also the state a new category starts in. Refuses, with a
    reason, when the category is not live-taught (the factory six already have their own row) or
    when the alias is not one of the factory six (``CATEGORY_EFFECTS`` is the only effect table;
    an alias never adds or copies a row). Returns a small dict, ``ok: False`` for a refusal.
    """
    cat = resolve_category(category)
    name = str(category if category is not None else "")
    if cat is None or not is_taught_category(cat):
        return {"ok": False, "category": cat, "alias": None,
                "error": "\"%s\" canlı öğretilmiş bir kategori değil — fabrika "
                         "kategorilerinin etki satırı zaten var" % name}
    plain = str(alias if alias is not None else "").strip().lower()
    if alias is None or plain in _ALIAS_NONE:
        previous = _EFFECT_ALIAS.pop(cat, None)
        res = {"ok": True, "category": cat, "alias": None, "previous": previous,
               "cleared": previous is not None, "why": "bilgi amaçlı: bedeni kıpırdatmaz"}
    else:
        want = resolve_category(alias)
        if want is None or want not in CATEGORIES:
            return {"ok": False, "category": cat, "alias": None,
                    "error": "etki \"%s\" fabrika kategorilerinden biri olmalı: %s"
                             % (str(alias), ", ".join(CATEGORIES))}
        previous = _EFFECT_ALIAS.get(cat)
        _EFFECT_ALIAS[cat] = want
        res = {"ok": True, "category": cat, "alias": want, "previous": previous,
               "cleared": False, "why": "%s gibi davranır (aynı etki satırı, yeni kopya yok)"
                                        % want}
    if save:
        res["saved"] = save_learned()
    return res


def _remember_factory():
    """Remember the factory keywords so an *override* can be told from a brand-new word."""
    _FACTORY_FOLDED.clear()
    for _cat in CATEGORIES:
        for _w in VOCAB[_cat]:
            _FACTORY_FOLDED[fold(_w)] = (_w, _cat)


_remember_factory()


def labels():
    """The readout's live output labels: the factory decisions + any live-taught category.

    ``CATEGORIES`` stays the frozen 6-decision factory table on purpose — ``game_loop.
    CATEGORY_EFFECTS`` is 1:1 with it and both self-tests assert that. A category taught at
    runtime is an extra *output row* of the readout, not a new physiology: the effect table has
    no row for it, so the body does not move and the note says so explicitly.
    """
    out = list(CATEGORIES)
    for _rec in TAUGHT.values():
        if _rec["category"] not in out:
            out.append(_rec["category"])
    return tuple(out)


def vocab_size():
    """Everything the fly can currently classify: factory 55 + words taught live."""
    return VOCAB_SIZE + sum(1 for _kw in TAUGHT if _kw not in _FACTORY_FOLDED)


def taught_words():
    """``{display word: category}`` in teach order — the additive, non-factory part."""
    return {_rec["word"]: _rec["category"] for _rec in TAUGHT.values()}


def current_category(word):
    """``(category, origin)`` for a word the fly knows, else ``None``.

    Used to catch a silent relabel: ``origin`` is ``"factory"`` for the 55 or for an override of
    one of them, ``"taught"`` for a word that only exists because it was taught live.
    """
    _kw = fold(word)
    _rec = TAUGHT.get(_kw)
    if _rec:
        return _rec["category"], _rec["source"]
    _hit = _FACTORY_FOLDED.get(_kw)
    return (_hit[1], _ORIGIN_FACTORY) if _hit else None


def is_taught_category(category):
    """True when this decision label exists only because it was taught live."""
    _cat = str(category if category is not None else "")
    return _cat in labels() and _cat not in CATEGORIES


def resolve_category(raw):
    """Map a typed category onto a known label, or name the new label it would create.

    Exact match first, then a folded match against the labels we already have (so a user typing
    ``Açlık`` lands on the factory ``açlık`` instead of founding a second hunger), and only then
    a brand-new label from the folded text. ``None`` means "not a usable category name" — the
    caller then answers with the usage line instead of inventing junk categories.
    """
    _txt = str(raw if raw is not None else "").strip()
    if not _txt:
        return None
    _known = labels()
    if _txt in _known:
        return _txt
    _folded = fold(_txt)
    for _lab in _known:
        if fold(_lab) == _folded:
            return _lab
    return _folded if re.fullmatch(r"[a-z][a-z0-9_]{1,23}", _folded) else None


def _rows():
    """Every word the readout is trained on, in ``vocabulary_codes()`` row order.

    Factory words first — an override changes the *label* of the factory row and never adds a
    second row for the same code — then live-taught words in teach order. ``_CODES`` is derived
    from this, so a repointed ``CATEGORIES``/``VOCAB`` (capacity_benchmark.py) stays consistent
    as long as ``_CODES`` is reset with them.
    """
    out = []
    for cat in CATEGORIES:
        for w in VOCAB[cat]:
            _rec = TAUGHT.get(fold(w))
            out.append((w, _rec["category"] if _rec else cat, _ORIGIN_FACTORY))
    for _kw, _rec in TAUGHT.items():
        if _kw not in _FACTORY_FOLDED:
            out.append((_rec["word"], _rec["category"], _ORIGIN_TAUGHT))
    return out


def _effective_category(keyword, factory_category):
    """The category a matched keyword routes to: a live override wins over the factory table."""
    _rec = TAUGHT.get(keyword)
    return _rec["category"] if _rec else factory_category


def _display_word(keyword):
    """How a matched keyword is written in Turkish (taught words carry their own spelling)."""
    _rec = TAUGHT.get(keyword)
    return _rec["word"] if _rec else _ORIG.get(keyword, keyword)


def _taught_index():
    """Extra routing keywords from live teaching, longest first — the same shape as ``INDEX``."""
    return tuple(sorted(((_kw, _rec["category"]) for _kw, _rec in TAUGHT.items()
                         if _kw not in _FACTORY_FOLDED), key=lambda p: (-len(p[0]), p[0])))


def keyword_matches(token, keyword):
    """Whole-word match, plus suffix matching for keywords >= ``MIN_PREFIX``.

    Turkish glues its case/possessive endings onto the stem (şeker → şeker-li, şeker-im),
    so exact matching alone would miss most real sentences.
    """
    if token == keyword:
        return True
    return len(keyword) >= MIN_PREFIX and token.startswith(keyword)


def scan(text):
    """Vocabulary hits in a sentence, most confident first.

    Each hit is ``{"word", "category", "confidence", "token", "scores", "classifier", "origin"}``:
    the vocabulary word, the category it routes to, the KC classifier's confidence for it, and
    what the KC readout *on its own* would have said (``classifier``). An empty list means
    ‟nothing in the vocabulary” — the caller then falls back to free chat (Phase 9 rule E). Note
    what is being classified: the *vocabulary* word, not the sentence — the word the user actually
    typed only selects which learned pattern the mushroom body is asked about.

    Phase 11: live-taught words are routable immediately (they are extra keywords) and a taught
    *override* of a factory word wins over the factory table — that is the whole point of asking
    for confirmation before relabelling, not of hiding the change.
    """
    toks = tokens(text)
    folded = " " + " ".join(toks) + " "
    hits, seen = [], set()
    for keyword, cat in INDEX + _taught_index():
        if keyword in seen:
            continue
        token = None
        if " " in keyword:
            if keyword in folded:
                token = keyword
        else:
            for t in toks:
                if keyword_matches(t, keyword):
                    token = t
                    break
        if token is None:
            continue
        seen.add(keyword)
        cat = _effective_category(keyword, cat)
        word = _display_word(keyword)
        kc_label, conf = classify(word)
        hits.append({"word": word, "keyword": keyword, "category": cat,
                     "confidence": conf, "token": token, "scores": scores(word),
                     "classifier": kc_label, "agrees": kc_label == cat,
                     # "taught" = the routing entry (or its label) came from live teaching
                     "origin": _ORIGIN_TAUGHT if keyword in TAUGHT else _ORIGIN_FACTORY})
    hits.sort(key=lambda h: (-h["confidence"], h["word"]))
    return hits


# --------------------------------------------------------------------------- #
# Phase 11: live teaching — one delta step, then measure the whole old vocabulary
# --------------------------------------------------------------------------- #
def _sync_codes():
    """Make sure the cached codes match ``_rows()``; rebuild only when the row set really moved."""
    global _CODES, _UNIT
    if _CODES is None or len(_CODES) != len(_rows()):
        _CODES = _UNIT = None
    return vocabulary_codes()


def _summarise(table):
    """``{"n", "accuracy", "min_confidence", "mean_confidence"}`` over ``vocabulary_table()``."""
    confs = [r["confidence"] for r in table]
    right = sum(1 for r in table if r["label"] == r["expected"])
    return {"n": len(table),
            "accuracy": round(right / len(table), 4) if table else 0.0,
            "min_confidence": round(min(confs), 4) if confs else 0.0,
            "mean_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0}


def vocabulary_table(W=None, B=None):
    """``[{word, expected, origin, label, confidence}, ...]`` for every word the fly knows.

    This is the same math as ``classify()`` (softmax over the readout, times the familiarity gate)
    done as ONE matmul over the cached codes — the regression check after a live teach then costs
    milliseconds instead of one ``encode()`` per word, which is what makes it affordable to run on
    every teach *and* to replay a whole learned file at startup. The self-test asserts it agrees
    with ``classify()`` word for word.

    A vocabulary row is always its own nearest learned code, so ``_familiarity()`` would return
    exactly 1.0 for it and the confidence column is the raw softmax winner — the same value
    ``classify()`` reports for a known word.

    ``W``/``B`` can be passed explicitly, which is how a caller measures a matrix it has not
    installed yet (the self-test uses it for a before/after pair without touching module state).
    """
    readout()
    W = _W if W is None else np.asarray(W, dtype=np.float32)
    B = _B if B is None else np.asarray(B, dtype=np.float32)
    lab = labels()
    codes = _sync_codes()
    probs = _softmax_rows(codes.astype(np.float32) @ W.T + B)
    best = probs.argmax(axis=1)
    return [{"word": word, "expected": expect, "origin": origin,
             "label": lab[int(best[k])], "confidence": round(float(probs[k, best[k]]), 4)}
            for k, (word, expect, origin) in enumerate(_rows())]


def set_learned_paths(json_path=None, weights_path=None, bias_path=None):
    """Point the learned-word store somewhere else (the self-tests use a temp directory).

    Returns the same cheap status dict as ``learned_status()`` so a test can record what the
    default paths were before it moved them.
    """
    global LEARNED_JSON, LEARNED_NPY, LEARNED_BIAS
    if json_path:
        LEARNED_JSON = os.path.abspath(json_path)
    if weights_path:
        LEARNED_NPY = os.path.abspath(weights_path)
    if bias_path:
        LEARNED_BIAS = os.path.abspath(bias_path)
    return learned_status()


def learned_status():
    """Cheap facts about the store for ``/state`` — filename checks only, never a read."""
    return {"file": os.path.basename(LEARNED_JSON), "exists": os.path.exists(LEARNED_JSON),
            "weights_file": os.path.basename(LEARNED_NPY),
            "weights_exist": os.path.exists(LEARNED_NPY),
            "taught": len(TAUGHT),
            "new_words": sum(1 for _kw in TAUGHT if _kw not in _FACTORY_FOLDED),
            "overrides": sum(1 for _kw in TAUGHT if _kw in _FACTORY_FOLDED),
            "can_undo": _LAST_TEACH is not None,
            "vocab_warn_size": VOCAB_WARN_SIZE,
            "last_load": (dict(_LOAD_INFO) if _LOAD_INFO else None)}


def teach(word, category, *, save=True, check=True, source="live"):
    """Teach ONE word (or relabel one) with a single-example delta-rule step — no full retrain.

    What happens, in order:

    1. ``encode(word)`` — the real KC code, exactly what the classifier would see.
    2. If the category is new, the readout **grows one row** starting at 0 (no restart, no
       architecture change: row *i* belongs to ``labels()[i]``).
    3. ONE delta step loop: production's own rule at batch size 1 (``W += lr·err⊗x``,
       ``B += lr·err``, ``lr = 1/mean active`` — the same formula ``readout()`` uses, with the
       single example as its batch). ``lr·‖x‖² = 1`` makes the *weight* part of one step exact
       (Newton for one sample) while the bias term adds ``lr·err`` on top, so the first update
       overshoots by ≈``lr·err``: **measured 2 updates / 3 loop passes** to fall inside
       ``LR_TOL``. ``TEACH_MAX_STEPS`` is the safety cap, not the plan; both counts are reported.
    4. **The whole old vocabulary is re-measured before and after** (``vocabulary_table()``, one
       matmul) and the difference is in the return value. The delta rule writes every label row —
       the error vector spans all of them — so "old words are safe because the codes are
       near-orthogonal" is an *assumption*, and Phase 10's rule is that assumptions get measured.
    5. **Phase 11.5: a stronger tier on top of that measurement.** Reusing the same table (no
       second measurement), two things raise ``safety_warning``:
         * a word is closer to ``CONFIDENCE_FLOOR`` than ``TEACH_SAFETY_MARGIN`` (measured
           justification: one teach costs the weakest old word 0.07-0.13, so 0.10 ≈ one teach of
           headroom), or
         * this single teach moved ONE word down by ``TEACH_SAFETY_STEP`` or more while it is
           still above the floor (measured: routine teaches move the weakest word ≤0.13, but
           relabelling a word whose code has a near neighbour costs that neighbour 0.396-0.445 —
           the shape that lets a following teach cross the floor).
       Detection only: nothing is rolled back. The warning names ``/öğret-geri`` as the fix.
    6. ``save=True`` writes ``learned_words.json`` plus the ``.npy`` weight/bias pair.

    Measured on the real connectome (55 words, this machine):
      * repeating the *same* relabel does **not** compound — it oscillates
        (``şeker`` besin↔tehlike: min confidence 0.527 ↔ 0.960, forever, because each flip undoes
        the neighbour damage the previous one did), and nothing crossed 0.40;
      * *different* teaches do compound: three new categories 0.960 → 0.832 → 0.756 → 0.662, and
        then relabelling ``şeker`` took ``şekerli`` from 0.748 to 0.352 — below the floor. That is
        the sequence ``safety_warning`` exists for.
      * scaling ``lr`` down was measured and **not** implemented: for a new category the drift is
        structural (min confidence 0.832 → 0.833 at lr×0.5, → 0.840 at lr×0.25 with 8 updates),
        and for a relabel the total displacement of the other rows telescopes to the same value
        (max|ΔW| 0.01681 at lr×1 vs 0.01654 at lr×0.5 with 7× the updates) — apparent gains at
        small ``lr`` are just the target row not converging inside ``TEACH_MAX_STEPS``
        (its own confidence 0.961 → 0.819 at lr×0.1). A knob that buys old-word confidence by
        shipping an incomplete teach would be a worse trade than saying it out loud.

    Returns ``before``/``after`` summaries over the *old* words only (the taught word is excluded,
    or a deliberate relabel would be reported as drift), plus ``lost`` (old words whose label
    moved), ``dropped`` (old words that fell below ``CONFIDENCE_FLOOR``), ``target`` (the taught
    word's own row), ``installed`` (did it actually clear the floor), ``warning`` (None or the
    sentence to show the user), ``size_warning`` (Task 4, past ``VOCAB_WARN_SIZE`` words),
    ``safety``/``safety_warning`` (Phase 11.5: the measured drift safety net, see step 5) and
    ``effect_alias`` (the factory effect this category borrows, if the user mapped one).

    Raises ``ValueError`` when the request itself is unusable (bad word or category name) and
    ``RuntimeError`` when the connectome is missing — the caller answers with the message.
    """
    global _W, _B, _CODES, _UNIT, _MEASURED, _LAST_TEACH
    display = " ".join(str(word if word is not None else "").split())
    keyword = fold(display)
    if not re.fullmatch(r"[a-z0-9_\- ]{2,32}", keyword) or len(re.sub(r"[^a-z]", "", keyword)) < 2:
        raise ValueError("kelime harf içermeli (2-32 karakter, rakam/boşluk olabilir): \"%s\""
                         % display)
    label = resolve_category(category)
    if label is None:
        raise ValueError("kategori adı kullanılamaz: \"%s\" (2-24 harf/rakam)"
                         % str(category if category is not None else ""))

    with _TRAIN_LOCK:
        readout()                                    # make sure the base 55 are trained first
        snapshot = {"W": _W.copy(), "B": _B.copy(),
                    "taught": {k: dict(v) for k, v in TAUGHT.items()},
                    "aliases": dict(_EFFECT_ALIAS),
                    "labels": labels()}
        before_table = vocabulary_table()
        keep = {fold(r["word"]): r for r in before_table if fold(r["word"]) != keyword}
        existed = current_category(display)
        overwrote = existed[0] if existed and existed[0] != label else None
        reattached = bool(existed and existed[0] == label)
        new_category = label not in snapshot["labels"]

        # register FIRST: labels() is derived from TAUGHT, so a brand-new category only exists
        # (and can only get a row) once the word that uses it is on the books
        TAUGHT[keyword] = {"word": display, "category": label, "taught": round(time.time(), 3),
                           "source": _ORIGIN_FACTORY if keyword in _FACTORY_FOLDED
                                     else _ORIGIN_TAUGHT}
        grown = _grow_readout(len(labels()))

        # ---- the incremental update: one example, one (or a few) delta steps ---------------
        code = encode(display)
        X = code.astype(np.float32)
        lab = labels()
        want = np.full(len(lab), -1.0, dtype=np.float32)
        want[lab.index(label)] = 1.0
        lr = 1.0 / max(1.0, float(X.sum()))
        steps = updates = 0
        while steps < TEACH_MAX_STEPS:
            err = want - (_W @ X + _B)
            steps += 1
            if float(np.abs(err).max()) < LR_TOL:
                break
            _W += lr * np.outer(err, X)              # production's rule, batch of one
            _B += lr * err
            updates += 1

        # ---- keep the code cache in step without re-encoding the whole vocabulary ----------
        if len(_CODES) != len(_rows()):              # a brand-new word: append exactly one row
            if len(_rows()) - len(_CODES) == 1:
                _CODES = np.vstack([_CODES, code[None, :]])
                _UNIT = np.vstack([_UNIT,
                                   (code / max(1e-9, float(np.linalg.norm(code))))[None, :]])
            else:                                    # cannot happen, but never guess: rebuild
                _CODES = _UNIT = None
        _MEASURED = None
        _TRAIN_INFO["live_updates"] = int(_TRAIN_INFO.get("live_updates", 0)) + 1

        # ---- regression check: the whole old vocabulary, before vs after --------------------
        after_table = vocabulary_table()
        after_old = [r for r in after_table if fold(r["word"]) in keep]
        lost, dropped = [], []
        if check:
            for r in after_old:
                ref = keep[fold(r["word"])]
                if r["label"] != ref["expected"]:
                    lost.append((r["word"], ref["expected"], r["label"]))
                if ref["confidence"] >= CONFIDENCE_FLOOR > r["confidence"]:
                    dropped.append((r["word"], ref["confidence"], r["confidence"]))
        target = next(r for r in after_table if fold(r["word"]) == keyword)
        installed = target["confidence"] >= CONFIDENCE_FLOOR

        warning = None
        if check and (lost or dropped or not installed):
            bits = []
            if lost:
                bits.append("%d kelimenin etiketi değişti (%s)"
                            % (len(lost), ", ".join("%s: %s→%s" % t for t in lost[:3])))
            if dropped:
                bits.append("%d kelimenin güveni %.2f tabanının altına düştü (%s)"
                            % (len(dropped), CONFIDENCE_FLOOR,
                               ", ".join("%s: %.2f→%.2f" % t for t in dropped[:3])))
            if not installed:
                bits.append("yeni kelime eşiği geçemedi (\"%s\" %.2f < %.2f)"
                            % (display, target["confidence"], CONFIDENCE_FLOOR))
            warning = ("GERİLEME ÖLÇÜLDÜ — " + "; ".join(bits) + ". Değişiklik geri alınmadı; "
                       "karar senin: /öğret-geri")

        # ---- Phase 11.5: the stronger tier — a word is close to the floor, or just took a
        # ---- big single-step hit. Detection only: nothing is rolled back automatically.
        safety = safety_warning = None
        if check:
            limit = CONFIDENCE_FLOOR + TEACH_SAFETY_MARGIN
            near = sorted([(r["word"], r["expected"], r["confidence"]) for r in after_table
                           if r["confidence"] < limit], key=lambda t: t[2])
            before_by = {fold(r["word"]): r for r in before_table}
            hits = []
            for r in after_table:                    # a deliberate relabel is covered by
                ref = before_by.get(fold(r["word"]))  # ``installed``: only the OTHER words here
                if ref is None or fold(r["word"]) == keyword:
                    continue
                drop = ref["confidence"] - r["confidence"]
                if drop >= TEACH_SAFETY_STEP:
                    hits.append((r["word"], ref["confidence"], r["confidence"], round(drop, 4)))
            hits.sort(key=lambda t: -t[3])
            if near or hits:
                safety = {"threshold": round(limit, 4), "margin": TEACH_SAFETY_MARGIN,
                          "step_limit": TEACH_SAFETY_STEP,
                          "min_confidence": round(min(r["confidence"] for r in after_table), 4),
                          "near": near, "hits": hits}
                bits = []
                if near:
                    w, cat, c = near[0]
                    bits.append("tabana yakın: \"%s\" (%s) %.3f — taban %.2f + marj %.2f "
                                "= %.2f; en düşük güven %.3f"
                                % (w, cat, c, CONFIDENCE_FLOOR, TEACH_SAFETY_MARGIN, limit,
                                   safety["min_confidence"]))
                if hits:
                    w, b, a, d = hits[0]
                    bits.append("tek adımda büyük düşüş: \"%s\" %.3f → %.3f (−%.3f; eşik %.2f)"
                                % (w, b, a, d, TEACH_SAFETY_STEP))
                safety_warning = ("⛔ GÜVENLİK SINIRI — " + "; ".join(bits) + ". Bu, \"GERİLEME "
                                  "ÖLÇÜLDÜ\"den daha güçlü bir uyarıdır. Otomatik geri alma YOK, "
                                  "karar senin: /öğret-geri")
        size_warning = None
        if vocab_size() > VOCAB_WARN_SIZE:
            size_warning = ("sözlük %d kelimeye çıktı — Phase 10 ölçümü: 150-200 civarında delta "
                            "kuralı ±1 toleransını kaçırıyor ve 0.40 güven tabanı zorlanıyor"
                            % vocab_size())

        result = {
            "ok": True, "word": display, "keyword": keyword, "category": label,
            "origin": TAUGHT[keyword]["source"], "created_category": new_category,
            "overwrote": overwrote, "reattached": reattached, "source": source,
            "steps": steps, "updates": updates, "lr": round(lr, 5),
            "readout_shape": [int(_W.shape[0]), int(_W.shape[1])], "grew_readout": bool(grown),
            "target": target, "installed": installed,
            "before": _summarise(list(keep.values())), "after": _summarise(after_old),
            "lost": lost, "dropped": dropped,
            "warning": warning, "size_warning": size_warning,
            "safety": safety, "safety_warning": safety_warning,
            "effect_alias": effect_alias(label),
            "vocabulary": vocab_size(), "factory_vocabulary": VOCAB_SIZE,
            "taught_total": len(TAUGHT), "labels": list(lab),
        }
        _LAST_TEACH = dict(snapshot, result=dict(result))
    if save:
        result["saved"] = save_learned()
    return result


def undo_last_teach():
    """Put the readout and the registry back exactly as they were before the last ``teach()``.

    The single-example step writes *every* label row (the error vector spans all of them), so a
    regression is always possible in principle. This is the way back — no restart, no retraining:
    the W/B pair and the taught registry are restored from the snapshot ``teach()`` kept, the code
    cache is rebuilt and the store is saved again so disk matches memory. Returns a summary, or
    ``{"ok": False, "error": ...}`` when there is nothing to undo.
    """
    global _W, _B, _CODES, _UNIT, _MEASURED, _LAST_TEACH
    if not _LAST_TEACH:
        return {"ok": False, "error": "geri alınacak öğretim yok"}
    snap = _LAST_TEACH
    with _TRAIN_LOCK:
        _W = snap["W"].copy()
        _B = snap["B"].copy()
        TAUGHT.clear()
        TAUGHT.update({k: dict(v) for k, v in snap["taught"].items()})
        # a category the undone teach invented may have borrowed an effect: that mapping goes
        # with it, or /öğret would list an alias for a category that no longer exists
        _EFFECT_ALIAS.clear()
        _EFFECT_ALIAS.update(snap.get("aliases") or {})
        _CODES = _UNIT = None                        # the row set may have shrunk
        _MEASURED = None
        _TRAIN_INFO["live_updates"] = max(0, int(_TRAIN_INFO.get("live_updates", 1)) - 1)
        _LAST_TEACH = None
        table = vocabulary_table()
        result = {"ok": True, "undone": snap["result"]["word"],
                  "category": snap["result"]["category"],
                  "was_new_word": snap["result"]["origin"] == _ORIGIN_TAUGHT,
                  "vocabulary": vocab_size(), "taught_total": len(TAUGHT),
                  "labels": list(labels()), "restored": _summarise(table),
                  "effect_aliases": effect_aliases()}
    result["saved"] = save_learned()
    return result


# --------------------------------------------------------------------------- #
# Phase 11: persistence — learned_words.json is the truth, the .npy pair is the readout
# --------------------------------------------------------------------------- #
def _write_json(path, obj):
    """Write JSON through a temp file + rename, so a crash cannot leave half a vocabulary."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    os.replace(tmp, path)


def save_learned(json_path=None, weights_path=None, bias_path=None):
    """Persist the taught words (JSON) and the current readout (``.npy`` weight + bias pair).

    The JSON is the human-readable/editable part — ``{"taught": {"elma": "besin"}}`` in teach
    order — and it is the source of truth on the next start. The ``.npy`` files carry the matrix
    itself (JSON cannot hold 6 × 5177 floats cleanly) and put the readout on disk as required;
    ``load_learned()`` loads them only to *compare* against the replay.
    """
    readout()
    jpath = json_path or LEARNED_JSON
    wpath = weights_path or LEARNED_NPY
    bpath = bias_path or LEARNED_BIAS
    payload = {
        "version": 1,
        "note": "Canlı öğretilen kelimeler: {\"kelime\": \"kategori\"} — elle düzenlenebilir. "
                "Fabrika sözlüğü (55 kelime) koda gömülüdür ve burada tutulmaz; açılışta bu "
                "dosya taban eğitimin üstüne yeniden öğretilir. \"effect_aliases\" canlı "
                "kategorilerin ödünç aldığı beden etkisini söyler (boş = sadece bilgi, "
                "Phase 11 davranışı).",
        "base_vocabulary": VOCAB_SIZE,
        "vocabulary": vocab_size(),
        "categories": list(labels()),
        "taught": taught_words(),
        "effect_aliases": effect_aliases(),
    }
    _write_json(jpath, payload)
    tmp_w, tmp_b = wpath + ".tmp.npy", bpath + ".tmp.npy"
    np.save(tmp_w, _W)
    np.save(tmp_b, _B)
    os.replace(tmp_w, wpath)
    os.replace(tmp_b, bpath)
    return {"json": os.path.basename(jpath), "weights": os.path.basename(wpath),
            "bias": os.path.basename(bpath), "taught": len(TAUGHT),
            "vocabulary": vocab_size(), "shape": [int(_W.shape[0]), int(_W.shape[1])]}
def _compare_weights(weights_path=None, bias_path=None):
    """How far is the readout we just rebuilt from the matrix saved next to the JSON?"""
    wpath = weights_path or LEARNED_NPY
    bpath = bias_path or LEARNED_BIAS
    out = {"file": os.path.basename(wpath), "exists": os.path.exists(wpath)}
    if not out["exists"]:
        return out
    try:
        saved = np.load(wpath)
        saved_b = np.load(bpath) if os.path.exists(bpath) else None
    except (OSError, ValueError) as e:          # a corrupt/foreign file must not kill startup
        out["error"] = "%s: %s" % (type(e).__name__, e)
        return out
    if saved.shape != _W.shape:
        out.update({"match": False, "shape_saved": list(saved.shape),
                    "shape_live": [int(_W.shape[0]), int(_W.shape[1])]})
        return out
    delta = float(np.abs(saved - _W).max())
    if saved_b is not None and saved_b.shape == _B.shape:
        delta = max(delta, float(np.abs(saved_b - _B).max()))
    out.update({"match": delta <= 1e-5, "max_delta": delta})
    return out


def load_learned(json_path=None, weights_path=None, bias_path=None):
    """Replay the taught words on top of the factory training — the startup path.

    Why replay instead of "just load the .npy": ``learned_words.json`` is meant to be hand-edited,
    and a saved matrix cannot know that a word was added or corrected in the file — it would
    silently contradict it. So the JSON is the source of truth, the same incremental step the live
    teach uses runs at every start (a stale matrix can therefore never mask a broken update), and
    the ``.npy`` pair is read only for the comparison reported in ``weights``.

    Never raises for a missing or corrupt file: it returns ``{"loaded": 0, "error": ...}`` and the
    server keeps running on the factory vocabulary (the Phase 9 rule for a missing connectome).
    """
    global _LOAD_INFO
    jpath = json_path or LEARNED_JSON
    wpath = weights_path or LEARNED_NPY
    bpath = bias_path or LEARNED_BIAS
    out = {"file": os.path.basename(jpath), "loaded": 0, "words": {}, "skipped": [], "error": None,
           "seconds": 0.0, "vocabulary": vocab_size(), "aliases": {}}
    if not os.path.exists(jpath):
        if os.path.exists(wpath):
            out["error"] = ("%s yok ama %s var — ağırlıklar hangi kelimeye ait olduğunu "
                            "söylemiyor, yeniden öğretim yapılmadı"
                            % (os.path.basename(jpath), os.path.basename(wpath)))
        _LOAD_INFO = dict(out)
        return out
    try:
        with open(jpath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        out["error"] = "okunamadı: %s" % e
        _LOAD_INFO = dict(out)
        return out
    words = data.get("taught") if isinstance(data, dict) else None
    if not isinstance(words, dict) and isinstance(data, dict) and data \
            and not (set(data) & {"version", "note", "taught"}) \
            and all(isinstance(v, str) for v in data.values()):
        words = data        # a hand-written bare {"kelime": "kategori"} file is fine too
                            # (a dict-valued key like "effect_aliases" is not a bare word map)
    if not isinstance(words, dict):
        out["error"] = "beklenen biçim: {\"taught\": {\"kelime\": \"kategori\"}}"
        _LOAD_INFO = dict(out)
        return out
    t0 = time.time()
    for w, cat in words.items():
        label = resolve_category(cat)
        if label is None:
            out["skipped"].append("%s→%s (kategori adı geçersiz)" % (w, cat))
            continue
        try:
            res = teach(w, label, save=False, check=False, source="file")
        except ValueError as e:
            out["skipped"].append("%s: %s" % (w, e))
            continue
        out["loaded"] += 1
        out["words"][res["word"]] = label
    # Phase 11.5: the effect mappings come back too — after the words, because a category only
    # exists once a taught word uses it (nothing is guessed if the file says nothing)
    aliases = data.get("effect_aliases") if isinstance(data, dict) else None
    if isinstance(aliases, dict):
        for cat, al in aliases.items():
            res = set_effect_alias(cat, al, save=False)
            if res["ok"]:
                out["aliases"][res["category"]] = res["alias"]
            elif str(al if al is not None else "").strip().lower() not in _ALIAS_NONE:
                out["skipped"].append("%s→%s (%s)" % (cat, al, res["error"]))
    out["seconds"] = round(time.time() - t0, 2)
    out["vocabulary"] = vocab_size()
    out["taught_total"] = len(TAUGHT)
    table = vocabulary_table()
    out["regression"] = _summarise(table)               # the whole live vocabulary, measured
    out["lost"] = [(r["word"], r["expected"], r["label"]) for r in table
                   if r["label"] != r["expected"]]
    out["weights"] = _compare_weights(wpath, bpath)
    _LOAD_INFO = dict(out)
    return out


# --------------------------------------------------------------------------- #
# measured numbers (status / README / tests) — computed once, then free
# --------------------------------------------------------------------------- #
def measured():
    """Everything that can be *measured* about this classifier, once per process.
    building (`server.py` warms this at startup) waits for that one computation instead of
    starting a second one — after the first call it is a dict lookup.
    """
    global _MEASURED
    if _MEASURED is not None:
        return _MEASURED
    with _TRAIN_LOCK:
        if _MEASURED is not None:
            return _MEASURED
        C = wire()
        readout()
        codes = vocabulary_codes()
        confs = [classify(w) for cat in CATEGORIES for w in VOCAB[cat]]
        n_factory = sum(len(v) for v in VOCAB.values())
        factory = codes[:n_factory]                     # Phase 11: taught rows are appended
        active = factory.sum(axis=1)
        live = vocabulary_table()
        taught_rows = [r for r in live if r["origin"] == _ORIGIN_TAUGHT]
        live_confs = [r["confidence"] for r in live]
        _MEASURED = {
            "pn_dim": len(C["pn"]), "kc_dim": len(C["kc"]), "mbon_dim": len(C["mb"]),
            "kc_active": int(round(float(active.mean()))),
            "kc_active_range": [int(active.min()), int(active.max())],
            "kc_density": round(float(factory.mean()), 5),
            "train_accuracy": _TRAIN_INFO.get("train_accuracy", 0.0),
            "epochs": _TRAIN_INFO.get("epochs"), "lr": _TRAIN_INFO.get("lr"),
            "vocab_confidence": {
                "min": round(min(c for _, c in confs), 4),
                "mean": round(sum(c for _, c in confs) / len(confs), 4),
                "max": round(max(c for _, c in confs), 4)},
            # Phase 11: the live vocabulary is the factory 55 plus everything taught since, and
            # its accuracy is *measured* on every teach — this is the number to quote after one.
            "factory_vocabulary": n_factory,
            "taught_vocabulary": len(taught_rows),
            "vocabulary_live": vocab_size(),
            "live_accuracy": _summarise(live)["accuracy"],
            "taught_accuracy": _summarise(taught_rows)["accuracy"] if taught_rows else None,
            "live_confidence": {"min": round(min(live_confs), 4),
                                "mean": round(sum(live_confs) / len(live_confs), 4),
                                "max": round(max(live_confs), 4)},
            "live_updates": int(_TRAIN_INFO.get("live_updates", 0)),
        }
    return _MEASURED


def warm():
    """Pay the one-time cost (connectome load + circuit + training) off the request path.

    ``server.py``'s warm thread calls this; ``sniff.circuit()`` is built there anyway, so on a
    normal start this only adds the ≈1.5 s delta-rule training of the readout.
    """
    try:
        measured()
    except RuntimeError:
        pass


def status():
    """What the classifier is made of — for ``/state``, the README and the tests."""
    out = {"module": "cognitive_matrix",
           "model": "alpn→kc coincidence code + delta-rule okuma (gerçek FlyWire Wpk)",
           "seed": SEED, "categories": list(CATEGORIES), "labels": list(labels()),
           # "vocabulary" = everything the fly can classify right now; the factory 55 are the
           # trained set and stay hardcoded, taught words are additive and reported separately.
           "vocabulary": vocab_size(), "factory_vocabulary": VOCAB_SIZE,
           "taught": len(TAUGHT), "taught_words": taught_words(),
           "confidence_floor": CONFIDENCE_FLOOR,
           "pn_active": PN_ACTIVE, "coincidence": COINCIDENCE,
           "learned": learned_status(),
           "honest_note": "KC kodu ÖLÇÜM: sniff.circuit()'ın gerçek ALPN→KC matrisi + "
                          "sniff.kc_code() eşik-tesadüfü (FlyWire 783, ≥3 sinaps). Kelime→ALPN "
                          "deseni ve delta-kuralı okuma BİZİM tasarımımız."}
    try:
        out.update(measured())
        out["connectome"] = True
        out["loaded"] = True
    except RuntimeError as e:                                # veri yok: sunucu yine de açılır
        out["connectome"] = False
        out["loaded"] = False
        out["error"] = str(e)
    return out


# --------------------------------------------------------------------------- #
# self-test — the real connectome, no server, no LLM
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import time

    t0 = time.time()
    C = wire()
    t_build = time.time() - t0
    readout()                                # delta kuralı: bir kez, sözlüğün tamamıyla
    t_train = time.time() - t0 - t_build
    st = status()
    print("gerçek devre: %d ALPN -> %d KC -> %d MBON | Wpk bağlı çift=%d | KC fan-in ort=%.2f"
          % (len(C["pn"]), len(C["kc"]), len(C["mb"]), int((C["Wpk"] > 0).sum()),
             float((C["Wpk"] > 0).sum(axis=1).mean())))
    print("                       (gerçek matris %.1f sn'de kuruldu, okuma %.1f sn'de eğitildi)"
          % (t_build, t_train))
    print("status: model=%s | connectome=%s | konnektom=%s"
          % (st["model"], st["connectome"], st["honest_note"][:28] + "…"))
    assert st["connectome"] is True and st["loaded"] is True, st

    print("\n-- KC kodu gerçekten sniff.kc_code() mu? --")
    for probe in ("şeker", "tehlike", "zzzz"):
        pn = pn_code(probe)
        mine = sniff.kc_code(pn, coincidence=COINCIDENCE)         # bu modülün yolu
        ref = ((C["Wpk"] > 0) @ pn) >= COINCIDENCE                # sniff.py'nin satırı
        assert mine.shape == ref.shape == (len(C["kc"]),), mine.shape
        assert bool((mine == ref).all()), probe    # aynı mekanizma, kopyası yok
        print("  %-8s -> PN %d aktif (%.1f%%), KC %d aktif (%.2f%%) — sniff ile aynı kural"
              % (probe, int(pn.sum()), 100.0 * pn.mean(), int(mine.sum()),
                 100.0 * mine.mean()))
    assert pn_code("123 !!!").sum() == 0, "sayı/noktalama PN uçurmamalı"
    assert encode("BANA BİR ŞİİR YAZ.").sum() > 0, "cümle kodlanamadı"     # cümle de kodlanabilir
    assert encode("").sum() == 0, "boş metin KC uçurmamalı"

    print("\n-- kod özellikleri --")
    code = encode("şeker")
    vc = vocabulary_codes().sum(axis=1)
    print("  dtype=%s shape=%s aktif=%d (%.2f%%), sözlük ort=%d, aralık=%s"
          % (code.dtype, code.shape, int(code.sum()), 100.0 * code.mean(),
             int(round(float(vc.mean()))), [int(vc.min()), int(vc.max())]))
    assert code.dtype == np.bool_ and code.shape == (len(C["kc"]),)
    assert (encode("şeker") == code).all(), "kod deterministik değil"
    assert (encode("seker") == code).all(), "şeker/seker aynı koda düşmedi"
    print("  şeker == seker (ASCII katlama) | şekerli ~ şeker: %d ortak hücre | "
          "şeker ~ tehlike: %d" % (int((encode("şeker") & encode("şekerli")).sum()),
                                   int((encode("şeker") & encode("tehlike")).sum())))

    print("\n-- delta kuralı (0/1 KC kodu üzerinde) --")
    print("  %d epoch, lr=%s, eğitim doğruluğu %.3f, en kötü doğru skor %.2f"
          % (_TRAIN_INFO["epochs"], _TRAIN_INFO["lr"], _TRAIN_INFO["train_accuracy"],
             _TRAIN_INFO["min_correct_score"]))
    assert _TRAIN_INFO["train_accuracy"] == 1.0, _TRAIN_INFO
    assert _TRAIN_INFO["epochs"] < LR_MAX_EPOCHS, "delta kuralı yakınsamadı: %s" % _TRAIN_INFO

    print("\n-- sözlük: her kelime kendi kategorisini bulmalı --")
    wrong, low = [], []
    for cat in CATEGORIES:
        for w in VOCAB[cat]:
            got, conf = classify(w)
            if got != cat:
                wrong.append((w, got, cat))
            if conf < CONFIDENCE_FLOOR:
                low.append((w, conf))
            print("  [%s] %-12s -> %-8s %.2f   tarama=%s"
                  % ("ok " if got == cat else "HATA", w, got, conf, CATEGORY_TR[got]))
    assert not wrong, "yanlış sınıflanan kelimeler: %s" % wrong
    assert not low, "güveni eşiğin altında kalan sözlük kelimeleri: %s" % low
    print("  %d/%d doğru; güven %.2f-%.2f (ort %.2f), eşik %.2f"
          % (VOCAB_SIZE - len(wrong), VOCAB_SIZE,
             measured()["vocab_confidence"]["min"], measured()["vocab_confidence"]["max"],
             measured()["vocab_confidence"]["mean"], CONFIDENCE_FLOOR))

    print("\n-- Türkçe ekler: sözlükte olmayan çekimli hâller --")
    for text, want in (("şekercik var mı", "besin"), ("tehlikesiz görünüyor", "tehlike"),
                       ("acıktım galiba", "açlık"), ("evettt", "onay")):
        hits = scan(text)
        assert hits and hits[0]["category"] == want, (text, hits)
        print("  %-20s -> %-8s (\"%s\", %.2f)"
              % (text, hits[0]["category"], hits[0]["word"], hits[0]["confidence"]))

    print("\n-- cümle taraması --")
    for text in ("önünde şeker var", "tokata dikkat", "merhaba nasılsın", "acıktın mı?",
                 "hayır istemem"):
        hits = scan(text)
        assert hits, text
        print("  %-20s -> %s" % (text, ", ".join("%s:%s" % (h["word"], h["category"])
                                                 for h in hits)))
    free = scan("Bana kısa bir şiir yaz.")
    assert free == [], free
    print("  sözlük dışı cümle -> %s (sınıflandırıcıya uğramaz: serbest sohbet)" % free)

    print("\n-- sözlük dışı kelimeler: eşiğin altında kalmalı --")
    for w in ("karpuz", "zzzzz", "kuantum", "bilgisayar", "mavi", "yağmur"):
        got, conf = classify(w)
        assert conf < CONFIDENCE_FLOOR, (w, got, conf)
        print("  %-12s -> %-8s %.2f" % (w, got, conf))
    print("  hepsi eşiğin altında: kod, öğrenilmiş hiçbir koda benzemiyor (tanıdıklık kapısı)")

    # ------------------------------------------------------------------ Faz 11 #
    print("\n-- Faz 11: canlı öğretim (tek örnekli delta adımı + gerileme kontrolü) --")
    import json as _json
    import shutil
    import tempfile

    default_json, default_npy = LEARNED_JSON, LEARNED_NPY
    default_existed = os.path.exists(default_json)
    tmpdir = tempfile.mkdtemp(prefix="cm_learned_")          # never touch the real defter
    set_learned_paths(os.path.join(tmpdir, "learned_words.json"),
                      os.path.join(tmpdir, "learned_weights.npy"),
                      os.path.join(tmpdir, "learned_bias.npy"))
    print("  taban: %d kelime (fabrika %d), etiketler %s; defter -> %s"
          % (vocab_size(), VOCAB_SIZE, ", ".join(labels()), os.path.basename(LEARNED_JSON)))

    oov_before = classify("kavun")
    print("  öğretim öncesi: \"kavun\" -> %s %.2f (eşik %.2f altında)"
          % (oov_before[0], oov_before[1], CONFIDENCE_FLOOR))
    assert oov_before[1] < CONFIDENCE_FLOOR, oov_before

    NEW = (("kavun", "besin"), ("kitap", "bilgi"), ("yıldırım", "tehlike"), ("elma", "besin"))
    for word, cat in NEW:
        res = teach(word, cat, save=False)                   # one save at the end of the group
        b, a = res["before"], res["after"]
        print("  öğretildi: %-9s -> %-8s %d adım/%d güncelleme lr=%-8s | eski sözlük %d/%d "
              "(min %.3f) -> %d/%d (min %.3f) | kayıp %s düşen %s"
              % (word, cat, res["steps"], res["updates"], res["lr"],
                 round(b["accuracy"] * b["n"]), b["n"], b["min_confidence"],
                 round(a["accuracy"] * a["n"]), a["n"], a["min_confidence"],
                 res["lost"], res["dropped"]))
        assert res["ok"] and res["installed"], res
        assert res["steps"] <= TEACH_MAX_STEPS and res["updates"] >= 1, res
        assert a["accuracy"] == 1.0, "gerileme: eski kelimeler yanlış sınıflandı: %s" % res
        assert not res["lost"], "gerileme: etiket değişti: %s" % res["lost"]
        assert res["target"]["confidence"] >= CONFIDENCE_FLOOR, res["target"]
        got = classify(word)
        assert got[0] == cat and got[1] >= CONFIDENCE_FLOOR, (word, got)
    assert vocab_size() == VOCAB_SIZE + 3, vocab_size()      # elma bir fabrika kelimesi: pekiştirme
    assert list(labels())[-1] == "bilgi" and is_taught_category("bilgi"), labels()
    assert "bilgi" not in CATEGORIES, "fabrika kategori tablosu değişti"
    readout()
    assert _W.shape[0] == len(labels()), (_W.shape, labels())
    print("  yeni kategori \"bilgi\" okuma matrisini büyüttü: %s satır (yeniden başlatma yok)"
          % (_W.shape,))

    print("  canlı kelimeler yönlendirmeye girdi: %s"
          % ", ".join("%s:%s" % (h["word"], h["category"])
                      for h in scan("kavun var mı, kitap okudum")[:2]))
    assert scan("kavun var mı")[0]["category"] == "besin", scan("kavun var mı")
    assert scan("kitap okudum")[0]["category"] == "bilgi", scan("kitap okudum")
    assert classify("kavun")[1] >= CONFIDENCE_FLOOR, "öğretilen kelime hâlâ eşiğin altında"

    print("  toplu ölçüm = classify(): ", end="")
    table = vocabulary_table()
    bad = [(r["word"], r["label"], classify(r["word"])) for r in table
           if r["label"] != classify(r["word"])[0]
           or abs(r["confidence"] - classify(r["word"])[1]) > 1e-4]
    assert not bad, bad
    print("%d/%d satır birebir aynı" % (len(table), len(table)))

    # ---- persistence: save, cold start, replay, hand-edit, undo --------------------------
    print("\n  -- defter: kaydet, yeniden başlat, geri yükle --")
    saved = save_learned()
    data = _json.load(open(LEARNED_JSON, encoding="utf-8"))
    print("  yazıldı: %s (%d kelime, %s) + %s %s"
          % (os.path.basename(saved["json"]), saved["taught"], saved["shape"],
             os.path.basename(saved["weights"]), os.path.basename(saved["bias"])))
    print("  dosya içeriği (elle düzenlenebilir): %s" % _json.dumps(data["taught"],
                                                                  ensure_ascii=False))
    assert data["taught"] == {"kavun": "besin", "kitap": "bilgi", "yıldırım": "tehlike",
                             "elma": "besin"}, data["taught"]
    assert data["base_vocabulary"] == VOCAB_SIZE and os.path.exists(LEARNED_NPY)

    W_trained = _W.copy()
    TAUGHT.clear()                                     # what a process restart does to memory
    _CODES = _UNIT = _W = _B = _MEASURED = None
    _TRAIN_INFO.pop("live_updates", None)
    assert vocab_size() == VOCAB_SIZE, "soğuk başlangıçta hayalet kelime kaldı"
    t_load = time.time()
    loaded = load_learned()
    print("  soğuk başlangıç -> %d kelime geri yüklendi (%.1f sn), sözlük %d, kayıp %s, "
          "ağırlık karşılaştırması %s"
          % (loaded["loaded"], time.time() - t_load, loaded["vocabulary"], loaded["lost"],
             loaded["weights"]))
    assert loaded["loaded"] == 4 and not loaded["skipped"], loaded
    assert loaded["vocabulary"] == VOCAB_SIZE + 3, loaded
    assert loaded["weights"]["match"] is True, loaded["weights"]
    assert np.array_equal(W_trained, _W), "yeniden oynatma ağırlıkları birebir üretmedi"
    for w, cat in NEW:
        assert classify(w)[0] == cat, (w, classify(w))

    print("\n  -- fabrika 55 kelime öğretimden sonra hâlâ doğru mu? --")
    wrong = [(w, classify(w)[0], cat) for cat in CATEGORIES for w in VOCAB[cat]
             if classify(w)[0] != cat]
    confs = [classify(w)[1] for cat in CATEGORIES for w in VOCAB[cat]]
    print("  %d/%d doğru; güven %.3f-%.3f (ort %.3f) — taban %.2f"
          % (VOCAB_SIZE - len(wrong), VOCAB_SIZE, min(confs), max(confs),
             sum(confs) / len(confs), CONFIDENCE_FLOOR))
    assert not wrong, wrong
    assert min(confs) >= CONFIDENCE_FLOOR, min(confs)

    print("\n  -- elle düzenleme: dosyaya bir kelime ekle, .npy bunu bilemez --")
    data["taught"]["zeytin"] = "besin"
    _json.dump(data, open(LEARNED_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    TAUGHT.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = None
    edited = load_learned()
    print("  yeniden yüklendi: %d kelime, \"zeytin\" -> %s, sözlük %d, ağırlık %s"
          % (edited["loaded"], classify("zeytin")[0], edited["vocabulary"],
             edited["weights"]))
    assert classify("zeytin")[0] == "besin", classify("zeytin")
    assert edited["weights"]["match"] is False and edited["weights"]["max_delta"] > 0, edited

    print("\n  -- elle yazılmış dosyayı yükleme + geri alma --")
    data = {"elma": "besin", "kitap": "bilgi"}    # a bare {word: category} file is accepted too
    _json.dump(data, open(LEARNED_JSON, "w", encoding="utf-8"), ensure_ascii=False)
    TAUGHT.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = None
    bare = load_learned()
    print("  sade biçim ({\"kelime\": \"kategori\"}) -> %d kelime yüklendi" % bare["loaded"])
    assert bare["loaded"] == 2, bare

    W_before_override = _W.copy()
    ov = teach("şeker", "tehlike")
    print("  fabrika kelimesi üzerine yazıldı: \"şeker\" %s -> %s (kaynak %s); şimdi %s"
          % (ov["overwrote"], ov["category"], ov["origin"], classify("şeker")))
    assert ov["overwrote"] == "besin" and classify("şeker")[0] == "tehlike", ov
    assert scan("şeker var mı")[0]["category"] == "tehlike", scan("şeker var mı")
    undo = undo_last_teach()
    print("  geri alındı: %s -> %s | defterde %s | ağırlıklar birebir geri geldi: %s"
          % (undo["undone"], classify("şeker"), list(taught_words()), 
             bool(np.array_equal(W_before_override, _W))))
    assert classify("şeker")[0] == "besin", classify("şeker")
    assert "şeker" not in taught_words() and np.array_equal(W_before_override, _W), undo
    assert undo_last_teach()["ok"] is False, "boşta geri alma başarılı göründü"

    print("\n  -- Faz 11 sözlük boyutu uyarısı (engel değil, uyarı) --")
    limit = VOCAB_WARN_SIZE
    VOCAB_WARN_SIZE = vocab_size() - 1
    big = teach("hurma", "besin")
    print("  %d kelime: %s" % (big["vocabulary"], big["size_warning"]))
    assert big["size_warning"] and "Phase 10" in big["size_warning"], big
    VOCAB_WARN_SIZE = limit
    undo_last_teach()

    # ------------------------------------------------------------- Faz 11.5 #
    print("\n-- Faz 11.5: güvenlik sınırı (ölçüm; otomatik geri alma YOK) --")
    print("  sabitler: taban %.2f, marj %.2f (eşik %.2f), tek adım eşiği %.2f"
          % (CONFIDENCE_FLOOR, TEACH_SAFETY_MARGIN, CONFIDENCE_FLOOR + TEACH_SAFETY_MARGIN,
             TEACH_SAFETY_STEP))
    TAUGHT.clear()
    _EFFECT_ALIAS.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = _LAST_TEACH = None
    _TRAIN_INFO.pop("live_updates", None)
    readout()

    def _lowest():
        """The weakest word of the FULL live vocabulary — the number the alert tier reads."""
        table = vocabulary_table()
        worst = min(table, key=lambda r: r["confidence"])
        return worst["confidence"], worst["word"], worst["label"]

    base, bw, bc = _lowest()
    print("  fabrika 55 tabanı: en düşük güven %.3f (%s/%s)" % (base, bw, bc))
    assert base > CONFIDENCE_FLOOR + TEACH_SAFETY_MARGIN, base

    print("\n  -- aynı fabrika kelimesini arka arkaya çevir (istenen test) --")
    n = 0
    alerts, crossings, lows = [], [], []

    def _step(no, w, c):
        """One teach + the FULL-vocabulary minimum, recorded the way the alert tier sees it."""
        r = teach(w, c, save=False)
        low, low_w, low_c = _lowest()
        lows.append(low)
        if r["safety_warning"]:
            alerts.append(no)
        if r["dropped"] or not r["installed"]:
            crossings.append(no)
        print("  %d) %-8s→%-8s en düşük %.3f (%s/%s) | kayıp %s düşen %s | uyarı %s"
              % (no, w, c, low, low_w, low_c, r["lost"],
                 [(x, round(a, 3), round(b, 3)) for x, a, b in r["dropped"]],
                 "⛔ EVET" if r["safety_warning"] else "yok"))
        return r

    for i in range(5):
        n += 1
        _step(n, "şeker", "tehlike" if i % 2 == 0 else "besin")
    print("     5 çevirme: %d uyarı, %d taban geçişi — aynı kelimeyi çevirmek BİRİKMİYOR "
          "(güven iki değer arasında salınıyor)" % (len(alerts), len(crossings)))
    assert alerts, "güvenlik uyarısı hiç çalışmadı"
    assert not crossings and min(lows) > CONFIDENCE_FLOOR, (crossings, min(lows))
    print("     uyarı, hiçbir kelime tabanı geçmeden geldi (en düşük güven %.3f > %.2f): %s"
          % (min(lows), CONFIDENCE_FLOOR, alerts))

    print("\n  -- farklı öğretimler BİRİKİR: 3 yeni kategori (aynı sıra devam ediyor) --")
    for w, c in (("kitap", "bilgi"), ("felsefe", "dusunce"), ("tarih", "zaman")):
        n += 1
        _step(n, w, c)
    print("     uyarılar %s | taban geçişleri %s" % (alerts, crossings))
    assert crossings, "birikme tabanı geçmedi (ölçüm değişti mi?)"
    assert min(alerts) < min(crossings), \
        "uyarı tabanın geçilmesinden önce gelmedi: uyarı %s, geçiş %s" % (alerts, crossings)
    print("     ilk uyarı öğretim #%d, ilk taban geçişi #%d — uyarı ÖNCE geldi"
          % (min(alerts), min(crossings)))

    print("\n  -- sade birikme sırası: uyarı geçişle aynı öğretimde gelir (dürüst sınır) --")
    TAUGHT.clear()
    _EFFECT_ALIAS.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = _LAST_TEACH = None
    readout()
    n2, alerts2, crossings2 = 0, [], []
    for w, c in (("kitap", "bilgi"), ("felsefe", "dusunce"), ("tarih", "zaman"),
                 ("şeker", "tehlike")):
        n2 += 1
        r = teach(w, c, save=False)
        low, _, _ = _lowest()
        if r["safety_warning"]:
            alerts2.append(n2)
        if r["dropped"] or not r["installed"]:
            crossings2.append(n2)
        print("  %d) %-8s→%-8s en düşük %.3f | düşen %s | uyarı %s"
              % (n2, w, c, low, [(x, round(a, 3), round(b, 3)) for x, a, b in r["dropped"]],
                 "⛔ EVET" if r["safety_warning"] else "yok"))
    print("     uyarılar %s | geçişler %s" % (alerts2, crossings2))
    assert crossings2, "sade birikme tabanı geçmedi"
    assert min(alerts2) == min(crossings2), "beklenmedik biçimde erken uyarı: %s" % alerts2
    print("     bitirdiği adım 0.396 düşürdü: sonradan ölçen bir sınır, görmediği bir adımı "
          "önceden haber veremez. Bu yüzden tabanı geçen kelime `dropped` ile ayrıca raporlanır "
          "ve çözüm adıyla söylenir: /öğret-geri")

    print("\n  -- uyarının adıyla söylediği çözüm: /öğret-geri --")
    undo = undo_last_teach()
    low, low_w, _ = _lowest()
    print("  geri alındı: \"%s\" | en düşük güven %.3f (%s) — taban %.2f"
          % (undo["undone"], low, low_w, CONFIDENCE_FLOOR))
    assert low >= CONFIDENCE_FLOOR, "geri alma tabanı düzeltmedi: %s" % low

    print("\n  -- Faz 11.5: canlı kategorinin beden etkisi (effect_alias) --")
    assert effect_aliases() == {}, effect_aliases()
    assert effect_alias("besin") is None, "fabrika kategorisine bağ takıldı"
    bound = set_effect_alias("bilgi", "besin")
    print("  bağlandı: %s → %s (%s)" % (bound["category"], bound["alias"], bound["why"]))
    assert bound["ok"] and effect_alias("bilgi") == "besin", bound
    print("  reddedildi: fabrika kategorisi (%s) | bilinmeyen etki (%s)"
          % (set_effect_alias("besin", "tehlike")["error"],
             set_effect_alias("bilgi", "yokdiyet")["error"]))
    assert set_effect_alias("besin", "tehlike")["ok"] is False
    assert set_effect_alias("bilgi", "yokdiyet")["ok"] is False
    assert set_effect_alias("hiçyok", "besin")["ok"] is False
    assert set_effect_alias("bilgi", "tehlike")["alias"] == "tehlike"        # değiştirilebilir
    data = _json.load(open(LEARNED_JSON, encoding="utf-8"))
    print("  defter: effect_aliases=%s (kategoriler %s)"
          % (data["effect_aliases"], data["categories"]))
    assert data["effect_aliases"] == {"bilgi": "tehlike"}, data["effect_aliases"]

    TAUGHT.clear()                                  # soğuk başlangıç: kelimeler + bağlar birlikte
    _EFFECT_ALIAS.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = None
    back = load_learned()
    print("  yeniden başlatma: %d kelime, alias %s, atlanan %s"
          % (back["loaded"], back["aliases"], back["skipped"]))
    assert back["aliases"] == {"bilgi": "tehlike"} and effect_alias("bilgi") == "tehlike", back
    assert not back["skipped"], back

    clear = set_effect_alias("bilgi", "yok")
    print("  çözüldü: %s → %s" % (clear["category"], clear["why"]))
    assert clear["ok"] and clear["cleared"] and effect_alias("bilgi") is None
    assert _json.load(open(LEARNED_JSON, encoding="utf-8"))["effect_aliases"] == {}
    assert set_effect_alias("bilgi", "yok")["cleared"] is False, "boşta çözme başarılı göründü"

    print("\n  -- elle yazılmış alias: olmayan kategori atlanır, dosya yine yüklenir --")
    _json.dump({"taught": {"zeytin": "besin"}, "effect_aliases": {"bilgi": "besin"}},
               open(LEARNED_JSON, "w", encoding="utf-8"), ensure_ascii=False)
    TAUGHT.clear()
    _EFFECT_ALIAS.clear()
    _CODES = _UNIT = _W = _B = _MEASURED = None
    hand = load_learned()
    print("  %d kelime yüklendi, alias %s, atlanan %s"
          % (hand["loaded"], hand["aliases"], hand["skipped"]))
    assert hand["loaded"] == 1 and hand["aliases"] == {} and len(hand["skipped"]) == 1, hand
    assert not hand["error"], hand

    print("\n  -- yeni kategoriyi geri almak bağını da götürür --")
    t = teach("deniz", "mavi", save=False)
    set_effect_alias("mavi", "selam", save=False)
    assert t["created_category"] and effect_alias("mavi") == "selam"
    u2 = undo_last_teach()
    print("  geri alındı: son etiket %s, kalan bağlar %s" % (u2["labels"][-1], u2["effect_aliases"]))
    assert u2["effect_aliases"] == {} and effect_alias("mavi") is None
    assert not is_taught_category("mavi") and "mavi" not in CATEGORIES, labels()
    print("  (CATEGORIES hâlâ %d fabrika kararı — etki tablosuyla 1:1)" % len(CATEGORIES))

    assert os.path.exists(default_json) == default_existed, "gerçek defter dosyasına dokunuldu"
    set_learned_paths(default_json, default_npy)     # put the real paths back
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("  (geçici defter silindi; %s %s)"
          % (os.path.basename(default_json), "korundu" if default_existed else "hiç oluşmadı"))

    print("\n-- özet --")
    print("  %d ALPN -> %d KC (%s hücre aktif, %.2f%% yoğunluk) -> %d MBON; "
          "okuma %d epoch'ta %d/%d"
          % (measured()["pn_dim"], measured()["kc_dim"], measured()["kc_active_range"],
             100.0 * measured()["kc_density"], measured()["mbon_dim"], measured()["epochs"],
             int(round(measured()["train_accuracy"] * VOCAB_SIZE)), VOCAB_SIZE))
    print("  canlı sözlük: %d kelime (%d fabrika + %d öğretilmiş), %d okuma etiketi"
          % (vocab_size(), VOCAB_SIZE, len(TAUGHT), len(labels())))
    print("  tüm testler geçti (%.1f sn)" % (time.time() - t0))
