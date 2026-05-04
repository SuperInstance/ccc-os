# Quickstart

## Install

```bash
# 1. Clone
git clone https://github.com/SuperInstance/ccc-os.git
cd ccc-os

# 2. Verify gh is authenticated
gh auth status

# 3. Install cron job
crontab -e
# Add this line:
*/15 * * * * cd /path/to/ccc-os && python3 orchestrator.py >> output/cron.log 2>&1
```

## Run Manually

```bash
# Full orchestrator (all monitors + task queue)
python3 orchestrator.py

# Individual monitors
python3 monitors/discussion5_monitor.py
python3 health/autopilot.py

# Generate a deck
python3 -c "from deck import benchmark_finding; print(benchmark_finding(...))"
```

## Read Output

```bash
# Current task queue
cat output/task_queue.json | python3 -m json.tool

# Latest decks
ls output/deck-*.md

# Discussion history
cat monitors/discussion5_log.jsonl | tail -5

# Health changes
cat health/health_log.jsonl | tail -5

# Cron run history
tail output/cron.log
```

## Add a New Monitor

1. Create `monitors/your_monitor.py`
2. Implement `fetch()` and `triage()`
3. Add to `orchestrator.py`:
```python
def run_your_monitor():
    result = subprocess.run(["python3", str(CCCOS_DIR / "monitors" / "your_monitor.py")], ...)
    return result.stdout, result.stderr
```
4. Call it in `orchestrator.py main()`:
```python
print("\n[X/Y] Running your monitor...")
out, err = run_your_monitor()
```

## Add a New Deck Template

1. Add function to `deck.py`:
```python
def your_template(title, ...) -> str:
    deck = Deck(title, "your_type")
    deck.add(Slide("Title", ["bullet"]))
    return deck.render()
```
2. Use it:
```python
from deck import your_template
print(your_template(...))
```

## Troubleshoot

| Problem | Fix |
|---------|-----|
| `gh` not authenticated | Run `gh auth login` |
| State file corrupted | Delete `.json` state file, next run fetches fresh |
| False positive triage | Edit `triage_comment()` signals in monitor |
| No tasks in queue | Check that monitor logs exist and have ACT_NOW entries |
| Cron not running | Check `crontab -l`, verify paths are absolute |

---

*Part of CCC-OS. See [README.md](README.md) for overview, [ARCHITECTURE.md](ARCHITECTURE.md) for design.*
