#!/usr/bin/env python3
"""
ZC Feed Monitor
Reads data/zeroclaw/logs/ every 15 minutes.
Auto-summarizes new tiles (3 bullets max).
Queues for CCC review.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/root/.openclaw/workspace/data/zeroclaw/logs")
STATE_FILE = Path("/root/.openclaw/workspace/ccc-os/monitors/zc_last_state.json")
OUTPUT_FILE = Path("/root/.openclaw/workspace/ccc-os/output/zc_queue.json")

def find_log_files():
    """Find all .jsonl files in the ZC log directory."""
    if not LOG_DIR.exists():
        return []
    return sorted(LOG_DIR.glob("*.jsonl"))

def load_last_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"files": {}, "last_run": None}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def read_new_lines(filepath, last_line):
    """Read lines from filepath that are new since last_line."""
    if not filepath.exists():
        return []
    lines = []
    with open(filepath) as f:
        for i, line in enumerate(f):
            if i >= last_line:
                try:
                    lines.append(json.loads(line))
                except:
                    pass
    return lines

def summarize_tile(tile):
    """Generate a 3-bullet summary of a tile."""
    summary = []
    
    # Extract key fields
    agent = tile.get("agent", "unknown")
    domain = tile.get("domain", "unknown")
    title = tile.get("title", "")
    body = tile.get("body", "")
    
    # Bullet 1: What
    if title:
        summary.append(f"[{agent}] {title[:80]}")
    else:
        summary.append(f"[{agent}] New tile in {domain}")
    
    # Bullet 2: Key insight (first sentence of body, or first 100 chars)
    if body:
        first_sent = body.split(".")[0][:100]
        summary.append(f"Insight: {first_sent}")
    
    # Bullet 3: Significance (if scores present)
    scores = tile.get("scores", {})
    if scores:
        score_str = ", ".join([f"{k}={v}" for k, v in list(scores.items())[:3]])
        summary.append(f"Scores: {score_str}")
    else:
        summary.append(f"Domain: {domain}")
    
    return summary

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking ZC feeds...")
    
    log_files = find_log_files()
    if not log_files:
        print("No ZC log files found.")
        save_state({"files": {}, "last_run": datetime.now(timezone.utc).isoformat()})
        return
    
    state = load_last_state()
    known_files = state.get("files", {})
    
    new_tiles = []
    
    for filepath in log_files:
        file_key = str(filepath)
        last_line = known_files.get(file_key, 0)
        
        lines = read_new_lines(filepath, last_line)
        if lines:
            print(f"  {filepath.name}: {len(lines)} new tile(s)")
            for tile in lines:
                summary = summarize_tile(tile)
                new_tiles.append({
                    "file": filepath.name,
                    "timestamp": tile.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "agent": tile.get("agent", "unknown"),
                    "domain": tile.get("domain", "unknown"),
                    "summary": summary,
                    "title": tile.get("title", ""),
                })
        
        # Update known line count
        with open(filepath) as f:
            total_lines = sum(1 for _ in f)
        known_files[file_key] = total_lines
    
    if new_tiles:
        print(f"\n📡 {len(new_tiles)} new tile(s) to review:")
        for t in new_tiles[:5]:
            print(f"  [{t['agent']}] {t['title'][:60]}")
        if len(new_tiles) > 5:
            print(f"  ... and {len(new_tiles) - 5} more")
    else:
        print("No new tiles.")
    
    # Save state
    save_state({
        "files": known_files,
        "last_run": datetime.now(timezone.utc).isoformat(),
    })
    
    # Save queue
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(new_tiles, f, indent=2)

if __name__ == "__main__":
    main()
