"""Geçici fizibilite testi: A alt ağının (N=4236, E=298.532) toplu seyrek matvec hızı.
Ölçüm DEĞİL; yalnızca uygulama bütçesi için. Sonra silinecek."""
import time
import numpy as np
import pandas as pd
import number_coding as nc

CX_CORE = {"EB", "PB", "FB", "NO"}
d = np.load("results_p7_0/scan_cache.npz")
pre, post, syn = [], [], []
for c in CX_CORE:
    k = "np_%s_pre" % c
    if k in d.files:
        pre.append(d[k]); post.append(d["np_%s_post" % c]); syn.append(d["np_%s_syn" % c])
pre = np.concatenate(pre); post = np.concatenate(post); syn = np.concatenate(syn)
have = set(np.unique(pre).tolist()) & set(np.unique(post).tolist())
cells = np.array(sorted(have), dtype=np.int64)
m = np.isin(pre, cells) & np.isin(post, cells)
a, b, w = pre[m], post[m], syn[m]
# remap 0..N-1
nodes = np.unique(np.concatenate([a, b]))
remap = -np.ones(int(nodes.max()) + 1, np.int32)
remap[nodes] = np.arange(len(nodes), dtype=np.int32)
r = remap[a].astype(np.int64); c2 = remap[b].astype(np.int64)
# ikili + agirlik toplami
pair = np.stack([r, c2], 1)
pairs, inv = np.unique(pair, axis=0, return_inverse=True)
ww = np.zeros(len(pairs)); np.add.at(ww, inv.ravel(), w.astype(np.float64))
N = len(nodes); E = len(pairs)
print("N=%d E=%d yogunluk=%.4f" % (N, E, E / N / N))
# CSR-benzeri: satira gore sirala, her satiri bos olmayacak sekilde doldur
order = np.argsort(pairs[:, 0], kind="mergesort")
rows_s = pairs[order, 0]; cols_s = pairs[order, 1]; vals_s = ww[order]
empty = np.setdiff1d(np.arange(N), np.unique(rows_s))
if len(empty):  # bos satirlara 0 agirlikli kendine kenar
    rows_s = np.concatenate([rows_s, empty]); cols_s = np.concatenate([cols_s, empty])
    vals_s = np.concatenate([vals_s, np.zeros(len(empty))])
    o2 = np.argsort(rows_s, kind="mergesort")
    rows_s, cols_s, vals_s = rows_s[o2], cols_s[o2], vals_s[o2]
starts = np.searchsorted(rows_s, np.arange(N))
print("satir segmentleri hazir; her satir dolu:", len(starts) == N)
rng = np.random.RandomState(0)
for B in (8, 16, 32, 64):
    X = rng.normal(size=(N, B))
    t0 = time.time()
    n_it = 50
    for _ in range(n_it):
        Xg = X[cols_s] * vals_s[:, None]
        Y = np.add.reduceat(Xg, starts, axis=0)
        X = np.tanh(Y)
    dt = (time.time() - t0) / n_it
    print("B=%-3d adim=%.1f ms | 101 adimlik yigin=%.1f s | 3000 dizi=%.1f s (E*B=%.1e)"
          % (B, dt * 1e3, dt * 101, dt * 101 * 3000 / B, E * B))
