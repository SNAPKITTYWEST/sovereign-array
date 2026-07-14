#include "sovereign_export.h"
#include "sovereign_array.h"
#include <cstring>
#include <cstddef>

// ── Paper I: NAND ─────────────────────────────────────────────────────────────

int sovarr_nand(int a, int b) {
    return sovarr::nand_gate(a != 0, b != 0) ? 1 : 0;
}
int sovarr_not(int a)         { return sovarr_nand(a, a); }
int sovarr_and(int a, int b)  { return sovarr_nand(sovarr_nand(a, b), sovarr_nand(a, b)); }
int sovarr_or(int a, int b)   { return sovarr_nand(sovarr_nand(a, a), sovarr_nand(b, b)); }

// ── Paper II: Softmax ─────────────────────────────────────────────────────────

void sovarr_softmax(const float* in, float* out, size_t n) {
    sovarr::Array<float> v({n}, std::vector<float>(in, in + n));
    auto sm = sovarr::softmax(v);
    for (size_t i = 0; i < n; ++i) out[i] = sm[i];
}

// Face centroid: exact uniform over support, zero elsewhere.
void sovarr_face_centroid(const int* support, size_t support_len,
                          float* out, size_t n) {
    std::memset(out, 0, n * sizeof(float));
    if (support_len == 0) return;
    float w = 1.0f / static_cast<float>(support_len);
    for (size_t k = 0; k < support_len; ++k) {
        int idx = support[k];
        if (idx >= 0 && static_cast<size_t>(idx) < n)
            out[idx] = w;
    }
}

// ── Paper III: Attention ──────────────────────────────────────────────────────

void sovarr_nand_attention(const float* q, const float* k, const float* v,
                           float* out, size_t n) {
    sovarr::Array<float> qa({n}, std::vector<float>(q, q + n));
    sovarr::Array<float> ka({n}, std::vector<float>(k, k + n));
    sovarr::Array<float> va({n}, std::vector<float>(v, v + n));
    auto res = sovarr::nand_attention(qa, ka, va);
    for (size_t i = 0; i < n; ++i) out[i] = res[i];
}

// ── Broadcast ─────────────────────────────────────────────────────────────────

void sovarr_broadcast_1d(const float* v, const float* w, float* out, size_t n) {
    for (size_t i = 0; i < n; ++i) out[i] = v[i] + w[i];
}

// ── Version ───────────────────────────────────────────────────────────────────

const char* sovarr_version(void) {
    return "sovereign-array-1.0.0 | Array I α = I→α | zero-sorry | 2026";
}
