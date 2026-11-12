import json
import os
from pathlib import Path
from app.api.schemas import SolveRequest
from app.generator.uspu_parser import uspu_parser


def test_uspu_parser_output_structure():
    base_dir = Path(__file__).resolve().parent.parent
    uspu_path = base_dir / "data" / "uspu_schedule.json"
    if not uspu_path.exists():
        uspu_path = Path("data/uspu_schedule.json")
    assert uspu_path.exists(), f"Файл {uspu_path} должен существовать"

    with open(uspu_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    req = SolveRequest.model_validate(data)
    assert len(req.slots) == 42  # 6 days * 7 slots
    assert len(req.rooms) > 0
    assert len(req.teachers) > 0
    assert len(req.lessons) > 0
    assert any(l.pinned for l in req.lessons), "Должны присутствовать зафиксированные пары"
    assert any(len(r.features) > 0 for r in req.rooms), "У аудиторий должны быть распознаны фичи"
    assert all(s.start_time is not None and s.end_time is not None for s in req.slots)
    slot1 = next(s for s in req.slots if s.slot_number == 1)
    assert slot1.start_time == "08:30"
    assert slot1.end_time == "10:00"
