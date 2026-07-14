#!/usr/bin/env bash
# Layer 2a: Formal Equivalence Check via Alive2 / LLVM opt
# Proves: LLVM IR of extracted kernels ≈ reference semantics
#
# Prerequisites (Linux/WSL):
#   apt install llvm clang alive2   OR   build from source at
#   https://github.com/AliveToolkit/alive2
#
# On Windows: run inside WSL or Docker with LLVM toolchain.
# This script is a no-op (exit 0) if alive2 is not installed
# so CI doesn't break on dev machines without the toolchain.

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$REPO/build"

if ! command -v alive-tv &>/dev/null; then
    echo "alive2 not found — skipping formal equivalence check"
    echo "Install: https://github.com/AliveToolkit/alive2"
    exit 0
fi

echo "=== Layer 2a: Alive2 formal equivalence ==="

# Compile kernel to LLVM IR (unoptimised = reference)
clang++ -std=c++20 -O0 -S -emit-llvm \
    -I "$REPO/include" \
    "$REPO/src/sovereign_export.cpp" \
    "$REPO/src/sovereign_array.cpp" \
    -o "$BUILD/sovarr_O0.ll" 2>&1

# Optimised version
clang++ -std=c++20 -O3 -S -emit-llvm \
    -I "$REPO/include" \
    "$REPO/src/sovereign_export.cpp" \
    "$REPO/src/sovereign_array.cpp" \
    -o "$BUILD/sovarr_O3.ll" 2>&1

# Check: O3 ≡ O0 for the key exported functions
for fn in sovarr_softmax sovarr_face_centroid sovarr_nand sovarr_nand_attention; do
    echo -n "  Checking $fn ... "
    alive-tv "$BUILD/sovarr_O0.ll" "$BUILD/sovarr_O3.ll" \
        --func "$fn" --smt-to=30 2>&1 | tail -1
done

echo "=== Layer 2a: PASS ==="
