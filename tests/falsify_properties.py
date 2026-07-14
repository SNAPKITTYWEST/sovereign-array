"""
Layer 1: Property-Based Falsifier
==================================
Attacks the extracted C++20 kernels via Hypothesis.
Every test corresponds to a named Lean 4 theorem.

Run:
    pip install hypothesis pytest
    cmake -S .. -B ../build && cmake --build ../build
    pytest falsify_properties.py -x -v --tb=short

Pass criteria: zero failures after 100k shrunk examples.
If Hypothesis finds one counterexample, the Lean theorem was weaker than intent.
"""

import ctypes
import math
import os
import pathlib
import sys

import pytest
from hypothesis import given, settings, assume, Phase
from hypothesis import strategies as st

# ── Load the shared library ───────────────────────────────────────────────────

def _load_lib():
    repo = pathlib.Path(__file__).parent.parent
    candidates = [
        repo / "build" / "libsovereign_array.so",
        repo / "build" / "libsovereign_array.dll",
        repo / "build" / "sovereign_array.dll",
        repo / "build" / "libsovereign_array.dylib",
    ]
    for p in candidates:
        if p.exists():
            return ctypes.CDLL(str(p))
    raise FileNotFoundError(
        "Build the shared library first:\n"
        "  cmake -S .. -B ../build && cmake --build ../build\n"
        f"Looked in: {[str(c) for c in candidates]}"
    )

try:
    _lib = _load_lib()

    # void sovarr_softmax(const float*, float*, size_t)
    _lib.sovarr_softmax.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_size_t,
    ]
    _lib.sovarr_softmax.restype = None

    # void sovarr_face_centroid(const int*, size_t, float*, size_t)
    _lib.sovarr_face_centroid.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_size_t,
    ]
    _lib.sovarr_face_centroid.restype = None

    # void sovarr_nand_attention(const float*, float*, float*, float*, size_t)
    _lib.sovarr_nand_attention.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_size_t,
    ]
    _lib.sovarr_nand_attention.restype = None

    # int sovarr_nand(int, int) etc.
    for fn in ("sovarr_nand", "sovarr_not", "sovarr_and", "sovarr_or"):
        getattr(_lib, fn).argtypes = [ctypes.c_int, ctypes.c_int]
        getattr(_lib, fn).restype  = ctypes.c_int

    LIB_OK = True
except FileNotFoundError as e:
    print(f"WARNING: {e}", file=sys.stderr)
    LIB_OK = False


def softmax_c(xs: list[float]) -> list[float]:
    n = len(xs)
    in_arr  = (ctypes.c_float * n)(*xs)
    out_arr = (ctypes.c_float * n)()
    _lib.sovarr_softmax(in_arr, out_arr, n)
    return list(out_arr)

def face_centroid_c(support: list[int], n: int) -> list[float]:
    sup_arr = (ctypes.c_int * len(support))(*support)
    out_arr = (ctypes.c_float * n)()
    _lib.sovarr_face_centroid(sup_arr, len(support), out_arr, n)
    return list(out_arr)

def nand_attention_c(q, k, v):
    n = len(q)
    def fa(xs): return (ctypes.c_float * n)(*xs)
    out = (ctypes.c_float * n)()
    _lib.sovarr_nand_attention(fa(q), fa(k), fa(v), out, n)
    return list(out)

def softmax_ref(xs: list[float]) -> list[float]:
    """Pure-Python reference implementation (exact, slow)."""
    m = max(xs)  # shift for numerical stability
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]

skip_no_lib = pytest.mark.skipif(not LIB_OK, reason="shared lib not built")

# ─────────────────────────────────────────────────────────────────────────────
# PAPER I — NAND universality
# Lean theorems: notGate_eq, andGate_eq, orGate_eq
# ─────────────────────────────────────────────────────────────────────────────

@skip_no_lib
class TestPaperI_NAND:

    @given(st.integers(0, 1), st.integers(0, 1))
    @settings(max_examples=4, phases=[Phase.generate])  # truth table is 4 entries
    def test_nand_truth_table(self, a, b):
        """sovarr_nand(a,b) == not(a and b)  [andGate_eq / notGate_eq]"""
        expected = 0 if (a == 1 and b == 1) else 1
        assert _lib.sovarr_nand(a, b) == expected

    @given(st.integers(0, 1))
    @settings(max_examples=2)
    def test_not_via_nand(self, a):
        """nand(a,a) == not(a)  [notGate_eq]"""
        assert _lib.sovarr_not(a, a) == (0 if a == 1 else 1)

    @given(st.integers(0, 1), st.integers(0, 1))
    @settings(max_examples=4)
    def test_and_via_nand(self, a, b):
        """nand(nand(a,b), nand(a,b)) == a and b  [andGate_eq]"""
        assert _lib.sovarr_and(a, b) == (1 if a == 1 and b == 1 else 0)

    @given(st.integers(0, 1), st.integers(0, 1))
    @settings(max_examples=4)
    def test_or_via_nand(self, a, b):
        """nand(nand(a,a), nand(b,b)) == a or b  [orGate_eq]"""
        assert _lib.sovarr_or(a, b) == (1 if a == 1 or b == 1 else 0)

    @given(st.integers(0, 1), st.integers(0, 1), st.integers(0, 1))
    @settings(max_examples=8)
    def test_demorgan(self, a, b, c):
        """not(a or b) == not(a) and not(b)  — derived via NAND"""
        lhs = _lib.sovarr_not(_lib.sovarr_or(a, b), _lib.sovarr_or(a, b))
        rhs = _lib.sovarr_and(_lib.sovarr_not(a, a), _lib.sovarr_not(b, b))
        assert lhs == rhs


# ─────────────────────────────────────────────────────────────────────────────
# PAPER II — Simplex / Softmax / Face Centroid
# Lean theorems: softmax_is_pmap, softmax_shift_invariant,
#                faceCentroid_nonneg, faceCentroid_support, vertex_centroid_eq
# ─────────────────────────────────────────────────────────────────────────────

@skip_no_lib
class TestPaperII_Simplex:

    @given(st.lists(st.floats(-20, 20, allow_nan=False, allow_infinity=False),
                    min_size=2, max_size=256))
    @settings(max_examples=50_000, phases=[Phase.generate, Phase.shrink])
    def test_softmax_sums_to_one(self, logits):
        """Σ softmax(z)_i = 1  [softmax_is_pmap, sum normalisation]"""
        out = softmax_c(logits)
        assert abs(sum(out) - 1.0) < 1e-5, f"sum={sum(out)} logits={logits[:4]}"

    @given(st.lists(st.floats(-10, 10, allow_nan=False, allow_infinity=False),
                    min_size=2, max_size=256),
           st.floats(-50, 50, allow_nan=False, allow_infinity=False))
    @settings(max_examples=20_000, phases=[Phase.generate, Phase.shrink])
    def test_softmax_shift_invariant(self, logits, c):
        """softmax(z+c) == softmax(z)  [softmax_shift_invariant]"""
        shifted = [x + c for x in logits]
        out1 = softmax_c(logits)
        out2 = softmax_c(shifted)
        for i, (a, b) in enumerate(zip(out1, out2)):
            assert abs(a - b) < 1e-4, f"shift broke at i={i}: {a} vs {b} (c={c})"

    @given(st.lists(st.floats(-10, 10, allow_nan=False, allow_infinity=False),
                    min_size=2, max_size=256))
    @settings(max_examples=20_000)
    def test_softmax_matches_reference(self, logits):
        """sovarr_softmax matches pure-Python reference  [kernel correctness]"""
        c_out  = softmax_c(logits)
        py_out = softmax_ref(logits)
        for i, (a, b) in enumerate(zip(c_out, py_out)):
            assert abs(a - b) < 1e-4, f"mismatch at i={i}: C={a} ref={b}"

    @given(st.integers(2, 64),
           st.lists(st.integers(0, 63), min_size=1, max_size=64, unique=True))
    @settings(max_examples=10_000, phases=[Phase.generate, Phase.shrink])
    def test_face_centroid_sums_to_one(self, n, raw_support):
        """Σ faceCentroid(F)_i = 1  [faceCentroid = uniform on F]"""
        support = [i for i in raw_support if i < n]
        assume(len(support) > 0)
        out = face_centroid_c(support, n)
        assert abs(sum(out) - 1.0) < 1e-6, f"sum={sum(out)} F={support} n={n}"

    @given(st.integers(2, 64),
           st.lists(st.integers(0, 63), min_size=1, max_size=64, unique=True))
    @settings(max_examples=10_000)
    def test_face_centroid_support_matches(self, n, raw_support):
        """faceCentroid(F)_i ≠ 0 ↔ i ∈ F  [faceCentroid_support]"""
        support = sorted(set(i for i in raw_support if i < n))
        assume(len(support) > 0)
        out = face_centroid_c(support, n)
        support_set = set(support)
        for i, v in enumerate(out):
            if i in support_set:
                assert v > 0, f"active coord {i} is zero"
            else:
                assert v == 0.0, f"inactive coord {i} is nonzero: {v}"

    @given(st.integers(2, 64),
           st.integers(0, 63))
    @settings(max_examples=5_000)
    def test_vertex_centroid_is_indicator(self, n, raw_v):
        """faceCentroid({v})_i = 1 if i==v else 0  [vertex_centroid_eq]"""
        v = raw_v % n
        out = face_centroid_c([v], n)
        assert abs(out[v] - 1.0) < 1e-7, f"vertex {v}: {out[v]} ≠ 1"
        for i, val in enumerate(out):
            if i != v:
                assert val == 0.0, f"non-vertex {i} nonzero: {val}"

    @given(st.lists(st.floats(-5, 5, allow_nan=False, allow_infinity=False),
                    min_size=2, max_size=64))
    @settings(max_examples=10_000)
    def test_softmax_all_positive(self, logits):
        """softmax(z)_i > 0 for all i  [softmax maps to interior of simplex]"""
        out = softmax_c(logits)
        for i, v in enumerate(out):
            assert v > 0, f"softmax[{i}]={v} ≤ 0 on {logits}"


# ─────────────────────────────────────────────────────────────────────────────
# PAPER III — NAND Attention
# Lean theorem: attention_is_pmap
# ─────────────────────────────────────────────────────────────────────────────

def attention_ref(q, k, v):
    """Pure-Python reference: scores_i = Σ q_i*k_j, w=softmax(scores), out_i = Σ w_i*v_j"""
    n = len(q)
    scores = [sum(q[i] * k[j] for j in range(n)) for i in range(n)]
    w = softmax_ref(scores)
    return [sum(w[i] * v[j] for j in range(n)) for i in range(n)]

@skip_no_lib
class TestPaperIII_Attention:

    @given(st.integers(1, 32),
           st.data())
    @settings(max_examples=5_000, phases=[Phase.generate, Phase.shrink])
    def test_attention_matches_reference(self, n, data):
        """sovarr_nand_attention ≡ reference attention  [attention_is_pmap]"""
        flt = st.floats(-5, 5, allow_nan=False, allow_infinity=False)
        q = data.draw(st.lists(flt, min_size=n, max_size=n))
        k = data.draw(st.lists(flt, min_size=n, max_size=n))
        v = data.draw(st.lists(flt, min_size=n, max_size=n))
        c_out  = nand_attention_c(q, k, v)
        py_out = attention_ref(q, k, v)
        for i, (a, b) in enumerate(zip(c_out, py_out)):
            assert abs(a - b) < 1e-3, \
                f"attention divergence at i={i}: C={a:.6f} ref={b:.6f}"

    @given(st.integers(1, 32), st.data())
    @settings(max_examples=2_000)
    def test_attention_output_size(self, n, data):
        """output has same size as input  [shape preservation]"""
        flt = st.floats(-3, 3, allow_nan=False, allow_infinity=False)
        q = data.draw(st.lists(flt, min_size=n, max_size=n))
        k = data.draw(st.lists(flt, min_size=n, max_size=n))
        v = data.draw(st.lists(flt, min_size=n, max_size=n))
        out = nand_attention_c(q, k, v)
        assert len(out) == n

    @given(st.integers(1, 16), st.data())
    @settings(max_examples=2_000)
    def test_attention_uniform_k_is_constant(self, n, data):
        """When k is uniform, all scores are equal → attention weights are uniform."""
        flt  = st.floats(-3, 3, allow_nan=False, allow_infinity=False)
        q    = data.draw(st.lists(flt, min_size=n, max_size=n))
        k    = [1.0] * n   # uniform key
        v    = data.draw(st.lists(flt, min_size=n, max_size=n))
        out  = nand_attention_c(q, k, v)
        # All outputs should be identical (uniform weight over v)
        mean = sum(out) / n
        for i, val in enumerate(out):
            assert abs(val - mean) < 1e-4, \
                f"uniform-k: out[{i}]={val} ≠ mean={mean}"


# ─────────────────────────────────────────────────────────────────────────────
# BROADCAST — pullback semantics
# Lean theorem: broadcast_is_pullback
# ─────────────────────────────────────────────────────────────────────────────

@skip_no_lib
class TestBroadcast:

    @given(st.lists(st.floats(-100, 100, allow_nan=False, allow_infinity=False),
                    min_size=1, max_size=256))
    @settings(max_examples=10_000)
    def test_broadcast_1d_pointwise(self, xs):
        """broadcast_1d(v, w)_i = v_i + w_i  [broadcast_is_pullback, 1D case]"""
        n = len(xs)
        # split into two halves (or use same list for both)
        v_arr = (ctypes.c_float * n)(*xs)
        w_arr = (ctypes.c_float * n)(*xs)
        out   = (ctypes.c_float * n)()
        _lib.sovarr_broadcast_1d.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
        ]
        _lib.sovarr_broadcast_1d.restype = None
        _lib.sovarr_broadcast_1d(v_arr, w_arr, out, n)
        for i, (a, b, o) in enumerate(zip(xs, xs, out)):
            assert abs(o - (a + b)) < 1e-4, f"broadcast[{i}]: {o} ≠ {a+b}"


# ─────────────────────────────────────────────────────────────────────────────
# Standalone: run without pytest
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-x", "-v", "--tb=short"],
        cwd=pathlib.Path(__file__).parent,
    )
    sys.exit(result.returncode)
