#!/usr/bin/env python3
"""Restore Chinese names and sectors in stocks.json."""
import json, subprocess, sys
from pathlib import Path

STOCKS_FILE = Path(__file__).resolve().parent.parent / "docs" / "data" / "stocks.json"

# Get original names from git
try:
    result = subprocess.run(
        ["git", "show", "HEAD:docs/data/stocks.json"],
        capture_output=True, text=True, encoding="utf-8",
        cwd=Path(__file__).resolve().parent.parent
    )
    git_data = json.loads(result.stdout)
    name_map = {}
    for s in git_data["stocks"]:
        name_map[s["symbol"]] = (s.get("name", s["symbol"]), s.get("sector", "Other"))
    print("Loaded name map from git:")
    for sym, (name, sector) in name_map.items():
        print(f"  {sym}: {name} [{sector}]")
except Exception as e:
    print(f"Failed to load from git: {e}")
    sys.exit(1)

# Load current stocks.json
with open(STOCKS_FILE, encoding="utf-8") as f:
    data = json.load(f)

# Apply names from git
for s in data["stocks"]:
    sym = s["symbol"]
    if sym in name_map:
        s["name"] = name_map[sym][0]
        s["sector"] = name_map[sym][1]
        print(f"  Fixed: {sym} -> {s['name']} [{s['sector']}]")

# Save
with open(STOCKS_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(data['stocks'])} stocks to {STOCKS_FILE}")
