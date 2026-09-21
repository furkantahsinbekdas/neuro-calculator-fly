"""
numcog/fly_calc.py — SİNEK HESAP MAKİNESİ SERVİSİ (yeni kod; tarihsel dosyaları DEĞİŞTİRMEZ).

İş bölümü (açık): **sinek** yalnızca `n -> n±1` tek adımını yapar (eğitilmiş okuma);
**kontrolcü** (tarihsel `calculator.CyborgFly`) sayaç/döngü/durma koşulunu tutar ve durumu taşır.
Bu modül yalnızca: (a) hızlı çekirdek yükleme, (b) ifade ayrıştırma, (c) **sınır doğrulaması**,
(d) adım dökümü/JSON üretimi ekler.

`expected()` **YALNIZCA doğrulama** içindir (sonucun 0..81 içinde olduğunu kontrol etmek ve testte
beklenen değeri üretmek); **yanıt yolu değildir** — yanıt her zaman `core.step` çağrılarından çıkar.
"""
from __future__ import annotations
import json
import os
import re
import sys

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import calculator as cal                      # tarihsel kontrolcü (DOKUNULMADI)
from operator_diagnosis import clip_result    # tarihsel kırpma tanımı (beklenen değer için)

MIN_V, MAX_V = 0, 81
DIV_Q_CAP = 50           # kontrolcünün tarihsel durma sınırı: `while n >= b and q < 50`
WEIGHTS_DIR = os.path.join(HERE, "fly_weights")


class OutOfRange(Exception):
    """Sonuç sineğin tablosunun dışında (sessiz yanlış cevap YOK)."""


class BadExpr(Exception):
    """Ayrıştırılamayan ya da tam sayı olmayan girdi."""


def default_weights():
    if not os.path.isdir(WEIGHTS_DIR):
        return None
    fs = sorted(f for f in os.listdir(WEIGHTS_DIR) if f.endswith(".npz"))
    return os.path.join(WEIGHTS_DIR, fs[0]) if fs else None


class CachedCore:
    """`phase4c.Core` ile aynı sözleşme: `.step(n, op) -> (digit, confidence)`."""

    def __init__(self, path):
        d = np.load(path, allow_pickle=True)
        self.W = d["W"].astype(np.float32)
        self.b = d["b"].astype(np.float32)
        self.X = sp.csr_matrix((d["X_data"], d["X_indices"], d["X_indptr"]),
                               shape=tuple(int(x) for x in d["X_shape"]))
        self.pairs = [(int(n), "+" if int(o) == 0 else "-")
                      for n, o in zip(d["pair_n"], d["pair_op"])]
        self.index = {p: i for i, p in enumerate(self.pairs)}
        self.meta = json.loads(str(d["meta"][0]))
        self.seed = int(self.meta["seed"])
        self.N = int(self.meta["N"])
        self.path = path

    def _scores(self, i):
        return self.X[i].toarray()[0] @ self.W.T + self.b

    def step(self, n, op):
        key = (int(n), op)
        if key not in self.index:
            raise OutOfRange("sinek tablosunda (%d,%s) yok" % (n, op))
        s = self._scores(self.index[key])
        d = int(np.argmax(s))
        e = np.exp(s - s.max())
        return d, float(e[d] / e.sum())

    def train_accuracy(self):
        y = np.array([clip_result(n, op, self.N) for n, op in self.pairs], np.int64)
        S = self.X @ self.W.T + self.b
        return float(np.mean(np.argmax(S, 1) == y))


class FakeCore:
    """SAHTE SİNEK: tek adımda rastgele bir rakam döndürür (integrity testi için)."""

    def __init__(self, seed=0, N=MAX_V):
        self.rng = np.random.RandomState(seed)
        self.N = N
        self.seed = -1
        self.meta = dict(seed=-1, fake=True)

    def step(self, n, op):
        return int(self.rng.randint(0, self.N + 1)), 1.0 / (self.N + 1)

    def train_accuracy(self):
        return float("nan")


_OPS = {"+": "add", "-": "subtract", "*": "multiply", "x": "multiply", "X": "multiply",
        "\u00d7": "multiply", "/": "divide", ":": "divide"}
_PAT = re.compile(r"^\s*(\d+)\s*([+\-*/xX:\u00d7])\s*(\d+)\s*$")


def parse(expr):
    """'3+5', '12-7', '7x8', '9/4' -> (a, op_adı, b). Yalnızca tam sayı kabul edilir."""
    s = (expr or "").strip().replace("?", " ").replace("=", " ")
    s = re.sub(r"\s+", " ", s).strip()
    m = _PAT.match(s)
    if not m:
        raise BadExpr("ayrıştırılamadı: %r (yalnızca 'a op b' biçimi, tam sayılar)" % expr)
    a, sym, b = int(m.group(1)), m.group(2), int(m.group(3))
    return a, _OPS[sym], b


def expected(a, op, b):
    """BEKLENEN değer — yalnızca sınır doğrulaması ve test karşılaştırması (yanıt yolu değil)."""
    if op == "add":
        return a + b, None
    if op == "subtract":
        return a - b, None            # negatif olabilir -> çağıran OutOfRange verir
    if op == "multiply":
        return a * b, None
    if op == "divide":
        if b == 0:
            raise BadExpr("bölme: bölen 0 olamaz")
        return a // b, a % b
    raise BadExpr("bilinmeyen işlem: %s" % op)


def controller_ops(a, op, b):
    """Kontrolcünün yaptığı işin düz metni (sineğin YAPMADIĞI kısım)."""
    if op == "add":
        return ["başlangıç: n = %d (sayaç, kontrolcüde)" % a,
                "döngü: %d kez  n = sinek(n, '+')" % b,
                "durma: sayaç %d kez döndü" % b]
    if op == "subtract":
        return ["başlangıç: n = %d" % a,
                "döngü: %d kez  n = sinek(n, '-')" % b,
                "durma: %d kez döndü (taban 0'da kırpılır)" % b]
    if op == "multiply":
        return ["başlangıç: toplam = 0",
                "dış döngü: %d kez  toplam = add(toplam, %d)" % (b, a),
                "iç döngü: her add = %d kez sinek(., '+')" % a,
                "durma: %d x %d = %d sinek adımı" % (b, a, a * b)]
    return ["başlangıç: n = %d, bölüm q = 0" % a,
            "durma koşulu: while n >= %d  (üst güvenlik sınırı q < 50)" % b,
            "her adım: n = subtract(n, %d) -> %d kez sinek(., '-')" % (b, b),
            "sonuç: q = tam bölüm, n = kalan"]


def run(expr, fake=False, weights=None, step_by_step=True):
    """Bir ifadeyi sinek + kontrolcü ile çalıştırır; sonucu ve iş bölümünü döndürür."""
    a, op, b = parse(expr)
    val, rem = expected(a, op, b)                    # YALNIZCA doğrulama
    if val > MAX_V:
        raise OutOfRange("sonuç %d > %d: sinek tablosu 0..%d ile sınırlı" % (val, MAX_V, MAX_V))
    if val < MIN_V:
        raise OutOfRange("sonuç %d < %d: sinek tablosu 0..%d ile sınırlı (negatif yok)"
                         % (val, MIN_V, MAX_V))
    if a > MAX_V or b > MAX_V:
        raise OutOfRange("operand > %d: sinek tablosunda yok" % MAX_V)
    if op == "divide" and val >= DIV_Q_CAP:
        # Kontrolcünün tarihsel durma sınırı: `while n >= b and q < 50`.
        # Bölüm 50'ye ulaşırsa döngü erken durur -> sonuç kırpılır. Sessiz yanlış cevap olmasın.
        raise OutOfRange("bölüm %d >= %d: kontrolcünün durma sınırı (q < %d) sonucu kırpar; "
                         "sinek tablosu 0..%d ama kontrolcü döngüsü erken duruyor"
                         % (val, DIV_Q_CAP, DIV_Q_CAP, MAX_V))
    path = weights or default_weights()
    if fake:
        core = FakeCore(seed=abs(hash(expr)) % 1000)
    else:
        if not path:
            raise BadExpr("ağırlık dosyası yok: önce `python -X utf8 numcog/build_fly.py`")
        core = CachedCore(path)
    cf = cal.CyborgFly(core)
    if op == "divide":
        q, rest = cf.divide(a, b)
        result, remainder = int(q), int(rest)
    else:
        result = int(getattr(cf, op)(a, b))
        remainder = None
    ticks = [dict(i=i + 1, n=int(n), op=o, out=int(d), confidence=float(c))
             for i, (n, o, d, c) in enumerate(cf.log)]
    two_digit = bool(a > 9 or b > 9)
    return dict(ok=True, expr=expr, op=op, a=a, b=b, result=result,
                remainder=remainder, expected=val, expected_matches=bool(result == val),
                fly_calls=int(cf.calls), ticks=ticks if step_by_step else [],
                n_ticks=len(ticks), controller_ops=controller_ops(a, op, b),
                seed=int(getattr(core, "seed", -1)), calibrated=bool(not fake),
                fake=bool(fake), two_digit=two_digit,
                note=("SAHTE SİNEK ETKİN: çekirdek rastgele çıktı veriyor" if fake else
                      ("iki haneli girdi (KEŞİFSEL): sonuç <= %d" % MAX_V if two_digit else
                       "1..9 ölçülmüş alan")))


def result_only(expr, **kw):
    """Kısa yol: yalnızca sonuç (arayüzün sade yanıtı)."""
    r = run(expr, step_by_step=False, **kw)
    return r["result"] if r["remainder"] is None else (r["result"], r["remainder"])


if __name__ == "__main__":
    w = default_weights()
    out = run(sys.argv[1] if len(sys.argv) > 1 else "3+5", weights=w)
    out["ticks"] = out["ticks"][:6] + [dict(note="... toplam %d adım" % out["n_ticks"])]
    print(json.dumps(out, ensure_ascii=False, indent=1))

