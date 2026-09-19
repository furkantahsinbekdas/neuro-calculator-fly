"""
numcog/phase4e_step4_calc.py — FAZ 4E Adım 4'ün hesap makinesi kısmı (yeniden başlatılabilir).

Koşu, Adım 4 kalibrasyonu tamamlandıktan sonra (calib81.csv yazıldı) hesap makinesi
döngüsünde terminal kapanmasıyla kesildi. Bu betik AYNI kod yolunu kullanarak yalnızca
KABUL EDİLEN tohumlar için ölçümü tamamlar; her tohumdan sonra CSV'ye ekler (kesintiye dayanıklı).
Ön-kayıt ve konfigürasyon DEĞİŞMEDİ (4D en iyi hücre: ep 25000, lr 0.05, top-k 80, sigma=1.5, N=81).
"""
from __future__ import annotations
import os
import time

import numpy as np
import pandas as pd

import operator_diagnosis as od
import calculator as cal
import phase4c as p4c
import phase4e as p4e

OUT = p4e.OUT
N_BIG = p4e.N_BIG
BEST = dict(p4e.BEST)
SIGMA = p4e.SIGMA
FINAL = os.path.join(OUT, "final81_seeds.csv")
COLS = ["seed", "table", "add", "subtract", "multiply", "divide"]


def accepted_seeds():
    calib = pd.read_csv(os.path.join(OUT, "calib81.csv"))
    return [int(s) for s in calib[calib.accept == 1].seed]


def main():
    acc_list = accepted_seeds()
    p4e.log("\n=== ADIM 4 (devam): HESAP MAKINESI (kabul edilen %d tohum) ===" % len(acc_list))
    done = []
    if os.path.exists(FINAL):
        try:
            old = pd.read_csv(FINAL)
            if "seed" in old.columns and len(old):
                done = [int(s) for s in old.seed]
        except Exception:
            done = []
    if not done:
        pd.DataFrame(columns=COLS).to_csv(FINAL, index=False)
    else:
        p4e.log("devam: onceden olculen tohum %d" % len(done))
    mats = od.load_sets()
    pairs = p4e.pairs_all()
    for s in acc_list:
        if s in done:
            continue
        t0 = time.time()
        code = p4c.make_code(N_BIG, s, mats, SIGMA, 0.0, None, BEST["topk"])
        X = np.array([code(n, op) for n, op in pairs], np.float32)
        y = np.array([od.clip_result(n, op, N_BIG) for n, op in pairs])
        W, b = p4c.fit_fast(X, y, N_BIG + 1, BEST["lr"], BEST["epochs"], s)
        core = p4c.Core(N_BIG, code, W, b)
        r = od.calc_measure(N_BIG, s, mats, core)
        row = dict(seed=s, table=float(np.mean(np.argmax(X @ W.T + b, 1) == y)),
                   add=r["add"], subtract=r["subtract"], multiply=r["multiply"], divide=r["divide"])
        pd.DataFrame([row], columns=COLS).to_csv(FINAL, mode="a", header=False, index=False)
        p4e.log("  tohum %3d: tablo=%.4f add=%.3f sub=%.3f mul=%.3f div=%.3f (%.0fs)"
                % (s, row["table"], r["add"], r["subtract"], r["multiply"], r["divide"],
                   time.time() - t0))

    df = pd.read_csv(FINAL)
    p4e.log("kabul edilen %d tohumda (N=%d; tum 9x9=%d <= 81 temsil edilebilir):"
            % (len(df), N_BIG, 81))
    for k in ("add", "subtract", "multiply", "divide"):
        m = float(df[k].mean())
        sd = float(df[k].std(ddof=1)) if len(df) > 1 else 0.0
        ci = 1.96 * sd / np.sqrt(len(df))
        p4e.log("  %-9s ort=%.4f +- %.4f  min=%.4f  GA95=[%.4f,%.4f]  dagilim=%s"
                % (k, m, sd, df[k].min(), m - ci, m + ci,
                   dict(df[k].value_counts().sort_index())))
    # zincir p^k: yalnizca kontrolcü cagrilari (yeniden egitim yok, hizli)
    chain = []
    for s in [int(x) for x in df.seed]:
        code = p4c.make_code(N_BIG, s, mats, SIGMA, 0.0, None, BEST["topk"])
        X = np.array([code(n, op) for n, op in pairs], np.float32)
        y = np.array([od.clip_result(n, op, N_BIG) for n, op in pairs])
        W, b = p4c.fit_fast(X, y, N_BIG + 1, BEST["lr"], BEST["epochs"], s)
        r = od.calc_measure(N_BIG, s, mats, p4c.Core(N_BIG, code, W, b))
        chain.extend(r["chain"])
    cdf = cal.chain_vs_k(chain, float(df["add"].mean()))
    cdf.to_csv(os.path.join(OUT, "final81_chain.csv"), index=False)
    p4e.log("zincir k vs p^k (ilk 4 / son 4):")
    p4e.log(cdf.head(4).to_string(index=False))
    p4e.log(cdf.tail(4).to_string(index=False))
    p4e.log("\nAdim 4 tamamlandi.")


if __name__ == "__main__":
    main()
