#!/usr/bin/env python3
"""
ZC Feed Monitor
Reads zeroclaw agent logs from oracle1-workspace/data/zeroclaw/logs/
Tracks new entries, extracts summaries, triages for relevance.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/root/.openclaw/workspace/oracle1-workspace/data/zeroclaw/logs")
STATE_FILE = Path("/root/.openclaw/workspace/ccc-os/monitors/zc_last_state.json")
OUTPUT_LOG = Path("/root/.openclaw/workspace/ccc-os/monitors/zc_monitor_log.jsonl")

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fleet_bridge import FleetBridgeLogger

BRIDGE = FleetBridgeLogger(OUTPUT_LOG, source="ccc-os/zc-monitor")

def log_event(event):
    BRIDGE.log_event(event)

def get_last_tick(filepath):
    """Get the highest tick number from a jsonl file."""
    max_tick = 0
    try:
        with open(filepath) as f:
            for line in f:
                data = json.loads(line)
                tick = data.get("tick", 0)
                if tick > max_tick:
                    max_tick = tick
    except:
        pass
    return max_tick

def get_entries_since(filepath, min_tick):
    """Get all entries with tick > min_tick."""
    entries = []
    try:
        with open(filepath) as f:
            for line in f:
                data = json.loads(line)
                if data.get("tick", 0) > min_tick:
                    entries.append(data)
    except:
        pass
    return entries

def summarize_entry(entry):
    """Extract a brief summary from a ZC entry."""
    agent = entry.get("agent", "unknown")
    topic = entry.get("topic", "unknown")
    question = entry.get("question", "")[:120]
    tick = entry.get("tick", 0)
    return {
        "agent": agent,
        "topic": topic,
        "tick": tick,
        "question_preview": question,
        "timestamp": entry.get("timestamp", ""),
    }

def triage_topic(topic):
    """Triage ZC topics by fleet relevance."""
    high_relevance = [
        "flux", "isa", "vm", "compiler", "verification",
        "safety", "certification", "asil", "constraint",
        "gpu", "cuda", "avx", "performance", "benchmark",
        "architecture", "protocol", "bridge", "nexus",
    ]
    medium_relevance = [
        "shell", "room", "mud", "plato", "tile", "gate",
        "agent", "spawn", "memory", "learning",
    ]
    topic_lower = topic.lower()
    for keyword in high_relevance:
        if keyword in topic_lower:
            return "ACT_NOW"
    for keyword in medium_relevance:
        if keyword in topic_lower:
            return "TRACK"
    return "IGNORE"

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] ZC Feed Monitor starting...")
    
    if not LOG_DIR.exists():
        print(f"ERROR: ZC log dir not found: {LOG_DIR}")
        return
    
    state = load_state()
    total_new = 0
    
    for log_file in sorted(LOG_DIR.glob("zc-*.jsonl")):
        agent_name = log_file.stem  # e.g., "zc-scout"
        last_tick = state.get(agent_name, 0)
        current_tick = get_last_tick(log_file)
        
        if current_tick <= last_tick:
            continue
        
        # Detect new agent spawn
        is_new_agent = agent_name not in state or last_tick == 0
        new_entries = get_entries_since(log_file, last_tick)
        if not new_entries:
            continue
        
        # Only process the most recent entry per agent (to avoid flooding)
        latest = new_entries[-1]
        summary = summarize_entry(latest)
        verdict = triage_topic(summary["topic"])
        
        print(f"\n{agent_name}: {len(new_entries)} new entries (tick {last_tick} → {current_tick})")
        print(f"  Latest: [{verdict}] {summary['topic']} — {summary['question_preview'][:80]}...")
        
        if is_new_agent:
            BRIDGE.emit("AGENT_SPAWN", {
                "agent": agent_name,
                "first_tick": current_tick,
                "topic": summary["topic"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        BRIDGE.emit("AGENT_STATUS", {
            "agent": agent_name,
            "tick": current_tick,
            "topic": summary["topic"],
            "verdict": verdict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        log_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "last_tick": last_tick,
            "current_tick": current_tick,
            "new_count": len(new_entries),
            "latest_summary": summary,
            "verdict": verdict,
        })
        
        state[agent_name] = current_tick
        total_new += len(new_entries)
    
    save_state(state)
    
    if total_new:
        print(f"\nTotal new entries: {total_new}")
    else:
        print("No new ZC entries.")
    
    print(f"State saved. Monitoring {len(list(LOG_DIR.glob('zc-*.jsonl')))} agents.")

if __name__ == "__main__":
    main()
