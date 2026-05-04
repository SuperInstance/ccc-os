# Changelog

All notable changes to CCC-OS.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] — 2026-05-05

### Added
- Component READMEs for monitors/, health/, output/
- `.gitignore` excluding `__pycache__` and logs
- Landing page copy auto-generator (`landing_page_gen.py`)

### Changed
- Removed committed `__pycache__` files from repo

## [1.0.0] — 2026-05-05

### Added
- **Discussion #5 Monitor** — Auto-polls GitHub Discussion, diffs state, triages ACT_NOW/TRACK/IGNORE
- **Decision Rubric** — Codified rules for TELL_NOW vs LOG vs ACT vs IGNORE. No deliberation.
- **Deck Template System** — 4 templates (benchmark, architecture, fleet status, research). <2 min generation.
- **Health Autopilot** — Probes 8 services every 5 min. Alerts only on state changes.
- **Orchestrator** — Runs all monitors, builds prioritized task queue.
- **Cron integration** — `*/15 * * * *` automatic execution
- 3 demo decks generated from first run:
  - CPU Breakthrough (AVX-512 vs GPU, 5.5x)
  - Bare Metal LLVM + eBPF Strategy
  - HDC Core + Fleet Publishing

### Infrastructure
- GitHub repo: `SuperInstance/ccc-os`
- State files: JSON for discussion history, health history
- Log files: JSONL for all events (append-only, human-readable)

---

*CCC-OS versioning: MAJOR = architectural change, MINOR = new component/feature, PATCH = fix/docs.*
