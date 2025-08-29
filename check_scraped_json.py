#!/usr/bin/env python3
import json

with open('data/opportunities_20250829_144540.json') as f:
    data = json.load(f)

showsubmit = [o for o in data if o.get('source_platform') == 'showsubmit']

print(f"Found {len(showsubmit)} ShowSubmit opportunities in JSON\n")

for i, opp in enumerate(showsubmit[:3], 1):
    print(f"[{i}] {opp.get('title')}")
    print(f"    location: {opp.get('location')}")
    desc = opp.get('description', '')
    if desc:
        print(f"    description length: {len(desc)}")
        print(f"    description: {desc[:200]}...")
    else:
        print(f"    description: None or empty")
    print()