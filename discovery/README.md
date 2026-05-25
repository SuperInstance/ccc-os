# Node Discovery

CCC-OS nodes discover each other through the fleet bridge (`fleet_bridge.jsonl`).

Each node writes its status to the shared bridge file. Other nodes read it to build a
live view of the fleet.

## Discovery Protocol

1. Node starts and writes its identity + capabilities to the bridge
2. Node polls the bridge every 15 minutes for new nodes
3. Node maintains a local peer list

See `docs/SCALING.md` for full multi-node configuration.
