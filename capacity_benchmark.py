"""
capacity_benchmark.py — Phase 10: how many words can the mushroom body hold?

A stress test of the classifier that actually runs in production, asking for TWO different
ceilings and refusing to confuse them:

    (A) biological / substrate ceiling — at what vocabulary size do the raw KC codes themselves
        stop being distinguishable, *whatever* readout sits on top? The 5177 Kenyon cells fire
        ~68 cells per word (1.3% density), so unrelated words are nearly orthogonal by chance;
        Turkish morphology is the real threat, because "kullanmak" / "kullanmayacak" share their
        character n-grams, therefore PNs, therefore Kenyon cells.
    (B) algorithmic ceiling — at what vocabulary size does *our* linear delta-rule readout give
        up, even though the codes may still be separable? If (B) << (A), the bottleneck is our
        readout, not the fly.

Nothing here re-implements the pipeline. The encoder is ``cognitive_matrix.encode`` and the
readout is ``cognitive_matrix.readout`` — both imported and called as-is; the only thing this
script does is repoint ``cm.CATEGORIES`` / ``cm.VOCAB`` (so the same trainer has N outputs, one
word per class) and reset the module caches between runs. Every hyper-parameter — the lr formula
``1/mean active``, the ±1 targets, the 4000-epoch cap, the 0.02 tolerance, the softmax
temperature and the familiarity gate — is production's, because it is production's code.

Read-only by design: server.py / game_loop.py / cognitive_matrix.py are never modified, and the
module globals are restored before the script exits.

    python capacity_benchmark.py                       # full grid 55…500 (~6 min: B1 at N≥150
    python capacity_benchmark.py --n 55,100 --log cap.txt   # runs to the 4000-epoch cap)

Reported honestly, including the parts that are unflattering: the per-word output layer is a
deviation from production's 6 outputs (required to ask "can they be told apart?"), and the
softmax confidence floor starts eating *correct* words as the class count grows — a property of
the readout's normalisation, not of the connectome.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request

import numpy as np

import cognitive_matrix as cm          # the production encoder + trainer + familiarity gate
import sniff                           # the real ALPN→KC wiring behind cm.encode()

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(HERE, "data", "tr_50k.txt")
CORPUS_URL = ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/"
              "content/2018/tr/tr_50k.txt")
CORPUS_NOTE = "hermitdave/FrequencyWords 2018/tr (OpenSubtitles), CC-BY-SA 4.0"

GRID = (55, 100, 150, 200, 300, 500)   # the Phase 10 grid
N_OOV = 100         # held-out words per OOV probe (fixed set + adjacent set)
COLLISION = 0.80    # Jaccard above this = near-identical codes: no readout could separate them
WARN = 0.50         # Jaccard above this = suspiciously similar codes
PARITY_WORDS = 3    # words used to cross-check the batched math against cm.classify()
SYLLABLES = ("ka", "ra", "mi", "so", "tu", "ne", "li", "ba", "du", "ge", "yo", "ze")
PROD_CATS = tuple(cm.CATEGORIES)   # production's 6 decision labels, captured before any repointing





class Out:
    """print() + optional UTF-8 log file, so the Turkish word data survives the console."""

    def __init__(self, path=None):
        self.fh = open(path, "w", encoding="utf-8") if path else None

    def __call__(self, text=""):
        try:
            print(text)
        except UnicodeEncodeError:              # legacy cp1252 console: never crash on ş/ı/≤
            enc = getattr(sys.stdout, "encoding", "ascii") or "ascii"
            print(text.encode(enc, "replace").decode(enc, "replace"))
        if self.fh:
            self.fh.write(text + "\n")
            self.fh.flush()

    def close(self):
        if self.fh:
            self.fh.close()
            self.fh = None


def _utf8_stdout():
    """Prefer UTF-8 output; the log file is UTF-8 either way."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _synthetic(limit):
    """Deterministic word-like strings — only used when a real corpus is unreachable."""
    out, seen = [], set()
    for a in SYLLABLES:
        for b in SYLLABLES:
            for c in SYLLABLES:
                w = a + b + c
                if w not in seen:
                    seen.add(w)
                    out.append(w)
                if len(out) >= limit:
                    return out
    return out



def load_corpus(path, limit):
    """Top-`limit` distinct surface words by frequency. Returns (words, source, stats).

    A real list is preferred; a synthetic fallback is *always* labelled, because a capacity
    number measured on made-up strings is not a measurement of the language.
    """
    if not os.path.exists(path):
        _download(path)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            raw = [ln.split()[0] for ln in fh if ln.split()]
        src = "REAL corpus: %s\n           %s" % (path, CORPUS_NOTE)
    else:
        raw = _synthetic(limit * 2)
        src = ("SYNTHETIC corpus (no %s and no network) — NOT a real-language measurement"
               % os.path.basename(path))
    seen, words, dup, junk = set(), [], 0, 0
    for w in raw:
        folded = cm.fold(w)                     # same folding the encoder applies
        if not re.fullmatch(r"[a-z]{2,}", folded):
            junk += 1                           # digits, punctuation, single letters
            continue
        if folded in seen:
            dup += 1                            # distinct spellings, identical code — by design
            continue
        seen.add(folded)
        words.append(w)
    return words, src, {"raw": len(raw), "dup_fold": dup, "junk": junk, "kept": len(words)}


def _download(path):
    print("corpus missing → downloading %s" % CORPUS_URL, file=sys.stderr)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(CORPUS_URL, headers={"User-Agent": "genesis-fly-phase10"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            blob = resp.read()
        with open(path, "wb") as fh:
            fh.write(blob)
        print("corpus saved: %s (%.0f KB)" % (path, len(blob) / 1024), file=sys.stderr)
        return True
    except Exception as exc:                    # offline / proxy / DNS: fall back, but say so
        print("corpus download failed (%s) → synthetic fallback" % exc, file=sys.stderr)
        return False


# --------------------------------------------------------------------------- #
# encoder — imported, never re-implemented
# --------------------------------------------------------------------------- #
def kc_codes(words):
    """The KC codes for these words, via the production encoder, with a timing readout."""
    t0 = time.time()
    codes = np.stack([cm.encode(w) for w in words])
    return codes, time.time() - t0


def encoder_identity(words):
    """Prove ``cm.encode`` is ``sniff.kc_code(cm.pn_code())`` — the pipeline under test."""
    for w in words:
        a = cm.encode(w)
        b = sniff.kc_code(cm.pn_code(w), coincidence=cm.COINCIDENCE)
        assert a.dtype == bool and np.array_equal(a, b), "encoder drifted from sniff on %r" % w
    return len(words)


# --------------------------------------------------------------------------- #
# ceiling (A): the raw code space, readout-independent
# --------------------------------------------------------------------------- #
def geometry(codes):
    """Pairwise Jaccard / containment / identity for a set of boolean KC codes."""
    n = len(codes)
    counts = codes.sum(axis=1).astype(np.float32)
    f = codes.astype(np.float32)
    inter = f @ f.T                                        # bool@bool is boolean matmul — cast
    union = counts[:, None] + counts[None, :] - inter
    jac = inter / np.maximum(union, 1.0)
    contain = inter / np.maximum(np.minimum(counts[:, None], counts[None, :]), 1.0)
    np.fill_diagonal(jac, 0.0)
    np.fill_diagonal(contain, 0.0)
    identical = (inter == counts[:, None]) & (inter == counts[None, :])
    np.fill_diagonal(identical, False)
    iu = np.triu_indices(n, 1)
    pairs = jac[iu]
    worst = np.argsort(pairs)[::-1][:5]
    return {
        "n": n,
        "counts": counts,
        "mean_active": float(counts.mean()),
        "density": float(counts.mean() / codes.shape[1]),
        "n_pairs": len(pairs),
        "mean": float(pairs.mean()) if len(pairs) else 0.0,
        "median": float(np.median(pairs)) if len(pairs) else 0.0,
        "p95": float(np.percentile(pairs, 95)) if len(pairs) else 0.0,
        "max": float(pairs.max()) if len(pairs) else 0.0,
        "max_contain": float(contain[iu].max()) if len(pairs) else 0.0,
        "n_ident": int(identical.sum() // 2),
        "n_collide": int((pairs > COLLISION).sum()),
        "n_warn": int((pairs > WARN).sum()),
        "worst": [(int(iu[0][k]), int(iu[1][k]), float(pairs[k])) for k in worst],
        "worst_c": [float(contain[iu[0][k], iu[1][k]]) for k in worst],
        "collide_pairs": [(int(iu[0][k]), int(iu[1][k]), float(pairs[k]))
                          for k in np.flatnonzero(pairs > COLLISION)],
        "warn_pairs": [(int(iu[0][k]), int(iu[1][k])) for k in np.flatnonzero(pairs > WARN)],
        "n_contain": int((contain[iu] > COLLISION).sum()),
        "contain_pairs": [(int(iu[0][k]), int(iu[1][k]))
                          for k in np.flatnonzero(contain[iu] > COLLISION)],
        "identical_pairs": [(int(a), int(b)) for a, b in zip(*np.nonzero(np.triu(identical, 1)))],
        "nearest": jac.max(axis=1),
    }


# --------------------------------------------------------------------------- #
# ceiling (B): the delta-rule readout, driven through cm.readout() itself
# --------------------------------------------------------------------------- #
_SAVED = None


def _reset_cm():
    """Drop cm's training caches so the next readout() call trains from scratch."""
    cm._CODES = cm._UNIT = cm._W = cm._B = None
    cm._TRAIN_INFO.clear()
    cm._MEASURED = None


def save_cm_state():
    """Keep the production vocabulary, so the module is left exactly as it was found."""
    global _SAVED
    _SAVED = (cm.CATEGORIES, cm.VOCAB)


def restore_cm_state():
    if _SAVED:
        cm.CATEGORIES, cm.VOCAB = _SAVED
    _reset_cm()


def train_readout(categories, vocab):
    """Train with the production trainer: cm.readout() — zero re-implementation.

    ``categories`` are the output names, ``vocab`` maps each output to its words. cm derives
    everything else itself (encode → codes, lr = 1/mean-active, ±1 targets, 4000-epoch cap,
    0.02 tolerance), because this *is* cm's code path.
    """
    cm.CATEGORIES = tuple(categories)
    cm.VOCAB = {c: tuple(ws) for c, ws in vocab.items()}
    _reset_cm()
    t0 = time.time()
    W, B = cm.readout()
    info = dict(cm._TRAIN_INFO)                 # copy before any later reset()
    info["seconds"] = round(time.time() - t0, 2)
    return W, B, info


def _index_of(categories, vocab):
    """Which output each training word belongs to — the same order cm.readout() builds its rows."""
    return np.array([categories.index(cat) for cat in categories for _w in vocab[cat]],
                    dtype=np.int64)


def eval_readout(W, B, X, index):
    """Exact training accuracy + separation margin of a trained readout (no cm internals)."""
    got = X @ W.T + B
    n = len(index)
    correct = got[np.arange(n), index]
    masked = got.copy()
    masked[np.arange(n), index] = -np.inf
    best_wrong = masked.max(axis=1)
    margin = correct - best_wrong
    want = np.full_like(got, -1.0)
    want[np.arange(n), index] = 1.0
    max_err = float(np.abs(want - got).max())
    return {
        "acc": float((got.argmax(axis=1) == index).mean()),
        "n_wrong": int((got.argmax(axis=1) != index).sum()),
        "min_correct": float(correct.min()),
        "min_margin": float(margin.min()),
        "n_fragile": int((margin < 0.10).sum()),
        "max_err": max_err,
        "converged": bool(max_err < cm.LR_TOL),
    }


def confidence(W, B, codes):
    """Production confidence for each code: softmax(readout) × familiarity — cm's own helpers."""
    z = np.asarray(codes, dtype=np.float32) @ W.T + B
    out = []
    for i in range(len(z)):
        p = cm._softmax(z[i])
        out.append((float(p.max()) * cm._familiarity(codes[i]), int(np.argmax(p))))
    return out


# --------------------------------------------------------------------------- #
# one vocabulary size: (A) geometry, (B1) one-output-per-word, (B2) production shape
# --------------------------------------------------------------------------- #
def measure_n(n, corpus, CODES, fixed0, oov, parity=False):
    """Everything the report needs for one vocabulary size.

    ``corpus`` is the whole encoded word list, ``CODES[i]`` its i-th KC code. The held-out "fixed"
    OOV set is CODES[fixed0:fixed0+oov] (outside every tested N, so it is comparable across N);
    the "adjacent" OOV set is CODES[n:n+oov] — the hardest words for that particular size.
    """
    pos = {w: i for i, w in enumerate(corpus)}
    X = CODES[:n]
    res = {"n": n, "geo": geometry(X), "oov_fixed_slice": CODES[fixed0:fixed0 + oov],
           "oov_adj_slice": CODES[n:n + oov]}

    # (B1) strict separability: one output per word, trained by cm.readout() itself
    cats = tuple(corpus[:n])
    vocab = {w: (w,) for w in cats}
    W, B, info = train_readout(cats, vocab)
    ev = eval_readout(W, B, X.astype(np.float32), _index_of(cats, vocab))
    conf = confidence(W, B, X)                      # learned words: cm's own gate + softmax
    res["B1"] = dict(info, **ev, conf_min=min(c for c, _ in conf),
                     conf_mean=float(np.mean([c for c, _ in conf])),
                     conf_all_right=all(cats[k] == cats[i] for k, (_, i) in enumerate(conf)),
                     oov_fixed=_oov_stats(confidence(W, B, res["oov_fixed_slice"])),
                     oov_adj=_oov_stats(confidence(W, B, res["oov_adj_slice"])))

    if parity:                                     # batched math == cm.classify(), proven once
        checks = [cats[0], cats[n // 2], corpus[fixed0]]
        for w in checks:
            label, c = cm.classify(w)
            mine, idx = confidence(W, B, cm.encode(w)[None, :])[0]
            assert label == cm.CATEGORIES[idx], (w, label)
            assert abs(round(c, 4) - round(mine, 4)) <= 1e-4, (w, c, mine)
        res["B1"]["parity_words"] = len(checks)

    # (B2) production shape: the same 6 outputs, only the vocabulary grows
    vocab6 = {c: tuple(corpus[i] for i in range(n) if i % len(PROD_CATS) == k)
              for k, c in enumerate(PROD_CATS)}
    X6 = CODES[[pos[w] for c in PROD_CATS for w in vocab6[c]]]
    W6, B6, info6 = train_readout(PROD_CATS, vocab6)
    ev6 = eval_readout(W6, B6, X6.astype(np.float32), _index_of(PROD_CATS, vocab6))
    conf6 = confidence(W6, B6, X6)
    res["B2"] = dict(info6, **ev6, conf_min=min(c for c, _ in conf6),
                     conf_mean=float(np.mean([c for c, _ in conf6])),
                     below_floor=sum(1 for c, _ in conf6 if c < cm.CONFIDENCE_FLOOR),
                     oov_fixed=_oov_stats(confidence(W6, B6, res["oov_fixed_slice"])),
                     oov_adj=_oov_stats(confidence(W6, B6, res["oov_adj_slice"])))
    return res


def _oov_stats(conf):
    """Familiarity-gate margin for held-out words: they must stay below CONFIDENCE_FLOOR."""
    vals = np.array([c for c, _ in conf], dtype=np.float64)
    return {"mean": float(vals.mean()), "max": float(vals.max()),
            "margin": float(cm.CONFIDENCE_FLOOR - vals.max()),
            "above_floor": int((vals >= cm.CONFIDENCE_FLOOR).sum())}


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def _first_n(pairs, label="pair"):
    """Smallest vocabulary size at which a flagged pair coexists — exact, not grid-snapped."""
    return min(max(i, j) + 1 for i, j in pairs) if pairs else None


def _floor_breach_n():
    """The class count at which softmax normalisation alone crosses CONFIDENCE_FLOOR.

    With perfect ±1 separation and familiarity 1.0 the winner's probability is
    1/(1+(N-1)·e^(-2/T)): the denominator, not the connectome, sets this ceiling.
    """
    for n in range(2, 100000):
        if 1.0 / (1.0 + (n - 1) * np.exp(-2.0 / cm.TEMP)) < cm.CONFIDENCE_FLOOR:
            return n
    return None


def _lcp(a, b):
    """Longest common prefix of two folded words — the morphological cause of a collision."""
    a, b = cm.fold(a), cm.fold(b)
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def report_header(out, ctx):
    g = ctx["geo_max"]
    out("=" * 100)
    out("Phase 10 — FlyWire mushroom-body capacity benchmark  (two ceilings, kept apart)")
    out("=" * 100)
    out("corpus     : %s" % ctx["src"])
    out("             %d lines -> %d distinct words kept (%d fold-duplicates collapsed onto an "
        "existing code, %d non-words dropped)"
        % (ctx["stats"]["raw"], ctx["stats"]["kept"], ctx["stats"]["dup_fold"], ctx["stats"]["junk"]))
    out("             grid N = %s = the N most frequent words (nested prefixes: N=55 ⊂ N=100 ⊂ …)"
        % ", ".join(str(r["n"]) for r in ctx["results"]))
    out("pipeline   : cm.pn_code() -> cm.encode() == sniff.kc_code(pn, coincidence=%d) [imported]"
        % cm.COINCIDENCE)
    out("             %d ALPN -> %d KC  (mean %.1f active/code, %.2f%% density, range %d-%d)  -> readout"
        % (ctx["prod"]["pn_dim"], ctx["prod"]["kc_dim"], g["mean_active"], 100 * g["density"],
           int(g["counts"].min()), int(g["counts"].max())))
    out("readout    : cm.readout() — the production delta rule, called as-is (no re-implementation)")
    out("hyper      : lr = 1/mean-active, ±1 targets, ≤%d epochs, tol %g, T=%g, floor %g"
        % (cm.LR_MAX_EPOCHS, cm.LR_TOL, cm.TEMP, cm.CONFIDENCE_FLOOR))
    p = ctx["prod"]
    out("")
    out("PIPELINE PARITY — production vocabulary, measured before any global is repointed")
    out("  %d categories / %d words -> %.0f%% training accuracy in %d epochs (lr=%s, min correct %.2f)"
        % (len(PROD_CATS), ctx["vocab_size"], 100 * p["train_accuracy"], p["epochs"], p["lr"],
           ctx["prod_train"]["min_correct_score"]))
    out("  classify(): %d/%d vocabulary words correct, confidence %.3f-%.3f (floor %.2f)"
        % (ctx["prod_correct"], ctx["vocab_size"], p["vocab_confidence"]["min"],
           p["vocab_confidence"]["max"], cm.CONFIDENCE_FLOOR))
    out("  encoder identity: cm.encode(w) == sniff.kc_code(cm.pn_code(w), %d) on %d probes  [OK]"
        % (cm.COINCIDENCE, ctx["identity_n"]))
    out("  batched benchmark math reproduced cm.classify() exactly on %d words at N=%d  [OK]"
        % (ctx["results"][0]["B1"].get("parity_words", 0), ctx["results"][0]["n"]))


def report_a(out, ctx):
    n_max = ctx["results"][-1]["n"]
    words = ctx["words"]
    g = ctx["geo_max"]
    out("")
    out("CEILING A — raw KC code geometry (readout-independent: the codes alone, no training)")
    out("  %4s %9s %7s %8s %8s %8s %8s %9s %11s %8s %8s"
        % ("N", "meanAct", "dens%", "pairs", "meanJ", "p95J", "maxJ", "meanNN_J", "identical",
           "J>0.80", "J>0.50"))
    for r in ctx["results"]:
        gg = r["geo"]
        out("  %4d %9.1f %7.3f %8d %8.4f %8.4f %8.4f %9.4f %11d %8d %8d"
            % (r["n"], gg["mean_active"], 100 * gg["density"], gg["n_pairs"], gg["mean"], gg["p95"],
               gg["max"], float(gg["nearest"].mean()), gg["n_ident"], gg["n_collide"], gg["n_warn"]))
    ident_n, coll_n, warn_n = (_first_n(g["identical_pairs"]), _first_n(g["collide_pairs"]),
                               _first_n(g["warn_pairs"]))
    out("  first IDENTICAL codes (same active cells)  : %s"
        % ("— none up to N=%d" % n_max if ident_n is None else "N=%d" % ident_n))
    out("  first true collision (Jaccard > %.2f)       : %s"
        % (COLLISION, "— none up to N=%d" % n_max if coll_n is None else
           "N=%d (%d pair%s)" % (coll_n, g["n_collide"], "" if g["n_collide"] == 1 else "s")))
    out("  first suspect overlap (Jaccard > %.2f)      : %s"
        % (WARN, "— none up to N=%d" % n_max if warn_n is None else
           "N=%d (%d pairs at N=%d)" % (warn_n, g["n_warn"], n_max)))
    involved = len({i for i, _ in g["collide_pairs"]} | {j for _, j in g["collide_pairs"]})
    out("  codes involved in a collision at N=%d       : %d of %d" % (n_max, involved, n_max))
    cont_n = _first_n(g["contain_pairs"])
    out("  pairs sharing >%.0f%% of the smaller code   : %d at N=%d (first at N=%s), max "
        "containment %.3f" % (100 * COLLISION, g["n_contain"], n_max,
                             cont_n if cont_n else "— none", g["max_contain"]))
    out("    (the task's \"overlap above 80% shared cells\" read as containment, not Jaccard: a short")
    out("     code can be nearly swallowed by a longer one while their union stays large)")
    out("  most similar code pairs at N=%d (Jaccard | containment | shared-prefix):" % n_max)
    for k, (i, j, jv) in enumerate(g["worst"][:3]):
        out('    "%s" vs "%s"   J=%.3f  cont=%.3f  active=%d/%d  LCP=%d chars'
            % (words[i], words[j], jv, g["worst_c"][k], int(g["counts"][i]), int(g["counts"][j]),
               _lcp(words[i], words[j])))
    kd = ctx["prod"]["kc_dim"]
    out("  reading: independent random %d-cell subsets of %d would average J≈%.4f; the measured "
        "meanJ sits ~2×" % (int(g["mean_active"]), kd,
                            g["mean_active"] / (2 * kd - g["mean_active"])))
    out("           above that — 8 salts per n-gram over 685 PNs collide by construction — and "
        "only the tail above it")
    out("           is shared letters (morphology).")


def report_b1(out, ctx):
    res = ctx["results"]
    n_max, oov, fixed0 = res[-1]["n"], ctx["oov"], ctx["fixed0"]
    out("")
    out("CEILING B1 — the delta-rule readout, one output per word (N outputs: strictest test)")
    out("  deviation from production: the output layer grows with N; every hyper-parameter is "
        "production's")
    out("  %4s %7s %5s %7s %6s %8s %9s %8s %10s %11s %11s %6s"
        % ("N", "epochs", "conv", "acc", "wrong", "minCorr", "minMargin", "fragile",
           "inConf%min", "oovFix max", "oovAdj max", "sec"))
    for r in res:
        b = r["B1"]
        out("  %4d %7d %5s %7.3f %6d %8.3f %9.3f %8d %10.4f %11.4f %11.4f %6.1f"
            % (r["n"], b["epochs"], "yes" if b["converged"] else "CAP", b["acc"], b["n_wrong"],
               b["min_correct"], b["min_margin"], b["n_fragile"], b["conf_min"],
               b["oov_fixed"]["max"], b["oov_adj"]["max"], b["seconds"]))
    out("  conv = met production's ±1 tolerance (max|err| < %g) inside the cap; CAP = ran out of "
        "epochs, i.e. the" % cm.LR_TOL)
    out("  separation never got every output within ±1 — accuracy can still be 100%%, which is why "
        "both columns are reported.")
    drop = [r["n"] for r in res if r["B1"]["acc"] < 1.0]
    out("  accuracy first drops below 100%% at N=%s"
        % (drop[0] if drop else "— never in this grid (max N=%d)" % n_max))
    capped = [r["n"] for r in res if not r["B1"]["converged"]]
    near = max(res, key=lambda r: r["B1"]["epochs"])
    out("  epoch pressure: most epochs used = %d/%d at N=%d (%.0f%% of the cap)%s"
        % (near["B1"]["epochs"], cm.LR_MAX_EPOCHS, near["n"],
           100.0 * near["B1"]["epochs"] / cm.LR_MAX_EPOCHS,
           " — hit the cap at N=%s" % capped if capped else ""))
    wm = min(res, key=lambda r: r["B1"]["min_margin"])
    out("  separation margin at N=%d: min correct-vs-runner-up gap %.3f, %d word(s) within 0.10 of "
        "a tie" % (wm["n"], wm["B1"]["min_margin"], wm["B1"]["n_fragile"]))
    wc = min(res, key=lambda r: r["B1"]["conf_min"])
    out("  routing floor: min in-vocabulary confidence %.4f at N=%d vs floor %.2f "
        "(familiarity is exactly 1.0 on a learned word, so this is pure softmax)"
        % (wc["B1"]["conf_min"], wc["n"], cm.CONFIDENCE_FLOOR))
    out("     → with N outputs the winner's probability is 1/(1+(N-1)e^-2/T), which crosses %.2f "
        "at N=%d" % (cm.CONFIDENCE_FLOOR, _floor_breach_n()))
    out("  OOV fixed set (ranks %d-%d, outside every tested N): max confidence per N = %s"
        % (fixed0 + 1, fixed0 + oov,
           ", ".join("%d:%.3f" % (r["n"], r["B1"]["oov_fixed"]["max"]) for r in res)))
    out("  OOV adjacent set (ranks N+1…N+%d, the hardest words for that size): max = %s"
        % (oov, ", ".join("%d:%.3f" % (r["n"], r["B1"]["oov_adj"]["max"]) for r in res)))
    out("     (B1's values are also shrunk by the N-way softmax denominator; the same gate with 6 "
        "outputs reads up")
    out("      to %.4f at N=%d — more learned codes also means more near-miss familiarity for words "
        "the fly never learned)"
        % (res[-1]["B2"]["oov_fixed"]["max"], res[-1]["n"]))
    above = sum(r["B1"]["oov_fixed"]["above_floor"] + r["B1"]["oov_adj"]["above_floor"] for r in res)
    out("  OOV words that cleared the floor across every probe: %d (0 = the gate never invents a "
        "decision)" % above)


def report_b2(out, ctx):
    res = ctx["results"]
    out("")
    out("CEILING B2 — production shape: the same %d outputs, only the vocabulary grows"
        % len(PROD_CATS))
    out("  (production's own category list, words assigned round-robin → \"does the substrate still "
        "hold N words?\")")
    out("  %4s %7s %5s %7s %6s %8s %9s %10s %10s %10s %11s %11s"
        % ("N", "epochs", "conv", "catAcc", "wrong", "minCorr", "minMargin", "conf%min",
           "conf%mean", "belowFloor", "oovFix max", "oovAdj max"))
    for r in res:
        b = r["B2"]
        out("  %4d %7d %5s %7.3f %6d %8.3f %9.3f %10.4f %10.4f %10d %11.4f %11.4f"
            % (r["n"], b["epochs"], "yes" if b["converged"] else "CAP", b["acc"], b["n_wrong"],
               b["min_correct"], b["min_margin"], b["conf_min"], b["conf_mean"], b["below_floor"],
               b["oov_fixed"]["max"], b["oov_adj"]["max"]))
    out("  conv = same ±1 tolerance test as above. belowFloor = learned words whose production "
        "confidence has fallen")
    out("  under %.2f (unroutable even though the argmax is right)." % cm.CONFIDENCE_FLOOR)
    drop = [r["n"] for r in res if r["B2"]["acc"] < 1.0]
    out("  category accuracy first drops below 100%% at N=%s"
        % (drop[0] if drop else "— never (6 outputs, vocabulary up to N=%d)" % res[-1]["n"]))
    low = [r for r in res if r["B2"]["below_floor"]]
    out("  words below the routing floor: %s"
        % ("none — every learned word stays routable" if not low
           else ", ".join("N=%d:%d" % (r["n"], r["B2"]["below_floor"]) for r in low)))
    out("  note: a %d-output softmax does not suffer the N-output normalisation collapse "
        "(floor-crossing needs N≈%d classes)." % (len(PROD_CATS), _floor_breach_n()))


def report_verdict(out, ctx):
    res, g = ctx["results"], ctx["geo_max"]
    n_max, words = res[-1]["n"], ctx["words"]
    ident_n, coll_n, warn_n = (_first_n(g["identical_pairs"]), _first_n(g["collide_pairs"]),
                               _first_n(g["warn_pairs"]))
    drop1 = [r["n"] for r in res if r["B1"]["acc"] < 1.0]
    drop2 = [r["n"] for r in res if r["B2"]["acc"] < 1.0]
    cap1 = [r["n"] for r in res if not r["B1"]["converged"]]
    cap2 = [r["n"] for r in res if not r["B2"]["converged"]]
    low1 = [r["n"] for r in res if r["B1"]["conf_min"] < cm.CONFIDENCE_FLOOR]
    low2 = [r["n"] for r in res if r["B2"]["conf_min"] < cm.CONFIDENCE_FLOOR]
    out("")
    out("VERDICT")
    if coll_n is None:
        out("  Ceiling A (code collision)   : no true collision up to N=%d — max Jaccard %.3f, "
            "%d pair(s) above %.2f" % (n_max, g["max"], g["n_warn"], WARN))
    else:
        out("  Ceiling A (code collision)   : first true collision at N=%d (%d pair(s) at N=%d)"
            % (coll_n, g["n_collide"], n_max))
    if drop1:
        out("  Ceiling B (misclassification): accuracy drops below 100%% at N=%d (one output/word)"
            % drop1[0])
    else:
        out("  Ceiling B (misclassification): never below 100%% up to N=%d — one output/word%s"
            % (n_max, "" if not drop2 else "; 6-output shape also 100%"))
    out("  first identical codes         : %s"
        % ("— none" if ident_n is None else "N=%d" % ident_n))
    out("  first suspect overlap (J>%.2f) : %s"
        % (WARN, "— none" if warn_n is None else "N=%d" % warn_n))
    out("  containment (>%.0f%% of smaller code)  : %d pair(s) at N=%d, max %.3f, first at N=%s"
        % (100 * COLLISION, g["n_contain"], n_max, g["max_contain"],
           _first_n(g["contain_pairs"]) or "— none"))
    out("  ±1 tolerance (±%g) not met from : N=%s (one output/word), N=%s (6 outputs)"
        % (cm.LR_TOL, cap1[0] if cap1 else "— not in this grid",
           cap2[0] if cap2 else "— not in this grid"))
    out("  in-vocab confidence, per-word   : %s"
        % "  ".join("%d:%.3f" % (r["n"], r["B1"]["conf_min"]) for r in res))
    out("  in-vocab confidence, 6 outputs  : %s"
        % "  ".join("%d:%.3f" % (r["n"], r["B2"]["conf_min"]) for r in res))
    if low1 or low2:
        out("  → the routing floor (%.2f) is crossed by the weak end of the vocabulary at N=%s "
            "(one output/word)%s"
            % (cm.CONFIDENCE_FLOOR, low1[0] if low1 else "—",
               "" if not low2 else " and N=%d (6 outputs)" % low2[0]))
        out("    while every argmax is still correct: the readout runs out of *confidence* well "
            "before it runs out of accuracy.")
    elif not drop1 and coll_n is None:
        out("  → nothing misclassifies and no pair of codes collides, so neither the code space nor "
            "the decision is the")
        out("    limit yet: what erodes is confidence. The %.2f floor is not crossed up to N=%d, "
            "but the weakest" % (cm.CONFIDENCE_FLOOR, n_max))
        out("    learned word sits at %.3f (per-word) / %.3f (6 outputs) — margins of %+.3f / %+.3f."
            % (res[-1]["B1"]["conf_min"], res[-1]["B2"]["conf_min"],
               res[-1]["B1"]["conf_min"] - cm.CONFIDENCE_FLOOR,
               res[-1]["B2"]["conf_min"] - cm.CONFIDENCE_FLOOR))
    out("  (analytic cross-check: with N outputs and perfect ±1 separation the floor would need "
        "N≈%d classes;" % _floor_breach_n())
    out("   it breaks earlier in practice because the winner's own score also sags below +1 — "
        "measured %+.3f at N=%d)"
        % (res[-1]["B1"]["min_correct"], n_max))
    if g["worst"]:
        i, j, jv = g["worst"][0]
        out("  → the most similar pair at N=%d is \"%s\"/\"%s\" (J=%.3f, shared prefix %d chars). The "
            "tail" % (n_max, words[i], words[j], jv, _lcp(words[i], words[j])))
        out("    is our encoder (shared stems + n-gram hash collisions), not an exhausted 5177-cell "
            "code space, so any")
        out("    capacity claim has to be measured on inflected forms — which is what a frequency "
            "list gives you.")


def report_notes(out, ctx):
    out("")
    out("HONEST NOTES")
    out("  * B1 uses one output per word — a deliberate deviation from production's %d outputs, "
        "required to ask"
        % len(PROD_CATS))
    out("    \"can these two words be told apart at all?\". B2 keeps production's output layer and "
        "grows only the vocabulary.")
    out("  * The word→ALPN pattern (char 3/4-grams → 75 of 685 PNs) is OUR encoding; only the "
        "ALPN→KC step is measured.")
    out("    A different input encoding moves both ceilings: these numbers bound this pipeline, "
        "not \"the fly\".")
    out("  * %d surface forms in the corpus fold onto a code that already exists (ş/ı/ğ/ü/ö/ç → "
        "ASCII), so they are"
        % ctx["stats"]["dup_fold"])
    out("    unrepresentable at the input layer no matter how large the mushroom body is.")
    out("  * Training is deterministic but the grid is re-trained per N on nested prefixes, so rows "
        "are related, not")
    out("    independent samples; a single N is one draw, not a distribution.")
    out("  * Runtime is dominated by B1 at large N: when the delta rule cannot separate everything "
        "it runs to the")
    out("    %d-epoch cap, and that is exactly the measurement." % cm.LR_MAX_EPOCHS)
    out("  * The grid stops at N=%d (the Phase 10 request). Beyond it the B1 cost grows ~N² per "
        "epoch, so the" % ctx["results"][-1]["n"])
    out("    crossing should be re-measured rather than extrapolated — --n takes any sizes the "
        "corpus covers (%d words)." % ctx["stats"]["kept"])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="Phase 10 — mushroom-body capacity benchmark")
    ap.add_argument("--n", default=",".join(str(g) for g in GRID),
                    help="vocabulary sizes, comma separated (default: %(default)s)")
    ap.add_argument("--corpus", default=CORPUS_PATH,
                    help="ranked word list, one 'word frequency' per line (default: %(default)s)")
    ap.add_argument("--oov", type=int, default=N_OOV, help="held-out words per OOV probe")
    ap.add_argument("--log", default=None, help="also write the report to this UTF-8 file")
    args = ap.parse_args(argv)
    _utf8_stdout()
    grid = sorted({int(x) for x in args.n.split(",") if x.strip()})
    if not grid or grid[0] < 2:
        raise SystemExit("--n needs vocabulary sizes >= 2")
    out = Out(args.log)
    t0 = time.time()
    n_max = grid[-1]
    words, src, stats = load_corpus(args.corpus, n_max + 2 * args.oov + 1)
    if len(words) < n_max + 2 * args.oov:
        raise SystemExit("corpus has %d distinct words, need %d"
                         % (len(words), n_max + 2 * args.oov))
    ALL = words[:n_max + args.oov]          # trained region + the fixed held-out set
    fixed0 = n_max
    try:
        # ---- parity first, with the production vocabulary untouched
        save_cm_state()
        _reset_cm()
        cm.wire()
        cm.readout()
        prod = dict(cm.measured())
        prod_train = dict(cm._TRAIN_INFO)
        vocab_size = cm.VOCAB_SIZE
        prod_correct = sum(1 for cat in PROD_CATS for w in cm.VOCAB[cat]
                           if cm.classify(w)[0] == cat)
        identity_n = encoder_identity([ALL[0], ALL[len(ALL) // 2], ALL[fixed0]])

        print("encoding %d words through the real ALPN→KC matrix …" % len(ALL), file=sys.stderr)
        CODES, enc_s = kc_codes(ALL)
        print("  %.1f s (%.1f ms/word)" % (enc_s, 1000 * enc_s / len(ALL)), file=sys.stderr)

        results = []
        for k, n in enumerate(grid):
            print("[%d/%d] N=%d …" % (k + 1, len(grid), n), file=sys.stderr, flush=True)
            r = measure_n(n, ALL, CODES, fixed0, args.oov, parity=(k == 0))
            results.append(r)
            print("      A maxJ=%.3f | B1 acc=%.3f in %d/%d epochs | B2 catAcc=%.3f | %.1f s"
                  % (r["geo"]["max"], r["B1"]["acc"], r["B1"]["epochs"], cm.LR_MAX_EPOCHS,
                     r["B2"]["acc"], r["B1"]["seconds"] + r["B2"]["seconds"]),
                  file=sys.stderr, flush=True)

        ctx = {"results": results, "words": ALL, "src": src, "stats": stats, "oov": args.oov,
               "fixed0": fixed0, "geo_max": results[-1]["geo"], "prod": prod,
               "prod_train": prod_train, "vocab_size": vocab_size, "prod_correct": prod_correct,
               "identity_n": identity_n}
        report_header(out, ctx)
        report_a(out, ctx)
        report_b1(out, ctx)
        report_b2(out, ctx)
        report_verdict(out, ctx)
        report_notes(out, ctx)
        out("")
        out("  encoder %.1f ms/word (%.1f s for %d words)  |  total wall clock %.1f s"
            % (1000 * enc_s / len(ALL), enc_s, len(ALL), time.time() - t0))
        out("  rerun: python capacity_benchmark.py --n %s [--log capacity_report.txt]" % args.n)
    finally:
        restore_cm_state()                   # leave cognitive_matrix exactly as we found it
        out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

