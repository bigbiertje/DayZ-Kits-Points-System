#!/usr/bin/env python3
"""Small offline checker for worker config files and local profile paths."""
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
workers = base / "05_WORKERS"

for name in ["points_events_worker_config.json", "points_special_kits_worker_config.json"]:
    p = workers / name
    print(f"
Checking {p}")
    if not p.exists():
        print("  MISSING")
        continue
    cfg = json.loads(p.read_text(encoding="utf-8"))
    print("  OK JSON")
    secret = cfg.get("website_api_secret", "")
    if not secret or secret == "CHANGE_THIS_POINTS_SECRET":
        print("  WARNING: API secret still uses the placeholder")
    if "point_event_paths" in cfg:
        for key, path in cfg["point_event_paths"].items():
            print(f"  PointEvents {key}: {path} -> {'FOUND' if Path(path).exists() else 'NOT FOUND YET'}")
    if "servers" in cfg:
        for key, path in cfg["servers"].items():
            print(f"  Server {key}: {path} -> {'FOUND' if Path(path).exists() else 'NOT FOUND YET'}")
