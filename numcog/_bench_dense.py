"""Geçici: yoğun BLAS matmul vs seyrek reduceat hızı (A alt ağı, N=4236)."""
import time
import numpy as np

N = 4236
rng = np.random.RandomState(0)
Wd = rng.normal(0, 1e-3, size=(N, N)).astype(np.float64)
Wf = Wd.astype(np.float32)
for B in (32, 128, 500):
    X = rng.normal(size=(N, B))
    for tag, W, Xt in (("f64", Wd, X), ("f32", Wf, X.astype(np.float32))):
        t0 = time.time()
        for _ in range(20):
            Y = W @ Xt
            Xt = np.tanh(Y)
        dt = (time.time() - t0) / 20
        print("%s B=%-3d adim=%.1f ms | 101 adim x 3000/B yigin=%.1f s"
              % (tag, B, dt * 1e3, dt * 101 * 3000 / B))
try:
    import scipy.sparse as sp
    print("scipy VAR")
    Wc = sp.csr_matrix(Wd * (rng.random((N, N)) < 0.0166))
    X = rng.normal(size=(N, 128))
    t0 = time.time()
    for _ in range(20):
        X = np.tanh(Wc @ X)
    dt = (time.time() - t0) / 20
    print("scipy CSR B=128 adim=%.1f ms | yigin=%.1f s" % (dt * 1e3, dt * 101 * 3000 / 128))
except ImportError:
    print("scipy YOK")
