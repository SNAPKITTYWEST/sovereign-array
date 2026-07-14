#pragma once
#include <stddef.h>
// C export layer — lets Python ctypes / Rust FFI call the C++20 kernels
// without name-mangling. Every function here maps to a theorem in ArrayLang/.

#ifdef __cplusplus
extern "C" {
#endif

// ── Paper I: NAND ──────────────────────────────────────────────────────────────
// nand(a,b) = !(a && b)   [maps to andGate_eq, notGate_eq, orGate_eq]
int  sovarr_nand(int a, int b);
int  sovarr_not(int a);
int  sovarr_and(int a, int b);
int  sovarr_or(int a, int b);

// ── Paper II: Softmax + Face Centroid ─────────────────────────────────────────
// softmax(in, out, n): out[i] = exp(in[i]) / Σ exp(in[j])
//   [maps to softmax_is_pmap, softmax_shift_invariant]
void sovarr_softmax(const float* in, float* out, size_t n);

// face_centroid(support, support_len, out, n):
//   out[i] = 1/|F| if i ∈ support, else 0
//   [maps to faceCentroid, faceCentroid_support]
void sovarr_face_centroid(const int* support, size_t support_len,
                          float* out, size_t n);

// ── Paper III: Attention ───────────────────────────────────────────────────────
// nand_attention(q,k,v,out,n): scores_i = Σ_j q_i*k_j, w=softmax(scores), out_i = Σ_j w_i*v_j
//   [maps to attention_is_pmap]
void sovarr_nand_attention(const float* q, const float* k, const float* v,
                           float* out, size_t n);

// ── Broadcast ─────────────────────────────────────────────────────────────────
// broadcast_1d(v, w, out, n): out[i] = v[i] + w[i]
//   (1D case of broadcast_is_pullback)
void sovarr_broadcast_1d(const float* v, const float* w, float* out, size_t n);

// ── Consistency probe ─────────────────────────────────────────────────────────
// Returns build-time git SHA + kernel version string.
const char* sovarr_version(void);

#ifdef __cplusplus
}
#endif
