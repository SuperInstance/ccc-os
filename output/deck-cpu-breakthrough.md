# CPU Beats GPU: The AVX-512 Finding
_Type: benchmark_finding | Generated: 2026-05-04T02:45_

---

## Slide 1: Context

- FM ran head-to-head AVX-512 vs RTX 4050 on constraint checking. Ryzen AI 9 HX 370 (Zen 5, 12C/24T) vs RTX 4050.

---

## Slide 2: The Numbers

- 1M inputs: CPU 2.2B/s vs GPU 404M/s (5.4x)
10M inputs: CPU 5.7B/s vs GPU 1.03B/s (5.5x)
100M inputs: CPU 5.4B/s vs GPU 1.19B/s (4.5x)
20 constraints parallel: 35.9B/s via AND-logic
CPU + GPU combined: 6.7B+ checks/s at ~19W

---

## Slide 3: What This Means

- FLUX-C (constraint layer) should compile to AVX-512, not CUDA. The bridge between FLUX-C and FLUX-X has a physical reason: constraints live in CPU register file, complex ops live in GPU VRAM. The split is not just architectural — it is physical.

---

## Slide 4: What We Should Do

- 1. Buy Ryzen AI 9s with AVX-512 for constraint screening layer
2. Reserve GPUs exclusively for complex FLUX-X branching/temporal/security opcodes
3. Three-tier architecture: CPU screens (5.7B/s), GPU evaluates complex (1B/s), ARM certifies (ASIL D)

---

## Slide 5: Next

- Oracle1: Add Section 13 to ISA v3 documenting bare-metal compilation targets
FM: Build flux-cpu-avx512 repo with AVX-512 constraint primitives
CCC: Update cocapn.ai landing page to reflect CPU-first architecture

---

