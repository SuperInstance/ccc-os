#!/usr/bin/env python3
"""
Fleet Health Autopilot
Runs lightweight health check every 5 minutes.
Alerts ONLY on state changes (up→down or down→up).
"""

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("/root/.openclaw/workspace/ccc-os/health/last_health.json")
LOG_FILE = Path("/root/.openclaw/workspace/ccc-os/health/health_log.jsonl")

SERVICES = [
    ("MUD", "147.224.38.131", 4042, "/status"),
    ("Arena", "147.224.38.131", 4044, "/status"),
    ("Grammar", "147.224.38.131", 4045, "/status"),
    ("PLATO Gate", "147.224.38.131", 8847, "/status"),
    ("PLATO Shell", "147.224.38.131", 8848, "/"),
    ("Rate-Attention", "147.224.38.131", 4056, "/status"),
    ("Skill Forge", "147.224.38.131", 4057, "/status"),
    ("Matrix Bridge", "147.224.38.131", 6168, "/status"),
]

def probe(name, host, port, path):
    try:
        req = urllib.request.Request(f"http://{host}:{port}{path}", method="HEAD")
        req.add_header("User-Agent", "ccc-health/1.0")
        resp = urllib.request.urlopen(req, timeout=5)
        return {"name": name, "status": "UP", "code": resp.status}
    except Exception as e:
        return {"name": name, "status": "DOWN", "error": str(e)[:80]}

def run_health_check():
    results = [probe(*s) for s in SERVICES]
    up = sum(1 for r in results if r["status"] == "UP")
    return {"services": results, "up": up, "total": len(results)}

def load_last():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"services": []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_event(event):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Health check...")
    current = run_health_check()
    last = load_last()
    last_map = {s["name"]: s["status"] for s in last.get("services", [])}
    
    changes = []
    for svc in current["services"]:
        prev = last_map.get(svc["name"])
        if prev and prev != svc["status"]:
            changes.append({
                "name": svc["name"],
                "from": prev,
                "to": svc["status"],
                "details": svc.get("error", ""),
            })
    
    if changes:
        print(f"\n⚠️ STATE CHANGES: {len(changes)}")
        for c in changes:
            icon = "🟢" if c["to"] == "UP" else "🔴"
            print(f"{icon} {c['name']}: {c['from']} → {c['to']}")
            if c["details"]:
                print(f"   {c['details']}")
        log_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "state_change",
            "changes": changes,
            "up": current["up"],
            "total": current["total"],
        })
    else:
        print(f"No changes. {current['up']}/{current['total']} UP.")
    
    save_state(current)

if __name__ == "__main__":
    main()
