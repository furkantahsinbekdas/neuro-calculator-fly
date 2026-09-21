"""
numcog/two_digit_probe.py — AŞAMA 3 (KEŞİFSEL): İKİ HANELİ GİRDİ ölçümü.

Ön-kayıt: HIPOTEZLER.md "KAPANIŞ PAKETİ — KEŞİFSEL ön-kayıt: İKİ HANELİ GİRDİ ölçümü" (commit
`d6bd546`, ÖLÇÜMDEN ÖNCE). Tasarım orada sabit: ≥20 kabul edilen tohum, her işlem ≥200 çift,
sonuç [0,81] süzgeci, en az bir operand ≥10, çürütme eşiği **%99**.

Beklenti: sonuç ≤81 ise ÇALIŞIR (çekirdek yalnızca n→n±1 tablosu; operand büyüklüğü sonucu değiştirmez).
NOT: "çok haneli aritmetik" YOKTUR; iki haneli (onlar/birler) tasarımı UYGULANMADI.

Kullanım: python -X utf8 numcog/two_digit_probe.py [n_tohum]
Çıktı:    numcog/results_release/two_digit.csv
"""
from __future__ import annotations
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import calculator as cal
import operator_diagnosis as od
import phase4c as p4c
import build_fly as BF

OUTD = os.path.join(HERE, "results_release")
N = BF.N
SIGMA = BF.SIGMA
TOPK = BF.TOPK
PAIRS_PER_OP = 200
A_MIN, A_MAX = 1, 81


def sample_pairs(op, rng, n=PAIRS_PER_OP):
    """Ön-kayıtlı süzgeçle iki haneli çiftler: en az bir operand ≥10, sonuç [0,81]."""
    out = []
    guard = 0
    while len(out) < n and guard < 200000:
        guard += 1
        a = int(rng.randint(A_MIN, A_MAX + 1))
        b = int(rng.randint(A_MIN, A_MAX + 1))
        if max(a, b) < 10:                       # en az bir operand iki haneli olmalı
            continue
        if op == "add":
            if a + b > 81:
                continue
            out.append((a, b, a + b, None))
        elif op == "subtract":
            if a < b:
                continue
            out.append((a, b, a - b, None))
        elif op == "multiply":
            if a * b > 81:
                continue
            out.append((a, b, a * b, None))
        else:                                    # divide: tam bölme + kalan
            if b == 0:
                continue
            out.append((a, b, a // b, a % b))
    return out


def build_core(seed, mats):
    code = p4c.make_code(N, seed, mats, SIGMA, 0.0, None, TOPK)
    pairs = [(n, op) for n in range(N + 1) for op in ("+", "-")]
    X = np.array([code(n, op) for n, op in pairs], np.float32)
    y = np.array([od.clip_result(n, op, N) for n, op in pairs], np.int64)
    W, b = p4c.fit_fast(X, y, N + 1, BF.LR, BF.EPOCHS, seed)
    table = float(np.mean(np.argmax(X @ W.T + b, 1) == y))
    return p4c.Core(N, code, W, b), table


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seeds = BF.accepted_seeds()[:n_seeds]
    print("kabul edilen tohumlar (%d/%d): %s" % (len(seeds), n_seeds, seeds))
    mats = od.load_sets()
    rows = []
    t0 = time.time()
    for s in seeds:
        core, table = build_core(s, mats)
        if abs(table - 1.0) > 1e-9:
            print("  tohum %d tablo=%.4f -> kalibrasyon gecmedi, ATLANDI" % (s, table))
            continue
        rng = np.random.RandomState(4242 + s)
        for op, fn in (("add", "add"), ("subtract", "subtract"),
                       ("multiply", "multiply"), ("divide", "divide")):
            pairs = sample_pairs(op, rng)
            cf = cal.CyborgFly(core)
            ok = tot = 0
            for (a, b, want, rem) in pairs:
                if op == "divide":
                    q, r = cf.divide(a, b)
                    good = int(q == want and r == rem)
                else:
                    got = getattr(cf, fn)(a, b)
                    good = int(got == want)
                ok += good
                tot += 1
            rows.append(dict(seed=s, op=op, n=tot, ok=ok, acc=ok / tot,
                             table_acc=table, fly_calls=cf.calls))
            print("  tohum %3d %-9s %3d/%3d = %.4f (sinek cagrisi %d)"
                  % (s, op, ok, tot, ok / tot, cf.calls))
    df = pd.DataFrame(rows)
    os.makedirs(OUTD, exist_ok=True)
    df.to_csv(os.path.join(OUTD, "two_digit.csv"), index=False)
    print("\n=== OZET (iki haneli girdi; %d tohum x %d cift/islem) ===" % (len(seeds), PAIRS_PER_OP))
    for op in ("add", "subtract", "multiply", "divide"):
        sub = df[df.op == op]
        if not len(sub):
            continue
        m, sd = float(sub.acc.mean()), float(sub.acc.std(ddof=1) if len(sub) > 1 else 0.0)
        ci = 1.96 * sd / np.sqrt(len(sub))
        verdict = "CALISIYOR (>= %99)" if m >= 0.99 else "CURUDU (< %99)"
        print("  %-9s dogruluk=%.4f +- %.4f (n=%d tohum, %d cift) -> %s"
              % (op, m, ci, len(sub), int(sub.n.sum()), verdict))
    m_all = float(df.acc.mean())
    print("\n  GENEL dogruluk=%.4f | toplam cift=%d | sure=%.0f s | cikti: %s"
          % (m_all, int(df.n.sum()), time.time() - t0,
             os.path.join(OUTD, "two_digit.csv")))
    print("  esik %%99 -> %s" % ("GECTI" if m_all >= 0.99 else "GECMEDI (curutme)"))
    return 0 if m_all >= 0.99 else 1


if __name__ == "__main__":
    sys.exit(main())
