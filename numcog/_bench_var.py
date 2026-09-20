"""Geçici: scipy seyrek matvec varyantlari (hiz)."""
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
pair = np.stack([remap[a].astype(np.int64), remap[b].astype(np.int64)], 1)
pairs, inv = np.unique(pair, axis=0, return_inverse=True)
ww = np.zeros(len(pairs)); np.add.at(ww, inv.ravel(), w.astype(np.float64))
N = len(nodes)
Wc = sp.csr_matrix((ww, (pairs[:, 0], pairs[:, 1])), shape=(N, N))
Wc.sort_indices()
Wt = sp.csr_matrix((ww, (pairs[:, 1], pairs[:, 0])), shape=(N, N))
Wf = Wc.astype(np.float32)
B = 64
X = np.random.RandomState(0).normal(size=(N, B))
Xf = np.asfortranarray(X)
X32 = X.astype(np.float32)
for tag, fn in (
        ("CSR@C-order", lambda: Wc @ X),
        ("CSR@F-order", lambda: Wc @ Xf),
        ("CSR32@C-order", lambda: Wf @ X32),
):
    fn()
    t0 = time.time()
    for _ in range(20):
        fn()
    dt = (time.time() - t0) / 20
    print("%-16s %.1f ms/adim | tohum-kol(355 adim x 720 dizi, B=64) = %.0f s"
          % (tag, dt * 1e3, dt * 355 * 720 / B), flush=True)
