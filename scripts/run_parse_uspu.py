import json
import os
from app.generator.uspu_parser import uspu_parser

os.makedirs('data', exist_ok=True)
print("Parsing USPU schedule for groups ['АИ-2431', 'АИ-2331']...")
req = uspu_parser.parse_groups(group_names=['АИ-2431', 'АИ-2331'], pin_ratio=0.25)

print(f"Parsed successfully:")
print(f"  - Slots: {len(req.slots)}")
print(f"  - Rooms: {len(req.rooms)}")
print(f"  - Teachers: {len(req.teachers)}")
print(f"  - Atomic groups: {len(req.atomic_groups)}")
print(f"  - Lessons: {len(req.lessons)}")

filepath = 'data/uspu_schedule.json'
with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(req.model_dump(mode='json'), f, ensure_ascii=False, indent=2)

print(f"Saved USPU schedule dataset to {filepath} ({os.path.getsize(filepath)} bytes)")
