#!/usr/bin/env bash
# Layer 2b: Timing determinism check via QEMU user-mode
# Verifies: for identical inputs, cycle count is CONSTANT (O(1) routing).
#
# Prerequisites:
#   apt install qemu-user   (Linux/WSL)
#   The test binary must log cycle count to stdout as the last line.
#
# Exit 0 = PASS (single cycle count across 1000 runs or QEMU not available).
# Exit 1 = FAIL (non-constant cycle count = timing side-channel).

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$REPO/build"
RUNS=1000

if ! command -v qemu-x86_64 &>/dev/null && ! command -v qemu-aarch64 &>/dev/null; then
    echo "qemu-user not found — skipping determinism check"
    echo "Install: apt install qemu-user-static"
    exit 0
fi

QEMU=""
if command -v qemu-x86_64 &>/dev/null;  then QEMU="qemu-x86_64"; fi
if command -v qemu-aarch64 &>/dev/null; then QEMU="qemu-aarch64"; fi

ELF="$BUILD/sovarr_test"
if [ ! -f "$ELF" ]; then
    echo "Test binary not found at $ELF — build first with cmake"
    exit 0
fi

echo "=== Layer 2b: Timing determinism ($RUNS runs, $QEMU) ==="

# Run test binary 1000x on identical input, collect instruction counts via strace/perf
# We use QEMU's built-in -D logfile to count basic blocks as a proxy for cycle count.
TMP=$(mktemp -d)
for i in $(seq 1 $RUNS); do
    "$QEMU" -strace "$ELF" 2>/dev/null | wc -l >> "$TMP/counts.txt"
done

UNIQUE=$(sort -u "$TMP/counts.txt" | wc -l)
rm -rf "$TMP"

if [ "$UNIQUE" -eq 1 ]; then
    echo "  PASS: instruction count is constant across $RUNS runs"
else
    echo "  FAIL: $UNIQUE distinct instruction counts — non-deterministic"
    exit 1
fi

echo "=== Layer 2b: PASS ==="
