#!/usr/bin/env python3
"""
Discussion #5 Auto-Monitor
Polls SuperInstance/SuperInstance/discussions/5 every 15 minutes.
Diffs against last-known state.
Auto-triage: ACT_NOW vs TRACK vs IGNORE.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("/root/.openclaw/workspace/ccc-os/monitors/discussion5_last_state.json")
LOG_FILE = Path("/root/.openclaw/workspace/ccc-os/monitors/discussion5_log.jsonl")

def fetch_discussion():
    """Fetch last 5 comments from Discussion #5."""
    query = '''
    {
      repository(owner:"SuperInstance", name:"SuperInstance") {
        discussion(number:5) {
          title
          comments(last:5) {
            nodes {
              id
              createdAt
              author { login }
              body
            }
          }
        }
      }
    }
    '''
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"ERROR: gh failed: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)

def load_last_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"comment_ids": [], "last_check": None}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fleet_bridge import FleetBridgeLogger

BRIDGE = FleetBridgeLogger(LOG_FILE, source="ccc-os/discussion5")

def log_event(event):
    BRIDGE.log_event(event)

def triage_comment(comment):
    """
    Auto-triage based on content signals.
    Returns: ACT_NOW, TRACK, or IGNORE
    """
    body = comment.get("body", "").lower()
    author = comment.get("author", {}).get("login", "")
    
    # ACT_NOW signals
    act_signals = [
        "breakthrough", "beats the gpu", "beats the", "demolished",
        "blocker", "stuck on", "401", "403", "error", "critical",
        "new benchmark", "head-to-head", "throughput", "b/s",
        "architecture implication", "strategic implication",
        "paradigm shift", "certification", "asil", "dal",
        "question from", "need from you", "need casey",
    ]
    
    for signal in act_signals:
        if signal in body:
            return "ACT_NOW"
    
    # IGNORE signals — routine status, coordination
    ignore_signals = [
        "next post at", "next check at", "monitoring every",
        "reply fires automatically", "routine", "status update only",
    ]
    for signal in ignore_signals:
        if signal in body:
            return "IGNORE"
    
    # Default: TRACK for anything else
    return "TRACK"

def format_summary(comment, verdict):
    """Generate a one-paragraph summary for ACT_NOW posts."""
    author = comment.get("author", {}).get("login", "")
    body = comment.get("body", "")
    created = comment.get("createdAt", "")
    
    # Extract first line as title if it starts with ##
    title = ""
    for line in body.split("\n"):
        if line.startswith("##"):
            title = line.lstrip("# ")
            break
    
    if not title:
        title = f"Post by {author}"
    
    # Extract key numbers/benchmarks
    numbers = []
    for word in body.split():
        if any(x in word for x in ["B/s", "M/s", "GB/s", "x faster", "%", "W"]):
            numbers.append(word.strip(".,;:"))
    
    numbers_str = ", ".join(numbers[:5]) if numbers else ""
    
    summary = f"**{title}** — by {author} at {created[:16]}"
    if numbers_str:
        summary += f" | Key numbers: {numbers_str}"
    summary += f" | Verdict: **{verdict}**"
    
    return summary

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking Discussion #5...")
    
    data = fetch_discussion()
    if not data:
        print("Fetch failed, exiting.")
        sys.exit(1)
    
    discussion = data["data"]["repository"]["discussion"]
    comments = discussion["comments"]["nodes"]
    
    state = load_last_state()
    known_ids = set(state.get("comment_ids", []))
    
    new_comments = []
    for c in comments:
        if c["id"] not in known_ids:
            new_comments.append(c)
    
    if not new_comments:
        print("No new comments.")
        save_state({
            "comment_ids": [c["id"] for c in comments],
            "last_check": datetime.now(timezone.utc).isoformat()
        })
        return
    
    print(f"Found {len(new_comments)} new comment(s):")
    
    for comment in new_comments:
        verdict = triage_comment(comment)
        summary = format_summary(comment, verdict)
        
        print(f"\n{summary}")
        
        log_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comment_id": comment["id"],
            "author": comment["author"]["login"],
            "created_at": comment["createdAt"],
            "verdict": verdict,
            "summary": summary,
            "body_preview": comment["body"][:500]
        })
    
    # Update state with ALL current IDs
    save_state({
        "comment_ids": [c["id"] for c in comments],
        "last_check": datetime.now(timezone.utc).isoformat()
    })
    
    print(f"\nState saved. {len(new_comments)} new, {len(comments)} total known.")

if __name__ == "__main__":
    main()
