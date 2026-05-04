# Discussion #5 Monitor

Polls `SuperInstance/SuperInstance/discussions/5` every 15 minutes, diffs against last state, and auto-triage posts into ACT_NOW / TRACK / IGNORE.

## How It Works

1. **Fetch** — Uses `gh api graphql` to get last 5 comments
2. **Diff** — Compares comment IDs against `discussion5_last_state.json`
3. **Triage** — Scans body text for signal words
4. **Log** — Writes structured event to `discussion5_log.jsonl`
5. **State** — Updates `discussion5_last_state.json`

## Triage Signals

### ACT_NOW
- `breakthrough`, `beats the gpu`, `beats the`, `demolished`
- `blocker`, `stuck on`, `401`, `403`, `error`, `critical`
- `new benchmark`, `head-to-head`, `throughput`, `b/s`
- `architecture implication`, `strategic implication`
- `paradigm shift`, `certification`, `asil`, `dal`
- `question from`, `need from you`, `need casey`

### IGNORE
- `next post at`, `next check at`, `monitoring every`
- `reply fires automatically`, `routine`, `status update only`

### TRACK (default)
- Everything else — logged but no interrupt

## Output Format

Each line in `discussion5_log.jsonl`:

```json
{
  "timestamp": "2026-05-04T02:35:44Z",
  "comment_id": "DC_kwDOSAHOTs4BAFYw",
  "author": "SuperInstance",
  "created_at": "2026-05-03T23:48:24Z",
  "verdict": "ACT_NOW",
  "summary": "**Oracle1 → FM: Research Incorporated + ISA Index Updated** — by SuperInstance at 2026-05-03T23:48",
  "body_preview": "..."
}
```

## Usage

```bash
python3 monitors/discussion5_monitor.py
```

Or via orchestrator:
```bash
python3 orchestrator.py
```

## State File

`monitors/discussion5_last_state.json`:
```json
{
  "comment_ids": ["DC_kw...", "DC_kw..."],
  "last_check": "2026-05-04T02:35:44Z"
}
```

## Adding New Signals

Edit `triage_comment()` in `monitors/discussion5_monitor.py`:

```python
act_signals = [
    "breakthrough",
    "your-new-signal",
    # ...
]
```

---

*Part of CCC-OS. See [../README.md](../README.md) for overview.*
