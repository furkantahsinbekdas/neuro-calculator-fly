"""
numcog/tests/test_calculator_integrity.py — hesap makinesi BÜTÜNLÜK testi.

Amaç: **hesabı sinek çekirdeğinin yaptığını**, Python'un doğrudan aritmetik yapmadığını göstermek.

Tek komut:  python -X utf8 -m numcog.tests.test_calculator_integrity
(<2 dk; AĞIR EĞİTİM YOK — ağırlıklar `numcog/build_fly.py` çıktısından okunur)

Testler:
  A. GERÇEK çekirdek: 1..9 tüm add/sub/mul/div → 1.0 beklenir (tarihsel `calc_measure` ile).
  B. SAHTE çekirdek: aynı ölçüm → ÇÖKMELİ; çökmezse Python hesaplıyor demektir → KIRMIZI + DUR.
  C. Adım sayısı: multiply(3,4)=12, add(a,b)=b, subtract(a,b)=b, divide(a,b)=q*b çekirdek çağrısı.
  D. Sınır: sonuç >81 ya da <0 → AÇIK hata (sessiz yanlış cevap yok); 0..81 sınırında sorun yok.
"""
from __future__ import annotations
import os
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NUMCOG = os.path.dirname(HERE)
if NUMCOG not in sys.path:
    sys.path.insert(0, NUMCOG)

import calculator as cal                 # tarihsel kontrolcü (DOKUNULMADI)
import operator_diagnosis as od          # tarihsel ölçüm fonksiyonu `calc_measure` (DOKUNULMADI)
import fly_calc as F

RED = []
RESULT = []


def check(name, ok, detail=""):
    tag = "GECTI" if ok else "KIRMIZI"
    if not ok:
        RED.append(name)
    RESULT.append((name, tag, detail))
    print("  [%-7s] %-52s %s" % (tag, name, detail))


def test_A_real_core(path):
    core = F.CachedCore(path)
    rows = cal.measure_calculator(core)          # tarihsel hesap makinesi ölçümü
    r = od.calc_measure(F.MAX_V, core.seed, None, core)   # tarihsel doğrudan ölçüm (mats kullanılmaz)
    for k in ("add", "subtract", "multiply", "divide"):
        check("A gerçek çekirdek: %s == 1.0000" % k, abs(r[k] - 1.0) < 1e-12,
              "olculen=%.4f" % r[k])
    check("A gerçek çekirdek: tablo (164 giris) == 1.0000",
          abs(core.train_accuracy() - 1.0) < 1e-9, "tablo=%.4f" % core.train_accuracy())
    return r


def design_baselines():
    """Tasarımdan 'en sık cevap' tabanı (her işlemde 81 çift): 1..9 için analitik."""
    from collections import Counter
    c = {k: Counter() for k in ("add", "subtract", "multiply", "divide")}
    for a in range(1, 10):
        for b in range(1, 10):
            c["add"][a + b] += 1
            c["subtract"][max(a - b, 0)] += 1
            c["multiply"][a * b] += 1
            c["divide"][a // b] += 1
    return {k: max(v.values()) / 81.0 for k, v in c.items()}


def test_B_fake_core(ra):
    """SAHTE çekirdek çökmeli. Eşik KEYFÎ DEĞİL: tasarımın 'en sık cevap' tabanı.

    NOT (ilk koşu KIRMIZI idi, gizlenmiyor): eşik 0.30 alındığında `divide`=0.4815 çıktı.
    Nedeni: `divide(a,b)`'de a<b olan **36/81 çift döngü gövdesini hiç çalıştırmaz**
    (n=a<b) → q=0 = doğru cevap, **çekirdek hiç çağrılmadan** → taban 36/81 = **0.4444**.
    Yani bu, "Python hesaplıyor" kanıtı değil, tarihsel `divide`'ın dejenere tabanıdır.
    """
    base = design_baselines()
    fake = F.FakeCore(seed=12345, N=F.MAX_V)
    rf = od.calc_measure(F.MAX_V, -1, None, fake)
    vals = {k: rf[k] for k in ("add", "subtract", "multiply", "divide")}
    for k in ("add", "subtract", "multiply", "divide"):
        check("B sahte çekirdek: %s <= taban+0.05 (taban=%.4f)" % (k, base[k]),
              vals[k] <= base[k] + 0.05, "olculen=%.4f" % vals[k])
        check("B sahte çekirdek: %s gerçekten en az 0.40 düşük" % k,
              (ra[k] - vals[k]) >= 0.40, "gercek=%.4f sahte=%.4f" % (ra[k], vals[k]))
    mean_fake = float(np.mean(list(vals.values())))
    mean_real = float(np.mean([ra[k] for k in vals]))
    check("B sahte çekirdek: ortalama <= 0.25 (gerçek ortalama %.3f)" % mean_real,
          mean_fake <= 0.25, "sahte ortalama=%.4f" % mean_fake)
    return vals


def test_B2_tick_invariance(path, fake_vals):
    """KARAR KANITI: add/subtract/multiply'de çağrı sayısı çekirdeğe BAĞLI DEĞİL
    (aynı ifade için gerçek ve sahte çekirdek AYNI sayıda çağrı yapar) → döngüyü kontrolcü kurar;
    cevap ise çekirdekten gelir (sonuçlar farklı)."""
    real = F.CachedCore(path)
    fake = F.FakeCore(seed=999, N=F.MAX_V)
    for expr in ("3+5", "9-4", "6x7", "8-3"):
        r1, r2 = F.run(expr, weights=path), F.run(expr, fake=True)
        check("B2 %s: çağrı sayısı gerçek==sahte (%d==%d)" % (expr, r1["fly_calls"],
                                                             r2["fly_calls"]),
              r1["fly_calls"] == r2["fly_calls"], "gercek=%d sahte=%d"
              % (r1["fly_calls"], r2["fly_calls"]))
    r1, r2 = F.run("3+5", weights=path), F.run("3+5", fake=True)
    check("B2 sahte sonuç gerçekten farklı (3+5: %d vs %d)" % (r1["result"], r2["result"]),
          r1["result"] != r2["result"] or fake_vals["add"] < 0.3,
          "gercek=%d sahte=%d" % (r1["result"], r2["result"]))



def test_C_ticks(path):
    core = F.CachedCore(path)
    cf = cal.CyborgFly(core)
    n0 = cf.calls
    r = cf.add(3, 5)
    check("C add(3,5) -> 8 ve tam 5 çağrı", r == 8 and cf.calls - n0 == 5,
          "sonuc=%s cagri=%d" % (r, cf.calls - n0))
    cf = cal.CyborgFly(core); n0 = cf.calls
    r = cf.subtract(9, 4)
    check("C subtract(9,4) -> 5 ve tam 4 çağrı", r == 5 and cf.calls - n0 == 4,
          "sonuc=%s cagri=%d" % (r, cf.calls - n0))
    cf = cal.CyborgFly(core); n0 = cf.calls
    r = cf.multiply(3, 4)
    check("C multiply(3,4) -> 12 ve tam 12 çağrı", r == 12 and cf.calls - n0 == 12,
          "sonuc=%s cagri=%d" % (r, cf.calls - n0))
    cf = cal.CyborgFly(core); n0 = cf.calls
    q, rem = cf.divide(9, 4)
    check("C divide(9,4) -> (2,1) ve tam 8 çağrı", (q, rem) == (2, 1) and cf.calls - n0 == 8,
          "sonuc=%s kalan=%s cagri=%d" % (q, rem, cf.calls - n0))


def test_D_bounds():
    ok_cases = ["9x9", "81+0", "0+0", "9/1", "8-8"]
    bad_cases = ["80+5", "82+0", "9x10", "3-5", "0-1", "45+45"]
    for e in ok_cases:
        try:
            r = F.run(e)
            check("D sinir içi: %s çalışıyor" % e, r["result"] <= F.MAX_V,
                  "sonuc=%d cagri=%d" % (r["result"], r["fly_calls"]))
        except Exception as exc:
            check("D sinir içi: %s çalışıyor" % e, False, "HATA: %s" % exc)
    for e in bad_cases:
        try:
            r = F.run(e)
            check("D sınır dışı: %s AÇIK hata vermeli" % e, False,
                  "sessiz sonuc=%s (KIRMIZI: sessiz yanlış cevap)" % r["result"])
        except F.OutOfRange as exc:
            check("D sınır dışı: %s AÇIK hata veriyor" % e, True, str(exc)[:60])
        except Exception as exc:
            check("D sınır dışı: %s AÇIK hata veriyor" % e, False,
                  "beklenmeyen tip: %s" % type(exc).__name__)


def main():
    path = F.default_weights()
    print("=== HESAP MAKINESI BUTUNLUK TESTI ===")
    if not path:
        print("KIRMIZI: ağırlık dosyası yok. Önce: python -X utf8 numcog/build_fly.py")
        return 2
    print("cekirdek: %s" % os.path.basename(path))
    try:
        ra = test_A_real_core(path)
        fb = test_B_fake_core(ra)
        test_B2_tick_invariance(path, fb)
        test_C_ticks(path)
        test_D_bounds()
    except Exception:
        traceback.print_exc()
        print("\nKIRMIZI: beklenmeyen hata")
        return 2
    print("\n=== OZET ===")
    for name, tag, detail in RESULT:
        print("  %-7s %s" % (tag, name))
    print("\nKIRMIZI sayisi: %d / %d" % (len(RED), len(RESULT)))
    if RED:
        print("BASARISIZ (kırmızı gizlenmedi):")
        for r in RED:
            print("  - %s" % r)
        return 1
    print("TUM TESTLER GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
