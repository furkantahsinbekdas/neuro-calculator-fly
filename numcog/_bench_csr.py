"""Geçici: scipy CSR x yogun durum matrisi hizi (gercek A alt agi)."""
import time
import numpy as np
import scipy.sparse as sp

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
nodes = np.unique(np.concatenate([a, b]))
remap = -np.ones(int(nodes.max()) + 1, np.int32)
remap[nodes] = np.arange(len(nodes), dtype=np.int32)
r = remap[a]; c2 = remap[b]
pair = np.stack([r.astype(np.int64), c2.astype(np.int64)], 1)
pairs, inv = np.unique(pair, axis=0, return_inverse=True)
ww = np.zeros(len(pairs)); np.add.at(ww, inv.ravel(), w.astype(np.float64))
N = len(nodes); E = len(pairs)
W = sp.csr_matrix((ww, (pairs[:, 0], pairs[:, 1])), shape=(N, N))
print("N=%d E=%d nnz=%d | komsu/notron ort=%.1f" % (N, E, W.nnz, E / N))
rng = np.random.RandomState(0)
for B in (64, 128, 256, 500):
    X = rng.normal(size=(N, B))
    t0 = time.time()
    for _ in range(20):
        X = np.tanh(W @ X)
    dt = (time.time() - t0) / 20
    print("B=%-4d adim=%6.1f ms | 101 adim x 3000/B = %.1f s/tohum-kol" % (B, dt * 1e3, dt * 101 * 3000 / B))
