# Deck: Bare Metal + LLVM Strategy (35.9B/s, eBPF = Free Certification)

- **Source:** Forgemaster (FM)
- **Urgency:** ACT_NOW — Certification cost eliminator
- **Generated:** 2026-05-04

---

## Summary

FM has validated a bare-metal compilation path for FLUX-C that eliminates the certification tax. By compiling constraints directly to AVX-512 via LLVM with zero OS abstraction layer, the constraint kernel achieves 35.9B checks/s. The critical unlock: eBPF verifier acts as a free, de-facto certification engine. If the kernel passes the eBPF verifier, it is memory-safe and bounded by construction — satisfying the same properties that cost $50K–$200K in traditional DO-178C / ISO 26262 tooling.

This is not a workaround. It is a strategic realignment: the eBPF ecosystem (Linux kernel, cloud-native runtimes, edge devices) has already invested billions in verifier correctness. FLUX-C compiled to eBPF inherits that investment for free.

---

## Action Items

1. **FM:** Prototype FLUX-C → LLVM IR → eBPF bytecode pipeline. Target: end of week.
2. **Oracle1:** Draft "eBPF as Certification Vehicle" whitepaper section for ISA v3 Appendix.
3. **CCC:** Design landing-page narrative: "Certified by the kernel, not by a committee."
4. **Fleet (all agents):** Audit existing constraint code for eBPF-compatibile patterns (no unbounded loops, no raw pointers).
5. **Casey:** Review IP landscape — any patents on "eBPF for safety certification"? File if clear.

---

## Stakeholders

| Role | Who | Responsibility |
|------|-----|--------------|
| Builder | FM | LLVM pipeline, eBPF verifier integration |
| Lighthouse | Oracle1 | Standards documentation, legal clearance |
| Art Director | CCC | Narrative design, proof the system works |
| Fleet-wide | All agents | Code audit for eBPF compatibility |
| Captain | Casey | IP strategy, go/no-go on public claim |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| eBPF verifier too restrictive for some FLUX-C constructs | High | Maintain dual path: eBPF (certified) + bare-metal (performance) |
| "Free certification" claim challenged by auditors | Medium | Frame as "verifier provides equivalent assurance," not "replaces process" |
| LLVM pipeline adds build complexity | Medium | Document step-by-step; CI gates on eBPF verifier pass |
| eBPF runtime not available on all target platforms | Medium | Provide wasmtime/ WASI fallback for non-Linux targets |
| Competitor files same patent first | High | Casey to search + file provisional this week |

---

## Success Criteria

- [ ] Working FLUX-C → eBPF pipeline committed to `flux-cpu-avx512` repo
- [ ] At least one non-trivial constraint set passes eBPF verifier on first try
- [ ] Whitepaper section peer-reviewed by Oracle1 + Casey
- [ ] Landing page copy approved by Casey before publication
- [ ] IP search completed with written go/no-go from Casey
