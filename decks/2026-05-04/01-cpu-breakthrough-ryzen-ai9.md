# Deck: CPU Breakthrough — Ryzen AI 9 Beats the GPU (5.5×)

- **Source:** Forgemaster (FM)
- **Urgency:** ACT_NOW — Foundational architecture pivot
- **Generated:** 2026-05-04

---

## Summary

FM ran head-to-head AVX-512 vs. RTX 4050 on constraint checking workloads. The result is not incremental — it is a 5.5× advantage for CPU over GPU on FLUX-C (constraint layer) operations. The Ryzen AI 9 achieves 5.7B checks/s vs. the GPU's 1.03B checks/s. With 20 constraints evaluated in parallel via AND-logic, throughput reaches 35.9B/s.

The physical reason is register-file locality: AVX-512 keeps working data on-die, while GPU VRAM round-trips kill throughput for simple constraint ops. FLUX-C should compile to AVX-512, not CUDA. GPUs should be reserved for complex FLUX-X operations only.

---

## Action Items

1. **FM:** Create `flux-cpu-avx512` repo — bare-metal AVX-512 constraint kernel.
2. **Oracle1:** Add Section 13 to ISA v3 documenting bare-metal compilation targets (AVX-512, NEON, SSE4.2).
3. **CCC:** Update fleet landing pages and documentation to reflect CPU-first constraint architecture.
4. **JetsonClaw1:** Evaluate Jetson Orin AVX-512 feasibility for edge deployment.
5. **Casey:** Approve hardware procurement — Ryzen AI 9 fleet nodes for constraint screening.

---

## Stakeholders

| Role | Who | Responsibility |
|------|-----|--------------|
| Builder | FM | AVX-512 kernel implementation, performance validation |
| Lighthouse | Oracle1 | ISA documentation, cross-package alignment |
| Art Director | CCC | Messaging, domain updates, proof the system works |
| Edge Operator | JetsonClaw1 | Edge hardware assessment |
| Captain | Casey | Go/no-go on hardware budget |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| GPU vendors lobby against CPU-first messaging | Medium | Frame as "right tool for right layer," not anti-GPU |
| AVX-512 not available on all target CPUs | High | Maintain SSE4.2 fallback; NEON for ARM |
| 35.9B/s number is synthetic (20 parallel constraints) | Low | Document methodology; real-world validation in Q3 |
| ISA v3 Section 13 delays downstream packages | Medium | Draft in parallel with kernel dev, not sequential |

---

## Success Criteria

- [ ] `flux-cpu-avx512` repo public with benchmark reproducibility script
- [ ] ISA v3 Section 13 published and version-tagged
- [ ] At least 1 fleet domain landing page updated with CPU-first architecture language
- [ ] Casey green-lights Ryzen AI 9 procurement within 72 hours
- [ ] Independent verification by non-FM agent confirms 5×+ speedup on same hardware
