"""Faz 7-2 tasarim tabanlari (olcumden ONCE): sans duzeyi + 'en sik sinif' taban cizgisi.

Tasarim ozelligidir (model olcumu DEGIL): 7-1 ile ayni tohumlu dizi ureteci kullanilir.
"""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reservoir_run as R          # yalnizca saf yardimcilar (make_sequences); 7-1'e YAZMAZ

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_p7_2")
os.makedirs(OUT, exist_ok=True)

K_GRID = (2, 4, 6, 8, 10)
lines = []
cnt = {k: collections.Counter() for k in K_GRID}
tot = 0
for s in range(10):
    rng = np.random.RandomState(20000 + s)
    P = R.make_sequences(R.TRAIN_N + R.VAL_N + R.TEST_N, rng, 10, 8)
    tot += len(P)
    for k in cnt:
        cnt[k].update(P[:, :k].sum(1).tolist())
lines.append("Faz 7-2 tasarim tabanlari (tohum 0..9, %d dizi)" % tot)
for k in K_GRID:
    c = cnt[k]
    n = sum(c.values())
    lines.append("k=%2d  ulasilabilir sinif=%2d  sans=%.4f  en_sik_sinif_tabani=%.4f"
                 % (k, len(c), 1.0 / len(c), max(c.values()) / n))
txt = "\n".join(lines)
print(txt)
with open(os.path.join(OUT, "design_baselines.txt"), "w", encoding="utf-8") as f:
    f.write(txt + "\n")
