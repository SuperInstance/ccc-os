# HDC Core + Fleet Publishing Round
_Type: research_summary | Generated: 2026-05-04T02:45_

---

## Slide 1: What We Learned

- Oracle1 built superinstance-hdc-core from Google research session. MurmurHash3 fingerprinting (10x faster than SHA), Bloom filter first-pass, SRAM cache-line aligned records, 1024-bit hypervector ops, XOR-POPCNT judge (1 cycle). AVX-512 and HDC judge are same principle: eliminate branch mispredictions with single wide instructions.

---

## Slide 2: Why It Matters

- The HDC layer is the bit-level cognition engine for the fleet. It enables O(1) fuzzy matching, hardware-accelerated similarity judgment, and cache-friendly record storage. Combined with AVX-512 batch comparison (16 hashes at once), this is the screening layer for the entire constraint system.

---

## Slide 3: What To Do

- 1. Integrate HDC bloom filter into flux-cpu-avx512 for first-pass screening
2. Publish remaining PyPI packages (cocapn-plato-sdk needs API token)
3. Benchmark HDC judge + AVX-512 batch comparison together
4. Document the TUTOR → PLATO → HDC lineage in landing page copy

---

