"""
_calc_smoke.py — İKAME smoke test (kayıp `_fly_smoke.py`/`_fly_frontend_test.js` yerine).

NEDEN İKAME: kapanış paketinin istediği iki test dosyası repoda **yoktur** (bkz.
`numcog/RELEASE_PREFLIGHT.md` §6). Bu betik onların yerine geçer ve şunu kanıtlar:
  (1) mevcut uçlar (`/health`, `/state`, `/chat`) HÂLÂ çalışıyor  -> kelime sınıflandırma bozulmadı
  (2) YENİ `/calc` ucu 1..9 tüm çiftlerde 4 işlemde DOĞRU
  (3) `fake=1` ile SAHTE sinek cevapları BOZULUYOR
  (4) sınır dışı istek AÇIK hata dönüyor (sessiz yanlış cevap yok)

Kullanım (sunucu 8000'de çalışıyorsa):
    python -X utf8 _calc_smoke.py
Sunucu yoksa: önce `python -X utf8 server.py`.
"""
from __future__ import annotations
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
RED = []


def _req(path, payload=None, timeout=30):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method=("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def check(name, ok, detail=""):
    if not ok:
        RED.append(name)
    print("  [%s] %-58s %s" % ("OK  " if ok else "KIRMIZI", name, detail))


def main():
    print("=== CALC SMOKE (mevcut uçlar + /calc + sahte mod + sınır) ===")
    st, h = _req("/health")
    check("mevcut uç /health yanıt veriyor", st == 200 and h.get("ok") is True, str(h)[:60])
    st, s = _req("/state")
    check("mevcut uç /state yanıt veriyor", st == 200 and len(s) > 0,
          "anahtarlar=%s" % ",".join(list(s)[:5]))
    st, c = _req("/chat", {"message": "elma"})
    ok_chat = st == 200 and bool(c.get("answer"))
    check("mevcut uç /chat kelime sınıflandırması çalışıyor", ok_chat,
          "cevap=%s" % str(c.get("answer"))[:40])
    # --- /calc: 1..9 tüm çiftler
    # DİKKAT (tasarım farkı, AŞAMA 1 §4.4): tarihsel `calc_measure` çıkarmayı 0'a KIRPAR
    # (want = max(a-b,0)); ARAYÜZ ise negatif sonucu **açıkça REDDEDER** (HTTP 422) — sessiz
    # yanlış cevap olmasın diye. Bu yüzden a<b çıkarmaları "değer" değil "ret" bekler.
    ops = {"+": lambda a, b: a + b, "-": lambda a, b: (a - b if a >= b else None),
           "x": lambda a, b: a * b, "/": lambda a, b: a // b}
    n_ok = n_tot = 0
    bad = []
    for a in range(1, 10):
        for b in range(1, 10):
            for sym, fn in ops.items():
                st, r = _req("/calc", {"expr": "%d%s%d" % (a, sym, b), "step_by_step": False})
                want = fn(a, b)
                if want is None:                       # çıkarma, negatif sonuç -> RET beklenir
                    good = (st == 422 and bool(r.get("out_of_range")))
                else:
                    good = (st == 200 and r.get("ok") and int(r.get("result", -1)) == want)
                n_tot += 1
                n_ok += int(good)
                if not good:
                    bad.append(("%d%s%d" % (a, sym, b), st, r.get("result"), want))
    check("/calc 1..9 tüm çiftler BEKLENEN davranış (324 istek)", n_ok == n_tot,
          "%d/%d; hatalı=%s" % (n_ok, n_tot, bad[:4]))
    # --- sahte sinek
    f_ok = f_tot = 0
    f_bad = []
    for a in range(1, 10):
        for b in range(1, 10):
            for sym, fn in ops.items():
                st, r = _req("/calc", {"expr": "%d%s%d" % (a, sym, b), "fake": True,
                                       "step_by_step": False})
                want = fn(a, b)
                good = (want is None and st == 422) or (want is not None and st == 200
                                                        and int(r.get("result", -1)) == want)
                f_tot += 1
                f_ok += int(good)
                if good and len(f_bad) < 4:
                    f_bad.append("%d%s%d->%s" % (a, sym, b, r.get("result")))
    acc_fake = f_ok / max(f_tot, 1)
    check("sahte sinek cevapları BOZULUYOR (doğruluk <= 0.60)", acc_fake <= 0.60,
          "sahte doğruluk=%.4f (rastgele=%d/%d)" % (acc_fake, f_ok, f_tot))
    st, r = _req("/calc", {"expr": "3+5", "fake": True})
    check("sahte modda 'not' alanı uyarı içeriyor", bool(r.get("note")) and "SAHTE" in str(r.get("note")),
          str(r.get("note"))[:50])
    # --- sınır
    for e in ("80+5", "3-5", "9x10"):
        st, r = _req("/calc", {"expr": e})
        check("sınır dışı %s AÇIK hata (HTTP 422)" % e, st == 422 and r.get("out_of_range"),
              "HTTP %s | %s" % (st, str(r.get("error"))[:50]))
    # --- sohbet kutusu: aritmetik ifade SİNEĞİN ÇEKİRDEĞİNE gider (kapanış sonrası düzeltme) ---
    st, cc = _req("/chat", {"message": "5+3=?"})
    check("sohbet: '5+3=?' sineğin çekirdeğiyle cevaplanıyor",
          st == 200 and "= 8" in str(cc.get("answer", ""))
          and cc.get("source") == "numcog_calculator",
          "kaynak=%s | cevap=%s" % (cc.get("source"), str(cc.get("answer"))[:52]))
    st, cd = _req("/chat", {"message": "9/4"})
    check("sohbet: '9/4' bölüm+kalan ile cevaplanıyor",
          st == 200 and "2" in str(cd.get("answer", ""))
          and ("kalan 1" in str(cd.get("answer", ""))
               or "remainder 1" in str(cd.get("answer", "")))
          and cd.get("source") == "numcog_calculator", str(cd.get("answer"))[:52])
    st, cw = _req("/chat", {"message": "ne haber"})
    check("sohbet: kelime yolu DEĞİŞMEDİ ('ne haber' hesap makinesine gitmiyor)",
          st == 200 and cw.get("source") != "numcog_calculator",
          "kaynak=%s" % cw.get("source"))
    st, ce = _req("/chat", {"message": "3 tane elma"})
    check("sohbet: harf içeren mesaj hesap makinesine GİTMİYOR",
          st == 200 and ce.get("source") != "numcog_calculator",
          "kaynak=%s" % ce.get("source"))
    print("\nKIRMIZI: %d" % len(RED))
    for r in RED:
        print("  - %s" % r)
    print("SONUC: %s" % ("TUM TESTLER GECTI" if not RED else "BASARISIZ"))
    return 1 if RED else 0


if __name__ == "__main__":
    sys.exit(main())
