# Bare Metal Strategy: LLVM + eBPF for Certification
_Type: architecture_decision | Generated: 2026-05-04T02:45_

---

## Slide 1: The Problem

- Python ctypes constraint checking runs at 63M/s — 100x slower than native. We need compilation targets that match our certification requirements.

---

## Slide 2: Options

- 1. x86-64 JIT (4 instructions per constraint) — 920M/s, fastest, limited to x86
2. AVX-512 (20 constraints parallel) — 35.9B/s, AND-logic nearly free per constraint
3. LLVM IR → multi-target — x86-64 / AVX-512 / Wasm / RISC-V / eBPF from one source
4. eBPF — free formal verification via kernel verifier (no crashes, no infinite loops, no OOB)

---

## Slide 3: Recommendation

- LLVM IR as unified backend. GUARD constraint → AST → Optimize → LLVM IR → target-specific native code. eBPF for the certification path (free formal verification + SMT solver = full proof pipeline).

---

## Slide 4: Risk

- LLVM dependency adds ~50MB to build. eBPF verifier limits recursion and unbounded loops — FLUX-C opcodes must be structured acyclic. JIT warm-up latency for first constraint compile.

---

## Slide 5: Timeline

- Week 1: flux-cpu-avx512 repo (FM)
Week 2: LLVM IR emitter for GUARD AST (FM)
Week 3: eBPF target + verifier test suite
Week 4: Integration test: CPU screen → GPU evaluate → ARM certify

---

