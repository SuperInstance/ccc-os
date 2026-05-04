#!/usr/bin/env python3
"""
CCC-OS Orchestrator
Runs all monitors, applies rubric, generates outputs.
This is the "CCC Operating System" entry point.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/root/.openclaw/workspace/ccc-os")
from rubric import Input, decide, explain

CCCOS_DIR = Path("/root/.openclaw/workspace/ccc-os")
OUTPUT_DIR = CCCOS_DIR / "output"

def run_discussion5():
    """Run Discussion #5 monitor."""
    result = subprocess.run(
        ["python3", str(CCCOS_DIR / "monitors" / "discussion5_monitor.py")],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout, result.stderr

def run_health():
    """Run health autopilot."""
    result = subprocess.run(
        ["python3", str(CCCOS_DIR / "health" / "autopilot.py")],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout, result.stderr

def generate_task_queue():
    """Read log files and build prioritized task queue."""
    tasks = []
    
    # Read Discussion #5 ACT_NOW items
    log_file = CCCOS_DIR / "monitors" / "discussion5_log.jsonl"
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                event = json.loads(line)
                if event.get("verdict") == "ACT_NOW":
                    tasks.append({
                        "source": "discussion5",
                        "priority": 1,
                        "title": event["summary"][:80],
                        "created": event["timestamp"],
                        "action": "Generate deck + notify Casey",
                    })
    
    # Sort by priority then time
    tasks.sort(key=lambda t: (t["priority"], t["created"]))
    return tasks

def save_queue(tasks):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "task_queue.json", "w") as f:
        json.dump(tasks, f, indent=2)

def main():
    print(f"=== CCC-OS Orchestrator | {datetime.now(timezone.utc).isoformat()} ===\n")
    
    print("[1/3] Running Discussion #5 monitor...")
    out, err = run_discussion5()
    if out:
        print(out)
    if err:
        print(f"ERR: {err}", file=sys.stderr)
    
    print("\n[2/3] Running health autopilot...")
    out, err = run_health()
    if out:
        print(out)
    if err:
        print(f"ERR: {err}", file=sys.stderr)
    
    print("\n[3/3] Generating task queue...")
    tasks = generate_task_queue()
    save_queue(tasks)
    
    if tasks:
        print(f"\n📋 TASK QUEUE: {len(tasks)} item(s)")
        for i, t in enumerate(tasks[:5], 1):
            print(f"  {i}. [{t['source']}] {t['title']}")
    else:
        print("\n📋 No pending tasks.")
    
    print(f"\n=== Done | Queue saved to {OUTPUT_DIR / 'task_queue.json'} ===")

if __name__ == "__main__":
    main()
