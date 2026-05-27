#!/usr/bin/env python3
"""Quick test: verify CCC breeder monitor fires alerts on critical values."""
import sys

sys.path.insert(0, "/root/.openclaw/workspace/ccc-os")
from monitors.breeder_monitor import BreederMonitor

# Test 1: Healthy
m = BreederMonitor()
result = m.run()
assert result["act_count"] == 0, "Healthy state should have no ACT"
print("✅ Test 1: Healthy → no alerts")

# Test 2: Critical diversity
class FakeBreeder:
    vector_table = None
    thermal_pressure = 0.3
    active_agents = [1, 2]
    state = "COMPETE"

m2 = BreederMonitor()
m2._synthetic_status = lambda: {
    "source": "synthetic",
    "diversity": 0.15,
    "thermal_pressure": 0.3,
    "active_agents": 12,
    "lifecycle_state": "COMPETE",
    "timestamp": 0,
}
result2 = m2.run()
assert result2["act_count"] >= 1 or "TELL_NOW" in result2["verdicts"].values(), "Critical diversity should trigger ACT or TELL_NOW"
print(f"✅ Test 2: Critical diversity → ACT={result2['act_count']}, verdicts={result2['verdicts']}")

# Test 3: Critical thermal
m3 = BreederMonitor()
m3._synthetic_status = lambda: {
    "source": "synthetic",
    "diversity": 0.85,
    "thermal_pressure": 0.95,
    "active_agents": 12,
    "lifecycle_state": "COMPETE",
    "timestamp": 0,
}
result3 = m3.run()
assert result3["act_count"] >= 1 or "TELL_NOW" in result3["verdicts"].values(), "Critical thermal should trigger ACT or TELL_NOW"
print(f"✅ Test 3: Critical thermal → ACT={result3['act_count']}, verdicts={result3['verdicts']}")

print("\nAll CCC breeder monitor tests passed.")
